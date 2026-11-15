"""Tests Qt du catalogue et de l'activation des modules par partie et par parc."""

import pytest

from jarvis.application.services.mod_service import ModService
from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


def test_mods_page_can_be_opened_without_active_project_and_targets_selected_park(
    tmp_path,
):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QFrame, QPushButton

    from jarvis.presentation.pages.mods.page import ModsPage

    app = QApplication.instance() or QApplication([])
    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    project_service = ProjectService(project_repository)
    park_service = ParkService(park_repository, project_repository)
    mod_service = ModService(park_repository)

    project = project_service.create_project("Partie UI mods")
    first_park = park_service.create_park(project.id, "Parc A")
    second_park = park_service.create_park(project.id, "Parc B")
    another_project = project_service.create_project("Autre partie")
    park_service.create_park(another_project.id, "Parc C")

    # Aucun appel à set_project : la page trouve elle-même les parties disponibles.
    page = ModsPage(mod_service, project_service)

    assert page.project_combo.count() == 2
    assert page.project_combo.findData(str(project.id)) >= 0
    assert len(page.findChildren(QFrame, "ModCard")) == 2

    page.project_combo.setCurrentIndex(
        page.project_combo.findData(str(project.id))
    )
    app.processEvents()

    assert page.project is not None
    assert page.project.id == project.id
    assert page.park_combo.count() == 2
    assert page.park_combo.currentData() == str(first_park.id)

    first_card = page.findChildren(QFrame, "ModCard")[0]
    add_button = next(
        button
        for button in first_card.findChildren(QPushButton)
        if button.text() == "Ajouter au parc"
    )
    add_button.click()
    app.processEvents()

    first_state = mod_service.get_mod_state(
        project.id,
        first_park.id,
        "refined_power",
    )
    second_state = mod_service.get_mod_state(
        project.id,
        second_park.id,
        "refined_power",
    )

    assert first_state.enabled is True
    assert second_state.enabled is False

    page.park_combo.setCurrentIndex(1)
    app.processEvents()
    second_card = page.findChildren(QFrame, "ModCard")[0]
    second_add_button = next(
        button
        for button in second_card.findChildren(QPushButton)
        if button.text() == "Ajouter au parc"
    )
    assert second_add_button.isEnabled()

    page.close()
    app.processEvents()


def test_mod_catalog_remains_visible_without_any_project(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QFrame, QPushButton

    from jarvis.presentation.pages.mods.page import ModsPage

    app = QApplication.instance() or QApplication([])
    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    project_service = ProjectService(project_repository)
    mod_service = ModService(park_repository)

    page = ModsPage(mod_service, project_service)

    assert page.project_combo.isEnabled() is False
    assert page.park_combo.isEnabled() is False
    assert len(page.findChildren(QFrame, "ModCard")) == 2
    assert all(
        not button.isEnabled()
        for button in page.findChildren(QPushButton)
        if button.text() == "Sélectionner un parc"
    )

    page.close()
    app.processEvents()
