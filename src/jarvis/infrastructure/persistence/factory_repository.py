import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from jarvis.config.paths import PROJECTS_DIR
from jarvis.domain.entities.factory import Factory
from jarvis.domain.entities.scenario import Scenario
from jarvis.infrastructure.persistence.archive_repository import ArchiveRepository
from jarvis.infrastructure.persistence.atomic_writer import write_json_atomic
from jarvis.infrastructure.persistence.json_store import read_json
from jarvis.infrastructure.persistence.park_repository import ParkRepository


class FactoryRepository:
    """Persistance JSON des usines et scénarios, isolés par parc."""

    def __init__(
        self,
        projects_dir: Path = PROJECTS_DIR,
        park_repository: ParkRepository | None = None,
        archive_repository: ArchiveRepository | None = None,
    ) -> None:
        self.projects_dir = Path(projects_dir)
        archive_root = self.projects_dir.parent / "Archives"
        self.archive_repository = archive_repository or ArchiveRepository(archive_root)
        self.park_repository = park_repository or ParkRepository(
            self.projects_dir,
            archive_repository=self.archive_repository,
        )

    def _factories_directory(self, project_id: UUID, park_id: UUID) -> Path:
        return (
            self.projects_dir
            / str(project_id)
            / "parks"
            / str(park_id)
            / "factories"
        )

    def _index_path(self, project_id: UUID, park_id: UUID) -> Path:
        return self._factories_directory(project_id, park_id) / "index.json"

    def _factory_directory(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
    ) -> Path:
        return self._factories_directory(project_id, park_id) / str(factory_id)

    def _factory_path(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
    ) -> Path:
        return self._factory_directory(project_id, park_id, factory_id) / "factory.json"

    def _scenarios_path(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
    ) -> Path:
        return self._factory_directory(project_id, park_id, factory_id) / "scenarios.json"

    def _legacy_scenarios_directory(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
    ) -> Path:
        return self._factory_directory(project_id, park_id, factory_id) / "scenarios"

    def _legacy_scenario_path(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
        scenario_id: UUID,
    ) -> Path:
        """Ancien emplacement individuel, lu uniquement pour compatibilité."""

        return (
            self._legacy_scenarios_directory(project_id, park_id, factory_id)
            / f"{scenario_id}.json"
        )

    @staticmethod
    def _scenarios_payload(scenarios: list[Scenario]) -> dict:
        return {
            "schema_version": 1,
            "scenarios": [scenario.model_dump(mode="json") for scenario in scenarios],
        }

    def _read_scenarios(self, factory: Factory) -> list[Scenario]:
        """Lit les scénarios depuis un index compact, ou l'ancien format individuel."""

        scenarios_path = self._scenarios_path(
            factory.project_id, factory.park_id, factory.id
        )
        legacy_directory = self._legacy_scenarios_directory(
            factory.project_id, factory.park_id, factory.id
        )
        legacy_index_path = legacy_directory / "index.json"
        if scenarios_path.is_file():
            data = read_json(scenarios_path)
            if (
                not isinstance(data, dict)
                or data.get("schema_version") != 1
                or not isinstance(data.get("scenarios"), list)
            ):
                raise ValueError("Fichier des scénarios invalide.")
            scenarios = [Scenario.model_validate(item) for item in data["scenarios"]]
        elif legacy_index_path.is_file():
            # Compatibilité avec une version intermédiaire utilisant scenarios/index.json.
            data = read_json(legacy_index_path)
            if (
                not isinstance(data, dict)
                or data.get("schema_version") != 1
                or not isinstance(data.get("scenarios"), list)
            ):
                raise ValueError("Ancien index des scénarios invalide.")
            scenarios = [Scenario.model_validate(item) for item in data["scenarios"]]
        else:
            scenarios = []
            for scenario_id in factory.scenario_ids:
                legacy_path = self._legacy_scenario_path(
                    factory.project_id, factory.park_id, factory.id, scenario_id
                )
                scenarios.append(read_json(legacy_path, Scenario))

        scenario_ids = [scenario.id for scenario in scenarios]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("L'index des scénarios contient des identifiants dupliqués.")
        if set(scenario_ids) != set(factory.scenario_ids):
            raise ValueError("Les scénarios enregistrés ne correspondent pas à l'usine.")
        for scenario in scenarios:
            self._validate_scenario_scope(factory, scenario)
        return scenarios

    def _ensure_park(self, project_id: UUID, park_id: UUID) -> None:
        park = self.park_repository.get(project_id, park_id)
        if park.project_id != project_id or park.id != park_id:
            raise ValueError("Le parc demandé ne correspond pas à la partie.")

    def _read_index(self, project_id: UUID, park_id: UUID) -> dict:
        path = self._index_path(project_id, park_id)
        if not path.is_file():
            return {"schema_version": 1, "factory_ids": []}
        data = read_json(path)
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != 1
            or not isinstance(data.get("factory_ids"), list)
            or any(not isinstance(value, str) for value in data["factory_ids"])
        ):
            raise ValueError("Index des usines invalide.")
        if len(data["factory_ids"]) != len(set(data["factory_ids"])):
            raise ValueError("L'index des usines contient des identifiants dupliqués.")
        for value in data["factory_ids"]:
            try:
                UUID(value)
            except ValueError as error:
                raise ValueError(f"Identifiant d'usine invalide : {value}") from error
        return data

    def _write_index(self, project_id: UUID, park_id: UUID, index: dict) -> None:
        write_json_atomic(self._index_path(project_id, park_id), index)

    def list_all(self, project_id: UUID, park_id: UUID) -> list[Factory]:
        self._ensure_park(project_id, park_id)
        index = self._read_index(project_id, park_id)
        factories = [
            self.get(project_id, park_id, UUID(factory_id))
            for factory_id in index["factory_ids"]
        ]
        return sorted(factories, key=lambda item: item.name.casefold())

    def get(self, project_id: UUID, park_id: UUID, factory_id: UUID) -> Factory:
        self._ensure_park(project_id, park_id)
        index = self._read_index(project_id, park_id)
        if str(factory_id) not in index["factory_ids"]:
            raise FileNotFoundError(f"Usine introuvable : {factory_id}")
        factory = read_json(
            self._factory_path(project_id, park_id, factory_id),
            Factory,
        )
        if (
            factory.id != factory_id
            or factory.project_id != project_id
            or factory.park_id != park_id
        ):
            raise ValueError("Les identifiants de l'usine ne correspondent pas à son emplacement.")
        return factory

    def create(self, factory: Factory) -> Factory:
        if factory.scenario_ids:
            raise ValueError(
                "Une usine créée sans scénario ne peut pas référencer des scénarios absents."
            )
        self._ensure_park(factory.project_id, factory.park_id)
        index = self._read_index(factory.project_id, factory.park_id)
        self._ensure_unique_name(factory, factory.name)
        if str(factory.id) in index["factory_ids"]:
            raise FileExistsError("Cette usine existe déjà.")
        directory = self._factory_directory(
            factory.project_id,
            factory.park_id,
            factory.id,
        )
        if directory.exists():
            raise FileExistsError(f"Le dossier de cette usine existe déjà : {directory}")
        directory.mkdir(parents=True)
        try:
            write_json_atomic(directory / "scenarios.json", self._scenarios_payload([]))
            write_json_atomic(directory / "factory.json", factory)
            index["factory_ids"].append(str(factory.id))
            self._write_index(factory.project_id, factory.park_id, index)
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        return factory

    def create_with_scenario(
        self,
        factory: Factory,
        scenario: Scenario,
    ) -> tuple[Factory, Scenario]:
        if factory.scenario_ids:
            raise ValueError(
                "Une nouvelle usine ne peut pas contenir de références de scénarios préexistantes."
            )
        self._validate_scenario_scope(factory, scenario)
        factory = Factory.model_validate(
            {**factory.model_dump(mode="python"), "scenario_ids": [scenario.id]}
        )
        self._ensure_park(factory.project_id, factory.park_id)
        index = self._read_index(factory.project_id, factory.park_id)
        self._ensure_unique_name(factory, factory.name)
        if str(factory.id) in index["factory_ids"]:
            raise FileExistsError("Cette usine existe déjà.")
        directory = self._factory_directory(factory.project_id, factory.park_id, factory.id)
        if directory.exists():
            raise FileExistsError(f"Le dossier de cette usine existe déjà : {directory}")
        directory.mkdir(parents=True)
        try:
            write_json_atomic(directory / "factory.json", factory)
            write_json_atomic(
                directory / "scenarios.json",
                self._scenarios_payload([scenario]),
            )
            index["factory_ids"].append(str(factory.id))
            self._write_index(factory.project_id, factory.park_id, index)
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        return factory, scenario

    def update(self, factory: Factory) -> Factory:
        current = self.get(factory.project_id, factory.park_id, factory.id)
        if current.id != factory.id:
            raise ValueError("L'identifiant d'une usine ne peut pas être modifié.")
        if current.scenario_ids != factory.scenario_ids:
            raise ValueError(
                "Les scénarios d'une usine doivent être gérés par les opérations dédiées."
            )
        if current.project_id != factory.project_id or current.park_id != factory.park_id:
            raise ValueError("Une usine ne peut pas changer de partie ou de parc.")
        self._ensure_unique_name(factory, factory.name, exclude_id=factory.id)
        factory.updated_at = datetime.now(UTC)
        write_json_atomic(
            self._factory_path(factory.project_id, factory.park_id, factory.id),
            factory,
        )
        return factory

    def list_scenarios(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
    ) -> list[Scenario]:
        factory = self.get(project_id, park_id, factory_id)
        scenarios = self._read_scenarios(factory)
        return sorted(scenarios, key=lambda item: item.created_at, reverse=True)

    def get_scenario(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
        scenario_id: UUID,
    ) -> Scenario:
        factory = self.get(project_id, park_id, factory_id)
        for scenario in self._read_scenarios(factory):
            if scenario.id == scenario_id:
                return scenario
        raise FileNotFoundError(f"Scénario introuvable : {scenario_id}")

    def add_scenario(self, scenario: Scenario) -> tuple[Factory, Scenario]:
        factory = self.get(scenario.project_id, scenario.park_id, scenario.factory_id)
        self._validate_scenario_scope(factory, scenario)
        if scenario.id in factory.scenario_ids:
            raise FileExistsError("Ce scénario existe déjà dans cette usine.")

        existing_scenarios = self._read_scenarios(factory)
        if any(
            existing.name.casefold() == scenario.name.casefold()
            for existing in existing_scenarios
        ):
            raise ValueError(
                f"Un scénario nommé '{scenario.name}' existe déjà dans cette usine."
            )

        scenarios_path = self._scenarios_path(
            scenario.project_id, scenario.park_id, scenario.factory_id
        )
        scenarios_path.parent.mkdir(parents=True, exist_ok=True)
        previous_index_exists = scenarios_path.is_file()
        previous_index = read_json(scenarios_path) if previous_index_exists else None
        updated = Factory.model_validate(
            {
                **factory.model_dump(mode="python"),
                "scenario_ids": [*factory.scenario_ids, scenario.id],
                "updated_at": datetime.now(UTC),
            }
        )

        try:
            write_json_atomic(
                scenarios_path,
                self._scenarios_payload([*existing_scenarios, scenario]),
            )
            write_json_atomic(
                self._factory_path(factory.project_id, factory.park_id, factory.id),
                updated,
            )
        except Exception:
            if previous_index_exists:
                write_json_atomic(scenarios_path, previous_index)
            else:
                scenarios_path.unlink(missing_ok=True)
            raise
        return updated, scenario

    def archive(self, project_id: UUID, park_id: UUID, factory_id: UUID) -> None:
        factory = self.get(project_id, park_id, factory_id)
        index = self._read_index(project_id, park_id)
        source = self._factory_directory(project_id, park_id, factory_id)
        record = self.archive_repository.archive(
            source_path=source,
            entity_type="factory",
            entity_id=factory.id,
            entity_name=factory.name,
            original_location=(
                f"Projects/{project_id}/parks/{park_id}/factories/{factory_id}"
            ),
            parent_project_id=project_id,
        )
        try:
            index["factory_ids"].remove(str(factory_id))
            self._write_index(project_id, park_id, index)
        except Exception:
            self.archive_repository.restore(record.archive_id, source)
            raise

    def _ensure_unique_name(
        self,
        factory: Factory,
        name: str,
        exclude_id: UUID | None = None,
    ) -> None:
        for existing in self.list_all(factory.project_id, factory.park_id):
            if (
                existing.id != exclude_id
                and existing.name.casefold() == name.strip().casefold()
            ):
                raise ValueError(f"Une usine nommée '{name.strip()}' existe déjà dans ce parc.")

    @staticmethod
    def _validate_scenario_scope(factory: Factory, scenario: Scenario) -> None:
        if (
            scenario.factory_id != factory.id
            or scenario.project_id != factory.project_id
            or scenario.park_id != factory.park_id
        ):
            raise ValueError("Le scénario ne correspond pas à l'usine, au parc ou au projet.")
