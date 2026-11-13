"""Objets métier du calcul de production industriel."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

FLUID_FORMS = frozenset({"RF_LIQUID", "RF_GAS"})


@dataclass(frozen=True, slots=True)
class ItemProfile:
    """Métadonnées nécessaires au calcul d'un objet du catalogue."""

    class_name: str
    display_name: str
    form: str = "RF_INVALID"
    native_class: str = ""
    description: str = ""

    @property
    def unit_label(self) -> str:
        if self.form in FLUID_FORMS:
            return "m³"
        if self.form == "RF_SOLID":
            return "objet"
        return "unité"

    @property
    def is_game_resource(self) -> bool:
        return self.native_class == "FGResourceDescriptor"


@dataclass(frozen=True, slots=True)
class MachineProfile:
    """Caractéristiques techniques d'un fabricant."""

    class_name: str
    display_name: str
    manufacturing_speed: Decimal = Decimal("1")
    fixed_power_mw: Decimal | None = None
    power_exponent: Decimal = Decimal("1.321929")
    estimated_power_min_mw: Decimal | None = None
    estimated_power_max_mw: Decimal | None = None
    minimum_clock_fraction: Decimal = Decimal("0.01")
    maximum_clock_fraction: Decimal = Decimal("1")


@dataclass(frozen=True, slots=True)
class ExtractorProfile:
    """Capacité nominale d'un bâtiment d'extraction pour une ressource."""

    class_name: str
    display_name: str
    base_rate_per_minute: Decimal
    form: str
    allowed_forms: frozenset[str]
    allowed_resource_classes: frozenset[str] = frozenset()
    restricted_resources: bool = False
    node_based: bool = True
    requires_resource_well: bool = False
    fixed_power_mw: Decimal | None = None
    power_exponent: Decimal = Decimal("1.321929")
    estimated_power_min_mw: Decimal | None = None
    estimated_power_max_mw: Decimal | None = None

    def supports(self, item: ItemProfile) -> bool:
        if item.form not in self.allowed_forms:
            return False
        return not self.restricted_resources or (
            item.class_name in self.allowed_resource_classes
        )


@dataclass(frozen=True, slots=True)
class RateAmount:
    """Débit d'un objet par minute : objet/min ou m³/min."""

    class_name: str
    display_name: str
    rate_per_minute: Decimal
    form: str
    unit_label: str


@dataclass(frozen=True, slots=True)
class MachineRequirement:
    """Besoin agrégé en fabricants pour une recette donnée."""

    recipe_class: str
    recipe_name: str
    producer_class: str
    producer_name: str
    cycles_per_minute: Decimal
    machine_equivalents: Decimal
    machine_count: int
    clock_percent: Decimal
    inputs: tuple[RateAmount, ...]
    outputs: tuple[RateAmount, ...]
    power_min_mw: Decimal | None
    power_max_mw: Decimal | None
    power_model: str


@dataclass(frozen=True, slots=True)
class ExtractionOption:
    """Dimensionnement théorique d'un type d'extracteur."""

    extractor_class: str
    extractor_name: str
    base_rate_per_minute: Decimal
    effective_rate_per_minute: Decimal
    machine_equivalents: Decimal
    machine_count: int
    clock_percent: Decimal
    power_min_mw: Decimal | None
    power_max_mw: Decimal | None
    power_model: str
    requires_resource_well: bool


@dataclass(frozen=True, slots=True)
class ResourceRequirement:
    """Matière première à fournir au réseau de production."""

    class_name: str
    display_name: str
    rate_per_minute: Decimal
    form: str
    unit_label: str
    is_game_resource: bool
    node_yield_multiplier: Decimal
    extraction_options: tuple[ExtractionOption, ...]
    selected_extractor_class: str | None


@dataclass(frozen=True, slots=True)
class ProductionPlan:
    """Résultat complet d'un calcul pour un objectif unique."""

    target_class_name: str
    target_name: str
    target_rate_per_minute: Decimal
    target_unit_label: str
    locale: str
    machine_requirements: tuple[MachineRequirement, ...]
    resource_requirements: tuple[ResourceRequirement, ...]
    byproducts: tuple[RateAmount, ...]
    production_power_min_mw: Decimal
    production_power_max_mw: Decimal
    extraction_power_min_mw: Decimal
    extraction_power_max_mw: Decimal
    total_power_min_mw: Decimal | None
    total_power_max_mw: Decimal | None
    power_estimate_complete: bool
    warnings: tuple[str, ...]
