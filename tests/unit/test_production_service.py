"""Tests d'intégration entre le catalogue, les recettes et le moteur."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from jarvis.application.services.production_service import ProductionService


def _object_path(class_name: str) -> str:
    return (
        "/Script/Engine.BlueprintGeneratedClass'"
        f"/Game/Test/{class_name}.{class_name}'"
    )


def _component(class_name: str, amount: str) -> str:
    return f'(ItemClass="{_object_path(class_name)}",Amount={amount})'


def _write_catalog(tmp_path):
    catalog_dir = tmp_path / "Catalog"
    locales_dir = catalog_dir / "locales"
    locales_dir.mkdir(parents=True)

    classes = {
        "Recipe_IronIngot_C": {
            "native_class": "FGRecipe",
            "properties": {
                "mIngredients": f"({_component('Desc_OreIron_C', '1')})",
                "mProduct": f"({_component('Desc_IronIngot_C', '1')})",
                "mManufactoringDuration": "2.000000",
                "mProducedIn": f'("{_object_path("Build_SmelterMk1_C")}")',
            },
        },
        "Recipe_IronPlate_C": {
            "native_class": "FGRecipe",
            "properties": {
                "mIngredients": f"({_component('Desc_IronIngot_C', '3')})",
                "mProduct": f"({_component('Desc_IronPlate_C', '2')})",
                "mManufactoringDuration": "6.000000",
                "mProducedIn": f'("{_object_path("Build_ConstructorMk1_C")}")',
            },
        },
        "Recipe_Plastic_C": {
            "native_class": "FGRecipe",
            "properties": {
                "mIngredients": f"({_component('Desc_LiquidOil_C', '3000')})",
                "mProduct": (
                    f"({_component('Desc_Plastic_C', '2')},"
                    f"{_component('Desc_HeavyOilResidue_C', '1000')})"
                ),
                "mManufactoringDuration": "6.000000",
                "mProducedIn": f'("{_object_path("Build_OilRefinery_C")}")',
            },
        },
        "Desc_OreIron_C": {
            "native_class": "FGResourceDescriptor",
            "properties": {"mForm": "RF_SOLID"},
        },
        "Desc_IronIngot_C": {
            "native_class": "FGItemDescriptor",
            "properties": {"mForm": "RF_SOLID"},
        },
        "Desc_IronPlate_C": {
            "native_class": "FGItemDescriptor",
            "properties": {"mForm": "RF_SOLID"},
        },
        "Desc_LiquidOil_C": {
            "native_class": "FGResourceDescriptor",
            "properties": {"mForm": "RF_LIQUID"},
        },
        "Desc_Plastic_C": {
            "native_class": "FGItemDescriptor",
            "properties": {"mForm": "RF_SOLID"},
        },
        "Desc_HeavyOilResidue_C": {
            "native_class": "FGItemDescriptor",
            "properties": {"mForm": "RF_LIQUID"},
        },
        "Build_SmelterMk1_C": {
            "native_class": "FGBuildableManufacturer",
            "properties": {
                "mManufacturingSpeed": "1.000000",
                "mPowerConsumption": "4.000000",
                "mPowerConsumptionExponent": "1.321929",
                "mMinPotential": "0.010000",
                "mMaxPotential": "1.000000",
            },
        },
        "Build_ConstructorMk1_C": {
            "native_class": "FGBuildableManufacturer",
            "properties": {
                "mManufacturingSpeed": "1.000000",
                "mPowerConsumption": "4.000000",
                "mPowerConsumptionExponent": "1.321929",
                "mMinPotential": "0.010000",
                "mMaxPotential": "1.000000",
            },
        },
        "Build_OilRefinery_C": {
            "native_class": "FGBuildableManufacturer",
            "properties": {
                "mManufacturingSpeed": "1.000000",
                "mPowerConsumption": "30.000000",
                "mPowerConsumptionExponent": "1.321929",
            },
        },
        "Build_MinerMk3_C": {
            "native_class": "FGBuildableResourceExtractor",
            "properties": {
                "mExtractCycleTime": "0.250000",
                "mItemsPerCycle": "1",
                "mAllowedResourceForms": "(RF_SOLID)",
                "mOnlyAllowCertainResources": "False",
                "mAllowedResources": "",
                "mPowerConsumption": "45.000000",
                "mPowerConsumptionExponent": "1.321929",
            },
        },
        "Build_OilPump_C": {
            "native_class": "FGBuildableResourceExtractor",
            "properties": {
                "mExtractCycleTime": "1.000000",
                "mItemsPerCycle": "2000",
                "mAllowedResourceForms": "(RF_LIQUID)",
                "mOnlyAllowCertainResources": "True",
                "mAllowedResources": f'("{_object_path("Desc_LiquidOil_C")}")',
                "mPowerConsumption": "40.000000",
                "mPowerConsumptionExponent": "1.321929",
            },
        },
        "Build_FrackingExtractor_C": {
            "native_class": "FGBuildableFrackingExtractor",
            "properties": {
                "mExtractCycleTime": "1.000000",
                "mItemsPerCycle": "1000",
                "mAllowedResourceForms": "(RF_LIQUID,RF_GAS)",
                "mOnlyAllowCertainResources": "True",
                "mAllowedResources": f'("{_object_path("Desc_LiquidOil_C")}")',
                "mPowerConsumption": "0.000000",
            },
        },
    }
    core = {
        "format_version": 1,
        "native_class_count": 4,
        "class_count": len(classes),
        "native_classes": {},
        "classes": classes,
    }
    locale = {
        "format_version": 1,
        "locale": "fr",
        "class_count": len(classes),
        "localized_value_count": 10,
        "placeholder_value_count": 0,
        "wrapped_untranslated_value_count": 0,
        "entries": {
            "Recipe_IronIngot_C": {"mDisplayName": "Lingot de fer"},
            "Recipe_IronPlate_C": {"mDisplayName": "Plaque de fer"},
            "Recipe_Plastic_C": {"mDisplayName": "Plastique"},
            "Desc_OreIron_C": {"mDisplayName": "Minerai de fer"},
            "Desc_IronIngot_C": {"mDisplayName": "Lingot de fer"},
            "Desc_IronPlate_C": {"mDisplayName": "Plaque de fer"},
            "Desc_LiquidOil_C": {"mDisplayName": "Pétrole brut"},
            "Desc_Plastic_C": {"mDisplayName": "Plastique"},
            "Desc_HeavyOilResidue_C": {"mDisplayName": "Résidus de pétrole lourd"},
            "Build_SmelterMk1_C": {"mDisplayName": "Fonderie"},
            "Build_ConstructorMk1_C": {"mDisplayName": "Constructeur"},
            "Build_OilRefinery_C": {"mDisplayName": "Raffinerie"},
            "Build_MinerMk3_C": {"mDisplayName": "Foreuse Mk.3"},
            "Build_OilPump_C": {"mDisplayName": "Extracteur de pétrole"},
            "Build_FrackingExtractor_C": {"mDisplayName": "Extracteur de puits"},
        },
    }
    (catalog_dir / "core.json").write_text(
        json.dumps(core),
        encoding="utf-8",
    )
    (locales_dir / "fr.json").write_text(
        json.dumps(locale),
        encoding="utf-8",
    )
    return catalog_dir


def test_production_service_builds_recursive_plan_from_catalog(tmp_path):
    catalog_dir = _write_catalog(tmp_path)

    plan = ProductionService(catalog_dir).plan_production(
        target_class_name="Desc_IronPlate_C",
        target_rate_per_minute=60,
    )

    lines = {line.recipe_class: line for line in plan.machine_requirements}
    assert plan.target_name == "Plaque de fer"
    assert lines["Recipe_IronPlate_C"].machine_count == 3
    assert lines["Recipe_IronIngot_C"].machine_count == 3
    assert plan.resource_requirements[0].display_name == "Minerai de fer"
    assert plan.resource_requirements[0].rate_per_minute == Decimal("90")
    assert plan.resource_requirements[0].selected_extractor_class == "Build_MinerMk3_C"
    assert plan.power_estimate_complete is True


def test_production_service_converts_fluid_extraction_rates_to_cubic_meters(tmp_path):
    catalog_dir = _write_catalog(tmp_path)

    plan = ProductionService(catalog_dir).plan_production(
        target_class_name="Desc_Plastic_C",
        target_rate_per_minute=40,
    )

    oil = plan.resource_requirements[0]
    assert oil.class_name == "Desc_LiquidOil_C"
    assert oil.rate_per_minute == Decimal("60")
    assert oil.unit_label == "m³"
    assert oil.selected_extractor_class == "Build_OilPump_C"
    assert oil.extraction_options[0].effective_rate_per_minute == Decimal("120")
    assert oil.extraction_options[0].machine_equivalents == Decimal("0.5")
    assert plan.byproducts[0].rate_per_minute == Decimal("20")
    assert plan.byproducts[0].unit_label == "m³"


def test_production_service_can_select_resource_well_extractor(tmp_path):
    catalog_dir = _write_catalog(tmp_path)

    plan = ProductionService(catalog_dir).plan_production(
        target_class_name="Desc_Plastic_C",
        target_rate_per_minute=40,
        extractor_choices={"Desc_LiquidOil_C": "Build_FrackingExtractor_C"},
    )

    oil = plan.resource_requirements[0]
    assert oil.selected_extractor_class == "Build_FrackingExtractor_C"
    assert plan.power_estimate_complete is False
    assert any("réseau de puits" in warning for warning in plan.warnings)
    assert any("puissance de l'extraction" in warning for warning in plan.warnings)


def test_production_service_accepts_resource_node_yield_multiplier(tmp_path):
    catalog_dir = _write_catalog(tmp_path)

    plan = ProductionService(catalog_dir).plan_production(
        target_class_name="Desc_Plastic_C",
        target_rate_per_minute=40,
        resource_node_multipliers={"Desc_LiquidOil_C": "2"},
    )

    oil = plan.resource_requirements[0]
    oil_pump = next(
        option
        for option in oil.extraction_options
        if option.extractor_class == "Build_OilPump_C"
    )
    assert oil_pump.effective_rate_per_minute == Decimal("240")
    assert oil_pump.machine_equivalents == Decimal("0.25")


def test_production_service_exposes_recipe_options_for_future_ui(tmp_path):
    catalog_dir = _write_catalog(tmp_path)

    options = ProductionService(catalog_dir).list_recipe_options("Desc_IronPlate_C")

    assert len(options) == 1
    assert options[0].class_name == "Recipe_IronPlate_C"


def test_production_service_rejects_missing_catalog(tmp_path):
    with pytest.raises(FileNotFoundError, match="catalogue Satisfactory n'est pas installé"):
        ProductionService(tmp_path / "missing").plan_production(
            target_class_name="Desc_IronPlate_C",
            target_rate_per_minute=60,
        )
