"""Service applicatif central pour la gestion des archives."""

from pathlib import Path
from uuid import UUID

from jarvis.config.paths import PROJECTS_DIR
from jarvis.domain.entities.archive_record import (
    ArchiveRecord,
    EntityType,
)
from jarvis.domain.entities.park import Park
from jarvis.infrastructure.persistence.archive_repository import (
    ArchiveRepository,
)
from jarvis.infrastructure.persistence.atomic_writer import (
    write_json_atomic,
)
from jarvis.infrastructure.persistence.json_store import read_json


class ArchiveService:
    """Service central des archives de J.A.R.V.I.S."""

    def __init__(
        self,
        repository: ArchiveRepository | None = None,
        projects_dir: Path = PROJECTS_DIR,
    ):
        self.repository = repository or ArchiveRepository()
        self.projects_dir = Path(projects_dir)

    def archive_element(
        self,
        source_path: Path,
        entity_type: EntityType,
        entity_id: UUID,
        entity_name: str,
        original_location: str,
        parent_project_id: UUID | None = None,
    ) -> ArchiveRecord:
        return self.repository.archive(
            source_path=source_path,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            original_location=original_location,
            parent_project_id=parent_project_id,
        )

    def get_archive(self, archive_id: UUID) -> ArchiveRecord:
        return self.repository.get(archive_id)

    def get_archives(
        self,
        entity_type: EntityType | None = None,
    ) -> list[ArchiveRecord]:
        return self.repository.list_all(entity_type)

    def get_archive_content(self, archive_id: UUID) -> Path:
        return self.repository.get_payload_path(archive_id)

    def restore_archive(
        self,
        archive_id: UUID,
        destination: Path,
    ) -> ArchiveRecord:
        """Restaure un élément non indexé dans un registre secondaire."""

        return self.repository.restore(
            archive_id,
            destination,
        )

    def restore_park_archive(
        self,
        archive_id: UUID,
        destination: Path,
    ) -> ArchiveRecord:
        """Restaure un parc et le réinscrit dans l'index de son projet.

        L'index est écrit avant le déplacement. Si le déplacement échoue,
        son contenu précédent est rétabli afin d'éviter un parc référencé
        alors que ses fichiers sont toujours archivés.
        """

        record = self.get_archive(archive_id)
        if record.entity_type != "park":
            raise ValueError("Cette archive ne correspond pas à un parc.")

        if record.parent_project_id is None:
            raise ValueError("Le projet parent de ce parc est inconnu.")

        project_id = record.parent_project_id
        project_directory = self.projects_dir / str(project_id)
        project_file = project_directory / "project.json"
        index_file = project_directory / "parks" / "index.json"
        destination = Path(destination)
        expected_destination = (
            project_directory / "parks" / str(record.entity_id)
        )

        if not project_file.is_file():
            raise FileNotFoundError(
                "Le projet parent doit être restauré avant ce parc."
            )

        if destination.resolve() != expected_destination.resolve():
            raise ValueError(
                "La destination ne correspond pas à l'emplacement d'origine du parc."
            )

        if destination.exists():
            raise FileExistsError(
                f"La destination existe déjà : {destination}"
            )

        index = read_json(index_file)
        if not isinstance(index, dict):
            raise ValueError("Index des parcs invalide.")

        park_ids = index.get("park_ids")
        if (
            index.get("schema_version") != 1
            or not isinstance(park_ids, list)
            or any(not isinstance(item, str) for item in park_ids)
        ):
            raise ValueError("Structure de l'index des parcs invalide.")

        if len(park_ids) != len(set(park_ids)):
            raise ValueError(
                "L'index des parcs contient des identifiants dupliqués."
            )

        for indexed_park_id in park_ids:
            try:
                UUID(indexed_park_id)
            except ValueError as error:
                raise ValueError(
                    f"Identifiant de parc invalide : {indexed_park_id}"
                ) from error

        park_id_text = str(record.entity_id)
        if park_id_text in park_ids:
            raise FileExistsError(
                "Ce parc est déjà référencé dans le projet."
            )

        payload_path = self.get_archive_content(archive_id)
        park_file = payload_path / "park.json"
        park = read_json(park_file, Park)

        if park.id != record.entity_id or park.project_id != project_id:
            raise ValueError(
                "Les données du parc ne correspondent pas aux métadonnées de l'archive."
            )

        original_index = dict(index)
        updated_index = dict(index)
        updated_index["park_ids"] = [*park_ids, park_id_text]

        write_json_atomic(index_file, updated_index)

        try:
            return self.repository.restore(
                archive_id,
                destination,
            )
        except Exception:
            # L'écriture atomique restaure exactement l'index précédent.
            write_json_atomic(index_file, original_index)
            raise

    def permanently_delete_archive(
        self,
        archive_id: UUID,
    ) -> None:
        self.repository.delete_permanently(archive_id)
