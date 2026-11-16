from decimal import Decimal
from uuid import uuid4

import pytest

from jarvis.application.services.factory_service import FactoryService
from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.domain.entities.production import ProductionPlan
from jarvis.infrastructure.persistence.factory_repository import FactoryRepository
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


@pytest.fixture
def factory_environment(tmp_path):
    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    factory_repository = FactoryRepository(projects_dir, park_repository)
    project_service = ProjectService(project_repository)
    park_service = ParkService(park_repository, project_repository)
    factory_service = FactoryService(factory_repository)
    project = project_service.create_project("Projet usines")
    park = park_service.create_park(project.id, "Parc principal")
    return project, park, park_service, factory_service, factory_repository


def sample_plan() -> ProductionPlan:
    return ProductionPlan(
        target_class_name="Desc_IronPlate_C",
        target_name="Plaque de fer",
        target_rate_per_minute=Decimal("30"),
        target_unit_label="objet",
        locale="fr",
        machine_requirements=(),
        resource_requirements=(),
        byproducts=(),
        production_power_min_mw=Decimal("10"),
        production_power_max_mw=Decimal("10"),
        extraction_power_min_mw=Decimal("2"),
        extraction_power_max_mw=Decimal("2"),
        total_power_min_mw=Decimal("12"),
        total_power_max_mw=Decimal("12"),
        power_estimate_complete=True,
        warnings=("Instantané de test",),
    )


def sample_inputs() -> dict:
    return {
        "target_class_name": "Desc_IronPlate_C",
        "target_rate_per_minute": Decimal("30"),
        "locale": "fr",
        "recipe_choices": {"Desc_IronPlate_C": "Recipe_IronPlate_C"},
        "producer_choices": {},
        "extractor_choices": {},
        "machine_clock_limits": {"Build_Foundry_C": Decimal("100")},
        "extractor_clock_limits": {},
    }


def test_create_list_and_rename_factory(factory_environment):
    project, park, _, service, _ = factory_environment

    factory = service.create_factory(project.id, park.id, "Usine plaques")
    assert factory.name == "Usine plaques"
    assert service.list_factories(project.id, park.id) == [factory]

    updated = service.update_factory(
        project.id,
        park.id,
        factory.id,
        "Usine plaques renforcées",
        "Production principale du parc",
    )
    assert updated.name == "Usine plaques renforcées"
    assert updated.description == "Production principale du parc"
    assert service.get_factory(project.id, park.id, factory.id).name == updated.name


def test_factory_names_are_unique_within_a_park(factory_environment):
    project, park, _, service, _ = factory_environment
    service.create_factory(project.id, park.id, "Usine A")

    with pytest.raises(ValueError, match="existe déjà"):
        service.create_factory(project.id, park.id, " usine a ")


def test_factories_are_isolated_between_parks(factory_environment):
    project, park_a, park_service, service, _ = factory_environment
    park_b = park_service.create_park(project.id, "Parc secondaire")
    factory = service.create_factory(project.id, park_a.id, "Usine dédiée")

    assert service.list_factories(project.id, park_a.id) == [factory]
    assert service.list_factories(project.id, park_b.id) == []
    with pytest.raises(FileNotFoundError):
        service.get_factory(project.id, park_b.id, factory.id)


def test_save_simulation_creates_factory_and_persists_plan_snapshot(factory_environment):
    project, park, _, service, repository = factory_environment

    factory, scenario = service.save_simulation(
        project.id,
        park.id,
        "Plaques à 30 par minute",
        sample_plan(),
        sample_inputs(),
        factory_name="Usine de plaques",
        factory_description="Production issue d'une simulation.",
    )

    assert scenario.factory_id == factory.id
    assert factory.scenario_ids == [scenario.id]
    reloaded = service.get_scenario(project.id, park.id, factory.id, scenario.id)
    assert reloaded.target_name == "Plaque de fer"
    assert reloaded.target_rate_per_minute == Decimal("30")
    assert reloaded.plan_snapshot["total_power_min_mw"] == "12"
    assert reloaded.simulation_inputs["target_rate_per_minute"] == "30"
    assert reloaded.plan_snapshot["warnings"] == ["Instantané de test"]
    assert repository.list_scenarios(project.id, park.id, factory.id) == [reloaded]


def test_scenarios_use_a_compact_index_file(factory_environment):
    project, park, _, service, repository = factory_environment

    factory, scenario = service.save_simulation(
        project.id,
        park.id,
        "Scénario compact",
        sample_plan(),
        sample_inputs(),
        factory_name="Usine compacte",
    )

    factory_directory = repository._factory_directory(project.id, park.id, factory.id)
    scenarios_path = factory_directory / "scenarios.json"

    assert scenarios_path.is_file()
    assert not (factory_directory / "scenarios" / f"{scenario.id}.json").exists()
    reloaded = service.get_scenario(project.id, park.id, factory.id, scenario.id)
    assert reloaded.id == scenario.id
    assert reloaded.target_rate_per_minute == scenario.target_rate_per_minute


def test_save_simulation_appends_scenario_to_existing_factory(factory_environment):
    project, park, _, service, _ = factory_environment
    factory = service.create_factory(project.id, park.id, "Usine commune")

    updated, scenario = service.save_simulation(
        project.id,
        park.id,
        "Scénario numéro un",
        sample_plan(),
        sample_inputs(),
        factory_id=factory.id,
    )

    assert updated.id == factory.id
    assert updated.scenario_ids == [scenario.id]
    assert len(service.list_scenarios(project.id, park.id, factory.id)) == 1


