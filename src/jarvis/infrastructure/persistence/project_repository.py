import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from jarvis.config.paths import PROJECTS_DIR
from jarvis.domain.entities.project import Project
from jarvis.infrastructure.persistence.archive_repository import (
    ArchiveRepository,
)
from jarvis.infrastructure.persistence.atomic_writer import (
    write_json_atomic,
)
from jarvis.infrastructure.persistence.json_store import read_json


class ProjectRepository:
    """Gestion des projets Satisfactory sur le disque."""

    def __init__(
        self,
        projects_dir: Path = PROJECTS_DIR,
        archive_repository: ArchiveRepository | None = None,
        *,
        archives_dir: Path | None = None,
    ):
        self.projects_dir = Path(projects_dir)

        if archive_repository is not None and archives_dir is not None:
            raise ValueError(
                "Fournis archive_repository ou archives_dir, pas les deux."
            )

        if archive_repository is not None:
            self.archive_repository = archive_repository
        else:
            # Compatibilité avec l'ancien constructeur, qui recevait le
            # dossier de catégorie Archives/Projects. Le dépôt central attend
            # désormais la racine Archives afin de gérer toutes les catégories.
            if archives_dir is not None:
                legacy_projects_archive_dir = Path(archives_dir)
                archive_root = legacy_projects_archive_dir.parent
            else:
                archive_root = self.projects_dir.parent / "Archives"

            self.archive_repository = ArchiveRepository(archive_root)

    def _get_project_directory(self, project_id: UUID) -> Path:
        return self.projects_dir / str(project_id)

    def create(self, project: Project) -> Project:
        """Crée une partie et sa structure de fichiers."""

        self.projects_dir.mkdir(parents=True, exist_ok=True)
        project_dir = self._get_project_directory(project.id)

        if project_dir.exists():
            raise FileExistsError(
                f"Ce projet existe déjà : {project.id}"
            )

        try:
            project_dir.mkdir()
            (project_dir / "parks").mkdir()
            (project_dir / "scenarios").mkdir()
            (project_dir / "backups").mkdir()

            write_json_atomic(
                project_dir / "parks" / "index.json",
                {
                    "schema_version": 1,
                    "park_ids": [],
                },
            )

            write_json_atomic(
                project_dir / "network.json",
                {
                    "schema_version": 1,
                    "resource_transfers": [],
                    "power_grids": [],
                },
            )

            write_json_atomic(
                project_dir / "targets.json",
                {
                    "schema_version": 1,
                    "targets": [],
                },
            )

            # Le fichier principal est écrit en dernier.
            write_json_atomic(
                project_dir / "project.json",
                project,
            )

            return project

        except Exception:
            if project_dir.exists():
                shutil.rmtree(project_dir)
            raise

    def get(self, project_id: UUID) -> Project:
        """Charge un projet depuis son identifiant."""

        project_file = (
            self._get_project_directory(project_id) / "project.json"
        )
        loaded = read_json(project_file, Project)

        if loaded.id != project_id:
            raise ValueError(
                "L'identifiant du fichier ne correspond pas au projet."
            )

        return loaded

    def list_all(self) -> list[Project]:
        """Retourne tous les projets actifs et valides."""

        if not self.projects_dir.exists():
            return []

        projects = []

        for directory in self.projects_dir.iterdir():
            if not directory.is_dir():
                continue

            project_file = directory / "project.json"
            if not project_file.is_file():
                continue

            try:
                project_id = UUID(directory.name)
            except ValueError:
                continue

            projects.append(self.get(project_id))

        return sorted(
            projects,
            key=lambda project: project.updated_at,
            reverse=True,
        )

    def save(self, project: Project) -> Project:
        """Enregistre les modifications d'un projet."""

        project_file = (
            self._get_project_directory(project.id) / "project.json"
        )

        if not project_file.is_file():
            raise FileNotFoundError(
                f"Projet introuvable : {project.id}"
            )

        project.updated_at = datetime.now(UTC)
        write_json_atomic(project_file, project)

        return project

    def archive(self, project_id: UUID) -> Path:
        """Archive une partie dans le système central d'archives.

        Le contenu du projet est déplacé dans le dossier `data` de
        l'archive. Le chemin retourné désigne ce contenu pour préserver
        le contrat utilisé par ProjectService et les tests existants.
        """

        project = self.get(project_id)
        project_dir = self._get_project_directory(project_id)

        record = self.archive_repository.archive(
            source_path=project_dir,
            entity_type="project",
            entity_id=project.id,
            entity_name=project.name,
            original_location=f"Projects/{project.id}",
            parent_project_id=None,
        )

        return self.archive_repository.get_payload_path(
            record.archive_id
        )
