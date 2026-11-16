"""Service applicatif central pour la gestion des archives."""

from pathlib import Path
from uuid import UUID

from jarvis.config.paths import PROJECTS_DIR
from jarvis.domain.entities.archive_record import (
    ArchiveRecord,
    EntityType,
)
from jarvis.domain.entities.factory import Factory
from jarvis.domain.entities.park import Park
from jarvis.domain.entities.scenario import Scenario
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

    def restore_factory_archive(
        self,
        archive_id: UUID,
        destination: Path,
    ) -> ArchiveRecord:
        """Restaure une usine et la réinscrit dans l'index de son parc."""

        record = self.get_archive(archive_id)
        if record.entity_type != "factory":
            raise ValueError("Cette archive ne correspond pas à une usine.")
        if record.parent_project_id is None:
            raise ValueError("Le projet parent de cette usine est inconnu.")

        parts = Path(record.original_location).parts
        if (
            len(parts) != 6
            or parts[0] != "Projects"
            or parts[2] != "parks"
            or parts[4] != "factories"
        ):
            raise ValueError("L'emplacement d'origine de cette usine est invalide.")

        project_id = record.parent_project_id
        try:
            path_project_id = UUID(parts[1])
            park_id = UUID(parts[3])
            factory_id = UUID(parts[5])
        except ValueError as error:
            raise ValueError(
                "Les identifiants de l'emplacement de l'usine sont invalides."
            ) from error

        if path_project_id != project_id or factory_id != record.entity_id:
            raise ValueError(
                "L'emplacement d'origine ne correspond pas aux métadonnées de l'archive."
            )

        project_directory = self.projects_dir / str(project_id)
        park_directory = project_directory / "parks" / str(park_id)
        project_file = project_directory / "project.json"
        park_file = park_directory / "park.json"
        index_file = park_directory / "factories" / "index.json"
        expected_destination = park_directory / "factories" / str(factory_id)
        destination = Path(destination)

        if not project_file.is_file():
            raise FileNotFoundError("Le projet parent doit être restauré avant cette usine.")
        if not park_file.is_file():
            raise FileNotFoundError("Le parc parent doit être restauré avant cette usine.")
        if destination.resolve() != expected_destination.resolve():
            raise ValueError(
                "La destination ne correspond pas à l'emplacement d'origine de l'usine."
            )
        if destination.exists():
            raise FileExistsError(f"La destination existe déjà : {destination}")
        if not index_file.is_file():
            raise FileNotFoundError("L'index des usines du parc est introuvable.")

        park = read_json(park_file, Park)
        if park.id != park_id or park.project_id != project_id:
            raise ValueError("Les données du parc parent ne correspondent pas à l'archive.")

        payload_path = self.get_archive_content(archive_id)
        factory = read_json(payload_path / "factory.json", Factory)
        if (
            factory.id != factory_id
            or factory.project_id != project_id
            or factory.park_id != park_id
        ):
            raise ValueError(
                "Les données de l'usine ne correspondent pas aux métadonnées de l'archive."
            )
        scenarios_path = payload_path / "scenarios.json"
        legacy_scenarios_directory = payload_path / "scenarios"
        legacy_index_path = legacy_scenarios_directory / "index.json"
        if scenarios_path.is_file():
            scenarios_data = read_json(scenarios_path)
            if (
                not isinstance(scenarios_data, dict)
                or scenarios_data.get("schema_version") != 1
                or not isinstance(scenarios_data.get("scenarios"), list)
            ):
                raise ValueError("Fichier des scénarios archivé invalide.")
            scenarios = [
                Scenario.model_validate(item) for item in scenarios_data["scenarios"]
            ]
        elif legacy_index_path.is_file():
            scenarios_data = read_json(legacy_index_path)
            if (
                not isinstance(scenarios_data, dict)
                or scenarios_data.get("schema_version") != 1
                or not isinstance(scenarios_data.get("scenarios"), list)
            ):
                raise ValueError("Ancien index des scénarios archivé invalide.")
            scenarios = [
                Scenario.model_validate(item) for item in scenarios_data["scenarios"]
            ]
        else:
            # Compatibilité avec les premières archives qui stockaient un fichier par scénario.
            scenarios = [
                read_json(legacy_scenarios_directory / f"{scenario_id}.json", Scenario)
                for scenario_id in factory.scenario_ids
            ]

        archived_scenario_ids = [scenario.id for scenario in scenarios]
        if (
            len(archived_scenario_ids) != len(set(archived_scenario_ids))
            or set(archived_scenario_ids) != set(factory.scenario_ids)
        ):
            raise ValueError(
                "Les scénarios archivés ne correspondent pas aux références de l'usine."
            )
        for scenario in scenarios:
            if (
                scenario.factory_id != factory_id
                or scenario.project_id != project_id
                or scenario.park_id != park_id
            ):
                raise ValueError("Un scénario archivé ne correspond pas à son usine.")

        index = read_json(index_file)
        if not isinstance(index, dict):
            raise ValueError("Index des usines invalide.")
        factory_ids = index.get("factory_ids")
        if (
            index.get("schema_version") != 1
            or not isinstance(factory_ids, list)
            or any(not isinstance(item, str) for item in factory_ids)
        ):
            raise ValueError("Structure de l'index des usines invalide.")
        if len(factory_ids) != len(set(factory_ids)):
            raise ValueError("L'index des usines contient des identifiants dupliqués.")
        active_factories: list[Factory] = []
        for active_factory_id in factory_ids:
            try:
                parsed_active_id = UUID(active_factory_id)
            except ValueError as error:
                raise ValueError(
                    "L'index contient un identifiant d'usine invalide."
                ) from error
            active_factory_path = (
                park_directory
                / "factories"
                / str(parsed_active_id)
                / "factory.json"
            )
            active_factory = read_json(active_factory_path, Factory)
            if (
                active_factory.id != parsed_active_id
                or active_factory.project_id != project_id
                or active_factory.park_id != park_id
            ):
                raise ValueError("Une usine active ne correspond pas à son emplacement.")
            active_factories.append(active_factory)

        if factory_id in {item.id for item in active_factories}:
            raise FileExistsError("Cette usine est déjà référencée dans le parc.")
        if any(
            item.name.casefold() == factory.name.casefold()
            for item in active_factories
        ):
            raise ValueError(
                "Une usine active porte déjà ce nom dans le parc. "
                "Renommez-la avant de restaurer cette archive."
            )

        original_index = dict(index)
        updated_index = dict(index)
        updated_index["factory_ids"] = [*factory_ids, str(factory_id)]
        write_json_atomic(index_file, updated_index)
        try:
            return self.repository.restore(archive_id, destination)
        except Exception:
            write_json_atomic(index_file, original_index)
            raise

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
