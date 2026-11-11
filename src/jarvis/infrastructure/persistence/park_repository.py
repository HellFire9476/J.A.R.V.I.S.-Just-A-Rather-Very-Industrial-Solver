import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from jarvis.config.paths import PROJECTS_DIR
from jarvis.domain.entities.park import Park
from jarvis.infrastructure.persistence.archive_repository import (
    ArchiveRepository,
)
from jarvis.infrastructure.persistence.atomic_writer import (
    write_json_atomic,
)
from jarvis.infrastructure.persistence.json_store import read_json


class ParkRepository:
    """Gestion physique des parcs industriels en JSON."""

    def __init__(
        self,
        projects_dir: Path = PROJECTS_DIR,
        archive_repository: ArchiveRepository | None = None,
    ):
        self.projects_dir = Path(projects_dir)

        # Le dépôt des parcs et celui des projets partagent ce dossier.
        archive_root = self.projects_dir.parent / "Archives"
        self.archive_repository = (
            archive_repository or ArchiveRepository(archive_root)
        )

    def _project_directory(self, project_id: UUID) -> Path:
        return self.projects_dir / str(project_id)

    def _parks_directory(self, project_id: UUID) -> Path:
        return self._project_directory(project_id) / "parks"

    def _index_file(self, project_id: UUID) -> Path:
        return self._parks_directory(project_id) / "index.json"

    def _ensure_project_exists(self, project_id: UUID) -> None:
        project_file = (
            self._project_directory(project_id) / "project.json"
        )

        if not project_file.is_file():
            raise FileNotFoundError(
                f"Projet introuvable : {project_id}"
            )

    def _read_index(self, project_id: UUID) -> dict:
        index_file = self._index_file(project_id)
        data = read_json(index_file)

        if not isinstance(data, dict):
            raise ValueError("Index des parcs invalide.")

        park_ids = data.get("park_ids")

        if (
            data.get("schema_version") != 1
            or not isinstance(park_ids, list)
            or any(not isinstance(item, str) for item in park_ids)
        ):
            raise ValueError("Structure de l'index des parcs invalide.")

        if len(park_ids) != len(set(park_ids)):
            raise ValueError(
                "L'index contient des identifiants dupliqués."
            )

        for park_id in park_ids:
            try:
                UUID(park_id)
            except ValueError as error:
                raise ValueError(
                    f"Identifiant de parc invalide : {park_id}"
                ) from error

        return data

    def _park_directory(
        self,
        project_id: UUID,
        park_id: UUID,
    ) -> Path:
        return self._parks_directory(project_id) / str(park_id)

    def get(
        self,
        project_id: UUID,
        park_id: UUID,
    ) -> Park:
        """Récupère un parc précis."""

        self._ensure_project_exists(project_id)
        index = self._read_index(project_id)

        if str(park_id) not in index["park_ids"]:
            raise FileNotFoundError(
                f"Parc introuvable : {park_id}"
            )

        park_file = (
            self._park_directory(project_id, park_id) / "park.json"
        )
        park = read_json(park_file, Park)

        if park.id != park_id or park.project_id != project_id:
            raise ValueError(
                "Les identifiants du parc ne correspondent pas."
            )

        return park

    def list_all(self, project_id: UUID) -> list[Park]:
        """Retourne tous les parcs d'un projet."""

        self._ensure_project_exists(project_id)
        index = self._read_index(project_id)

        parks = [
            self.get(project_id, UUID(park_id))
            for park_id in index["park_ids"]
        ]

        return sorted(
            parks,
            key=lambda park: park.name.casefold(),
        )

    def create(self, park: Park) -> Park:
        """Crée un parc et actualise son index."""

        self._ensure_project_exists(park.project_id)
        index = self._read_index(park.project_id)

        if str(park.id) in index["park_ids"]:
            raise FileExistsError("Ce parc existe déjà.")

        park_directory = self._park_directory(
            park.project_id,
            park.id,
        )

        if park_directory.exists():
            raise FileExistsError(
                "Le répertoire de ce parc existe déjà."
            )

        park_directory.mkdir(parents=True)

        try:
            write_json_atomic(
                park_directory / "park.json",
                park,
            )

            index["park_ids"].append(str(park.id))

            write_json_atomic(
                self._index_file(park.project_id),
                index,
            )

        except Exception:
            shutil.rmtree(park_directory, ignore_errors=True)
            raise

        return park

    def update(self, park: Park) -> Park:
        """Enregistre les modifications d'un parc."""

        self._ensure_project_exists(park.project_id)

        # Vérifie que le parc appartient bien à cet index.
        existing = self.get(park.project_id, park.id)

        if existing.id != park.id:
            raise ValueError("Identité du parc incohérente.")

        park.updated_at = datetime.now(UTC)

        write_json_atomic(
            self._park_directory(
                park.project_id,
                park.id,
            ) / "park.json",
            park,
        )

        return park

    def delete(
        self,
        project_id: UUID,
        park_id: UUID,
    ) -> None:
        """Archive un parc dans le système central d'archives."""

        park = self.get(project_id, park_id)
        index = self._read_index(project_id)
        park_directory = self._park_directory(
            project_id,
            park_id,
        )

        record = self.archive_repository.archive(
            source_path=park_directory,
            entity_type="park",
            entity_id=park.id,
            entity_name=park.name,
            original_location=(
                f"Projects/{project_id}/parks/{park_id}"
            ),
            parent_project_id=project_id,
        )

        try:
            index["park_ids"].remove(str(park_id))

            write_json_atomic(
                self._index_file(project_id),
                index,
            )

        except Exception:
            # Si l'index ne peut pas être actualisé, restaurer le parc.
            self.archive_repository.restore(
                record.archive_id,
                park_directory,
            )
            raise
