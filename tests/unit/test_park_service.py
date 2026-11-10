
import pytest

from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


@pytest.fixture
def park_environment(tmp_path):
    """Prépare un projet isolé pour les tests."""

    root = tmp_path / "Projects"

    project_repository = ProjectRepository(root)
    park_repository = ParkRepository(root)

    project_service = ProjectService(project_repository)

    park_service = ParkService(
        park_repository,
        project_repository,
    )

    project = project_service.create_project(
        name="Projet de test",
    )

    return project, park_service


def test_create_park(park_environment):
    project, service = park_environment

    park = service.create_park(
        project.id,
        "Parc métallurgique",
        "Production de métaux",
        "Dune Desert",
    )

    assert park.name == "Parc métallurgique"
    assert len(service.get_all_parks(project.id)) == 1


def test_duplicate_park_name_is_rejected(park_environment):
    project, service = park_environment

    service.create_park(project.id, "Parc minier")

    with pytest.raises(ValueError):
        service.create_park(project.id, "parc minier")


def test_update_park(park_environment):
    project, service = park_environment

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


def test_archive_park(park_environment):
    project, service = park_environment

    park = service.create_park(
        project.id,
        "Parc énergétique",
    )

    service.delete_park(project.id, park.id)

    assert service.get_all_parks(project.id) == []


def test_cannot_create_park_in_unknown_project(
    park_environment,
):
    from uuid import uuid4

    _, service = park_environment

    with pytest.raises(FileNotFoundError):
        service.create_park(
            uuid4(),
            "Parc impossible",
        )
