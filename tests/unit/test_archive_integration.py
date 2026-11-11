
from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.infrastructure.persistence.park_repository import (
    ParkRepository,
)
from jarvis.infrastructure.persistence.project_repository import (
    ProjectRepository,
)


def test_project_archive_uses_central_repository(tmp_path):
    """Vérifie que les projets utilisent le moteur central."""

    projects_dir = tmp_path / "Projects"

    repository = ProjectRepository(projects_dir)
    service = ProjectService(repository)

    project = service.create_project(
        name="Projet à archiver",
        description="Test d'intégration",
    )

    payload = service.delete_project(project.id)

    assert (payload / "project.json").is_file()

    archives = repository.archive_repository.list_all("project")

    assert len(archives) == 1
    assert archives[0].entity_id == project.id
    assert archives[0].entity_name == "Projet à archiver"


def test_park_archive_uses_central_repository(tmp_path):
    """Vérifie que les parcs utilisent le moteur central."""

    projects_dir = tmp_path / "Projects"

    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)

    project_service = ProjectService(project_repository)

    park_service = ParkService(
        park_repository,
        project_repository,
    )

    project = project_service.create_project(
        name="Partie de test",
    )

    park = park_service.create_park(
        project.id,
        "Parc métallurgique",
    )

    park_service.delete_park(project.id, park.id)

    archives = park_repository.archive_repository.list_all("park")

    assert len(archives) == 1
    assert archives[0].entity_id == park.id
    assert archives[0].parent_project_id == project.id

    payload = park_repository.archive_repository.get_payload_path(
        archives[0].archive_id
    )

    assert (payload / "park.json").is_file()


def test_projects_and_parks_share_archive_root(tmp_path):
    """Vérifie que les deux dépôts utilisent le même emplacement."""

    projects_dir = tmp_path / "Projects"

    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)

    assert (
        project_repository.archive_repository.archives_dir
        == park_repository.archive_repository.archives_dir
    )
