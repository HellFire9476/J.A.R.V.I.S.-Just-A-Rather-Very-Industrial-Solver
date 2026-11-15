"""Moteur pur de calcul des chaînes Modular Power de Refined Power."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from jarvis.domain.entities.refined_power import (
    RefinedPowerCatalog,
    RefinedPowerChainConfiguration,
)

ZERO = Decimal("0")
ONE = Decimal("1")


class RefinedPowerCalculationError(ValueError):
    """Configuration impossible à calculer avec le catalogue chargé."""


@dataclass(frozen=True, slots=True)
class RefinedPowerFlow:
    resource_id: str
    display_name: str
    rate_per_minute: Decimal
    unit: str


@dataclass(frozen=True, slots=True)
class RefinedPowerChainResult:
    chain_id: str
    chain_name: str
    catalog_version: str
    fuel_consumption_per_minute: Decimal
    fuel_unit: str
    water_consumption_m3_per_minute: Decimal
    high_pressure_steam_generated_m3_per_minute: Decimal
    high_pressure_steam_demand_m3_per_minute: Decimal
    high_pressure_steam_used_m3_per_minute: Decimal
    high_pressure_steam_surplus_m3_per_minute: Decimal
    turbine_rpm: Decimal
    turbine_steam_utilization: Decimal
    connected_generator_count: int
    idle_generator_count: int
    turbine_without_generator_count: int
    estimated_power_mw: Decimal
    low_pressure_steam_output_m3_per_minute: Decimal
    low_pressure_steam_vent_capacity_m3_per_minute: Decimal
    low_pressure_steam_overflow_m3_per_minute: Decimal
    co2_output_m3_per_minute: Decimal
    co2_vent_capacity_m3_per_minute: Decimal
    co2_overflow_m3_per_minute: Decimal
    byproducts: tuple[RefinedPowerFlow, ...]
    sustainable: bool
    power_is_estimated: bool
    warnings: tuple[str, ...]


class RefinedPowerEngine:
    """Calcule un régime permanent pour une chaîne chaudière/turbine/générateur."""

    def calculate(
        self,
        configuration: RefinedPowerChainConfiguration,
        catalog: RefinedPowerCatalog,
    ) -> RefinedPowerChainResult:
        heater = catalog.get_heater(configuration.heater_id)
        fuel = catalog.get_fuel(configuration.fuel_id)
        boiler = catalog.get_boiler(configuration.boiler_id)
        turbine = catalog.get_turbine(configuration.turbine_id)
        generator = catalog.get_generator(configuration.generator_id)

        if fuel.heater_id != heater.heater_id:
            raise RefinedPowerCalculationError(
                f"Le combustible {fuel.display_name} n'est pas compatible avec "
                f"le chauffage {heater.display_name}."
            )
        if fuel.operating_temperature_c > heater.maximum_temperature_c:
            raise RefinedPowerCalculationError(
                f"Le combustible {fuel.display_name} dépasse la température maximale "
                f"du chauffage {heater.display_name}."
            )

        try:
            boiler_point = boiler.operating_point(fuel.operating_temperature_c)
            generator_performance = catalog.get_generator_performance(
                turbine.turbine_id,
                generator.generator_id,
            )
        except ValueError as error:
            raise RefinedPowerCalculationError(str(error)) from error

        boiler_count = Decimal(configuration.boiler_count)
        turbine_count = Decimal(configuration.turbine_count)
        generator_count = configuration.generator_count

        fuel_consumption = fuel.consumption_per_minute * boiler_count
        water_consumption = boiler_point.water_consumption_m3_per_minute * boiler_count
        steam_generated = boiler_point.high_pressure_steam_m3_per_minute * boiler_count
        steam_demand = (
            turbine.high_pressure_steam_input_m3_per_minute * turbine_count
        )
        steam_used = min(steam_generated, steam_demand)
        steam_surplus = max(ZERO, steam_generated - steam_used)
        steam_utilization = (
            steam_used / steam_demand if steam_demand > ZERO else ZERO
        )
        turbine_rpm = turbine.maximum_rpm * steam_utilization

        connected_generators = min(configuration.turbine_count, generator_count)
        idle_generators = max(0, generator_count - configuration.turbine_count)
        turbines_without_generators = max(0, configuration.turbine_count - generator_count)
        estimated_power_per_generator = (
            generator_performance.maximum_power_mw_at_full_turbine_speed
            * steam_utilization
        )
        estimated_power = estimated_power_per_generator * Decimal(connected_generators)

        low_pressure_steam_output = (
            turbine.low_pressure_steam_output_m3_per_minute
            * turbine_count
            * steam_utilization
        )
        steam_vent_capacity = (
            catalog.ventilation.steam_cooling_tower_capacity_m3_per_minute
            * Decimal(configuration.steam_cooling_tower_count)
        )
        steam_overflow = max(ZERO, low_pressure_steam_output - steam_vent_capacity)

        co2_output = fuel.co2_output_m3_per_minute * boiler_count
        co2_vent_capacity = (
            catalog.ventilation.co2_chimney_capacity_m3_per_minute
            * Decimal(configuration.co2_chimney_count)
        )
        co2_overflow = max(ZERO, co2_output - co2_vent_capacity)

        byproduct_totals: dict[tuple[str, str, str], Decimal] = {}
        for byproduct in fuel.byproducts:
            key = (byproduct.resource_id, byproduct.display_name, byproduct.unit)
            byproduct_totals[key] = (
                byproduct_totals.get(key, ZERO)
                + byproduct.rate_per_minute * boiler_count
            )
        byproducts = tuple(
            RefinedPowerFlow(
                resource_id=resource_id,
                display_name=display_name,
                rate_per_minute=rate,
                unit=unit,
            )
            for (resource_id, display_name, unit), rate in sorted(byproduct_totals.items())
        )

        warnings: list[str] = []
        if boiler.boiler_id == "mk1" and fuel.operating_temperature_c > 500:
            warnings.append(
                "La chaudière Mk.1 est limitée à 500 °C : une partie de la chaleur "
                "du chauffage est perdue sans augmenter le débit de vapeur."
            )
        if configuration.turbine_count == 0:
            warnings.append("Aucune turbine : la vapeur haute pression n'est pas convertie.")
        if configuration.generator_count == 0:
            warnings.append("Aucun générateur : aucune puissance électrique n'est produite.")
        if turbines_without_generators:
            warnings.append(
                f"{turbines_without_generators} turbine(s) ne sont reliées à aucun générateur."
            )
        if idle_generators:
            warnings.append(
                f"{idle_generators} générateur(s) ne disposent pas d'une turbine associée."
            )
        if steam_surplus > ZERO:
            warnings.append(
                "Vapeur haute pression excédentaire : vérifie le nombre de turbines "
                "ou la répartition du réseau."
            )
        if steam_overflow > ZERO:
            warnings.append(
                "Capacité d'évacuation de vapeur basse pression insuffisante : "
                f"déficit de {steam_overflow} m³/min."
            )
        if co2_overflow > ZERO:
            warnings.append(
                "Capacité d'évacuation du CO₂ insuffisante : "
                f"déficit de {co2_overflow} m³/min."
            )
        if ZERO < steam_utilization < ONE:
            warnings.append(
                "Alimentation vapeur partielle : le calcul électrique utilise une "
                "approximation linéaire du régime RPM."
            )

        sustainable = (
            steam_overflow == ZERO
            and co2_overflow == ZERO
            and steam_surplus == ZERO
        )

        return RefinedPowerChainResult(
            chain_id=str(configuration.chain_id),
            chain_name=configuration.name,
            catalog_version=catalog.mod_version,
            fuel_consumption_per_minute=fuel_consumption,
            fuel_unit=fuel.input_unit,
            water_consumption_m3_per_minute=water_consumption,
            high_pressure_steam_generated_m3_per_minute=steam_generated,
            high_pressure_steam_demand_m3_per_minute=steam_demand,
            high_pressure_steam_used_m3_per_minute=steam_used,
            high_pressure_steam_surplus_m3_per_minute=steam_surplus,
            turbine_rpm=turbine_rpm,
            turbine_steam_utilization=steam_utilization,
            connected_generator_count=connected_generators,
            idle_generator_count=idle_generators,
            turbine_without_generator_count=turbines_without_generators,
            estimated_power_mw=estimated_power,
            low_pressure_steam_output_m3_per_minute=low_pressure_steam_output,
            low_pressure_steam_vent_capacity_m3_per_minute=steam_vent_capacity,
            low_pressure_steam_overflow_m3_per_minute=steam_overflow,
            co2_output_m3_per_minute=co2_output,
            co2_vent_capacity_m3_per_minute=co2_vent_capacity,
            co2_overflow_m3_per_minute=co2_overflow,
            byproducts=byproducts,
            sustainable=sustainable,
            power_is_estimated=steam_utilization < ONE,
            warnings=tuple(warnings),
        )
