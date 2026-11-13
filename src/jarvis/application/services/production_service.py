"""Préparation des données du catalogue pour le moteur de production."""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path

from jarvis.application.services.recipe_service import RecipeService
from jarvis.config.paths import CATALOG_DIR
from jarvis.domain.entities.production import (
    ExtractorProfile,
    ItemProfile,
    MachineProfile,
    ProductionPlan,
)
from jarvis.engines.production_engine import ProductionEngine
from jarvis.infrastructure.persistence.catalog_repository import CatalogRepository


class ProductionCatalogError(ValueError):
    """Une donnée technique du catalogue ne peut pas être interprétée."""


_QUOTED_PATH_PATTERN = re.compile(r'"(?P<path>[^"]+)"')
_FORM_PATTERN = re.compile(r"RF_[A-Z]+")
_EXTRACTOR_NATIVE_CLASSES = frozenset(
    {
        "FGBuildableResourceExtractor",
        "FGBuildableWaterPump",
        "FGBuildableFrackingExtractor",
    }
)


class ProductionService:
    """Expose une API applicative indépendante de la couche graphique."""

    def __init__(
        self,
        catalog_dir: str | Path = CATALOG_DIR,
        *,
        recipe_service: RecipeService | None = None,
        repository: CatalogRepository | None = None,
    ) -> None:
        if recipe_service is not None:
            self.recipe_service = recipe_service
            self.repository = recipe_service.repository
        else:
            self.repository = repository or CatalogRepository(catalog_dir)
            self.recipe_service = RecipeService(
                catalog_dir,
                repository=self.repository,
            )

    def plan_production(
        self,
        *,
        target_class_name: str,
        target_rate_per_minute: Decimal | int | float | str,
        locale: str = "fr",
        recipe_choices: Mapping[str, str] | None = None,
        producer_choices: Mapping[str, str] | None = None,
        extractor_choices: Mapping[str, str] | None = None,
        resource_node_multipliers: Mapping[str, Decimal | int | float | str] | None = None,
    ) -> ProductionPlan:
        """Calcule un objectif en objets/min ou m³/min."""

        if not self.repository.is_initialized:
            raise FileNotFoundError(
                "Le catalogue Satisfactory n'est pas installé. Importez d'abord un export."
            )

        recipes = self.recipe_service.list_recipes(locale)
        item_profiles = self._build_item_profiles(recipes, locale)
        machine_profiles = self._build_machine_profiles(recipes, locale)
        extractor_profiles = self._build_extractor_profiles(locale, item_profiles)
        engine = ProductionEngine(
            recipes=recipes,
            item_profiles=item_profiles,
            machine_profiles=machine_profiles,
            extractor_profiles=extractor_profiles,
        )
        return engine.plan(
            target_class_name=target_class_name,
            target_rate_per_minute=target_rate_per_minute,
            locale=locale,
            recipe_choices=recipe_choices,
            producer_choices=producer_choices,
            extractor_choices=extractor_choices,
            resource_node_multipliers=resource_node_multipliers,
        )

    def list_recipe_options(self, item_class_name: str, locale: str = "fr"):
        """Retourne les recettes candidates pour alimenter un futur sélecteur."""

        return tuple(
            recipe
            for recipe in self.recipe_service.list_recipes(locale)
            if any(product.class_name == item_class_name for product in recipe.products)
        )

    def _build_item_profiles(self, recipes, locale: str) -> dict[str, ItemProfile]:
        item_classes = {
            component.class_name
            for recipe in recipes
            for component in (*recipe.ingredients, *recipe.products)
        }
        item_classes.update(self.repository.list_classes("FGResourceDescriptor"))
        profiles: dict[str, ItemProfile] = {}
        for class_name in item_classes:
            record = self.repository.get_class(class_name)
            if record is None:
                continue
            properties = record.get("properties", {})
            profiles[class_name] = ItemProfile(
                class_name=class_name,
                display_name=self.repository.get_display_name(class_name, locale),
                form=str(properties.get("mForm", "RF_INVALID")),
                native_class=str(record.get("native_class", "")),
                description=self.repository.get_description(class_name, locale),
            )
        return profiles

    def _build_machine_profiles(self, recipes, locale: str) -> dict[str, MachineProfile]:
        class_names = {
            producer.class_name
            for recipe in recipes
            for producer in recipe.producers
            if producer.producer_type == "manufacturer"
        }
        profiles: dict[str, MachineProfile] = {}
        for class_name in class_names:
            record = self.repository.get_class(class_name)
            if record is None:
                continue
            if not str(record.get("native_class", "")).startswith(
                "FGBuildableManufacturer"
            ):
                continue
            properties = record.get("properties", {})
            base_power = self._decimal(properties, "mPowerConsumption", Decimal("0"))
            estimated_min = self._optional_decimal(
                properties,
                "mEstimatedMininumPowerConsumption",
            )
            estimated_max = self._optional_decimal(
                properties,
                "mEstimatedMaximumPowerConsumption",
            )
            profiles[class_name] = MachineProfile(
                class_name=class_name,
                display_name=self.repository.get_display_name(class_name, locale),
                manufacturing_speed=self._decimal(
                    properties,
                    "mManufacturingSpeed",
                    Decimal("1"),
                ),
                fixed_power_mw=base_power if base_power > 0 else None,
                power_exponent=self._decimal(
                    properties,
                    "mPowerConsumptionExponent",
                    Decimal("1.321929"),
                ),
                estimated_power_min_mw=estimated_min,
                estimated_power_max_mw=estimated_max,
                minimum_clock_fraction=self._decimal(
                    properties,
                    "mMinPotential",
                    Decimal("0.01"),
                ),
                maximum_clock_fraction=self._decimal(
                    properties,
                    "mMaxPotential",
                    Decimal("1"),
                ),
            )
        return profiles

    def _build_extractor_profiles(
        self,
        locale: str,
        item_profiles: Mapping[str, ItemProfile],
    ) -> tuple[ExtractorProfile, ...]:
        profiles: list[ExtractorProfile] = []
        for class_name in self.repository.list_classes():
            record = self.repository.get_class(class_name)
            if record is None:
                continue
            native_class = str(record.get("native_class", ""))
            if native_class not in _EXTRACTOR_NATIVE_CLASSES:
                continue

            properties = record.get("properties", {})
            cycle_time = self._decimal(properties, "mExtractCycleTime", Decimal("0"))
            items_per_cycle = self._decimal(properties, "mItemsPerCycle", Decimal("0"))
            if cycle_time <= 0 or items_per_cycle <= 0:
                continue

            allowed_forms = frozenset(
                _FORM_PATTERN.findall(str(properties.get("mAllowedResourceForms", "")))
            )
            allowed_resource_classes = frozenset(
                self._class_name_from_path(match.group("path"))
                for match in _QUOTED_PATH_PATTERN.finditer(
                    str(properties.get("mAllowedResources", ""))
                )
            )
            restricted = str(
                properties.get("mOnlyAllowCertainResources", "False")
            ).casefold() == "true"

            compatible_forms = {
                item.form
                for item in item_profiles.values()
                if item.is_game_resource
                and item.form in allowed_forms
                and (
                    not restricted
                    or item.class_name in allowed_resource_classes
                )
            }
            if not compatible_forms:
                continue

            rate_per_minute = items_per_cycle * Decimal("60") / cycle_time
            if compatible_forms.issubset({"RF_LIQUID", "RF_GAS"}):
                rate_per_minute /= Decimal("1000")
            base_power = self._decimal(properties, "mPowerConsumption", Decimal("0"))
            profiles.append(
                ExtractorProfile(
                    class_name=class_name,
                    display_name=self.repository.get_display_name(class_name, locale),
                    base_rate_per_minute=rate_per_minute,
                    form=next(iter(compatible_forms)) if len(compatible_forms) == 1 else "RF_MIXED",
                    allowed_forms=allowed_forms,
                    allowed_resource_classes=allowed_resource_classes,
                    restricted_resources=restricted,
                    node_based=native_class == "FGBuildableResourceExtractor",
                    requires_resource_well=native_class == "FGBuildableFrackingExtractor",
                    fixed_power_mw=base_power if base_power > 0 else None,
                    power_exponent=self._decimal(
                        properties,
                        "mPowerConsumptionExponent",
                        Decimal("1.321929"),
                    ),
                    estimated_power_min_mw=self._optional_decimal(
                        properties,
                        "mEstimatedMininumPowerConsumption",
                    ),
                    estimated_power_max_mw=self._optional_decimal(
                        properties,
                        "mEstimatedMaximumPowerConsumption",
                    ),
                )
            )
        return tuple(profiles)

    @staticmethod
    def _class_name_from_path(value: str) -> str:
        leaf = value.rsplit("/", 1)[-1]
        if "." in leaf:
            leaf = leaf.rsplit(".", 1)[-1]
        return leaf.strip("'\" ")

    @staticmethod
    def _decimal(
        properties: Mapping[str, object],
        name: str,
        default: Decimal,
    ) -> Decimal:
        value = properties.get(name)
        if value in (None, ""):
            return default
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ProductionCatalogError(
                f"Valeur numérique invalide pour {name} : {value!r}."
            ) from exc
        if not result.is_finite():
            raise ProductionCatalogError(f"Valeur non finie pour {name}.")
        return result

    @classmethod
    def _optional_decimal(
        cls,
        properties: Mapping[str, object],
        name: str,
    ) -> Decimal | None:
        if properties.get(name) in (None, ""):
            return None
        return cls._decimal(properties, name, Decimal("0"))
