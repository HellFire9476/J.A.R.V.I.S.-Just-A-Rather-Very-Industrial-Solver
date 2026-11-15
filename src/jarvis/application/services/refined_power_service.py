"""Orchestration du module Refined Power pour les parcs industriels."""

from uuid import UUID

from jarvis.domain.entities.mod import ParkModInstallation
from jarvis.domain.entities.refined_power import (
    RefinedPowerCatalog,
    RefinedPowerChainConfiguration,
    RefinedPowerParkConfiguration,
)
from jarvis.engines.refined_power_engine import (
    RefinedPowerChainResult,
    RefinedPowerEngine,
)
from jarvis.infrastructure.catalog.refined_power_catalog_repository import (
    RefinedPowerCatalogRepository,
)
from jarvis.infrastructure.persistence.park_repository import ParkRepository


class RefinedPowerService:
    """Gère les chaînes Refined Power et leurs calculs pour un parc précis."""

    MOD_ID = "refined_power"

    def __init__(
        self,
        park_repository: ParkRepository | None = None,
        catalog_repository: RefinedPowerCatalogRepository | None = None,
        engine: RefinedPowerEngine | None = None,
    ):
        self.park_repository = park_repository or ParkRepository()
        self.catalog_repository = catalog_repository or RefinedPowerCatalogRepository()
        self.engine = engine or RefinedPowerEngine()

    def get_catalog(self) -> RefinedPowerCatalog:
        """Retourne le catalogue technique local et versionné."""

        return self.catalog_repository.get_catalog()

    def get_configuration(
        self,
        project_id: UUID,
        park_id: UUID,
    ) -> RefinedPowerParkConfiguration:
        """Lit la configuration d'un parc, même si le module est désactivé."""

        park = self.park_repository.get(project_id, park_id)
        installation = park.mods.get(self.MOD_ID)
        if installation is None or not installation.configuration:
            return RefinedPowerParkConfiguration()
        return RefinedPowerParkConfiguration.model_validate(
            installation.configuration
        )

    def list_chains(
        self,
        project_id: UUID,
        park_id: UUID,
    ) -> tuple[RefinedPowerChainConfiguration, ...]:
        return self.get_configuration(project_id, park_id).chains

    def create_chain(
        self,
        project_id: UUID,
        park_id: UUID,
        configuration: RefinedPowerChainConfiguration,
    ) -> RefinedPowerChainConfiguration:
        """Ajoute une chaîne après validation de sa configuration."""

        park = self.park_repository.get(project_id, park_id)
        installation = self._get_enabled_installation(park.mods.get(self.MOD_ID))
        current = self._parse_configuration(installation)

        if any(chain.chain_id == configuration.chain_id for chain in current.chains):
            raise ValueError("Une chaîne avec cet identifiant existe déjà.")
        if any(chain.name.casefold() == configuration.name.casefold() for chain in current.chains):
            raise ValueError(f"Une chaîne nommée '{configuration.name}' existe déjà dans ce parc.")

        updated = RefinedPowerParkConfiguration(
            chains=(*current.chains, configuration),
        )
        self._save_configuration(project_id, park_id, updated)
        return configuration

    def update_chain(
        self,
        project_id: UUID,
        park_id: UUID,
        chain_id: UUID,
        configuration: RefinedPowerChainConfiguration,
    ) -> RefinedPowerChainConfiguration:
        """Remplace une chaîne existante sans changer son identifiant."""

        if configuration.chain_id != chain_id:
            raise ValueError("L'identifiant de la chaîne ne peut pas être modifié.")

        park = self.park_repository.get(project_id, park_id)
        installation = self._get_enabled_installation(park.mods.get(self.MOD_ID))
        current = self._parse_configuration(installation)
        if not any(chain.chain_id == chain_id for chain in current.chains):
            raise FileNotFoundError(f"Chaîne Refined Power introuvable : {chain_id}.")
        if any(
            chain.chain_id != chain_id
            and chain.name.casefold() == configuration.name.casefold()
            for chain in current.chains
        ):
            raise ValueError(f"Une chaîne nommée '{configuration.name}' existe déjà dans ce parc.")

        updated = RefinedPowerParkConfiguration(
            chains=tuple(
                configuration if chain.chain_id == chain_id else chain
                for chain in current.chains
            ),
        )
        self._save_configuration(project_id, park_id, updated)
        return configuration

    def delete_chain(
        self,
        project_id: UUID,
        park_id: UUID,
        chain_id: UUID,
    ) -> None:
        """Supprime une chaîne sans toucher aux autres données du parc."""

        park = self.park_repository.get(project_id, park_id)
        installation = self._get_enabled_installation(park.mods.get(self.MOD_ID))
        current = self._parse_configuration(installation)
        remaining = tuple(chain for chain in current.chains if chain.chain_id != chain_id)
        if len(remaining) == len(current.chains):
            raise FileNotFoundError(f"Chaîne Refined Power introuvable : {chain_id}.")

        updated = RefinedPowerParkConfiguration(chains=remaining)
        self._save_configuration(project_id, park_id, updated)

    def calculate_chain(
        self,
        project_id: UUID,
        park_id: UUID,
        chain_id: UUID,
    ) -> RefinedPowerChainResult:
        """Calcule une chaîne enregistrée dans le parc."""

        park = self.park_repository.get(project_id, park_id)
        installation = park.mods.get(self.MOD_ID)
        if installation is None or not installation.enabled:
            raise ValueError("Refined Power doit être activé sur ce parc pour lancer le calcul.")
        configuration = self._parse_configuration(installation)
        chain = next(
            (item for item in configuration.chains if item.chain_id == chain_id),
            None,
        )
        if chain is None:
            raise FileNotFoundError(f"Chaîne Refined Power introuvable : {chain_id}.")
        return self.engine.calculate(chain, self.get_catalog())

    def _save_configuration(
        self,
        project_id: UUID,
        park_id: UUID,
        configuration: RefinedPowerParkConfiguration,
    ) -> None:
        park = self.park_repository.get(project_id, park_id)
        current_installation = park.mods.get(self.MOD_ID)
        self._get_enabled_installation(current_installation)
        versioned_configuration = configuration.model_copy(
            update={"catalog_version": self.get_catalog().mod_version},
            deep=True,
        )
        park.mods[self.MOD_ID] = current_installation.model_copy(
            update={"configuration": versioned_configuration.model_dump(mode="json")},
            deep=True,
        )
        self.park_repository.update(park)

    @staticmethod
    def _get_enabled_installation(
        installation: ParkModInstallation | None,
    ) -> ParkModInstallation:
        if installation is None or not installation.enabled:
            raise ValueError("Refined Power doit être activé sur ce parc.")
        return installation.model_copy(deep=True)

    @staticmethod
    def _parse_configuration(
        installation: ParkModInstallation,
    ) -> RefinedPowerParkConfiguration:
        if not installation.configuration:
            return RefinedPowerParkConfiguration()
        return RefinedPowerParkConfiguration.model_validate(
            installation.configuration
        )
