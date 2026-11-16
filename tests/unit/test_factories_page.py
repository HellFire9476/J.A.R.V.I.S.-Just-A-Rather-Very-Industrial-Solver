from decimal import Decimal
from uuid import uuid4

import pytest

from jarvis.application.services.factory_service import FactoryService
from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.domain.entities.factory import Factory
from jarvis.domain.entities.scenario import Scenario
from jarvis.infrastructure.persistence.factory_repository import FactoryRepository
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


def test_factories_page_lists_factories_for_selected_project_and_park(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.factories.page import FactoriesPage

    app = QApplication.instance() or QApplication([])
    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    project_service = ProjectService(project_repository)
    park_service = ParkService(park_repository, project_repository)
    factory_service = FactoryService(FactoryRepository(projects_dir, park_repository))

    project = project_service.create_project("Usines UI")
    park_a = park_service.create_park(project.id, "Parc A")
    park_b = park_service.create_park(project.id, "Parc B")
    factory_service.create_factory(project.id, park_a.id, "Usine A")
    factory_service.create_factory(project.id, park_b.id, "Usine B")

    page = FactoriesPage(factory_service, park_service)
    page.set_project(project)

    assert page.park_combo.count() == 2
    assert page.selected_park_id == park_a.id
    assert page.count_label.text() == "USINES  •  1"

    page.park_combo.setCurrentIndex(page.park_combo.findData(str(park_b.id)))
    app.processEvents()
    assert page.selected_park_id == park_b.id
    assert page.count_label.text() == "USINES  •  1"

    page.set_project(None)
    assert page.create_button.isEnabled() is False
    assert page.count_label.text() == "USINES  •  0"
    page.close()
    app.processEvents()


def test_factories_page_is_registered_in_primary_navigation():
    pytest.importorskip("PySide6")
    from jarvis.presentation.widgets.sidebar import Sidebar

    assert any(item[0] == "factories" for item in Sidebar.NAV_ITEMS)


def test_scenario_details_dialog_formats_rates_and_power_compactly():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.factories.page import ScenarioDetailsDialog

    app = QApplication.instance() or QApplication([])
    project_id = uuid4()
    park_id = uuid4()
    factory = Factory(project_id=project_id, park_id=park_id, name="Usine de plaques")
    scenario = Scenario(
        project_id=project_id,
        park_id=park_id,
        factory_id=factory.id,
        name="Plaques à 60/min",
        target_class_name="Desc_IronPlate_C",
        target_name="Plaque de fer",
        target_rate_per_minute=Decimal("60.000"),
        target_unit_label="objet",
        locale="fr",
        simulation_inputs={"target_rate_per_minute": "60"},
        plan_snapshot={
            "production_power_min_mw": 24.0,
            "production_power_max_mw": 24.0,
            "extraction_power_min_mw": 12.30586350072816,
            "extraction_power_max_mw": 12.30586350072816,
            "total_power_min_mw": 36.30586350072816,
            "total_power_max_mw": 36.30586350072816,
            "machine_requirements": [
                {
                    "recipe_name": "Plaque de fer",
                    "producer_name": "Constructeur",
                    "machine_count": 3,
                    "clock_percent": 100.0,
                }
            ],
            "resource_requirements": [
                {"display_name": "Minerai de fer", "rate_per_minute": 90.0, "unit_label": "objet"}
            ],
        },
    )

    dialog = ScenarioDetailsDialog(factory, [scenario])
    assert "Plaque de fer · 60 objet/min" in dialog.scenario_list.item(0).text()
    details = dialog.scenario_details.toPlainText()
    assert "Objectif : 60 objet/min" in details
    assert "Fabrication : 24 à 24 MW" in details
    assert "Extraction : 12,31 à 12,31 MW" in details
    assert "Total : 36,31 à 36,31 MW" in details
    assert "3 machine(s), 100 %" in details
    assert "Minerai de fer : 90 objet/min" in details

    dialog.close()
    app.processEvents()
