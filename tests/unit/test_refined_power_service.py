from uuid import uuid4

import pytest

from jarvis.application.services.mod_service import ModService
from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.application.services.refined_power_service import RefinedPowerService
from jarvis.domain.entities.refined_power import RefinedPowerChainConfiguration
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


@pytest.fixture
def environment(tmp_path):
    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    project = ProjectService(project_repository).create_project("RP Test")
    park_service = ParkService(park_repository, project_repository)
    park = park_service.create_park(project.id, "Parc énergie")
    mod_service = ModService(park_repository)
    refined_power_service = RefinedPowerService(park_repository)
    return project, park, mod_service, refined_power_service, park_repository, park_service


def sample_chain(name="Chaîne principale"):
    return RefinedPowerChainConfiguration(
        name=name,
        heater_id="coal",
        fuel_id="coal",
        boiler_id="mk1",
        boiler_count=1,
        turbine_id="mk1",
        turbine_count=1,
        generator_id="lv",
        generator_count=1,
        co2_chimney_count=1,
        steam_cooling_tower_count=1,
    )


def test_chains_require_refined_power_enabled(environment):
    project, park, _, service, _, _ = environment

    with pytest.raises(ValueError, match="doit être activé"):
        service.create_chain(project.id, park.id, sample_chain())


def test_create_calculate_and_reload_chain(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)

    chain = service.create_chain(project.id, park.id, sample_chain())
    reloaded = service.list_chains(project.id, park.id)
    persisted = service.get_configuration(project.id, park.id)
    result = service.calculate_chain(project.id, park.id, chain.chain_id)

    assert persisted.catalog_version == "2026.3.26"
    assert len(reloaded) == 1
    assert reloaded[0].chain_id == chain.chain_id
    assert result.estimated_power_mw == 150


def test_chains_are_scoped_to_the_selected_park(environment):
    project, park_a, mod_service, service, _, park_service = environment
    park_b = park_service.create_park(project.id, "Parc secondaire")
    mod_service.set_mod_enabled(project.id, park_a.id, "refined_power", True)
    mod_service.set_mod_enabled(project.id, park_b.id, "refined_power", True)

    service.create_chain(project.id, park_a.id, sample_chain())

    assert len(service.list_chains(project.id, park_a.id)) == 1
    assert service.list_chains(project.id, park_b.id) == ()


def test_deactivation_preserves_configuration_but_blocks_calculation(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    chain = service.create_chain(project.id, park.id, sample_chain())

    mod_service.set_mod_enabled(project.id, park.id, "refined_power", False)

    assert len(service.list_chains(project.id, park.id)) == 1
    with pytest.raises(ValueError, match="doit être activé"):
        service.calculate_chain(project.id, park.id, chain.chain_id)


def test_update_and_delete_chain(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    chain = service.create_chain(project.id, park.id, sample_chain())
    updated = chain.model_copy(update={"name": "Chaîne mise à jour"})

    service.update_chain(project.id, park.id, chain.chain_id, updated)
    assert service.list_chains(project.id, park.id)[0].name == "Chaîne mise à jour"

    service.delete_chain(project.id, park.id, chain.chain_id)
    assert service.list_chains(project.id, park.id) == ()


def test_update_rejects_changed_identifier(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    chain = service.create_chain(project.id, park.id, sample_chain())
    changed = sample_chain().model_copy(update={"chain_id": uuid4()})

    with pytest.raises(ValueError, match="ne peut pas être modifié"):
        service.update_chain(project.id, park.id, chain.chain_id, changed)
