import pytest

from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


@pytest.fixture
def park_environment(tmp_path):
    """Prépare un projet isolé pour les tests de parcs."""

    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    project_service = ProjectService(project_repository)
    park_service = ParkService(
        park_repository,
        project_repository,
    )

    project = project_service.create_project(
        name="Projet de test",
    )

    return project, park_service, park_repository


def test_create_park(park_environment):
    project, service, _ = park_environment

    park = service.create_park(
        project.id,
        "Parc métallurgique",
        "Production de métaux",
        "Dune Desert",
    )

    assert park.name == "Parc métallurgique"
    assert len(service.get_all_parks(project.id)) == 1


def test_duplicate_park_name_is_rejected(park_environment):
    project, service, _ = park_environment

    service.create_park(project.id, "Parc minier")

    with pytest.raises(ValueError):
        service.create_park(project.id, "parc minier")


def test_update_park(park_environment):
    project, service, _ = park_environment

    park = service.create_park(
        project.id,
        "Ancien nom",
    )

    updated = service.update_park(
        project.id,
        park.id,
        "Nouveau nom",
        "Nouvelle description",
        "Northern Forest",
    )

    assert updated.name == "Nouveau nom"
    assert updated.description == "Nouvelle description"
    assert updated.location == "Northern Forest"


def test_archive_park_uses_central_archive_repository(park_environment):
    project, service, repository = park_environment

    park = service.create_park(
        project.id,
        "Parc énergétique",
    )

    service.delete_park(project.id, park.id)

    assert service.get_all_parks(project.id) == []

    archives = repository.archive_repository.list_all("park")
    assert len(archives) == 1
    assert archives[0].entity_id == park.id
    assert archives[0].parent_project_id == project.id

    payload = repository.archive_repository.get_payload_path(
        archives[0].archive_id
    )
    assert (payload / "park.json").is_file()


def test_cannot_create_park_in_unknown_project(park_environment):
    from uuid import uuid4

    _, service, _ = park_environment

    with pytest.raises(FileNotFoundError):
        service.create_park(
            uuid4(),
            "Parc impossible",
        )
