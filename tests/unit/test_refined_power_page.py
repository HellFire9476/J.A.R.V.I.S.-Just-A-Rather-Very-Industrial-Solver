"""Tests Qt de l'interface de gestion Refined Power."""

import pytest

from jarvis.application.services.mod_service import ModService
from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.application.services.refined_power_service import RefinedPowerService
from jarvis.domain.entities.refined_power import RefinedPowerChainConfiguration
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


def _create_environment(tmp_path):
    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    project_service = ProjectService(project_repository)
    park_service = ParkService(park_repository, project_repository)
    mod_service = ModService(park_repository)
    refined_power_service = RefinedPowerService(park_repository)
    project = project_service.create_project("Partie Refined Power")
    park = park_service.create_park(project.id, "Parc énergétique")
    return (
        project,
        park,
        project_service,
        park_service,
        mod_service,
        refined_power_service,
    )


def test_refined_power_page_requires_explicit_module_activation(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.refined_power.page import RefinedPowerPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        park,
        project_service,
        park_service,
        _,
        refined_power_service,
    ) = _create_environment(tmp_path)

    page = RefinedPowerPage(
        refined_power_service,
        project_service,
        park_service,
    )

    assert page.project.id == project.id
    assert page.selected_park_id == park.id
    assert page.new_chain_button.isEnabled() is False
    assert page.manage_mods_button.isEnabled() is True
    assert refined_power_service.list_chains(project.id, park.id) == ()

    page.close()
    app.processEvents()


def test_refined_power_page_creates_and_calculates_chain_for_selected_park(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.refined_power.page import RefinedPowerPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        park,
        project_service,
        park_service,
        mod_service,
        refined_power_service,
    ) = _create_environment(tmp_path)
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)

    page = RefinedPowerPage(
        refined_power_service,
        project_service,
        park_service,
    )
    page.new_chain_button.click()
    page.chain_name_input.setText("Centrale charbon UI")
    page.heater_combo.setCurrentIndex(page.heater_combo.findData("coal"))
    page.fuel_combo.setCurrentIndex(page.fuel_combo.findData("coal"))
    page.boiler_combo.setCurrentIndex(page.boiler_combo.findData("mk1"))
    page.turbine_combo.setCurrentIndex(page.turbine_combo.findData("mk1"))
    page.generator_combo.setCurrentIndex(page.generator_combo.findData("lv"))
    assert refined_power_service.list_chains(project.id, park.id) == ()
    assert page.result_state_label.text().startswith("APERÇU NON ENREGISTRÉ")

    page.save_button.click()
    app.processEvents()

    chains = refined_power_service.list_chains(project.id, park.id)
    assert len(chains) == 1
    assert chains[0].name == "Centrale charbon UI"
    assert page.power_value.text() == "150,00 MW"
    assert page.result_state_label.text() == "FLUX ÉQUILIBRÉS"

    page.park_combo.setCurrentIndex(page.park_combo.findData(str(park.id)))
    app.processEvents()
    assert page.chain_list.count() == 1
    assert page.chain_list.item(0).data(Qt.ItemDataRole.UserRole) == str(chains[0].chain_id)

    page.close()
    app.processEvents()


def test_refined_power_page_keeps_disabled_chains_read_only(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.refined_power.page import RefinedPowerPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        park,
        project_service,
        park_service,
        mod_service,
        refined_power_service,
    ) = _create_environment(tmp_path)
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    chain = RefinedPowerChainConfiguration(
        name="Chaîne conservée",
        heater_id="coal",
        fuel_id="coal",
        boiler_id="mk1",
        turbine_id="mk1",
        generator_id="lv",
    )
    refined_power_service.create_chain(project.id, park.id, chain)
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", False)

    page = RefinedPowerPage(
        refined_power_service,
        project_service,
        park_service,
    )

    assert page.chain_list.count() == 1
    assert page.chain_name_input.isEnabled() is False
    assert page.save_button.isEnabled() is False
    assert page.manage_mods_button.isEnabled() is True
    assert refined_power_service.list_chains(project.id, park.id)[0].chain_id == chain.chain_id

    page.close()
    app.processEvents()


def test_mods_navigation_keeps_the_part_and_park_selected_in_refined_power(
    tmp_path,
):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.mods.page import ModsPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        _,
        project_service,
        park_service,
        mod_service,
        _,
    ) = _create_environment(tmp_path)
    target_park = park_service.create_park(project.id, "Parc ciblé")

    page = ModsPage(mod_service, project_service)
    page.set_target(project, target_park.id)

    assert page.project.id == project.id
    assert page.park_combo.currentData() == str(target_park.id)

    page.close()
    app.processEvents()


def test_refined_power_is_registered_as_an_independent_navigation_page():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.app.main_window import MainWindow
    from jarvis.presentation.widgets.sidebar import Sidebar

    app = QApplication.instance() or QApplication([])
    sidebar = Sidebar()

    assert "refined_power" not in MainWindow.PROJECT_REQUIRED_PAGES
    assert any(item[0] == "refined_power" for item in Sidebar.NAV_ITEMS)
    assert "refined_power" in sidebar.buttons

    sidebar.close()
    app.processEvents()


def test_refined_power_page_exposes_three_optimization_modes(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.refined_power.page import RefinedPowerPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        park,
        project_service,
        park_service,
        mod_service,
        refined_power_service,
    ) = _create_environment(tmp_path)
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)

    page = RefinedPowerPage(
        refined_power_service,
        project_service,
        park_service,
    )

    optimizer = page.optimization_panel
    assert page.detail_tabs.tabText(1) == "Équilibrage automatique"
    assert [
        optimizer.mode_combo.itemData(index)
        for index in range(optimizer.mode_combo.count())
    ] == ["balance_existing", "maximize", "target"]
    assert optimizer.preview_button.isEnabled() is True
    assert optimizer.apply_button.isEnabled() is False

    page.close()
    app.processEvents()


