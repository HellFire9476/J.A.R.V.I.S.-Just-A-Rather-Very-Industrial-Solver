"""Modèles de requête et de résultat pour l'équilibrage Refined Power."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from pydantic import Field, field_validator, model_validator

from jarvis.domain.entities.refined_power import (
    RefinedPowerChainConfiguration,
    StrictModel,
)

if TYPE_CHECKING:
    from jarvis.engines.refined_power_engine import RefinedPowerChainResult

OptimizationMode = Literal["balance_existing", "maximize", "target"]


class RefinedPowerOptimizationLimits(StrictModel):
    """Limites matérielles et de ressources prises en compte par le solveur.

    Les clés de ``fuel_available_per_minute`` utilisent l'unité déclarée pour le
    combustible concerné dans le catalogue (item/min ou m³/min). Les clés de
    ``byproduct_capacity_per_minute`` désignent les identifiants de coproduits.
    Un coproduit sans capacité déclarée est considéré comme non évacuable.
    """

    max_water_m3_per_minute: Decimal | None = Field(default=None, ge=0)
    fuel_available_per_minute: dict[str, Decimal] = Field(default_factory=dict)
    byproduct_capacity_per_minute: dict[str, Decimal] = Field(default_factory=dict)
    max_boilers: int | None = Field(default=None, ge=0, le=10000)
    max_turbines: int | None = Field(default=None, ge=0, le=10000)
    max_generators: int | None = Field(default=None, ge=0, le=10000)
    max_co2_chimneys: int | None = Field(default=None, ge=0, le=10000)
    max_steam_cooling_towers: int | None = Field(default=None, ge=0, le=10000)

    @field_validator("fuel_available_per_minute", "byproduct_capacity_per_minute")
    @classmethod
    def validate_capacity_maps(cls, value: dict[str, Decimal]) -> dict[str, Decimal]:
        for resource_id, rate in value.items():
            if not resource_id.strip():
                raise ValueError("Un identifiant de ressource ne peut pas être vide.")
            if rate < 0:
                raise ValueError("Une capacité de ressource ne peut pas être négative.")
        return value


class RefinedPowerOptimizationRequest(StrictModel):
    """Entrées d'un équilibrage, d'une maximisation ou d'une puissance cible."""

    mode: OptimizationMode
    reference_configuration: RefinedPowerChainConfiguration | None = None
    target_power_mw: Decimal | None = Field(default=None, gt=0)
    chain_name: str = Field(default="Centrale optimisée", min_length=1, max_length=80)
    allowed_heater_ids: tuple[str, ...] = ()
    allowed_fuel_ids: tuple[str, ...] = ()
    allowed_boiler_ids: tuple[str, ...] = ()
    allowed_turbine_ids: tuple[str, ...] = ()
    allowed_generator_ids: tuple[str, ...] = ()
    limits: RefinedPowerOptimizationLimits = Field(
        default_factory=RefinedPowerOptimizationLimits
    )

    @field_validator("chain_name")
    @classmethod
    def normalize_chain_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Le nom de la chaîne optimisée ne peut pas être vide.")
        return normalized

    @field_validator(
        "allowed_heater_ids",
        "allowed_fuel_ids",
        "allowed_boiler_ids",
        "allowed_turbine_ids",
        "allowed_generator_ids",
    )
    @classmethod
    def validate_allowed_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("Les identifiants autorisés ne peuvent pas être vides.")
        if len(value) != len(set(value)):
            raise ValueError("Les identifiants autorisés ne peuvent pas être dupliqués.")
        return value

    @model_validator(mode="after")
    def validate_mode_inputs(self) -> RefinedPowerOptimizationRequest:
        if self.mode == "balance_existing" and self.reference_configuration is None:
            raise ValueError(
                "L'équilibrage d'une installation exige une configuration de référence."
            )
        if self.mode != "balance_existing" and self.reference_configuration is not None:
            raise ValueError(
                "Une configuration de référence est réservée au mode balance_existing."
            )
        if self.mode in {"maximize", "target"} and self.limits.max_boilers is None:
            raise ValueError(
                "Un nombre maximal de chaudières doit être défini pour borner la recherche."
            )
        if self.mode == "target" and self.target_power_mw is None:
            raise ValueError("Le mode puissance cible exige une puissance en MW.")
        if self.mode != "target" and self.target_power_mw is not None:
            raise ValueError("La puissance cible n'est utilisable qu'en mode target.")
        return self


@dataclass(frozen=True, slots=True)
class RefinedPowerOptimizationChange:
    """Changement proposé entre une installation et son équilibrage."""

    field_name: str
    label: str
    previous_value: str
    proposed_value: str
    reason: str


@dataclass(frozen=True, slots=True)
class RefinedPowerOptimizationSolution:
    """Proposition de calcul ; elle ne modifie jamais les données persistées."""

    mode: OptimizationMode
    feasible: bool
    target_reached: bool | None
    target_power_mw: Decimal | None
    configuration: RefinedPowerChainConfiguration | None
    calculation: RefinedPowerChainResult | None
    reference_calculation: RefinedPowerChainResult | None
    changes: tuple[RefinedPowerOptimizationChange, ...]
    limiting_constraints: tuple[str, ...]
    warnings: tuple[str, ...]
    candidates_evaluated: int
    objective_summary: str
