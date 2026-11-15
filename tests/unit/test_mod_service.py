"""Tests du catalogue de modules et de leur activation par parc."""

import pytest

from jarvis.application.services.mod_service import ModService
from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


@pytest.fixture
def mod_environment(tmp_path):
    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    project_service = ProjectService(project_repository)
    park_service = ParkService(park_repository, project_repository)
    mod_service = ModService(park_repository)

    project = project_service.create_project("Partie Mods")
    first_park = park_service.create_park(project.id, "Parc principal")
    second_park = park_service.create_park(project.id, "Parc secondaire")

    return project, first_park, second_park, mod_service, park_repository


def test_mod_registry_contains_refined_power_and_digital_storage():
    service = ModService()

    assert {mod.mod_id for mod in service.list_supported_mods()} == {
        "refined_power",
        "digital_storage",
    }


def test_mods_are_not_automatically_added_to_a_new_park(mod_environment):
    project, park, _, service, repository = mod_environment

    state = service.get_mod_state(project.id, park.id, "refined_power")
    refreshed = repository.get(project.id, park.id)

    assert state.enabled is False
    assert refreshed.mods == {}


def test_enabling_a_mod_is_scoped_to_the_selected_park(mod_environment):
    project, first_park, second_park, service, repository = mod_environment

    updated = service.set_mod_enabled(
        project.id,
        first_park.id,
        "refined_power",
        True,
    )

    first_state = repository.get(project.id, first_park.id).mods["refined_power"]
    second_park_refreshed = repository.get(project.id, second_park.id)

    assert updated.mods["refined_power"].enabled is True
    assert first_state.enabled is True
    assert second_park_refreshed.mods == {}


def test_disabling_a_mod_preserves_its_configuration(mod_environment):
    project, park, _, service, repository = mod_environment

    service.set_mod_enabled(project.id, park.id, "digital_storage", True)
    service.update_mod_configuration(
        project.id,
        park.id,
        "digital_storage",
        {
            "rack_count": 2,
            "servers": {"server_1u_item": 3},
        },
    )

    service.set_mod_enabled(project.id, park.id, "digital_storage", False)
    refreshed = repository.get(project.id, park.id)
    state = refreshed.mods["digital_storage"]

    assert state.enabled is False
    assert state.configuration == {
        "rack_count": 2,
        "servers": {"server_1u_item": 3},
    }


def test_unknown_mod_cannot_be_enabled(mod_environment):
    project, park, _, service, _ = mod_environment

    with pytest.raises(ValueError, match="Module non pris en charge"):
        service.set_mod_enabled(project.id, park.id, "unknown_mod", True)


def test_mod_configuration_requires_a_json_object(mod_environment):
    project, park, _, service, _ = mod_environment

    with pytest.raises(ValueError, match="objet JSON"):
        service.update_mod_configuration(
            project.id,
            park.id,
            "refined_power",
            ["invalid"],  # type: ignore[arg-type]
        )
