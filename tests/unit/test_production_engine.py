"""Tests du moteur récursif de calcul de production."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from jarvis.domain.entities.production import (
    ExtractorProfile,
    ItemProfile,
    MachineProfile,
)
from jarvis.domain.entities.recipe import Recipe, RecipeComponent, RecipeProducer
from jarvis.engines.production_engine import (
    InvalidExtractorChoiceError,
    InvalidProductionRateError,
    InvalidRecipeChoiceError,
    NonAutomatableRecipeError,
    ProducerChoiceRequiredError,
    ProductionCycleError,
    ProductionEngine,
    RecipeChoiceRequiredError,
    UnknownProductionItemError,
)


def _item(
    class_name: str,
    *,
    form: str = "RF_SOLID",
    native_class: str = "FGItemDescriptor",
) -> ItemProfile:
    return ItemProfile(
        class_name=class_name,
        display_name=class_name.removesuffix("_C"),
        form=form,
        native_class=native_class,
    )


def _component(class_name: str, amount: str, *, form: str = "RF_SOLID"):
    return RecipeComponent(
        class_name=class_name,
        display_name=class_name.removesuffix("_C"),
        amount=Decimal(amount),
        form=form,
    )


def _recipe(
    class_name: str,
    *,
    ingredients: tuple[RecipeComponent, ...],
    products: tuple[RecipeComponent, ...],
    duration: str = "6",
    producer: str = "Build_ConstructorMk1_C",
    producer_type: str = "manufacturer",
) -> Recipe:
    return Recipe(
        class_name=class_name,
        display_name=class_name.removeprefix("Recipe_").removesuffix("_C"),
        duration_seconds=Decimal(duration),
        ingredients=ingredients,
        products=products,
        producers=(
            RecipeProducer(
                class_name=producer,
                display_name=producer.removesuffix("_C"),
                producer_type=producer_type,
            ),
        ),
        recipe_type="production",
    )


def _machine(
    class_name: str,
    *,
    power: str | None = "4",
    speed: str = "1",
    exponent: str = "1.321929",
    minimum_power: str | None = None,
    maximum_power: str | None = None,
    min_clock: str = "0.01",
) -> MachineProfile:
    return MachineProfile(
        class_name=class_name,
        display_name=class_name.removesuffix("_C"),
        manufacturing_speed=Decimal(speed),
        fixed_power_mw=Decimal(power) if power is not None else None,
        power_exponent=Decimal(exponent),
        estimated_power_min_mw=(
            Decimal(minimum_power) if minimum_power is not None else None
        ),
        estimated_power_max_mw=(
            Decimal(maximum_power) if maximum_power is not None else None
        ),
        minimum_clock_fraction=Decimal(min_clock),
    )


def _engine(
    recipes: tuple[Recipe, ...],
    items: tuple[ItemProfile, ...],
    *,
    machines: tuple[MachineProfile, ...] | None = None,
    extractors: tuple[ExtractorProfile, ...] | None = None,
) -> ProductionEngine:
    machine_profiles = machines or (
        _machine("Build_ConstructorMk1_C"),
        _machine("Build_SmelterMk1_C"),
        _machine("Build_AssemblerMk1_C", power="15"),
    )
    return ProductionEngine(
        recipes=recipes,
        item_profiles={item.class_name: item for item in items},
        machine_profiles={machine.class_name: machine for machine in machine_profiles},
        extractor_profiles=extractors or (),
    )


def test_engine_recursively_calculates_materials_machines_and_power():
    recipes = (
        _recipe(
            "Recipe_IronIngot_C",
            ingredients=(_component("Desc_OreIron_C", "1"),),
            products=(_component("Desc_IronIngot_C", "1"),),
            duration="2",
            producer="Build_SmelterMk1_C",
        ),
        _recipe(
            "Recipe_IronPlate_C",
            ingredients=(_component("Desc_IronIngot_C", "3"),),
            products=(_component("Desc_IronPlate_C", "2"),),
            duration="6",
            producer="Build_ConstructorMk1_C",
        ),
    )
    extractor = ExtractorProfile(
        class_name="Build_MinerMk3_C",
        display_name="Foreuse Mk.3",
        base_rate_per_minute=Decimal("240"),
        form="RF_SOLID",
        allowed_forms=frozenset({"RF_SOLID"}),
        fixed_power_mw=Decimal("45"),
    )
    engine = _engine(
        recipes,
        (
            _item("Desc_OreIron_C", native_class="FGResourceDescriptor"),
            _item("Desc_IronIngot_C"),
            _item("Desc_IronPlate_C"),
        ),
        machines=(
            _machine("Build_ConstructorMk1_C"),
            _machine("Build_SmelterMk1_C"),
        ),
        extractors=(extractor,),
    )

    plan = engine.plan(
        target_class_name="Desc_IronPlate_C",
        target_rate_per_minute=60,
        locale="fr",
    )

    assert plan.target_rate_per_minute == Decimal("60")
    assert len(plan.machine_requirements) == 2
    lines = {line.recipe_class: line for line in plan.machine_requirements}
    assert lines["Recipe_IronPlate_C"].cycles_per_minute == Decimal("30")
    assert lines["Recipe_IronPlate_C"].machine_equivalents == Decimal("3")
    assert lines["Recipe_IronPlate_C"].machine_count == 3
    assert lines["Recipe_IronIngot_C"].cycles_per_minute == Decimal("90")
    assert lines["Recipe_IronIngot_C"].machine_count == 3

    assert len(plan.resource_requirements) == 1
    ore = plan.resource_requirements[0]
    assert ore.rate_per_minute == Decimal("90")
    assert ore.selected_extractor_class == "Build_MinerMk3_C"
    assert ore.extraction_options[0].machine_equivalents == Decimal("0.375")
    assert ore.extraction_options[0].clock_percent == Decimal("37.500")
    assert plan.power_estimate_complete is True
    assert plan.total_power_min_mw == plan.total_power_max_mw


def test_engine_reports_multi_output_byproducts_without_netted_credit():
    recipe = _recipe(
        "Recipe_Plastic_C",
        ingredients=(
            _component("Desc_LiquidOil_C", "3", form="RF_LIQUID"),
        ),
        products=(
            _component("Desc_Plastic_C", "2"),
            _component("Desc_HeavyOilResidue_C", "1", form="RF_LIQUID"),
        ),
        duration="6",
        producer="Build_OilRefinery_C",
    )
    engine = _engine(
        (recipe,),
        (
            _item("Desc_LiquidOil_C", form="RF_LIQUID", native_class="FGResourceDescriptor"),
            _item("Desc_Plastic_C"),
            _item("Desc_HeavyOilResidue_C", form="RF_LIQUID"),
        ),
        machines=(_machine("Build_OilRefinery_C", power="30"),),
    )

    plan = engine.plan(
        target_class_name="Desc_Plastic_C",
        target_rate_per_minute=40,
        locale="fr",
    )

    assert plan.resource_requirements[0].rate_per_minute == Decimal("60")
    assert plan.resource_requirements[0].unit_label == "m³"
    assert len(plan.byproducts) == 1
    assert plan.byproducts[0].class_name == "Desc_HeavyOilResidue_C"
    assert plan.byproducts[0].rate_per_minute == Decimal("20")
    assert plan.byproducts[0].unit_label == "m³"
    assert any("coproduits" in warning.casefold() for warning in plan.warnings)


def test_engine_selects_unique_standard_recipe_before_alternatives():
    standard = _recipe(
        "Recipe_IronIngot_C",
        ingredients=(_component("Desc_OreIron_C", "1"),),
        products=(_component("Desc_IronIngot_C", "1"),),
        producer="Build_SmelterMk1_C",
    )
    alternate = _recipe(
        "Recipe_Alternate_IronIngot_C",
        ingredients=(_component("Desc_OreIron_C", "2"),),
        products=(_component("Desc_IronIngot_C", "2"),),
        producer="Build_AssemblerMk1_C",
    )
    engine = _engine(
        (standard, alternate),
        (_item("Desc_OreIron_C", native_class="FGResourceDescriptor"), _item("Desc_IronIngot_C")),
    )

    plan = engine.plan(
        target_class_name="Desc_IronIngot_C",
        target_rate_per_minute=30,
        locale="fr",
    )

    assert [line.recipe_class for line in plan.machine_requirements] == [
        "Recipe_IronIngot_C"
    ]


def test_engine_accepts_explicit_alternate_recipe_selection():
    standard = _recipe(
        "Recipe_IronIngot_C",
        ingredients=(_component("Desc_OreIron_C", "1"),),
        products=(_component("Desc_IronIngot_C", "1"),),
        producer="Build_SmelterMk1_C",
    )
    alternate = _recipe(
        "Recipe_Alternate_IronIngot_C",
        ingredients=(_component("Desc_OreIron_C", "2"),),
        products=(_component("Desc_IronIngot_C", "2"),),
        producer="Build_AssemblerMk1_C",
    )
    engine = _engine(
        (standard, alternate),
        (_item("Desc_OreIron_C", native_class="FGResourceDescriptor"), _item("Desc_IronIngot_C")),
    )

    plan = engine.plan(
        target_class_name="Desc_IronIngot_C",
        target_rate_per_minute=30,
        locale="fr",
        recipe_choices={"Desc_IronIngot_C": "Recipe_Alternate_IronIngot_C"},
    )

    assert plan.machine_requirements[0].recipe_class == "Recipe_Alternate_IronIngot_C"
    assert plan.resource_requirements[0].rate_per_minute == Decimal("30")


def test_engine_requires_explicit_choice_when_multiple_standard_recipes_exist():
    recipes = tuple(
        _recipe(
            name,
            ingredients=(_component("Desc_Input_C", "1"),),
            products=(_component("Desc_Output_C", "1"),),
        )
        for name in ("Recipe_OutputA_C", "Recipe_OutputB_C")
    )
    engine = _engine(recipes, (_item("Desc_Input_C"), _item("Desc_Output_C")))

    with pytest.raises(RecipeChoiceRequiredError) as error:
        engine.plan(
            target_class_name="Desc_Output_C",
            target_rate_per_minute=10,
            locale="fr",
        )

    assert error.value.item_class == "Desc_Output_C"
    assert set(error.value.recipe_classes) == {"Recipe_OutputA_C", "Recipe_OutputB_C"}


def test_engine_treats_resource_descriptors_as_raw_inputs_by_default():
    artificial_recipe = _recipe(
        "Recipe_Coal_Synthetic_C",
        ingredients=(_component("Desc_Biomass_C", "1"),),
        products=(_component("Desc_Coal_C", "2"),),
    )
    engine = _engine(
        (artificial_recipe,),
        (
            _item("Desc_Coal_C", native_class="FGResourceDescriptor"),
            _item("Desc_Biomass_C"),
        ),
    )

    plan = engine.plan(
        target_class_name="Desc_Coal_C",
        target_rate_per_minute=60,
        locale="fr",
    )

    assert plan.machine_requirements == ()
    assert plan.resource_requirements[0].rate_per_minute == Decimal("60")


def test_engine_detects_recursive_production_cycles():
    recipes = (
        _recipe(
            "Recipe_A_C",
            ingredients=(_component("Desc_B_C", "1"),),
            products=(_component("Desc_A_C", "1"),),
        ),
        _recipe(
            "Recipe_B_C",
            ingredients=(_component("Desc_A_C", "1"),),
            products=(_component("Desc_B_C", "1"),),
        ),
    )
    engine = _engine(recipes, (_item("Desc_A_C"), _item("Desc_B_C")))

    with pytest.raises(ProductionCycleError, match="Cycle de production détecté"):
        engine.plan(
            target_class_name="Desc_A_C",
            target_rate_per_minute=1,
            locale="fr",
        )


def test_engine_rejects_recipe_without_automated_producer():
    recipe = _recipe(
        "Recipe_Handmade_C",
        ingredients=(_component("Desc_Input_C", "1"),),
        products=(_component("Desc_Output_C", "1"),),
        producer="BP_WorkBenchComponent_C",
        producer_type="workbench",
    )
    engine = _engine(recipes=(recipe,), items=(_item("Desc_Input_C"), _item("Desc_Output_C")))

    with pytest.raises(NonAutomatableRecipeError):
        engine.plan(
            target_class_name="Desc_Output_C",
            target_rate_per_minute=1,
            locale="fr",
        )


def test_engine_requires_producer_choice_when_several_automated_machines_exist():
    recipe = _recipe(
        "Recipe_Output_C",
        ingredients=(_component("Desc_Input_C", "1"),),
        products=(_component("Desc_Output_C", "1"),),
    )
    second_producer = RecipeProducer(
        class_name="Build_AssemblerMk1_C",
        display_name="Assembleuse",
        producer_type="manufacturer",
    )
    recipe = replace(recipe, producers=(recipe.producers[0], second_producer))
    engine = _engine(
        (recipe,),
        (_item("Desc_Input_C"), _item("Desc_Output_C")),
    )

    with pytest.raises(ProducerChoiceRequiredError):
        engine.plan(
            target_class_name="Desc_Output_C",
            target_rate_per_minute=1,
            locale="fr",
        )

    plan = engine.plan(
        target_class_name="Desc_Output_C",
        target_rate_per_minute=1,
        locale="fr",
        producer_choices={"Recipe_Output_C": "Build_AssemblerMk1_C"},
    )
    assert plan.machine_requirements[0].producer_class == "Build_AssemblerMk1_C"


def test_engine_reports_variable_machine_power_as_a_range():
    recipe = _recipe(
        "Recipe_Output_C",
        ingredients=(_component("Desc_Input_C", "1"),),
        products=(_component("Desc_Output_C", "1"),),
        duration="2",
    )
    machine = _machine(
        "Build_ConstructorMk1_C",
        power=None,
        minimum_power="100",
        maximum_power="400",
    )
    engine = _engine(
        (recipe,),
        (_item("Desc_Input_C"), _item("Desc_Output_C")),
        machines=(machine,),
    )

    plan = engine.plan(
        target_class_name="Desc_Output_C",
        target_rate_per_minute=30,
        locale="fr",
    )

    line = plan.machine_requirements[0]
    assert line.power_model == "range"
    assert line.power_min_mw == Decimal("100")
    assert line.power_max_mw == Decimal("400")
    assert plan.power_estimate_complete is True
    assert plan.total_power_min_mw == Decimal("100")
    assert plan.total_power_max_mw == Decimal("400")


def test_engine_applies_node_yield_multiplier_to_extraction_capacity():
    recipe = _recipe(
        "Recipe_Output_C",
        ingredients=(_component("Desc_Ore_C", "120"),),
        products=(_component("Desc_Output_C", "1"),),
    )
    extractor = ExtractorProfile(
        class_name="Build_MinerMk3_C",
        display_name="Foreuse Mk.3",
        base_rate_per_minute=Decimal("240"),
        form="RF_SOLID",
        allowed_forms=frozenset({"RF_SOLID"}),
        fixed_power_mw=Decimal("45"),
        node_based=True,
    )
    engine = _engine(
        (recipe,),
        (
            _item("Desc_Ore_C", native_class="FGResourceDescriptor"),
            _item("Desc_Output_C"),
        ),
        extractors=(extractor,),
    )

    normal = engine.plan(
        target_class_name="Desc_Output_C",
        target_rate_per_minute=1,
        locale="fr",
    )
    impure = engine.plan(
        target_class_name="Desc_Output_C",
        target_rate_per_minute=1,
        locale="fr",
        resource_node_multipliers={"Desc_Ore_C": "0.5"},
    )

    normal_option = normal.resource_requirements[0].extraction_options[0]
    assert normal_option.machine_equivalents == Decimal("0.5")
    assert impure.resource_requirements[0].extraction_options[0].machine_equivalents == Decimal("1")


def test_engine_rejects_invalid_target_and_choices():
    recipe = _recipe(
        "Recipe_Output_C",
        ingredients=(_component("Desc_Input_C", "1"),),
        products=(_component("Desc_Output_C", "1"),),
    )
    extractor = ExtractorProfile(
        class_name="Build_MinerMk1_C",
        display_name="Foreuse Mk.1",
        base_rate_per_minute=Decimal("60"),
        form="RF_SOLID",
        allowed_forms=frozenset({"RF_SOLID"}),
    )
    engine = _engine(
        (recipe,),
        (_item("Desc_Input_C", native_class="FGResourceDescriptor"), _item("Desc_Output_C")),
        extractors=(extractor,),
    )

    with pytest.raises(InvalidProductionRateError):
        engine.plan(target_class_name="Desc_Output_C", target_rate_per_minute=0, locale="fr")
    with pytest.raises(UnknownProductionItemError):
        engine.plan(target_class_name="Missing_C", target_rate_per_minute=1, locale="fr")
    with pytest.raises(InvalidRecipeChoiceError):
        engine.plan(
            target_class_name="Desc_Output_C",
            target_rate_per_minute=1,
            locale="fr",
            recipe_choices={"Desc_Output_C": "Recipe_NotHere_C"},
        )
    with pytest.raises(InvalidExtractorChoiceError):
        engine.plan(
            target_class_name="Desc_Output_C",
            target_rate_per_minute=1,
            locale="fr",
            extractor_choices={"Desc_Input_C": "Build_NotMiner_C"},
        )
