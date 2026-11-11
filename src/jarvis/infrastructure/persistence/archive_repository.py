
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from jarvis.config.paths import ARCHIVES_DIR
from jarvis.domain.entities.archive_record import (
    ArchiveRecord,
    EntityType,
)
from jarvis.infrastructure.persistence.atomic_writer import (
    write_json_atomic,
)
from jarvis.infrastructure.persistence.json_store import read_json


class ArchiveRepository:
    """Gestion physique et centralisée des archives."""

    CATEGORIES = {
        "project": "Projects",
        "park": "Parks",
        "factory": "Factories",
        "machine": "Machines",
        "extractor": "Extractors",
        "generator": "Generators",
        "power_grid": "PowerGrids",
        "transfer": "Transfers",
    }

    def __init__(self, archives_dir: Path = ARCHIVES_DIR):
        self.archives_dir = Path(archives_dir)

    def _category_directory(self, entity_type: EntityType) -> Path:
        return self.archives_dir / self.CATEGORIES[entity_type]

    def _find_archive_directory(
        self,
        archive_id: UUID,
    ) -> tuple[ArchiveRecord, Path]:
        """Retrouve une archive par son identifiant."""

        if not self.archives_dir.exists():
            raise FileNotFoundError("Aucune archive disponible.")

        for category in self.CATEGORIES.values():
            category_dir = self.archives_dir / category

            if not category_dir.is_dir():
                continue

            archive_dir = category_dir / str(archive_id)
            metadata_file = archive_dir / "archive.json"

            if not metadata_file.is_file():
                continue

            record = read_json(metadata_file, ArchiveRecord)

            if record.archive_id != archive_id:
                raise ValueError(
                    f"Identifiant d'archive incohérent : {archive_id}"
                )

            return record, archive_dir

        raise FileNotFoundError(
            f"Archive introuvable : {archive_id}"
        )

    def archive(
        self,
        source_path: Path,
        entity_type: EntityType,
        entity_id: UUID,
        entity_name: str,
        original_location: str,
        parent_project_id: UUID | None = None,
    ) -> ArchiveRecord:
        """
        Déplace un fichier ou un dossier dans les archives.

        Le déplacement passe par un dossier temporaire afin
        de ne publier l'archive qu'une fois ses métadonnées écrites.
        """

        source_path = Path(source_path)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Élément à archiver introuvable : {source_path}"
            )

        if entity_type not in self.CATEGORIES:
            raise ValueError(
                f"Type d'archive non pris en charge : {entity_type}"
            )

        archive_root = self.archives_dir.resolve()
        resolved_source = source_path.resolve()

        # Interdit d'archiver un élément déjà contenu dans les archives.
        try:
            resolved_source.relative_to(archive_root)
        except ValueError:
            pass
        else:
            raise ValueError(
                "Un élément déjà archivé ne peut pas être réarchivé."
            )

        category_dir = self._category_directory(entity_type)
        category_dir.mkdir(parents=True, exist_ok=True)

        archive_id = uuid4()

        final_directory = category_dir / str(archive_id)
        temporary_directory = category_dir / f".{archive_id}.pending"
        payload_path = temporary_directory / "data"

        record = ArchiveRecord(
            archive_id=archive_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name.strip(),
            parent_project_id=parent_project_id,
            original_location=original_location,
        )

        if not record.entity_name:
            raise ValueError("Le nom de l'élément est obligatoire.")

        temporary_directory.mkdir()

        try:
            # Déplacement de l'élément complet.
            shutil.move(str(source_path), str(payload_path))

            # Enregistrement des métadonnées.
            write_json_atomic(
                temporary_directory / "archive.json",
                record,
            )

            # Publication de l'archive terminée.
            temporary_directory.rename(final_directory)

        except Exception:
            # Restauration si une étape de l'archivage échoue.
            if payload_path.exists() and not source_path.exists():
                source_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                shutil.move(
                    str(payload_path),
                    str(source_path),
                )

            shutil.rmtree(
                temporary_directory,
                ignore_errors=True,
            )
            raise

        return record

    def get(self, archive_id: UUID) -> ArchiveRecord:
        """Récupère les métadonnées d'une archive."""

        record, _ = self._find_archive_directory(archive_id)
        return record

    def list_all(
        self,
        entity_type: EntityType | None = None,
    ) -> list[ArchiveRecord]:
        """Liste les archives, éventuellement par catégorie."""

        records = []

        categories = (
            [self.CATEGORIES[entity_type]]
            if entity_type is not None
            else list(self.CATEGORIES.values())
        )

        for category in categories:
            category_dir = self.archives_dir / category

            if not category_dir.is_dir():
                continue

            for archive_dir in category_dir.iterdir():

                if not archive_dir.is_dir():
                    continue

                # Les dossiers temporaires ne sont pas des archives publiées.
                if archive_dir.name.startswith("."):
                    continue

                metadata_file = archive_dir / "archive.json"

                if not metadata_file.is_file():
                    continue

                record = read_json(metadata_file, ArchiveRecord)

                if archive_dir.name != str(record.archive_id):
                    raise ValueError(
                        f"Archive incohérente : {archive_dir}"
                    )

                records.append(record)

        return sorted(
            records,
            key=lambda record: record.archived_at,
            reverse=True,
        )

    def get_payload_path(self, archive_id: UUID) -> Path:
        """Retourne le chemin du contenu archivé en lecture seule."""

        record, archive_dir = self._find_archive_directory(
            archive_id
        )

        payload_path = archive_dir / "data"

        if not payload_path.exists():
            raise FileNotFoundError(
                f"Contenu absent de l'archive : {record.archive_id}"
            )

        return payload_path

    def restore(
        self,
        archive_id: UUID,
        destination: Path,
    ) -> ArchiveRecord:
        """Restaure le contenu d'une archive vers sa destination."""

        record, archive_dir = self._find_archive_directory(
            archive_id
        )

        payload_path = archive_dir / "data"
        destination = Path(destination)

        if not payload_path.exists():
            raise FileNotFoundError(
                "Le contenu de l'archive est introuvable."
            )

        if destination.exists():
            raise FileExistsError(
                f"La destination existe déjà : {destination}"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            shutil.move(
                str(payload_path),
                str(destination),
            )

            shutil.rmtree(archive_dir)

        except Exception:
            # Si la finalisation échoue, conserver l'archive.
            if destination.exists() and not payload_path.exists():
                archive_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                shutil.move(
                    str(destination),
                    str(payload_path),
                )

            raise

        return record

    def delete_permanently(self, archive_id: UUID) -> None:
        """Détruit définitivement une archive après validation."""

        _, archive_dir = self._find_archive_directory(archive_id)

        if not archive_dir.is_dir():
            raise FileNotFoundError(archive_dir)

        shutil.rmtree(archive_dir)
