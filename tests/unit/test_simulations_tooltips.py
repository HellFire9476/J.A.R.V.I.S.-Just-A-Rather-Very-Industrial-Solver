"""Vérifie les aides contextuelles de la page Simulations."""

from __future__ import annotations

from decimal import Decimal

import pytest

from jarvis.domain.entities.production import (
    ExtractionOption,
    MachineRequirement,
    ProductionPlan,
    RateAmount,
    ResourceRequirement,
)
from jarvis.domain.entities.recipe import Recipe, RecipeComponent, RecipeProducer

_QT_APPLICATION = None


def _new_page():
    global _QT_APPLICATION
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.simulations.page import SimulationsPage

    _QT_APPLICATION = QApplication.instance() or QApplication([])
    return SimulationsPage(service=object())


def _sample_plan() -> tuple[ProductionPlan, Recipe]:
    recipe = Recipe(
        class_name="Recipe_IronPlate_C",
        display_name="Plaque de fer",
        duration_seconds=Decimal("6"),
        ingredients=(
            RecipeComponent(
                class_name="Desc_IronOre_C",
                display_name="Minerai de fer",
                amount=Decimal("3"),
                form="RF_SOLID",
                description="Minerai extrait d'un gisement de fer.",
            ),
        ),
        products=(
            RecipeComponent(
                class_name="Desc_IronPlate_C",
                display_name="Plaque de fer",
                amount=Decimal("2"),
                form="RF_SOLID",
            ),
        ),
        producers=(
            RecipeProducer(
                class_name="Desc_ConstructorMk1_C",
                display_name="Constructeur",
                producer_type="manufacturer",
                description="Transforme des matériaux en composants.",
            ),
        ),
        recipe_type="Standard",
    )
    machine = MachineRequirement(
        recipe_class=recipe.class_name,
        recipe_name=recipe.display_name,
        producer_class="Desc_ConstructorMk1_C",
        producer_name="Constructeur",
        cycles_per_minute=Decimal("30"),
        machine_equivalents=Decimal("1.25"),
        machine_count=1,
        clock_percent=Decimal("125"),
        clock_limit_percent=Decimal("125"),
        inputs=(
            RateAmount(
                class_name="Desc_IronOre_C",
                display_name="Minerai de fer",
                rate_per_minute=Decimal("90"),
                form="RF_SOLID",
                unit_label="objet",
            ),
        ),
        outputs=(
            RateAmount(
                class_name="Desc_IronPlate_C",
                display_name="Plaque de fer",
                rate_per_minute=Decimal("60"),
                form="RF_SOLID",
                unit_label="objet",
            ),
        ),
        power_min_mw=Decimal("4"),
        power_max_mw=Decimal("4"),
        power_model="fixed",
    )
    resource = ResourceRequirement(
        class_name="Desc_IronOre_C",
        display_name="Minerai de fer",
        rate_per_minute=Decimal("90"),
        form="RF_SOLID",
        unit_label="objet",
        is_game_resource=True,
        node_yield_multiplier=Decimal("1"),
        extraction_options=(
            ExtractionOption(
                extractor_class="Build_MinerMk1_C",
                extractor_name="Foreuse Mk.1",
                base_rate_per_minute=Decimal("60"),
                effective_rate_per_minute=Decimal("60"),
                machine_equivalents=Decimal("1.5"),
                machine_count=2,
                clock_percent=Decimal("75"),
                clock_limit_percent=Decimal("125"),
                power_min_mw=Decimal("10"),
                power_max_mw=Decimal("10"),
                power_model="fixed",
                requires_resource_well=False,
            ),
        ),
        selected_extractor_class="Build_MinerMk1_C",
    )
    plan = ProductionPlan(
        target_class_name="Desc_IronPlate_C",
        target_name="Plaque de fer",
        target_rate_per_minute=Decimal("60"),
        target_unit_label="objet",
        locale="fr",
        machine_requirements=(machine,),
        resource_requirements=(resource,),
        byproducts=(
            RateAmount(
                class_name="Desc_Concrete_C",
                display_name="Béton",
                rate_per_minute=Decimal("2"),
                form="RF_SOLID",
                unit_label="objet",
            ),
        ),
        production_power_min_mw=Decimal("4"),
        production_power_max_mw=Decimal("4"),
        extraction_power_min_mw=Decimal("5"),
        extraction_power_max_mw=Decimal("5"),
        total_power_min_mw=Decimal("9"),
        total_power_max_mw=Decimal("9"),
        power_estimate_complete=True,
        warnings=(),
    )
    return plan, recipe


def test_simulations_controls_and_table_headers_have_tooltips() -> None:
    page = _new_page()

    for widget in (
        page.scope_label,
        page.target_combo,
        page.target_combo.lineEdit(),
        page.rate_spin,
        page.locale_combo,
        page.recipe_combo,
        page.calculate_button,
        page.status_label,
    ):
        assert widget.toolTip().strip()

    for table in (page.machine_table, page.resource_table, page.byproduct_table):
        for column in range(table.columnCount()):
            header = table.horizontalHeaderItem(column)
            assert header is not None
            assert header.toolTip().strip()

    assert "Machines équivalentes à 100 %" in page.machine_table.horizontalHeaderItem(3).text()
    page.close()


def test_simulations_result_cells_and_metrics_have_explanatory_tooltips() -> None:
    page = _new_page()
    plan, recipe = _sample_plan()
    page._recipes_by_class = {recipe.class_name: recipe}

    page._render_plan(plan)

    for column in range(page.machine_table.columnCount()):
        widget = page.machine_table.cellWidget(0, column)
        item = page.machine_table.item(0, column)
        assert (widget is not None and widget.toolTip().strip()) or (
            item is not None and item.toolTip().strip()
        )
    assert all(
        "Recipe_IronPlate_C" not in (
            page.machine_table.item(0, column).toolTip()
            if page.machine_table.item(0, column) is not None
            else ""
        )
        for column in range(page.machine_table.columnCount())
    )

    for column in range(page.resource_table.columnCount()):
        widget = page.resource_table.cellWidget(0, column)
        item = page.resource_table.item(0, column)
        assert (widget is not None and widget.toolTip().strip()) or (
            item is not None and item.toolTip().strip()
        )

    for column in range(page.byproduct_table.columnCount()):
        item = page.byproduct_table.item(0, column)
        assert item is not None and item.toolTip().strip()

    for _card, value in (page.target_metric, page.machine_metric, page.power_metric):
        assert value.toolTip().strip()

    assert "Fabrication" in page.power_metric[1].toolTip()
    assert "Extraction" in page.power_metric[1].toolTip()
    page.close()


def test_recipe_choice_labels_hide_internal_class_names_and_explain_recipe() -> None:
    page = _new_page()
    _plan, recipe = _sample_plan()
    label = type(page)._recipe_choice_label(recipe)
    details = type(page)._recipe_details(recipe)

    assert "Recipe_IronPlate_C" not in label
    assert "Recipe_IronPlate_C" not in details
    assert "Minerai de fer" in label
    assert "objets Minerai de fer" in label
    assert "Ingrédients consommés par cycle" in details
    assert "Produits obtenus par cycle" in details
    assert "Durée d'un cycle" in details
    page.close()
