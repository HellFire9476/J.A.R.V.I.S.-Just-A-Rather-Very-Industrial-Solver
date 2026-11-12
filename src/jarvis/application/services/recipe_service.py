"""Interprétation métier des recettes contenues dans le catalogue Satisfactory."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from jarvis.config.paths import CATALOG_DIR
from jarvis.domain.entities.recipe import (
    Recipe,
    RecipeComponent,
    RecipeProducer,
)
from jarvis.infrastructure.persistence.catalog_repository import CatalogRepository


class RecipeFormatError(ValueError):
    """Une propriété de recette ne respecte pas la structure attendue."""


_COMPONENT_PATTERN = re.compile(
    r'ItemClass="(?P<path>[^"]+)"\s*,\s*Amount=(?P<amount>-?\d+(?:\.\d+)?)'
)
_QUOTED_PATH_PATTERN = re.compile(r'"(?P<path>[^"]+)"')

_SPECIAL_PRODUCERS = {
    "BP_BuildGun_C": ("Pistolet de construction", "construction"),
    "FGBuildGun": ("Pistolet de construction", "construction"),
    "BP_WorkBenchComponent_C": ("Établi", "workbench"),
    "BP_WorkshopComponent_C": ("Atelier", "workshop"),
    "Build_AutomatedWorkBench_C": ("Établi automatisé", "workbench"),
}
_IGNORED_PRODUCERS = {
    "FGBuildableAutomatedWorkBench",
}


class RecipeService:
    """Construit des recettes lisibles à partir du dépôt du catalogue JSON."""

    def __init__(
        self,
        catalog_dir: str | Path = CATALOG_DIR,
        *,
        repository: CatalogRepository | None = None,
    ) -> None:
        self.repository = repository or CatalogRepository(catalog_dir)
        self._building_component_aliases: dict[str, tuple[str, str]] = {}
        self._aliases_locale: str | None = None

    @property
    def is_initialized(self) -> bool:
        return self.repository.is_initialized

    def list_locales(self) -> list[str]:
        return self.repository.list_locales()

    def get_catalog_summary(self) -> dict[str, int | list[str]]:
        return self.repository.get_summary()

    def list_recipes(self, locale: str) -> list[Recipe]:
        """Retourne toutes les recettes, triées selon leur nom affiché."""

        if not self.repository.is_initialized:
            return []

        self._prepare_building_component_aliases(locale)
        recipes: list[Recipe] = []
        for class_name in self.repository.list_classes("FGRecipe"):
            record = self.repository.get_class(class_name)
            if record is None:
                continue
            properties = record.get("properties", {})
            recipes.append(self._build_recipe(class_name, properties, locale))

        return sorted(
            recipes,
            key=lambda recipe: (recipe.display_name.casefold(), recipe.class_name),
        )

    def _build_recipe(
        self,
        class_name: str,
        properties: dict[str, Any],
        locale: str,
    ) -> Recipe:
        ingredients = self._parse_components(
            class_name,
            properties.get("mIngredients", ""),
            locale,
            "mIngredients",
        )
        products = self._parse_components(
            class_name,
            properties.get("mProduct", ""),
            locale,
            "mProduct",
        )
        duration = self._parse_duration(
            class_name,
            properties.get("mManufactoringDuration", "0"),
        )
        producers = self._parse_producers(
            properties.get("mProducedIn", ""),
            locale,
        )
        recipe_type = self._resolve_recipe_type(producers)

        return Recipe(
            class_name=class_name,
            display_name=self.repository.get_display_name(class_name, locale),
            duration_seconds=duration,
            ingredients=ingredients,
            products=products,
            producers=producers,
            recipe_type=recipe_type,
            description=self.repository.get_description(class_name, locale),
        )

    def _parse_components(
        self,
        recipe_class: str,
        raw_value: Any,
        locale: str,
        property_name: str,
    ) -> tuple[RecipeComponent, ...]:
        if raw_value in (None, "", "()"):
            return ()
        if not isinstance(raw_value, str):
            raise RecipeFormatError(
                f"{recipe_class}.{property_name} doit être une chaîne de caractères."
            )

        components: list[RecipeComponent] = []
        for match in _COMPONENT_PATTERN.finditer(raw_value):
            component_class = self._class_name_from_path(match.group("path"))
            try:
                amount = Decimal(match.group("amount"))
            except InvalidOperation as exc:
                raise RecipeFormatError(
                    f"Quantité invalide dans {recipe_class}.{property_name}."
                ) from exc
            if amount < 0:
                raise RecipeFormatError(
                    f"Quantité négative dans {recipe_class}.{property_name}."
                )
            record = self.repository.get_class(component_class) or {}
            component_properties = record.get("properties", {})
            form = str(component_properties.get("mForm", "RF_INVALID"))
            display_name = self.repository.get_display_name(
                component_class,
                locale,
            )
            description = self.repository.get_description(component_class, locale)

            # Les descripteurs de bâtiments n'ont volontairement pas de nom ni
            # de description dans l'export. Leur recette de construction porte
            # le nom traduit, et la classe Build_* porte généralement le texte.
            if display_name == component_class:
                alias = self._building_component_aliases.get(component_class)
                if alias is not None:
                    display_name = alias[0]
                    description = description or alias[1]

            normalized_amount = amount / Decimal("1000") if form in {
                "RF_LIQUID",
                "RF_GAS",
            } else amount
            components.append(
                RecipeComponent(
                    class_name=component_class,
                    display_name=display_name,
                    amount=normalized_amount,
                    form=form,
                    description=description,
                    source_amount=amount,
                )
            )

        if not components:
            raise RecipeFormatError(
                f"Structure non reconnue dans {recipe_class}.{property_name} : "
                f"{raw_value[:120]!r}."
            )
        return tuple(components)

    @staticmethod
    def _parse_duration(recipe_class: str, raw_value: Any) -> Decimal:
        try:
            duration = Decimal(str(raw_value))
        except InvalidOperation as exc:
            raise RecipeFormatError(
                f"Durée invalide pour la recette {recipe_class} : {raw_value!r}."
            ) from exc
        if duration < 0:
            raise RecipeFormatError(
                f"Durée négative pour la recette {recipe_class}."
            )
        return duration

    def _parse_producers(
        self,
        raw_value: Any,
        locale: str,
    ) -> tuple[RecipeProducer, ...]:
        if not isinstance(raw_value, str) or not raw_value:
            return ()

        producers: list[RecipeProducer] = []
        seen: set[str] = set()
        for match in _QUOTED_PATH_PATTERN.finditer(raw_value):
            class_name = self._class_name_from_path(match.group("path"))
            if class_name in seen or class_name in _IGNORED_PRODUCERS:
                continue
            seen.add(class_name)

            special = _SPECIAL_PRODUCERS.get(class_name)
            record = self.repository.get_class(class_name)
            if special is not None:
                fallback_name, producer_type = special
                display_name = (
                    self.repository.get_display_name(class_name, locale)
                    if record is not None
                    else fallback_name
                )
                if display_name == class_name:
                    display_name = fallback_name
                description = self.repository.get_description(class_name, locale)
                producers.append(
                    RecipeProducer(
                        class_name,
                        display_name,
                        producer_type,
                        description,
                    )
                )
                continue

            if record is None:
                continue
            native_class = str(record.get("native_class", ""))
            if not native_class.startswith("FGBuildableManufacturer"):
                continue
            producers.append(
                RecipeProducer(
                    class_name=class_name,
                    display_name=self.repository.get_display_name(
                        class_name,
                        locale,
                    ),
                    producer_type="manufacturer",
                    description=self.repository.get_description(class_name, locale),
                )
            )

        return tuple(producers)

    def _prepare_building_component_aliases(self, locale: str) -> None:
        """Résout les noms et descriptions des sorties de type bâtiment."""

        if self._aliases_locale == locale:
            return

        aliases: dict[str, tuple[str, str]] = {}
        for recipe_class in self.repository.list_classes("FGRecipe"):
            record = self.repository.get_class(recipe_class)
            if record is None:
                continue
            raw_products = record.get("properties", {}).get("mProduct", "")
            if not isinstance(raw_products, str) or not raw_products:
                continue

            recipe_name = self.repository.get_display_name(recipe_class, locale)
            if not recipe_name or recipe_name == recipe_class:
                continue

            for match in _COMPONENT_PATTERN.finditer(raw_products):
                component_class = self._class_name_from_path(match.group("path"))
                component_record = self.repository.get_class(component_class)
                if component_record is None:
                    continue
                if component_record.get("native_class") != "FGBuildingDescriptor":
                    continue

                build_class = f"Build_{component_class.removeprefix('Desc_')}"
                build_record = self.repository.get_class(build_class)
                build_description = (
                    self.repository.get_description(build_class, locale)
                    if build_record is not None
                    else ""
                )
                aliases.setdefault(
                    component_class,
                    (recipe_name, build_description),
                )

        self._building_component_aliases = aliases
        self._aliases_locale = locale

    @staticmethod
    def _class_name_from_path(value: str) -> str:
        """Extrait le nom de classe Unreal final d'un chemin d'objet."""

        leaf = value.rsplit("/", 1)[-1]
        if "." in leaf:
            leaf = leaf.rsplit(".", 1)[-1]
        return leaf.strip("'\" ")

    @staticmethod
    def _resolve_recipe_type(producers: tuple[RecipeProducer, ...]) -> str:
        producer_types = {producer.producer_type for producer in producers}
        if "construction" in producer_types:
            return "construction"
        if "manufacturer" in producer_types:
            return "production"
        if "workshop" in producer_types:
            return "workshop"
        if "workbench" in producer_types:
            return "workbench"
        return "unknown"
