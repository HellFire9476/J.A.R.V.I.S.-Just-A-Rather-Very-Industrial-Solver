
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from jarvis.config.paths import PROJECTS_DIR
from jarvis.domain.entities.project import Project
from jarvis.infrastructure.persistence.atomic_writer import (
    write_json_atomic,
)
from jarvis.infrastructure.persistence.json_store import read_json


class ProjectRepository:
    """Gestion des projets Satisfactory sur le disque."""

    def __init__(self, projects_dir: Path = PROJECTS_DIR):
        self.projects_dir = Path(projects_dir)

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

            # Structure initiale du projet
            (project_dir / "parks").mkdir()
            (project_dir / "scenarios").mkdir()
            (project_dir / "backups").mkdir()

            # Index des parcs
            write_json_atomic(
                project_dir / "parks" / "index.json",
                {
                    "schema_version": 1,
                    "park_ids": [],
                },
            )

            # Réseau industriel
            write_json_atomic(
                project_dir / "network.json",
                {
                    "schema_version": 1,
                    "resource_transfers": [],
                    "power_grids": [],
                },
            )

            # Objectifs de production
            write_json_atomic(
                project_dir / "targets.json",
                {
                    "schema_version": 1,
                    "targets": [],
                },
            )

            # Fichier principal écrit en dernier
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

        if not isinstance(loaded, Project):
            raise TypeError("Le contenu du projet est invalide.")

        if loaded.id != project_id:
            raise ValueError(
                "L'identifiant du fichier ne correspond pas au projet."
            )

        return loaded

    def list_all(self) -> list[Project]:
        """Retourne tous les projets valides."""

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
