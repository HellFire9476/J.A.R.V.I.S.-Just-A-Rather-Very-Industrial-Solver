"""Tests du décodage des recettes du catalogue Satisfactory."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from jarvis.application.services.recipe_service import (
    RecipeFormatError,
    RecipeService,
)


def _write_catalog(tmp_path, *, ingredients: str = ""):
    catalog_dir = tmp_path / "Catalog"
    locales_dir = catalog_dir / "locales"
    locales_dir.mkdir(parents=True)

    classes = {
        "Recipe_IronPlate_C": {
            "native_class": "FGRecipe",
            "properties": {
                "mIngredients": ingredients,
                "mProduct": (
                    "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass'"
                    "/Game/FactoryGame/Resource/Parts/IronPlate/"
                    "Desc_IronPlate.Desc_IronPlate_C'\",Amount=2))"
                ),
                "mManufactoringDuration": "6.000000",
                "mProducedIn": (
                    '("/Game/FactoryGame/Buildable/Factory/ConstructorMk1/'
                    'Build_ConstructorMk1.Build_ConstructorMk1_C",'
                    '"/Game/FactoryGame/Buildable/-Shared/WorkBench/'
                    'BP_WorkBenchComponent.BP_WorkBenchComponent_C",'
                    '"/Script/FactoryGame.FGBuildableAutomatedWorkBench")'
                ),
            },
        },
        "Desc_IronIngot_C": {
            "native_class": "FGItemDescriptor",
            "properties": {"mForm": "RF_SOLID"},
        },
        "Desc_LiquidOil_C": {
            "native_class": "FGResourceDescriptor",
            "properties": {"mForm": "RF_LIQUID"},
        },
        "Desc_NitrogenGas_C": {
            "native_class": "FGItemDescriptor",
            "properties": {"mForm": "RF_GAS"},
        },
        "Desc_IronPlate_C": {
            "native_class": "FGItemDescriptor",
            "properties": {"mForm": "RF_SOLID"},
        },
        "Build_ConstructorMk1_C": {
            "native_class": "FGBuildableManufacturer",
            "properties": {},
        },
    }
    core = {
        "format_version": 1,
        "native_class_count": 3,
        "class_count": len(classes),
        "native_classes": {},
        "classes": classes,
    }
    locale = {
        "format_version": 1,
        "locale": "fr",
        "class_count": len(classes),
        "localized_value_count": 4,
        "placeholder_value_count": 0,
        "wrapped_untranslated_value_count": 0,
        "entries": {
            "Recipe_IronPlate_C": {"mDisplayName": "Plaque de fer"},
            "Desc_IronIngot_C": {"mDisplayName": "Lingot de fer"},
            "Desc_IronPlate_C": {"mDisplayName": "Plaque de fer"},
            "Desc_LiquidOil_C": {
                "mDisplayName": "Pétrole brut",
                "mDescription": "Raffiné pour produire du carburant et du plastique.",
            },
            "Desc_NitrogenGas_C": {
                "mDisplayName": "Azote",
                "mDescription": "Utilisé dans différents procédés industriels.",
            },
            "Build_ConstructorMk1_C": {
                "mDisplayName": "Constructeur",
                "mDescription": "Transforme une pièce en une nouvelle pièce.",
            },
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


def _ingredient_string() -> str:
    return (
        "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass'"
        "/Game/FactoryGame/Resource/Parts/IronIngot/"
        "Desc_IronIngot.Desc_IronIngot_C'\",Amount=3))"
    )


def test_recipe_service_resolves_components_and_machines(tmp_path):
    catalog_dir = _write_catalog(tmp_path, ingredients=_ingredient_string())

    recipes = RecipeService(catalog_dir).list_recipes("fr")

    assert len(recipes) == 1
    recipe = recipes[0]
    assert recipe.class_name == "Recipe_IronPlate_C"
    assert recipe.display_name == "Plaque de fer"
    assert recipe.duration_seconds == Decimal("6.000000")
    assert recipe.ingredients[0].class_name == "Desc_IronIngot_C"
    assert recipe.ingredients[0].display_name == "Lingot de fer"
    assert recipe.ingredients[0].amount == Decimal("3")
    assert recipe.products[0].display_name == "Plaque de fer"
    assert recipe.products[0].amount == Decimal("2")
    assert recipe.producer_names == ("Constructeur", "Établi")
    assert recipe.recipe_type == "production"


def test_recipe_service_converts_liquids_and_gases_from_liters_to_cubic_meters(
    tmp_path,
):
    liquid_ingredient = (
        "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass'"
        "/Game/FactoryGame/Resource/RawResources/CrudeOil/"
        "Desc_LiquidOil.Desc_LiquidOil_C'\",Amount=3000))"
    )
    catalog_dir = _write_catalog(tmp_path, ingredients=liquid_ingredient)

    recipe = RecipeService(catalog_dir).list_recipes("fr")[0]
    component = recipe.ingredients[0]

    assert component.display_name == "Pétrole brut"
    assert component.amount == Decimal("3")
    assert component.source_amount == Decimal("3000")
    assert component.form == "RF_LIQUID"
    assert component.is_fluid is True
    assert component.unit_label == "m³"
    assert component.description == "Raffiné pour produire du carburant et du plastique."


def test_recipe_service_converts_gas_amounts_to_cubic_meters(tmp_path):
    gas_ingredient = (
        "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass'"
        "/Game/FactoryGame/Resource/RawResources/NitrogenGas/"
        "Desc_NitrogenGas.Desc_NitrogenGas_C'\",Amount=2500))"
    )
    catalog_dir = _write_catalog(tmp_path, ingredients=gas_ingredient)

    recipe = RecipeService(catalog_dir).list_recipes("fr")[0]
    component = recipe.ingredients[0]

    assert component.display_name == "Azote"
    assert component.amount == Decimal("2.5")
    assert component.source_amount == Decimal("2500")
    assert component.form == "RF_GAS"
    assert component.is_fluid is True
    assert component.unit_label == "m³"


def test_recipe_service_resolves_building_descriptors_from_construction_recipe(
    tmp_path,
):
    catalog_dir = _write_catalog(tmp_path, ingredients=_ingredient_string())
    core_path = catalog_dir / "core.json"
    locale_path = catalog_dir / "locales" / "fr.json"
    core = json.loads(core_path.read_text(encoding="utf-8"))
    locale = json.loads(locale_path.read_text(encoding="utf-8"))

    core["classes"].update(
        {
            "Recipe_WorkBench_C": {
                "native_class": "FGRecipe",
                "properties": {
                    "mIngredients": "()",
                    "mProduct": (
                        "((ItemClass=\"/Script/Engine.BlueprintGeneratedClass'"
                        "/Game/FactoryGame/Buildable/Factory/WorkBench/"
                        "Desc_WorkBench.Desc_WorkBench_C'\",Amount=1))"
                    ),
                    "mManufactoringDuration": "1.000000",
                    "mProducedIn": "()",
                },
            },
            "Desc_WorkBench_C": {
                "native_class": "FGBuildingDescriptor",
                "properties": {"mForm": "RF_INVALID"},
            },
            "Build_WorkBench_C": {
                "native_class": "FGBuildable",
                "properties": {},
            },
        }
    )
    locale["entries"].update(
        {
            "Recipe_WorkBench_C": {"mDisplayName": "Établi"},
            "Build_WorkBench_C": {
                "mDisplayName": "Établi",
                "mDescription": "Poste manuel de fabrication.",
            },
        }
    )
    core_path.write_text(json.dumps(core), encoding="utf-8")
    locale_path.write_text(json.dumps(locale), encoding="utf-8")

    recipes = RecipeService(catalog_dir).list_recipes("fr")
    workbench_recipe = next(
        recipe for recipe in recipes if recipe.class_name == "Recipe_WorkBench_C"
    )

    assert workbench_recipe.products[0].display_name == "Établi"
    assert workbench_recipe.products[0].description == "Poste manuel de fabrication."


def test_recipe_service_keeps_solid_amounts_as_item_counts(tmp_path):
    catalog_dir = _write_catalog(tmp_path, ingredients=_ingredient_string())

    recipe = RecipeService(catalog_dir).list_recipes("fr")[0]
    component = recipe.ingredients[0]

    assert component.amount == Decimal("3")
    assert component.source_amount == Decimal("3")
    assert component.form == "RF_SOLID"
    assert component.is_fluid is False
    assert component.unit_label == "unité"


def test_recipe_service_loads_localized_machine_description(tmp_path):
    catalog_dir = _write_catalog(tmp_path, ingredients=_ingredient_string())

    recipe = RecipeService(catalog_dir).list_recipes("fr")[0]

    assert recipe.producers[0].description == (
        "Transforme une pièce en une nouvelle pièce."
    )


def test_recipe_service_keeps_recipes_with_no_declared_ingredients(tmp_path):
    catalog_dir = _write_catalog(tmp_path)

    recipes = RecipeService(catalog_dir).list_recipes("fr")

    assert len(recipes) == 1
    assert recipes[0].ingredients == ()
    assert recipes[0].products[0].amount == Decimal("2")


def test_recipe_service_rejects_unrecognized_component_structure(tmp_path):
    catalog_dir = _write_catalog(
        tmp_path,
        ingredients="((UnexpectedField=3))",
    )

    with pytest.raises(RecipeFormatError, match="Structure non reconnue"):
        RecipeService(catalog_dir).list_recipes("fr")


def test_recipe_service_returns_empty_when_catalog_is_missing(tmp_path):
    service = RecipeService(tmp_path / "missing")

    assert service.is_initialized is False
    assert service.list_recipes("fr") == []
