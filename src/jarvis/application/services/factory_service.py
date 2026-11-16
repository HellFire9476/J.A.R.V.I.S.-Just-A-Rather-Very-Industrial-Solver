from dataclasses import asdict, is_dataclass
from typing import Any
from uuid import UUID

from jarvis.domain.entities.factory import Factory
from jarvis.domain.entities.production import ProductionPlan
from jarvis.domain.entities.scenario import Scenario
from jarvis.infrastructure.persistence.factory_repository import FactoryRepository


class FactoryService:
    """Coordonne la gestion des usines et l'enregistrement des simulations."""

    def __init__(self, repository: FactoryRepository | None = None) -> None:
        self.repository = repository or FactoryRepository()

    def create_factory(
        self,
        project_id: UUID,
        park_id: UUID,
        name: str,
        description: str = "",
    ) -> Factory:
        factory = Factory(
            project_id=project_id,
            park_id=park_id,
            name=name,
            description=description,
        )
        return self.repository.create(factory)

    def get_factory(self, project_id: UUID, park_id: UUID, factory_id: UUID) -> Factory:
        return self.repository.get(project_id, park_id, factory_id)

    def list_factories(self, project_id: UUID, park_id: UUID) -> list[Factory]:
        return self.repository.list_all(project_id, park_id)

    def update_factory(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
        name: str,
        description: str = "",
    ) -> Factory:
        factory = self.get_factory(project_id, park_id, factory_id)
        updated = Factory.model_validate(
            {
                **factory.model_dump(mode="python"),
                "name": name,
                "description": description,
            }
        )
        return self.repository.update(updated)

    def archive_factory(self, project_id: UUID, park_id: UUID, factory_id: UUID) -> None:
        self.repository.archive(project_id, park_id, factory_id)

    def list_scenarios(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
    ) -> list[Scenario]:
        return self.repository.list_scenarios(project_id, park_id, factory_id)

    def get_scenario(
        self,
        project_id: UUID,
        park_id: UUID,
        factory_id: UUID,
        scenario_id: UUID,
    ) -> Scenario:
        return self.repository.get_scenario(project_id, park_id, factory_id, scenario_id)

    def save_simulation(
        self,
        project_id: UUID,
        park_id: UUID,
        scenario_name: str,
        plan: ProductionPlan,
        simulation_inputs: dict[str, Any],
        *,
        factory_id: UUID | None = None,
        factory_name: str | None = None,
        factory_description: str = "",
    ) -> tuple[Factory, Scenario]:
        if not isinstance(plan, ProductionPlan):
            raise TypeError("Le résultat à enregistrer doit être un ProductionPlan.")
        if not isinstance(simulation_inputs, dict) or not simulation_inputs:
            raise ValueError("Les paramètres de la simulation sont absents.")

        if factory_id is None:
            if not factory_name or not factory_name.strip():
                raise ValueError("Le nom de la nouvelle usine est obligatoire.")
            factory = Factory(
                project_id=project_id,
                park_id=park_id,
                name=factory_name,
                description=factory_description,
            )
        else:
            factory = self.get_factory(project_id, park_id, factory_id)

        snapshot = asdict(plan) if is_dataclass(plan) else dict(plan)
        scenario = Scenario(
            project_id=project_id,
            park_id=park_id,
            factory_id=factory.id,
            name=scenario_name,
            target_class_name=plan.target_class_name,
            target_name=plan.target_name,
            target_rate_per_minute=plan.target_rate_per_minute,
            target_unit_label=plan.target_unit_label,
            locale=plan.locale,
            simulation_inputs=simulation_inputs,
            plan_snapshot=snapshot,
        )
        if factory_id is None:
            return self.repository.create_with_scenario(factory, scenario)
        return self.repository.add_scenario(scenario)
