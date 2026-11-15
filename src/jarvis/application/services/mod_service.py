"""Catalogue des modules pris en charge et activation par parc."""

from typing import Any
from uuid import UUID

from jarvis.domain.entities.mod import ModDefinition, ParkModInstallation
from jarvis.domain.entities.park import Park
from jarvis.infrastructure.persistence.park_repository import ParkRepository

MOD_DEFINITIONS: tuple[ModDefinition, ...] = (
    ModDefinition(
        mod_id="refined_power",
        name="Refined Power",
        category="Énergie",
        summary=(
            "Modélisation de filières énergétiques complémentaires et de chaînes "
            "thermodynamiques."
        ),
        description=(
            "Prépare la gestion des équipements Refined Power dans un parc : "
            "production de vapeur, conversion en rotation, production électrique "
            "et sources d'énergie directes."
        ),
        features=(
            "Chaudières : combustible + eau vers vapeur (m³/min).",
            "Turbines : vapeur vers vitesse de rotation (RPM).",
            "Alternateurs : RPM vers puissance électrique (MW).",
            "Sources directes : éoliennes, turbines hydrauliques et barrages.",
            "Réacteurs micro/modulaires et chaîne Project Icarus.",
            "Bilans de combustible, d'eau, de vapeur et de consommation auxiliaire.",
        ),
        integration_note=(
            "Le moteur de calcul Modular Power et la persistance des chaînes par parc "
            "sont disponibles dans le socle applicatif. L'écran de configuration, les "
            "sources directes, les réacteurs et Project Icarus restent à développer."
        ),
    ),
    ModDefinition(
        mod_id="digital_storage",
        name="Digital Storage",
        category="Stockage et logistique",
        summary=(
            "Infrastructure de stockage numérique et échanges de ressources "
            "entre usines."
        ),
        description=(
            "Prépare la configuration des baies, serveurs, disques, capacités, "
            "partitions et flux d'importation/exportation propres à ce parc."
        ),
        features=(
            "Baie de disques (Server Rack) : 22 unités de rack.",
            "Serveur 1U : 1 unité de rack et 4 disques ; serveur 2U : 2 unités et 12 disques.",
            "Serveur de Craft : 1 unité de rack pour l'automatisation du craft à la demande.",
            "Disques d'objets : 256 / 512 / 1K / 2K (4 partitions), puis 4K à 64K (8).",
            "Disques de fluides : 10 m³ (4 partitions), puis 20 à 240 m³ (8).",
            "Disques de gaz : 40 / 60 / 120 / 240 m³ (8 partitions).",
            "Capacité installée, partitions, bande passante et saturation du réseau.",
            "Flux d'importation et d'exportation entre les parcs et consommation électrique."
        ),
        integration_note=(
            "L'activation par parc est disponible. Les équipements, capacités et "
            "échanges Digital Storage seront intégrés dans les prochaines étapes."
        ),
    ),
)


class ModService:
    """Gère les modules disponibles et leur activation indépendante par parc."""

    def __init__(self, park_repository: ParkRepository | None = None):
        self.park_repository = park_repository or ParkRepository()
        self._definitions = {
            definition.mod_id: definition
            for definition in MOD_DEFINITIONS
        }

    def list_supported_mods(self) -> tuple[ModDefinition, ...]:
        """Retourne les modules connus de J.A.R.V.I.S."""

        return MOD_DEFINITIONS

    def list_parks(self, project_id: UUID) -> list[Park]:
        """Retourne les parcs du projet actif."""

        return self.park_repository.list_all(project_id)

    def get_mod_state(
        self,
        project_id: UUID,
        park_id: UUID,
        mod_id: str,
    ) -> ParkModInstallation:
        """Retourne l'état d'un module sans créer d'entrée implicite."""

        self._ensure_supported(mod_id)
        park = self.park_repository.get(project_id, park_id)
        state = park.mods.get(mod_id, ParkModInstallation())
        return state.model_copy(deep=True)

    def set_mod_enabled(
        self,
        project_id: UUID,
        park_id: UUID,
        mod_id: str,
        enabled: bool,
    ) -> Park:
        """Active ou désactive un module sans effacer sa configuration."""

        self._ensure_supported(mod_id)
        if not isinstance(enabled, bool):
            raise ValueError("L'état d'un module doit être un booléen.")

        park = self.park_repository.get(project_id, park_id)
        current = park.mods.get(mod_id, ParkModInstallation())
        park.mods[mod_id] = current.model_copy(
            update={"enabled": enabled},
            deep=True,
        )
        return self.park_repository.update(park)

    def update_mod_configuration(
        self,
        project_id: UUID,
        park_id: UUID,
        mod_id: str,
        configuration: dict[str, Any],
    ) -> Park:
        """Enregistre les paramètres d'un module pour un parc précis."""

        self._ensure_supported(mod_id)
        if not isinstance(configuration, dict):
            raise ValueError("La configuration du module doit être un objet JSON.")

        park = self.park_repository.get(project_id, park_id)
        current = park.mods.get(mod_id, ParkModInstallation())
        park.mods[mod_id] = current.model_copy(
            update={"configuration": dict(configuration)},
            deep=True,
        )
        return self.park_repository.update(park)

    def _ensure_supported(self, mod_id: str) -> None:
        if mod_id not in self._definitions:
            raise ValueError(f"Module non pris en charge : {mod_id}")
