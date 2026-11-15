from decimal import Decimal

import pytest

from jarvis.domain.entities.refined_power import RefinedPowerChainConfiguration
from jarvis.engines.refined_power_engine import (
    RefinedPowerCalculationError,
    RefinedPowerEngine,
)
from jarvis.infrastructure.catalog.refined_power_catalog_repository import (
    RefinedPowerCatalogRepository,
)


@pytest.fixture
def catalog():
    return RefinedPowerCatalogRepository().get_catalog()


@pytest.fixture
def engine():
    return RefinedPowerEngine()


def coal_mk1_chain(**overrides):
    values = {
        "name": "Centrale charbon test",
        "heater_id": "coal",
        "fuel_id": "coal",
        "boiler_id": "mk1",
        "boiler_count": 1,
        "turbine_id": "mk1",
        "turbine_count": 1,
        "generator_id": "lv",
        "generator_count": 1,
        "co2_chimney_count": 1,
        "steam_cooling_tower_count": 1,
    }
    values.update(overrides)
    return RefinedPowerChainConfiguration(**values)


def test_catalog_loads_with_unique_profiles(catalog):
    assert catalog.mod_version == "2026.3.26"
    assert len(catalog.fuels) == 24
    assert catalog.get_boiler("mk2").operating_point(1250).high_pressure_steam_m3_per_minute == 360


def test_mk1_coal_chain_reaches_documented_nominal_output(engine, catalog):
    result = engine.calculate(coal_mk1_chain(), catalog)

    assert result.fuel_consumption_per_minute == Decimal("15")
    assert result.water_consumption_m3_per_minute == Decimal("45")
    assert result.high_pressure_steam_generated_m3_per_minute == Decimal("60")
    assert result.turbine_rpm == Decimal("10000")
    assert result.estimated_power_mw == Decimal("150")
    assert result.low_pressure_steam_output_m3_per_minute == Decimal("60")
    assert result.co2_output_m3_per_minute == Decimal("30")
    assert result.sustainable is True
    assert result.warnings == ()


def test_mk2_ionized_fuel_uses_1250_degree_operating_point(engine, catalog):
    configuration = coal_mk1_chain(
        name="Solution Mk2",
        heater_id="solution",
        fuel_id="ionized_fuel",
        boiler_id="mk2",
        turbine_id="mk1",
        boiler_count=1,
        turbine_count=6,
        generator_count=6,
        generator_id="lv",
        co2_chimney_count=1,
        steam_cooling_tower_count=2,
    )

    result = engine.calculate(configuration, catalog)

    assert result.fuel_consumption_per_minute == Decimal("10")
    assert result.water_consumption_m3_per_minute == Decimal("270")
    assert result.high_pressure_steam_generated_m3_per_minute == Decimal("360")
    assert result.turbine_rpm == Decimal("10000")
    assert result.estimated_power_mw == Decimal("900")
    assert result.co2_output_m3_per_minute == Decimal("75")
    assert result.low_pressure_steam_output_m3_per_minute == Decimal("360")
    assert result.low_pressure_steam_overflow_m3_per_minute == Decimal("0")
    assert result.sustainable is True


def test_mk1_boiler_warns_when_higher_temperature_heat_is_wasted(engine, catalog):
    configuration = coal_mk1_chain(
        heater_id="solution",
        fuel_id="fuel",
        boiler_id="mk1",
    )

    result = engine.calculate(configuration, catalog)

    assert result.high_pressure_steam_generated_m3_per_minute == Decimal("60")
    assert any("chaudière Mk.1 est limitée à 500 °C" in item for item in result.warnings)


def test_insufficient_steam_scales_rpm_and_flags_estimate(engine, catalog):
    result = engine.calculate(
        coal_mk1_chain(boiler_count=1, turbine_count=2, generator_count=2),
        catalog,
    )

    assert result.turbine_steam_utilization == Decimal("0.5")
    assert result.turbine_rpm == Decimal("5000")
    assert result.estimated_power_mw == Decimal("150")
    assert result.power_is_estimated is True
    assert any("approximation linéaire" in warning for warning in result.warnings)


def test_insufficient_chimney_and_cooling_capacity_is_reported(engine, catalog):
    result = engine.calculate(
        coal_mk1_chain(
            boiler_count=6,
            turbine_count=6,
            generator_count=6,
            co2_chimney_count=1,
            steam_cooling_tower_count=1,
        ),
        catalog,
    )

    assert result.co2_output_m3_per_minute == Decimal("180")
    assert result.co2_overflow_m3_per_minute == Decimal("30")
    assert result.low_pressure_steam_output_m3_per_minute == Decimal("360")
    assert result.low_pressure_steam_overflow_m3_per_minute == Decimal("60")
    assert result.sustainable is False


def test_incompatible_fuel_and_heater_are_rejected(engine, catalog):
    configuration = coal_mk1_chain(heater_id="biomass", fuel_id="coal")

    with pytest.raises(RefinedPowerCalculationError, match="n'est pas compatible"):
        engine.calculate(configuration, catalog)


def test_mk1_hv_generator_uses_documented_combination_output(engine, catalog):
    configuration = coal_mk1_chain(turbine_id="mk1", generator_id="hv")
    result = engine.calculate(configuration, catalog)
    assert result.estimated_power_mw == Decimal("176")



def test_solution_fuel_uses_cubic_metres_per_minute(engine, catalog):
    configuration = coal_mk1_chain(
        heater_id="solution",
        fuel_id="fuel",
        boiler_id="mk2",
        turbine_count=2,
        generator_count=2,
        turbine_id="mk1",
        generator_id="lv",
        steam_cooling_tower_count=1,
    )

    result = engine.calculate(configuration, catalog)

    assert result.fuel_unit == "m³/min"
    assert result.fuel_consumption_per_minute == Decimal("12")
    assert result.water_consumption_m3_per_minute == Decimal("90")
    assert result.high_pressure_steam_generated_m3_per_minute == Decimal("120")


def test_nuclear_fuel_reports_waste_byproduct(engine, catalog):
    configuration = coal_mk1_chain(
        heater_id="nuclear",
        fuel_id="nuclear_fuel_rod",
        boiler_id="mk2",
        turbine_id="mk2",
        generator_id="hv",
        boiler_count=1,
        turbine_count=5,
        generator_count=5,
        co2_chimney_count=0,
        steam_cooling_tower_count=2,
    )

    result = engine.calculate(configuration, catalog)

    assert result.fuel_consumption_per_minute == Decimal("0.125")
    assert result.water_consumption_m3_per_minute == Decimal("450")
    assert result.high_pressure_steam_generated_m3_per_minute == Decimal("600")
    assert len(result.byproducts) == 1
    assert result.byproducts[0].resource_id == "nuclear_waste"
    assert result.byproducts[0].rate_per_minute == Decimal("6.25")
    assert result.byproducts[0].unit == "item/min"
    assert result.co2_output_m3_per_minute == Decimal("0")
