
from uuid import UUID

from jarvis.domain.entities.park import Park
from jarvis.infrastructure.persistence.park_repository import (
    ParkRepository,
)
from jarvis.infrastructure.persistence.project_repository import (
    ProjectRepository,
)


class ParkService:
    """Coordonne la gestion des parcs industriels."""

    def __init__(
        self,
        park_repository: ParkRepository | None = None,
        project_repository: ProjectRepository | None = None,
    ):
        self.park_repository = (
            park_repository or ParkRepository()
        )

        self.project_repository = (
            project_repository or ProjectRepository()
        )

    def create_park(
        self,
        project_id: UUID,
        name: str,
        description: str = "",
        location: str | None = None,
    ) -> Park:
        """Crée un parc dans une partie existante."""

        # Vérification de la partie
        self.project_repository.get(project_id)

        normalized_name = name.strip().casefold()

        if not normalized_name:
            raise ValueError("Le nom du parc est obligatoire.")

        # Vérification des doublons
        existing_parks = self.park_repository.list_all(
            project_id
        )

        if any(
            park.name.casefold() == normalized_name
            for park in existing_parks
        ):
            raise ValueError(
                f"Un parc nommé '{name.strip()}' existe déjà."
            )

        park = Park(
            project_id=project_id,
            name=name,
            description=description,
            location=location,
        )

        return self.park_repository.create(park)

    def get_park(
        self,
        project_id: UUID,
        park_id: UUID,
    ) -> Park:
        return self.park_repository.get(
            project_id,
            park_id,
        )

    def get_all_parks(
        self,
        project_id: UUID,
    ) -> list[Park]:
        self.project_repository.get(project_id)

        return self.park_repository.list_all(project_id)

    def update_park(
        self,
        project_id: UUID,
        park_id: UUID,
        name: str,
        description: str = "",
        location: str | None = None,
    ) -> Park:
        """Modifie les informations d'un parc."""

        park = self.get_park(project_id, park_id)

        normalized_name = name.strip().casefold()

        if not normalized_name:
            raise ValueError("Le nom du parc est obligatoire.")

        for other in self.get_all_parks(project_id):
            if (
                other.id != park_id
                and other.name.casefold() == normalized_name
            ):
                raise ValueError(
                    f"Un parc nommé '{name.strip()}' existe déjà."
                )

        park.name = name
        park.description = description
        park.location = location

        return self.park_repository.update(park)

    def delete_park(
        self,
        project_id: UUID,
        park_id: UUID,
    ) -> None:
        """Supprime un parc en conservant son archive."""

        self.park_repository.delete(
            project_id,
            park_id,
        )
