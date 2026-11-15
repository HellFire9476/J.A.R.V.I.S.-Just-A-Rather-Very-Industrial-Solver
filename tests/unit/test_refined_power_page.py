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
