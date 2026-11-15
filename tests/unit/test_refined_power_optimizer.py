from decimal import Decimal

import pytest

from jarvis.domain.entities.refined_power import RefinedPowerChainConfiguration
from jarvis.domain.entities.refined_power_optimization import (
    RefinedPowerOptimizationLimits,
    RefinedPowerOptimizationRequest,
)
from jarvis.engines.refined_power_optimizer import (
    RefinedPowerOptimizationError,
    RefinedPowerOptimizer,
)
from jarvis.infrastructure.catalog.refined_power_catalog_repository import (
    RefinedPowerCatalogRepository,
)


@pytest.fixture
def catalog():
    return RefinedPowerCatalogRepository().get_catalog()


@pytest.fixture
def optimizer():
    return RefinedPowerOptimizer()


def sample_chain(**overrides):
    values = {
        "name": "Centrale charbon à équilibrer",
        "heater_id": "coal",
        "fuel_id": "coal",
        "boiler_id": "mk1",
        "boiler_count": 2,
        "turbine_id": "mk1",
        "turbine_count": 1,
        "generator_id": "lv",
        "generator_count": 1,
        "co2_chimney_count": 0,
        "steam_cooling_tower_count": 0,
    }
    values.update(overrides)
    return RefinedPowerChainConfiguration(**values)


def coal_limits(**overrides):
    values = {
        "max_water_m3_per_minute": Decimal("45"),
        "fuel_available_per_minute": {"coal": Decimal("15")},
        "max_boilers": 1,
        "max_turbines": 2,
        "max_generators": 2,
        "max_co2_chimneys": 1,
        "max_steam_cooling_towers": 1,
    }
    values.update(overrides)
    return RefinedPowerOptimizationLimits(**values)


def test_balance_existing_preserves_profiles_and_repairs_integer_counts(
    optimizer,
    catalog,
):
    reference = sample_chain()
    request = RefinedPowerOptimizationRequest(
        mode="balance_existing",
        reference_configuration=reference,
    )

    solution = optimizer.optimize(request, catalog)

    assert solution.feasible is True
    assert solution.configuration is not None
    assert solution.configuration.chain_id == reference.chain_id
    assert solution.configuration.boiler_count == 2
    assert solution.configuration.turbine_id == "mk1"
    assert solution.configuration.generator_id == "lv"
    assert solution.configuration.turbine_count == 2
    assert solution.configuration.generator_count == 2
    assert solution.configuration.co2_chimney_count == 1
    assert solution.configuration.steam_cooling_tower_count == 1
    assert solution.calculation is not None
    assert solution.calculation.estimated_power_mw == Decimal("300")
    assert solution.calculation.sustainable is True
    assert solution.reference_calculation is not None
    assert solution.reference_calculation.sustainable is False
    assert {change.field_name for change in solution.changes} == {
        "turbine_count",
        "generator_count",
        "co2_chimney_count",
        "steam_cooling_tower_count",
    }


def test_balance_existing_reports_resource_and_equipment_shortages(
    optimizer,
    catalog,
):
    request = RefinedPowerOptimizationRequest(
        mode="balance_existing",
        reference_configuration=sample_chain(),
        limits=RefinedPowerOptimizationLimits(
            max_water_m3_per_minute=Decimal("45"),
            max_turbines=1,
            max_generators=1,
            max_co2_chimneys=1,
            max_steam_cooling_towers=1,
        ),
    )

    solution = optimizer.optimize(request, catalog)

    assert solution.feasible is False
    assert solution.configuration is not None
    assert any("turbines requis" in item for item in solution.limiting_constraints)
    assert any("générateurs requis" in item for item in solution.limiting_constraints)


def test_maximize_selects_highest_power_within_fuel_and_water_limits(
    optimizer,
    catalog,
):
    request = RefinedPowerOptimizationRequest(
        mode="maximize",
        allowed_fuel_ids=("coal",),
        allowed_boiler_ids=("mk1",),
        limits=coal_limits(),
    )

    solution = optimizer.optimize(request, catalog)

    assert solution.feasible is True
    assert solution.configuration is not None
    assert solution.configuration.fuel_id == "coal"
    assert solution.configuration.boiler_count == 1
    assert solution.configuration.turbine_id == "mk2"
    assert solution.configuration.generator_id == "hv"
    assert solution.calculation is not None
    assert solution.calculation.estimated_power_mw == Decimal("250")
    assert solution.calculation.water_consumption_m3_per_minute == Decimal("45")
    assert solution.calculation.fuel_consumption_per_minute == Decimal("15")
    assert solution.calculation.sustainable is True


def test_target_mode_selects_closest_feasible_power_without_exceeding_limits(
    optimizer,
    catalog,
):
    request = RefinedPowerOptimizationRequest(
        mode="target",
        target_power_mw=Decimal("180"),
        allowed_fuel_ids=("coal",),
        allowed_boiler_ids=("mk1",),
        limits=coal_limits(),
    )

    solution = optimizer.optimize(request, catalog)

    assert solution.feasible is True
    assert solution.target_reached is True
    assert solution.configuration is not None
    assert solution.configuration.turbine_id == "mk1"
    assert solution.configuration.generator_id == "mv"
    assert solution.calculation is not None
    assert solution.calculation.estimated_power_mw == Decimal("181.9")