def test_optimization_preview_does_not_persist_until_user_applies_it(
    tmp_path,
    monkeypatch,
):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QMessageBox

    from jarvis.presentation.pages.refined_power.page import RefinedPowerPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        park,
        project_service,
        park_service,
        mod_service,
        refined_power_service,
    ) = _create_environment(tmp_path)
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    original = RefinedPowerChainConfiguration(
        name="Centrale à équilibrer",
        heater_id="coal",
        fuel_id="coal",
        boiler_id="mk1",
        boiler_count=2,
        turbine_id="mk1",
        turbine_count=1,
        generator_id="lv",
        generator_count=1,
        co2_chimney_count=0,
        steam_cooling_tower_count=0,
    )
    refined_power_service.create_chain(project.id, park.id, original)

    page = RefinedPowerPage(
        refined_power_service,
        project_service,
        park_service,
    )
    panel = page.optimization_panel
    panel.mode_combo.setCurrentIndex(panel.mode_combo.findData("balance_existing"))
    panel.preview_button.click()

    preview = panel.solution
    assert preview is not None
    assert preview.feasible is True
    assert preview.configuration is not None
    assert preview.configuration.turbine_count == 2
    assert panel.apply_button.isEnabled() is True

    before_apply = refined_power_service.list_chains(project.id, park.id)
    assert len(before_apply) == 1
    assert before_apply[0].turbine_count == 1
    assert before_apply[0].co2_chimney_count == 0
    assert before_apply[0].steam_cooling_tower_count == 0

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes),
    )
    panel.apply_button.click()
    app.processEvents()

    after_apply = refined_power_service.list_chains(project.id, park.id)
    assert len(after_apply) == 1
    assert after_apply[0].chain_id == original.chain_id
    assert after_apply[0].turbine_count == 2
    assert after_apply[0].generator_count == 2
    assert after_apply[0].co2_chimney_count == 1
    assert after_apply[0].steam_cooling_tower_count == 1

    page.close()
    app.processEvents()


def test_optimization_tutorial_and_mode_explanations_are_available(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QLabel

    from jarvis.presentation.pages.refined_power.page import RefinedPowerPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        park,
        project_service,
        park_service,
        mod_service,
        refined_power_service,
    ) = _create_environment(tmp_path)
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)

    page = RefinedPowerPage(
        refined_power_service,
        project_service,
        park_service,
    )
    panel = page.optimization_panel

    panel.tutorial_button.click()
    assert panel.tutorial_panel.isHidden() is False
    tutorial_text = " ".join(
        child.text() for child in panel.tutorial_panel.findChildren(QLabel)
    )
    assert "GUIDE PAS À PAS" in tutorial_text

    panel.mode_combo.setCurrentIndex(panel.mode_combo.findData("target"))
    assert "puissance" in panel.mode_explanation_label.text().lower()
    assert "500 MW" in panel.mode_example_label.text()

    page.close()
    app.processEvents()


def test_refined_power_resource_and_machine_names_follow_selected_locale(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.refined_power.page import RefinedPowerPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        park,
        project_service,
        park_service,
        mod_service,
        refined_power_service,
    ) = _create_environment(tmp_path)
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)

    page = RefinedPowerPage(
        refined_power_service,
        project_service,
        park_service,
    )
    page.heater_combo.setCurrentIndex(page.heater_combo.findData("coal"))
    coal_index = page.fuel_combo.findData("coal")
    assert page.heater_combo.currentText() == "Chauffage au charbon"
    assert page.fuel_combo.itemText(coal_index).startswith("Charbon")

    english_index = page.locale_combo.findData("en-US")
    assert english_index >= 0
    page.locale_combo.setCurrentIndex(english_index)
    app.processEvents()

    coal_index = page.fuel_combo.findData("coal")
    assert page.heater_combo.currentText() == "Coal Heater"
    assert page.fuel_combo.itemText(coal_index).startswith("Coal")

    optimization_coal_index = page.optimization_panel.fuel_filter.findData("coal")
    assert page.optimization_panel.fuel_filter.itemText(optimization_coal_index) == "Coal"

    page.close()
    app.processEvents()


def test_byproduct_capacity_edit_invalidates_preview_after_locale_change(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.refined_power.page import RefinedPowerPage

    app = QApplication.instance() or QApplication([])
    (
        project,
        park,
        project_service,
        park_service,
        mod_service,
        refined_power_service,
    ) = _create_environment(tmp_path)
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)

    page = RefinedPowerPage(
        refined_power_service,
        project_service,
        park_service,
    )
    panel = page.optimization_panel
    panel.mode_combo.setCurrentIndex(panel.mode_combo.findData("maximize"))
    panel.fuel_filter.setCurrentIndex(panel.fuel_filter.findData("coal"))
    panel.boiler_filter.setCurrentIndex(panel.boiler_filter.findData("mk1"))
    panel.max_boilers_spin.setValue(1)

    panel.preview_button.click()
    assert panel.solution is not None
    assert panel.apply_button.isEnabled() is True
    assert panel.byproduct_inputs

    panel.set_locale("en-US")
    panel.preview_button.click()
    assert panel.solution is not None
    assert panel.apply_button.isEnabled() is True

    capacity_field = next(iter(panel.byproduct_inputs.values()))
    capacity_field.setText("1")

    assert panel.solution is None
    assert panel.apply_button.isEnabled() is False

    page.close()
    app.processEvents()
