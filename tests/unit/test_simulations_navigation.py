"""Vérifie que les simulations ne dépendent pas d'une partie active."""

import pytest


def test_simulations_page_is_not_restricted_to_an_active_project() -> None:
    pytest.importorskip("PySide6")

    from jarvis.app.main_window import MainWindow

    assert "simulations" not in MainWindow.PROJECT_REQUIRED_PAGES
    assert "factories" in MainWindow.PROJECT_REQUIRED_PAGES


def test_simulations_can_run_without_a_project_but_cannot_be_saved_yet() -> None:
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    from jarvis.domain.entities.project import Project
    from jarvis.presentation.pages.simulations.page import SimulationsPage

    app = QApplication.instance() or QApplication([])
    page = SimulationsPage(service=object())

    assert page.project is None
    assert page.save_factory_button.isEnabled() is False
    assert "CALCUL INDÉPENDANT" in page.scope_label.text()
    assert "aucun stock" in page.scope_label.toolTip().casefold()
    assert "enregistré comme scénario" in page.scope_label.toolTip().casefold()

    project = Project(name="Partie de test")
    page.set_project(project)
    assert page.project.id == project.id
    assert page.save_factory_button.isEnabled() is False

    page.close()
    app.processEvents()


def test_editing_target_rate_invalidates_a_saved_scenario_preview() -> None:
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    from jarvis.domain.entities.project import Project
    from jarvis.presentation.pages.simulations.page import SimulationsPage

    app = QApplication.instance() or QApplication([])
    page = SimulationsPage(service=object())
    page.set_project(Project(name="Partie test"))
    page._current_plan = object()
    page._current_inputs = {"target_rate_per_minute": "60"}
    page._update_save_button()
    assert page.save_factory_button.isEnabled() is True

    page.rate_spin.setValue(page.rate_spin.value() + 1)

    assert page._current_plan is None
    assert page._current_inputs is None
    assert page.save_factory_button.isEnabled() is False
    assert "relancez le calcul" in page.status_label.text().casefold()

    page.close()
    app.processEvents()


def test_editing_recipe_invalidates_a_saved_scenario_preview() -> None:
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    from jarvis.domain.entities.project import Project
    from jarvis.presentation.pages.simulations.page import SimulationsPage

    app = QApplication.instance() or QApplication([])
    page = SimulationsPage(service=object())
    page.set_project(Project(name="Partie test"))
    page._current_plan = object()
    page._current_inputs = {"recipe_choices": {"Target": "RecipeA"}}
    page._update_save_button()
    page.recipe_combo.addItem("Recette A", "RecipeA")
    page.recipe_combo.addItem("Recette B", "RecipeB")
    page.recipe_combo.setCurrentIndex(1)

    assert page._current_plan is None
    assert page._current_inputs is None
    assert page.save_factory_button.isEnabled() is False

    page.close()
    app.processEvents()


def test_switching_project_discards_a_result_from_an_inflight_calculation() -> None:
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    from jarvis.domain.entities.project import Project
    from jarvis.presentation.pages.simulations.page import SimulationsPage

    app = QApplication.instance() or QApplication([])
    page = SimulationsPage(service=object())
    page.set_project(Project(name="Partie A"))
    page._plan_generation += 1
    request_generation = page._plan_generation
    page._pending_plan_arguments = {"target_class_name": "TargetA"}

    page.set_project(Project(name="Partie B"))
    page._on_plan_completed(object(), None, request_generation)

    assert page._current_plan is None
    assert page._current_inputs is None
    assert page._pending_plan_arguments is None
    assert page.save_factory_button.isEnabled() is False

    page.close()
    app.processEvents()


def test_simulation_rate_spin_hides_insignificant_decimal_zeros() -> None:
    pytest.importorskip("PySide6")

    from PySide6.QtCore import QLocale
    from PySide6.QtWidgets import QApplication

    from jarvis.domain.entities.project import Project
    from jarvis.presentation.pages.simulations.page import SimulationsPage

    app = QApplication.instance() or QApplication([])
    page = SimulationsPage(service=object())
    page.set_project(Project(name="Partie test"))
    page.rate_spin.setLocale(QLocale(QLocale.Language.French, QLocale.Country.France))

    assert page.rate_spin.textFromValue(60.0) == "60"
    assert page.rate_spin.textFromValue(60.5) == "60,5"
    assert page.rate_spin.textFromValue(60.125) == "60,125"

    page.close()
    app.processEvents()