def test_target_mode_returns_best_feasible_output_when_target_is_unreachable(
    optimizer,
    catalog,
):
    request = RefinedPowerOptimizationRequest(
        mode="target",
        target_power_mw=Decimal("300"),
        allowed_fuel_ids=("coal",),
        allowed_boiler_ids=("mk1",),
        allowed_turbine_ids=("mk1",),
        allowed_generator_ids=("lv",),
        limits=coal_limits(),
    )

    solution = optimizer.optimize(request, catalog)

    assert solution.feasible is True
    assert solution.target_reached is False
    assert solution.calculation is not None
    assert solution.calculation.estimated_power_mw == Decimal("150")
    assert any("n'est pas atteignable" in item for item in solution.limiting_constraints)


def test_unmanaged_byproducts_are_not_treated_as_balanced(optimizer, catalog):
    request = RefinedPowerOptimizationRequest(
        mode="maximize",
        allowed_fuel_ids=("nuclear_fuel_rod",),
        allowed_boiler_ids=("mk2",),
        allowed_turbine_ids=("mk2",),
        allowed_generator_ids=("hv",),
        limits=RefinedPowerOptimizationLimits(
            max_water_m3_per_minute=Decimal("450"),
            max_boilers=1,
            max_turbines=5,
            max_generators=5,
            max_co2_chimneys=0,
            max_steam_cooling_towers=2,
        ),
    )

    solution = optimizer.optimize(request, catalog)

    assert solution.feasible is False
    assert solution.configuration is None
    assert any("coproduit" in item.lower() for item in solution.limiting_constraints)


def test_byproduct_capacity_allows_nuclear_solution(optimizer, catalog):
    request = RefinedPowerOptimizationRequest(
        mode="maximize",
        allowed_fuel_ids=("nuclear_fuel_rod",),
        allowed_boiler_ids=("mk2",),
        allowed_turbine_ids=("mk2",),
        allowed_generator_ids=("hv",),
        limits=RefinedPowerOptimizationLimits(
            max_water_m3_per_minute=Decimal("450"),
            byproduct_capacity_per_minute={"nuclear_waste": Decimal("6.25")},
            max_boilers=1,
            max_turbines=5,
            max_generators=5,
            max_co2_chimneys=0,
            max_steam_cooling_towers=2,
        ),
    )

    solution = optimizer.optimize(request, catalog)

    assert solution.feasible is True
    assert solution.configuration is not None
    assert solution.configuration.fuel_id == "nuclear_fuel_rod"
    assert solution.calculation is not None
    assert solution.calculation.estimated_power_mw == Decimal("2500")
    assert solution.calculation.byproducts[0].rate_per_minute == Decimal("6.25")


def test_search_request_requires_an_explicit_boiler_bound():
    with pytest.raises(ValueError, match="nombre maximal de chaudières"):
        RefinedPowerOptimizationRequest(mode="maximize")


def test_unknown_allowed_profile_is_rejected(optimizer, catalog):
    request = RefinedPowerOptimizationRequest(
        mode="maximize",
        allowed_fuel_ids=("unknown_fuel",),
        limits=RefinedPowerOptimizationLimits(max_boilers=1),
    )

    with pytest.raises(RefinedPowerOptimizationError, match="combustible inconnu"):
        optimizer.optimize(request, catalog)


def test_optimizer_search_budget_prevents_excessive_search(optimizer, catalog):
    optimizer.MAX_CANDIDATE_EVALUATIONS = 5
    request = RefinedPowerOptimizationRequest(
        mode="maximize",
        allowed_fuel_ids=("coal",),
        allowed_boiler_ids=("mk1",),
        allowed_turbine_ids=("mk1",),
        allowed_generator_ids=("lv",),
        limits=RefinedPowerOptimizationLimits(max_boilers=10),
    )

    with pytest.raises(RefinedPowerOptimizationError, match="budget de calcul"):
        optimizer.optimize(request, catalog)


def test_partial_load_is_explicitly_marked_as_estimated(optimizer, catalog):
    request = RefinedPowerOptimizationRequest(
        mode="maximize",
        allowed_fuel_ids=("coal",),
        allowed_boiler_ids=("mk1",),
        allowed_turbine_ids=("mk2",),
        allowed_generator_ids=("hv",),
        limits=coal_limits(),
    )

    solution = optimizer.optimize(request, catalog)

    assert solution.calculation is not None
    assert solution.calculation.power_is_estimated is True
    assert any("estimation" in warning.lower() for warning in solution.warnings)


@pytest.mark.parametrize(
    ("mode", "target_power_mw"),
    [
        ("maximize", None),
        ("target", Decimal("100")),
    ],
)
def test_search_modes_reject_reference_configuration(mode, target_power_mw):
    values = {
        "mode": mode,
        "reference_configuration": sample_chain(),
        "limits": RefinedPowerOptimizationLimits(max_boilers=1),
    }
    if target_power_mw is not None:
        values["target_power_mw"] = target_power_mw

    with pytest.raises(ValueError, match="réservée au mode balance_existing"):
        RefinedPowerOptimizationRequest(**values)

