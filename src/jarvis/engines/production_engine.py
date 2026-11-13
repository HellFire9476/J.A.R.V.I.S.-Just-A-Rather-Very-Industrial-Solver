"""Moteur pur de décomposition récursive des besoins de production.

Ce module ne dépend ni de PySide6, ni du dépôt JSON. Il reçoit des recettes et
profils déjà normalisés, puis calcule les débits, fabricants et extracteurs.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import ROUND_CEILING, Decimal, InvalidOperation

from jarvis.domain.entities.production import (
    ExtractionOption,
    ExtractorProfile,
    ItemProfile,
    MachineProfile,
    MachineRequirement,
    ProductionPlan,
    RateAmount,
    ResourceRequirement,
)
from jarvis.domain.entities.recipe import Recipe

ZERO = Decimal("0")
SIXTY = Decimal("60")


class ProductionCalculationError(ValueError):
    """Erreur empêchant de produire un plan cohérent."""


class UnknownProductionItemError(ProductionCalculationError):
    """La cible ou un composant n'existe pas dans le catalogue chargé."""


class RecipeChoiceRequiredError(ProductionCalculationError):
    """Plusieurs recettes plausibles existent pour un même objet."""

    def __init__(self, item_class: str, recipe_classes: Sequence[str]) -> None:
        self.item_class = item_class
        self.recipe_classes = tuple(recipe_classes)
        options = ", ".join(self.recipe_classes)
        super().__init__(
            f"Un choix de recette est nécessaire pour {item_class}. "
            f"Recettes disponibles : {options}."
        )


class InvalidRecipeChoiceError(ProductionCalculationError):
    """La recette choisie ne produit pas l'objet demandé."""


class ProducerChoiceRequiredError(ProductionCalculationError):
    """Plusieurs fabricants automatisés peuvent exécuter une recette."""


class NonAutomatableRecipeError(ProductionCalculationError):
    """La recette choisie ne possède pas de fabricant automatisé reconnu."""


class ProductionCycleError(ProductionCalculationError):
    """Une dépendance circulaire empêche la décomposition récursive."""


class InvalidProductionRateError(ProductionCalculationError):
    """Le débit cible ou une valeur technique est invalide."""


class InvalidExtractorChoiceError(ProductionCalculationError):
    """L'extracteur choisi ne peut pas fournir la ressource."""


