"""Modèles métier du module Refined Power."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Base de modèles métier stricts et validés."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class RefinedPowerByproductProfile(StrictModel):
    resource_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    game_class_name: str | None = None
    localized_names: dict[str, str] = Field(default_factory=dict)
    rate_per_minute: Decimal = Field(ge=0)
    unit: Literal["item/min", "m³/min"]


class RefinedPowerHeaterProfile(StrictModel):
    heater_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    localized_names: dict[str, str] = Field(default_factory=dict)
    maximum_temperature_c: int = Field(gt=0)


class RefinedPowerFuelProfile(StrictModel):
    fuel_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    game_class_name: str | None = None
    localized_names: dict[str, str] = Field(default_factory=dict)
    heater_id: str = Field(min_length=1)
    heat_per_cycle: Decimal = Field(gt=0)
    consumption_per_minute: Decimal = Field(gt=0)
    input_unit: Literal["item/min", "m³/min"]
    operating_temperature_c: int = Field(gt=0)
    co2_output_m3_per_minute: Decimal = Field(ge=0)
    byproducts: tuple[RefinedPowerByproductProfile, ...] = ()

    @model_validator(mode="after")
    def unique_byproduct_resources(self):
        resource_ids = [item.resource_id for item in self.byproducts]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError(
                "Un identifiant de coproduit ne peut apparaître qu'une fois par combustible."
            )
        return self


class RefinedPowerBoilerOperatingPoint(StrictModel):
    temperature_c: int = Field(gt=0)
    water_consumption_m3_per_minute: Decimal = Field(gt=0)
    high_pressure_steam_m3_per_minute: Decimal = Field(gt=0)


class RefinedPowerBoilerProfile(StrictModel):
    boiler_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    localized_names: dict[str, str] = Field(default_factory=dict)
    operating_points: tuple[RefinedPowerBoilerOperatingPoint, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_temperature_points(self):
        temperatures = [point.temperature_c for point in self.operating_points]
        if len(temperatures) != len(set(temperatures)):
            raise ValueError("Une température de chaudière ne peut apparaître qu'une fois.")
        return self

    def operating_point(self, temperature_c: int) -> RefinedPowerBoilerOperatingPoint:
        for point in self.operating_points:
            if point.temperature_c == temperature_c:
                return point
        raise ValueError(
            f"Aucun rendement {self.display_name} documenté à {temperature_c} °C."
        )


class RefinedPowerTurbineProfile(StrictModel):
    turbine_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    localized_names: dict[str, str] = Field(default_factory=dict)
    high_pressure_steam_input_m3_per_minute: Decimal = Field(gt=0)
    low_pressure_steam_output_m3_per_minute: Decimal = Field(gt=0)
    maximum_rpm: Decimal = Field(gt=0)


class RefinedPowerGeneratorProfile(StrictModel):
    generator_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    localized_names: dict[str, str] = Field(default_factory=dict)
    maximum_power_mw: Decimal = Field(gt=0)
    required_rpm: Decimal = Field(gt=0)


class RefinedPowerGeneratorPerformance(StrictModel):
    turbine_id: str = Field(min_length=1)
    generator_id: str = Field(min_length=1)
    maximum_power_mw_at_full_turbine_speed: Decimal = Field(gt=0)


class RefinedPowerVentilationProfile(StrictModel):
    co2_chimney_capacity_m3_per_minute: Decimal = Field(gt=0)
    steam_cooling_tower_capacity_m3_per_minute: Decimal = Field(gt=0)


class RefinedPowerCatalog(StrictModel):
    schema_version: int = Field(ge=1)
    mod_id: Literal["refined_power"]
    mod_version: str = Field(min_length=1)
    catalog_revision: str = Field(min_length=1)
    source_urls: tuple[str, ...] = Field(min_length=1)
    heaters: tuple[RefinedPowerHeaterProfile, ...] = Field(min_length=1)
    fuels: tuple[RefinedPowerFuelProfile, ...] = Field(min_length=1)
    boilers: tuple[RefinedPowerBoilerProfile, ...] = Field(min_length=1)
    turbines: tuple[RefinedPowerTurbineProfile, ...] = Field(min_length=1)
    generators: tuple[RefinedPowerGeneratorProfile, ...] = Field(min_length=1)
    generator_performance: tuple[RefinedPowerGeneratorPerformance, ...] = Field(
        min_length=1
    )
    ventilation: RefinedPowerVentilationProfile
    calculation_notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_references(self):
        self._validate_unique_ids("heater", [item.heater_id for item in self.heaters])
        self._validate_unique_ids("fuel", [item.fuel_id for item in self.fuels])
        self._validate_unique_ids("boiler", [item.boiler_id for item in self.boilers])
        self._validate_unique_ids("turbine", [item.turbine_id for item in self.turbines])
        self._validate_unique_ids("generator", [item.generator_id for item in self.generators])

        heater_ids = {item.heater_id for item in self.heaters}
        for fuel in self.fuels:
            heater = next((item for item in self.heaters if item.heater_id == fuel.heater_id), None)
            if heater is None:
                raise ValueError(f"Chauffage inconnu pour le combustible {fuel.fuel_id}.")
            if fuel.operating_temperature_c > heater.maximum_temperature_c:
                raise ValueError(
                    f"Le combustible {fuel.fuel_id} dépasse la température maximale "
                    f"du chauffage {fuel.heater_id}."
                )
        if not heater_ids:
            raise ValueError("Le catalogue doit contenir au moins un chauffage.")

        turbine_ids = {item.turbine_id for item in self.turbines}
        generator_ids = {item.generator_id for item in self.generators}
        combinations: set[tuple[str, str]] = set()
        for combination in self.generator_performance:
            key = (combination.turbine_id, combination.generator_id)
            if key in combinations:
                raise ValueError("Une combinaison turbine/générateur est dupliquée.")
            combinations.add(key)
            if combination.turbine_id not in turbine_ids:
                raise ValueError(f"Turbine inconnue : {combination.turbine_id}.")
            if combination.generator_id not in generator_ids:
                raise ValueError(f"Générateur inconnu : {combination.generator_id}.")
        return self

    @staticmethod
    def _validate_unique_ids(label: str, values: list[str]) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"Identifiants {label} dupliqués dans le catalogue.")

    def get_heater(self, heater_id: str) -> RefinedPowerHeaterProfile:
        return self._get_by_id(self.heaters, "heater_id", heater_id, "chauffage")

    def get_fuel(self, fuel_id: str) -> RefinedPowerFuelProfile:
        return self._get_by_id(self.fuels, "fuel_id", fuel_id, "combustible")

    def get_boiler(self, boiler_id: str) -> RefinedPowerBoilerProfile:
        return self._get_by_id(self.boilers, "boiler_id", boiler_id, "chaudière")

    def get_turbine(self, turbine_id: str) -> RefinedPowerTurbineProfile:
        return self._get_by_id(self.turbines, "turbine_id", turbine_id, "turbine")

    def get_generator(self, generator_id: str) -> RefinedPowerGeneratorProfile:
        return self._get_by_id(self.generators, "generator_id", generator_id, "générateur")

    def get_generator_performance(
        self,
        turbine_id: str,
        generator_id: str,
    ) -> RefinedPowerGeneratorPerformance:
        for profile in self.generator_performance:
            if profile.turbine_id == turbine_id and profile.generator_id == generator_id:
                return profile
        raise ValueError(
            f"Combinaison non documentée : turbine {turbine_id} / générateur {generator_id}."
        )

    @staticmethod
    def _get_by_id(items, attribute: str, value: str, label: str):
        for item in items:
            if getattr(item, attribute) == value:
                return item
        raise ValueError(f"{label.capitalize()} inconnu(e) : {value}.")


class RefinedPowerChainConfiguration(StrictModel):
    """Configuration d'une chaîne modulaire, rattachée à un parc."""

    chain_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=80)
    heater_id: str = Field(min_length=1)
    fuel_id: str = Field(min_length=1)
    boiler_id: str = Field(min_length=1)
    boiler_count: int = Field(default=1, ge=1, le=10000)
    turbine_id: str = Field(min_length=1)
    turbine_count: int = Field(default=1, ge=0, le=10000)
    generator_id: str = Field(min_length=1)
    generator_count: int = Field(default=1, ge=0, le=10000)
    co2_chimney_count: int = Field(default=1, ge=0, le=10000)
    steam_cooling_tower_count: int = Field(default=1, ge=0, le=10000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Le nom de la chaîne ne peut pas être vide.")
        return normalized


class RefinedPowerParkConfiguration(StrictModel):
    """Configuration Refined Power persistée dans le module du parc."""

    schema_version: int = Field(default=1, ge=1)
    catalog_version: str | None = None
    chains: tuple[RefinedPowerChainConfiguration, ...] = ()

    @model_validator(mode="after")
    def unique_chain_ids(self):
        identifiers = [chain.chain_id for chain in self.chains]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Identifiants de chaînes Refined Power dupliqués.")
        return self
