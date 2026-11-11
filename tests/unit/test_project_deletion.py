
from jarvis.application.services.project_service import ProjectService
from jarvis.infrastructure.persistence.project_repository import (
    ProjectRepository,
)


def test_delete_project_archives_all_data(tmp_path):
    """La suppression retire le projet actif sans perdre ses fichiers."""

    projects_dir = tmp_path / "Projects"
    archives_dir = tmp_path / "Archives" / "Projects"

    repository = ProjectRepository(
        projects_dir=projects_dir,
        archives_dir=archives_dir,
    )

    service = ProjectService(repository)

    project = service.create_project(
        name="Partie à supprimer",
        description="Projet de test",
        game_version="1.2",
    )

    original_directory = projects_dir / str(project.id)

    assert original_directory.exists()

    archive_directory = service.delete_project(project.id)

    # Le projet a quitté la liste active.
    assert not original_directory.exists()
    assert service.get_all_projects() == []

    # Toutes les données principales ont été conservées.
    assert archive_directory.exists()
    assert (archive_directory / "project.json").is_file()
    assert (archive_directory / "parks" / "index.json").is_file()
    assert (archive_directory / "network.json").is_file()
    assert (archive_directory / "targets.json").is_file()


def test_delete_project_does_not_affect_other_projects(tmp_path):
    """Supprimer une partie ne doit pas supprimer les autres."""

    repository = ProjectRepository(
        projects_dir=tmp_path / "Projects",
        archives_dir=tmp_path / "Archives" / "Projects",
    )

    service = ProjectService(repository)

    project_a = service.create_project(name="Partie A")
    project_b = service.create_project(name="Partie B")

    service.delete_project(project_a.id)

    remaining_projects = service.get_all_projects()

    assert len(remaining_projects) == 1
    assert remaining_projects[0].id == project_b.id