class ProductionEngine:
    """Calcule les besoins d'une cible à partir des recettes Satisfactory.

    Les recettes alternatives sont sélectionnées explicitement lorsqu'aucune
    recette standard unique ne peut être déterminée. Les ressources natives
    (FGResourceDescriptor) restent des entrées brutes par défaut, même si le
    catalogue contient également des recettes capables de les fabriquer.

    Les coproduits sont comptabilisés et présentés, mais ne compensent pas encore
    les besoins d'une autre branche. Le bilan multi-sorties sera traité dans une
    étape d'optimisation dédiée.
    """

    def __init__(
        self,
        *,
        recipes: Sequence[Recipe],
        item_profiles: Mapping[str, ItemProfile],
        machine_profiles: Mapping[str, MachineProfile],
        extractor_profiles: Sequence[ExtractorProfile] = (),
    ) -> None:
        self.recipes = tuple(recipes)
        self.item_profiles = dict(item_profiles)
        self.machine_profiles = dict(machine_profiles)
        self.extractor_profiles = tuple(extractor_profiles)
        self._recipes_by_product: dict[str, list[Recipe]] = defaultdict(list)
        for recipe in self.recipes:
            for product in recipe.products:
                self._recipes_by_product[product.class_name].append(recipe)

    def plan(
        self,
        *,
        target_class_name: str,
        target_rate_per_minute: Decimal | int | float | str,
        locale: str,
        recipe_choices: Mapping[str, str] | None = None,
        producer_choices: Mapping[str, str] | None = None,
        extractor_choices: Mapping[str, str] | None = None,
        resource_node_multipliers: Mapping[str, Decimal | int | float | str] | None = None,
    ) -> ProductionPlan:
        """Décompose un débit cible en recettes, matières premières et machines."""

        target_rate = self._positive_decimal(
            target_rate_per_minute,
            "Le débit cible doit être strictement positif.",
        )
        if target_class_name not in self.item_profiles:
            raise UnknownProductionItemError(
                f"Objet inconnu dans le catalogue : {target_class_name}."
            )

        recipe_choices = recipe_choices or {}
        producer_choices = producer_choices or {}
        extractor_choices = extractor_choices or {}
        resource_node_multipliers = resource_node_multipliers or {}

        self._recipe_cycles: dict[str, Decimal] = defaultdict(lambda: ZERO)
        self._selected_recipes: dict[str, Recipe] = {}
        self._selected_producers: dict[str, MachineProfile] = {}
        self._raw_requirements: dict[str, Decimal] = defaultdict(lambda: ZERO)
        self._byproducts: dict[str, Decimal] = defaultdict(lambda: ZERO)
        self._warnings: list[str] = []

        self._expand(
            target_class_name,
            target_rate,
            (),
            recipe_choices,
            producer_choices,
        )

        machine_requirements = self._build_machine_requirements()
        resource_requirements = self._build_resource_requirements(
            extractor_choices,
            resource_node_multipliers,
        )
        if self._byproducts:
            self._warnings.append(
                "Les coproduits sont recensés séparément et ne réduisent pas encore "
                "les besoins d'autres branches du calcul."
            )
        byproducts = self._build_rate_amounts(self._byproducts)

        production_min, production_max, production_complete = self._sum_power(
            machine_requirements
        )
        extraction_min, extraction_max, extraction_complete = self._sum_extraction_power(
            resource_requirements
        )
        complete = production_complete and extraction_complete
        total_min = production_min + extraction_min if complete else None
        total_max = production_max + extraction_max if complete else None

        target_profile = self.item_profiles[target_class_name]
        return ProductionPlan(
            target_class_name=target_class_name,
            target_name=target_profile.display_name,
            target_rate_per_minute=target_rate,
            target_unit_label=target_profile.unit_label,
            locale=locale,
            machine_requirements=machine_requirements,
            resource_requirements=resource_requirements,
            byproducts=byproducts,
            production_power_min_mw=production_min,
            production_power_max_mw=production_max,
            extraction_power_min_mw=extraction_min,
            extraction_power_max_mw=extraction_max,
            total_power_min_mw=total_min,
            total_power_max_mw=total_max,
            power_estimate_complete=complete,
            warnings=tuple(dict.fromkeys(self._warnings)),
        )

    def _expand(
        self,
        item_class: str,
        required_rate: Decimal,
        ancestry: tuple[str, ...],
        recipe_choices: Mapping[str, str],
        producer_choices: Mapping[str, str],
    ) -> None:
        if required_rate <= ZERO:
            return
        if item_class in ancestry:
            cycle = " -> ".join((*ancestry, item_class))
            raise ProductionCycleError(
                f"Cycle de production détecté : {cycle}."
            )

        item_profile = self.item_profiles.get(item_class)
        if item_profile is None:
            raise UnknownProductionItemError(
                f"Composant absent du catalogue : {item_class}."
            )

        recipe = self._select_recipe(item_profile, recipe_choices)
        if recipe is None:
            self._raw_requirements[item_class] += required_rate
            return

        producer = self._select_producer(recipe, producer_choices)
        product_amount = sum(
            (product.amount for product in recipe.products if product.class_name == item_class),
            ZERO,
        )
        if product_amount <= ZERO:
            raise InvalidProductionRateError(
                "La recette "
                f"{recipe.class_name} ne produit aucune quantité positive "
                f"de {item_class}."
            )
        if recipe.duration_seconds <= ZERO:
            raise InvalidProductionRateError(
                f"La durée de cycle de {recipe.class_name} doit être positive."
            )

        # Le débit est exprimé par minute : le nombre de cycles nécessaires
        # est donc le débit demandé divisé par la quantité produite par cycle.
        # La durée sert ensuite à calculer le nombre de cycles/minute d'une machine.
        cycles_per_minute = required_rate / product_amount
        self._recipe_cycles[recipe.class_name] += cycles_per_minute
        self._selected_recipes[recipe.class_name] = recipe
        self._selected_producers[recipe.class_name] = producer

        for product in recipe.products:
            if product.class_name != item_class:
                self._byproducts[product.class_name] += (
                    product.amount * cycles_per_minute
                )

        next_ancestry = (*ancestry, item_class)
        for ingredient in recipe.ingredients:
            self._expand(
                ingredient.class_name,
                ingredient.amount * cycles_per_minute,
                next_ancestry,
                recipe_choices,
                producer_choices,
            )

    def _select_recipe(
        self,
        item: ItemProfile,
        recipe_choices: Mapping[str, str],
    ) -> Recipe | None:
        candidates = self._recipes_by_product.get(item.class_name, [])
        explicit_choice = recipe_choices.get(item.class_name)

        if explicit_choice:
            selected = next(
                (recipe for recipe in candidates if recipe.class_name == explicit_choice),
                None,
            )
            if selected is None:
                raise InvalidRecipeChoiceError(
                    f"La recette {explicit_choice} ne produit pas {item.class_name}."
                )
            return selected

        if item.is_game_resource:
            return None
        if not candidates:
            return None

        unique_candidates = {recipe.class_name: recipe for recipe in candidates}
        candidates = list(unique_candidates.values())
        if len(candidates) == 1:
            return candidates[0]

        standard = [
            recipe
            for recipe in candidates
            if "alternate" not in recipe.class_name.casefold()
        ]
        if len(standard) == 1:
            return standard[0]

        options = sorted(recipe.class_name for recipe in (standard or candidates))
        raise RecipeChoiceRequiredError(item.class_name, options)

    def _select_producer(
        self,
        recipe: Recipe,
        producer_choices: Mapping[str, str],
    ) -> MachineProfile:
        candidates = [
            self.machine_profiles[producer.class_name]
            for producer in recipe.producers
            if producer.producer_type == "manufacturer"
            and producer.class_name in self.machine_profiles
        ]
        explicit_choice = producer_choices.get(recipe.class_name)
        if explicit_choice:
            selected = next(
                (machine for machine in candidates if machine.class_name == explicit_choice),
                None,
            )
            if selected is None:
                raise ProducerChoiceRequiredError(
                    f"Le fabricant {explicit_choice} ne peut pas exécuter {recipe.class_name}."
                )
            return selected
        if not candidates:
            raise NonAutomatableRecipeError(
                f"La recette {recipe.display_name} ({recipe.class_name}) ne possède "
                "pas de fabricant automatisé reconnu."
            )
        if len(candidates) > 1:
            names = ", ".join(sorted(machine.class_name for machine in candidates))
            raise ProducerChoiceRequiredError(
                f"Plusieurs fabricants sont possibles pour {recipe.class_name} : {names}."
            )
        return candidates[0]

    def _build_machine_requirements(self) -> tuple[MachineRequirement, ...]:
        requirements: list[MachineRequirement] = []
        for recipe_class, cycles_per_minute in sorted(self._recipe_cycles.items()):
            recipe = self._selected_recipes[recipe_class]
            machine = self._selected_producers[recipe_class]
            cycles_per_machine_minute = (
                SIXTY / recipe.duration_seconds * machine.manufacturing_speed
            )
            equivalents = cycles_per_minute / cycles_per_machine_minute
            machine_count = self._ceil_positive(equivalents)
            clock_fraction = equivalents / Decimal(machine_count)
            clock_percent = clock_fraction * Decimal("100")

            recipe_input_rates: dict[str, Decimal] = defaultdict(lambda: ZERO)
            recipe_output_rates: dict[str, Decimal] = defaultdict(lambda: ZERO)
            for ingredient in recipe.ingredients:
                recipe_input_rates[ingredient.class_name] += (
                    ingredient.amount * cycles_per_minute
                )
            for product in recipe.products:
                recipe_output_rates[product.class_name] += (
                    product.amount * cycles_per_minute
                )

            power_min, power_max, power_model = self._machine_power(
                machine,
                machine_count,
                clock_fraction,
            )
            if clock_fraction < machine.minimum_clock_fraction:
                self._warnings.append(
                    f"{machine.display_name} pour {recipe.display_name} nécessite "
                    f"une cadence théorique de {clock_percent}% sous le minimum "
                    "de la machine ; une marche intermittente peut être nécessaire."
                )
            if power_model != "fixed":
                self._warnings.append(
                    f"La consommation électrique de {machine.display_name} "
                    "est variable ou incomplète ; une valeur exacte n'est pas disponible."
                )

            requirements.append(
                MachineRequirement(
                    recipe_class=recipe.class_name,
                    recipe_name=recipe.display_name,
                    producer_class=machine.class_name,
                    producer_name=machine.display_name,
                    cycles_per_minute=cycles_per_minute,
                    machine_equivalents=equivalents,
                    machine_count=machine_count,
                    clock_percent=clock_percent,
                    inputs=self._build_rate_amounts(recipe_input_rates),
                    outputs=self._build_rate_amounts(recipe_output_rates),
                    power_min_mw=power_min,
                    power_max_mw=power_max,
                    power_model=power_model,
                )
            )
        return tuple(requirements)

    def _build_resource_requirements(
        self,
        extractor_choices: Mapping[str, str],
        node_multipliers: Mapping[str, Decimal | int | float | str],
    ) -> tuple[ResourceRequirement, ...]:
        requirements: list[ResourceRequirement] = []
        for item_class, required_rate in sorted(self._raw_requirements.items()):
            item = self.item_profiles[item_class]
            multiplier = self._positive_decimal(
                node_multipliers.get(item_class, Decimal("1")),
                f"Le multiplicateur de rendement de {item.display_name} doit être positif.",
            )
            if not item.is_game_resource:
                multiplier = Decimal("1")

            compatible = [
                profile
                for profile in self.extractor_profiles
                if item.is_game_resource and profile.supports(item)
            ]
            if not compatible and item.is_game_resource:
                self._warnings.append(
                    "Aucun profil d'extraction exploitable n'est disponible "
                    f"pour {item.display_name}."
                )

            options: list[ExtractionOption] = []
            for profile in compatible:
                applied_multiplier = multiplier if profile.node_based else Decimal("1")
                effective_rate = profile.base_rate_per_minute * applied_multiplier
                equivalents = required_rate / effective_rate
                machine_count = self._ceil_positive(equivalents)
                clock_fraction = equivalents / Decimal(machine_count)
                power_min, power_max, power_model = self._extractor_power(
                    profile,
                    machine_count,
                    clock_fraction,
                )
                options.append(
                    ExtractionOption(
                        extractor_class=profile.class_name,
                        extractor_name=profile.display_name,
                        base_rate_per_minute=profile.base_rate_per_minute,
                        effective_rate_per_minute=effective_rate,
                        machine_equivalents=equivalents,
                        machine_count=machine_count,
                        clock_percent=clock_fraction * Decimal("100"),
                        power_min_mw=power_min,
                        power_max_mw=power_max,
                        power_model=power_model,
                        requires_resource_well=profile.requires_resource_well,
                    )
                )

            options.sort(
                key=lambda option: (
                    -option.effective_rate_per_minute,
                    option.power_max_mw if option.power_max_mw is not None else Decimal("Infinity"),
                    option.extractor_class,
                )
            )
            requested_extractor = extractor_choices.get(item_class)
            if requested_extractor:
                selected = next(
                    (option for option in options if option.extractor_class == requested_extractor),
                    None,
                )
                if selected is None:
                    raise InvalidExtractorChoiceError(
                        f"L'extracteur {requested_extractor} ne peut pas fournir "
                        f"{item.display_name}."
                    )
            else:
                selected = options[0] if options else None

            selected_profile = next(
                (
                    profile
                    for profile in compatible
                    if selected is not None
                    and profile.class_name == selected.extractor_class
                ),
                None,
            )
            selected_node_multiplier = (
                multiplier
                if selected_profile is not None and selected_profile.node_based
                else Decimal("1")
            )
            if selected is not None and selected.requires_resource_well:
                self._warnings.append(
                    f"{item.display_name} nécessite un réseau de puits de ressources ; "
                    "le pressuriseur et la capacité globale du puits ne sont pas dimensionnés."
                )
            if selected is not None and selected.power_model == "unknown":
                self._warnings.append(
                    "La puissance de l'extraction de "
                    f"{item.display_name} n'est pas fournie par le catalogue."
                )

            requirements.append(
                ResourceRequirement(
                    class_name=item.class_name,
                    display_name=item.display_name,
                    rate_per_minute=required_rate,
                    form=item.form,
                    unit_label=item.unit_label,
                    is_game_resource=item.is_game_resource,
                    node_yield_multiplier=selected_node_multiplier,
                    extraction_options=tuple(options),
                    selected_extractor_class=(
                        selected.extractor_class if selected is not None else None
                    ),
                )
            )
        return tuple(requirements)

    def _build_rate_amounts(
        self,
        rates: Mapping[str, Decimal],
    ) -> tuple[RateAmount, ...]:
        values: list[RateAmount] = []
        for item_class, rate in sorted(rates.items()):
            item = self.item_profiles.get(item_class)
            if item is None:
                raise UnknownProductionItemError(
                    f"Composant absent du catalogue : {item_class}."
                )
            values.append(
                RateAmount(
                    class_name=item.class_name,
                    display_name=item.display_name,
                    rate_per_minute=rate,
                    form=item.form,
                    unit_label=item.unit_label,
                )
            )
        return tuple(values)

    @staticmethod
    def _machine_power(
        machine: MachineProfile,
        machine_count: int,
        clock_fraction: Decimal,
    ) -> tuple[Decimal | None, Decimal | None, str]:
        if machine.fixed_power_mw is not None:
            power = (
                Decimal(machine_count)
                * machine.fixed_power_mw
                * (clock_fraction ** machine.power_exponent)
            )
            return power, power, "fixed"
        if (
            machine.estimated_power_min_mw is not None
            and machine.estimated_power_max_mw is not None
        ):
            minimum = Decimal(machine_count) * machine.estimated_power_min_mw
            maximum = Decimal(machine_count) * machine.estimated_power_max_mw
            return minimum, maximum, "range"
        return None, None, "unknown"

    @staticmethod
    def _extractor_power(
        extractor: ExtractorProfile,
        machine_count: int,
        clock_fraction: Decimal,
    ) -> tuple[Decimal | None, Decimal | None, str]:
        if extractor.fixed_power_mw is not None:
            power = (
                Decimal(machine_count)
                * extractor.fixed_power_mw
                * (clock_fraction ** extractor.power_exponent)
            )
            return power, power, "fixed"
        if (
            extractor.estimated_power_min_mw is not None
            and extractor.estimated_power_max_mw is not None
        ):
            minimum = Decimal(machine_count) * extractor.estimated_power_min_mw
            maximum = Decimal(machine_count) * extractor.estimated_power_max_mw
            return minimum, maximum, "range"
        return None, None, "unknown"

    @staticmethod
    def _sum_power(
        requirements: Sequence[MachineRequirement],
    ) -> tuple[Decimal, Decimal, bool]:
        minimum = ZERO
        maximum = ZERO
        complete = True
        for requirement in requirements:
            if requirement.power_min_mw is None or requirement.power_max_mw is None:
                complete = False
                continue
            minimum += requirement.power_min_mw
            maximum += requirement.power_max_mw
        return minimum, maximum, complete

    @staticmethod
    def _sum_extraction_power(
        requirements: Sequence[ResourceRequirement],
    ) -> tuple[Decimal, Decimal, bool]:
        minimum = ZERO
        maximum = ZERO
        complete = True
        for requirement in requirements:
            if not requirement.extraction_options:
                # Les matières sans extracteur catalogué restent des entrées externes.
                if requirement.is_game_resource:
                    complete = False
                continue
            selected = next(
                (
                    option
                    for option in requirement.extraction_options
                    if option.extractor_class == requirement.selected_extractor_class
                ),
                None,
            )
            if selected is None or selected.power_min_mw is None or selected.power_max_mw is None:
                complete = False
                continue
            minimum += selected.power_min_mw
            maximum += selected.power_max_mw
        return minimum, maximum, complete

    @staticmethod
    def _positive_decimal(value: Decimal | int | float | str, message: str) -> Decimal:
        try:
            result = value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvalidProductionRateError(message) from exc
        if not result.is_finite() or result <= ZERO:
            raise InvalidProductionRateError(message)
        return result

    @staticmethod
    def _ceil_positive(value: Decimal) -> int:
        return int(value.to_integral_value(rounding=ROUND_CEILING))