def test_scenario_cannot_be_read_through_another_park(factory_environment):
    project, park_a, park_service, service, _ = factory_environment
    park_b = park_service.create_park(project.id, "Parc isolé")
    factory, scenario = service.save_simulation(
        project.id,
        park_a.id,
        "Scénario",
        sample_plan(),
        sample_inputs(),
        factory_name="Usine A",
    )

    with pytest.raises(FileNotFoundError):
        service.get_scenario(project.id, park_b.id, factory.id, scenario.id)


def test_archiving_factory_preserves_its_scenarios(factory_environment):
    project, park, _, service, repository = factory_environment
    factory, scenario = service.save_simulation(
        project.id,
        park.id,
        "Plan conservé",
        sample_plan(),
        sample_inputs(),
        factory_name="Usine à archiver",
    )

    service.archive_factory(project.id, park.id, factory.id)

    assert service.list_factories(project.id, park.id) == []
    archived = repository.archive_repository.list_all("factory")
    assert len(archived) == 1
    assert archived[0].entity_id == factory.id
    payload = repository.archive_repository.get_payload_path(archived[0].archive_id)
    assert (payload / "factory.json").is_file()
    assert (payload / "scenarios.json").is_file()
    assert not (payload / "scenarios" / f"{scenario.id}.json").exists()


def test_creating_factory_for_unknown_park_is_rejected(factory_environment):
    project, _, _, service, _ = factory_environment
    with pytest.raises(FileNotFoundError):
        service.create_factory(project.id, uuid4(), "Usine impossible")


def test_saving_simulation_requires_non_empty_inputs(factory_environment):
    project, park, _, service, _ = factory_environment
    with pytest.raises(ValueError, match="paramètres"):
        service.save_simulation(
            project.id,
            park.id,
            "Scénario",
            sample_plan(),
            {},
            factory_name="Usine",
        )


def test_duplicate_scenario_name_is_rejected_within_factory(factory_environment):
    project, park, _, service, _ = factory_environment
    factory, _ = service.save_simulation(
        project.id,
        park.id,
        "Plan initial",
        sample_plan(),
        sample_inputs(),
        factory_name="Usine scénarios",
    )

    with pytest.raises(ValueError, match="existe déjà"):
        service.save_simulation(
            project.id,
            park.id,
            "plan initial",
            sample_plan(),
            sample_inputs(),
            factory_id=factory.id,
        )


def test_archived_factory_can_be_restored_and_reindexed(factory_environment):
    from jarvis.application.services.archive_service import ArchiveService

    project, park, _, service, repository = factory_environment
    factory, scenario = service.save_simulation(
        project.id,
        park.id,
        "Plan restaurable",
        sample_plan(),
        sample_inputs(),
        factory_name="Usine restaurable",
    )
    service.archive_factory(project.id, park.id, factory.id)
    archive = repository.archive_repository.list_all("factory")[0]
    archive_service = ArchiveService(
        repository.archive_repository,
        repository.projects_dir,
    )
    destination = (
        repository.projects_dir
        / str(project.id)
        / "parks"
        / str(park.id)
        / "factories"
        / str(factory.id)
    )

    restored_record = archive_service.restore_factory_archive(
        archive.archive_id,
        destination,
    )

    assert restored_record.entity_id == factory.id
    restored = service.get_factory(project.id, park.id, factory.id)
    assert restored.name == factory.name
    assert service.get_scenario(project.id, park.id, factory.id, scenario.id).id == scenario.id
    assert repository.archive_repository.list_all("factory") == []


def test_restoring_factory_rejects_active_name_collision(factory_environment):
    from jarvis.application.services.archive_service import ArchiveService

    project, park, _, service, repository = factory_environment
    archived_factory, _ = service.save_simulation(
        project.id,
        park.id,
        "Scénario archivé",
        sample_plan(),
        sample_inputs(),
        factory_name="Usine réutilisée",
    )
    service.archive_factory(project.id, park.id, archived_factory.id)
    current_factory = service.create_factory(
        project.id,
        park.id,
        "Usine réutilisée",
    )
    archive = repository.archive_repository.list_all("factory")[0]
    archive_service = ArchiveService(
        repository.archive_repository,
        repository.projects_dir,
    )
    destination = (
        repository.projects_dir
        / str(project.id)
        / "parks"
        / str(park.id)
        / "factories"
        / str(archived_factory.id)
    )

    with pytest.raises(ValueError, match="porte déjà ce nom"):
        archive_service.restore_factory_archive(archive.archive_id, destination)

    assert service.list_factories(project.id, park.id) == [current_factory]
    assert len(repository.archive_repository.list_all("factory")) == 1


def test_factory_metadata_update_cannot_remove_scenario_references(factory_environment):
    project, park, _, service, repository = factory_environment
    factory, scenario = service.save_simulation(
        project.id,
        park.id,
        "Scénario protégé",
        sample_plan(),
        sample_inputs(),
        factory_name="Usine protégée",
    )
    tampered = factory.model_copy(update={"scenario_ids": []})

    with pytest.raises(ValueError, match="opérations dédiées"):
        repository.update(tampered)

    assert service.get_factory(project.id, park.id, factory.id).scenario_ids == [scenario.id]
