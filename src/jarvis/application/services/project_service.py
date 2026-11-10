
from uuid import UUID

from jarvis.domain.entities.project import Project
from jarvis.infrastructure.persistence.project_repository import (
    ProjectRepository,
)


class ProjectService:
    """Coordonne les opérations de gestion des projets."""

    def __init__(
        self,
        repository: ProjectRepository | None = None,
    ):
        self.repository = repository or ProjectRepository()

    def create_project(
        self,
        name: str,
        description: str = "",
        game_version: str | None = None,
    ) -> Project:
        """Crée une nouvelle partie."""

        project = Project(
            name=name,
            description=description,
            game_version=game_version,
        )

        return self.repository.create(project)

    def get_project(self, project_id: UUID) -> Project:
        """Récupère une partie."""

        return self.repository.get(project_id)

    def get_all_projects(self) -> list[Project]:
        """Liste les parties disponibles."""

        return self.repository.list_all()

    def save_project(self, project: Project) -> Project:
        """Enregistre les modifications d'une partie."""

        return self.repository.save(project)
