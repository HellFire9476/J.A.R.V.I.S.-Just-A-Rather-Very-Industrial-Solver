"""Orchestration du module Refined Power pour les parcs industriels."""

from uuid import UUID

from jarvis.domain.entities.mod import ParkModInstallation
from jarvis.domain.entities.refined_power import (
    RefinedPowerCatalog,
    RefinedPowerChainConfiguration,
    RefinedPowerParkConfiguration,
)
from jarvis.domain.entities.refined_power_optimization import (
    RefinedPowerOptimizationRequest,
    RefinedPowerOptimizationSolution,
)
from jarvis.engines.refined_power_engine import (
    RefinedPowerChainResult,
    RefinedPowerEngine,
)
from jarvis.engines.refined_power_optimizer import RefinedPowerOptimizer
from jarvis.infrastructure.catalog.refined_power_catalog_repository import (
    RefinedPowerCatalogRepository,
)
from jarvis.infrastructure.persistence.catalog_repository import CatalogRepository
from jarvis.infrastructure.persistence.park_repository import ParkRepository


class RefinedPowerService:
    """Gère les chaînes Refined Power et leurs calculs pour un parc précis."""

    MOD_ID = "refined_power"

    def __init__(
        self,
        park_repository: ParkRepository | None = None,
        catalog_repository: RefinedPowerCatalogRepository | None = None,
        engine: RefinedPowerEngine | None = None,
        optimizer: RefinedPowerOptimizer | None = None,
        game_catalog_repository: CatalogRepository | None = None,
    ):
        self.park_repository = park_repository or ParkRepository()
        self.catalog_repository = catalog_repository or RefinedPowerCatalogRepository()
        self.engine = engine or RefinedPowerEngine()
        self.optimizer = optimizer or RefinedPowerOptimizer(self.engine)
        self.game_catalog_repository = game_catalog_repository or CatalogRepository()

    def get_catalog(self) -> RefinedPowerCatalog:
        """Retourne le catalogue technique local et versionné."""

        return self.catalog_repository.get_catalog()

    def list_locales(self) -> list[str]:
        """Retourne les langues du catalogue Satisfactory installé.

        Le module conserve un repli français/anglais lorsque le catalogue de jeu
        n'a pas encore été importé, afin que ses propres libellés restent lisibles.
        """

        locales = (
            self.game_catalog_repository.list_locales()
            if self.game_catalog_repository.is_initialized
            else []
        )
        # N'ajoute une langue de secours que si aucune variante régionale de
        # cette langue n'est déjà importée (ex. fr-FR au lieu de fr).
        imported_languages = {item.casefold().split("-", 1)[0] for item in locales}
        for fallback in ("fr", "en-US"):
            language = fallback.casefold().split("-", 1)[0]
            if language not in imported_languages and fallback not in locales:
                locales.append(fallback)
        return sorted(
            locales,
            key=lambda item: (
                item.casefold().split("-", 1)[0] not in {"fr", "en"},
                {"fr": 0, "en": 1}.get(
                    item.casefold().split("-", 1)[0],
                    2,
                ),
                item.casefold(),
            ),
        )

    def get_profile_display_name(self, profile, locale: str) -> str:
        """Résout le nom d'un profil dans la langue demandée.

        Les ressources du jeu utilisent leur classe Satisfactory et le catalogue
        de langue importé. Les équipements propres à Refined Power utilisent les
        traductions embarquées dans le catalogue du mod.
        """

        game_class_name = getattr(profile, "game_class_name", None)
        if game_class_name and self.game_catalog_repository.is_initialized:
            for candidate in self._locale_candidates(locale):
                localized = self.game_catalog_repository.get_localized_value(
                    game_class_name,
                    "mDisplayName",
                    candidate,
                    fallback_locales=(),
                )
                if isinstance(localized, str) and localized.strip():
                    return localized

        localized_names = getattr(profile, "localized_names", {})
        locale_candidates = self._locale_candidates(
            locale,
            tuple(localized_names),
        )
        for candidate in dict.fromkeys(locale_candidates):
            value = localized_names.get(candidate)
            if isinstance(value, str) and value.strip():
                return value
        return profile.display_name

    def _locale_candidates(
        self,
        locale: str,
        available_locales: tuple[str, ...] | list[str] | None = None,
    ) -> tuple[str, ...]:
        """Retourne les variantes exactes puis régionales d'une langue."""

        available = list(available_locales or ())
        if not available and self.game_catalog_repository.is_initialized:
            available = self.game_catalog_repository.list_locales()
        candidates: list[str] = []

        def add(value: str) -> None:
            if value and value.casefold() not in {item.casefold() for item in candidates}:
                candidates.append(value)

        add(locale)
        language = locale.split("-", 1)[0]
        add(language)
        for candidate in available:
            if candidate.casefold().split("-", 1)[0] == language.casefold():
                add(candidate)
        # L'anglais est le repli universel des éléments du mod. Le français
        # n'est prioritaire que lorsqu'une langue française a été demandée.
        fallback_locales = ("fr", "en-US") if language.casefold() == "fr" else ("en-US",)
        for fallback in fallback_locales:
            add(fallback)
            fallback_language = fallback.split("-", 1)[0]
            for candidate in available:
                if candidate.casefold().split("-", 1)[0] == fallback_language.casefold():
                    add(candidate)
        return tuple(candidates)

    def get_localized_catalog(self, locale: str) -> RefinedPowerCatalog:
        """Construit une vue localisée du catalogue sans modifier ses données.

        Les moteurs reçoivent cette vue afin que leurs avertissements, raisons
        d'incompatibilité et sous-produits utilisent la même langue que l'écran.
        Les identifiants techniques et toutes les valeurs numériques restent
        strictement inchangés.
        """

        catalog = self.get_catalog()
        heaters = tuple(
            profile.model_copy(
                update={"display_name": self.get_profile_display_name(profile, locale)}
            )
            for profile in catalog.heaters
        )
        fuels = tuple(
            profile.model_copy(
                update={
                    "display_name": self.get_profile_display_name(profile, locale),
                    "byproducts": tuple(
                        product.model_copy(
                            update={
                                "display_name": self.get_profile_display_name(
                                    product,
                                    locale,
                                )
                            }
                        )
                        for product in profile.byproducts
                    ),
                }
            )
            for profile in catalog.fuels
        )
        boilers = tuple(
            profile.model_copy(
                update={"display_name": self.get_profile_display_name(profile, locale)}
            )
            for profile in catalog.boilers
        )
        turbines = tuple(
            profile.model_copy(
                update={"display_name": self.get_profile_display_name(profile, locale)}
            )
            for profile in catalog.turbines
        )
        generators = tuple(
            profile.model_copy(
                update={"display_name": self.get_profile_display_name(profile, locale)}
            )
            for profile in catalog.generators
        )
        return catalog.model_copy(
            update={
                "heaters": heaters,
                "fuels": fuels,
                "boilers": boilers,
                "turbines": turbines,
                "generators": generators,
            },
            deep=True,
        )

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

    def preview_configuration(
        self,
        configuration: RefinedPowerChainConfiguration,
        locale: str = "fr",
    ) -> RefinedPowerChainResult:
        """Calcule une configuration sans l'enregistrer dans un parc."""

        return self.engine.calculate(configuration, self.get_localized_catalog(locale))

    def preview_optimization(
        self,
        request: RefinedPowerOptimizationRequest,
        locale: str = "fr",
    ) -> RefinedPowerOptimizationSolution:
        """Propose un équilibrage sans modifier les chaînes enregistrées."""

        return self.optimizer.optimize(request, self.get_localized_catalog(locale))

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
        configuration = self._validate_chain_configuration(configuration)

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
        configuration = self._validate_chain_configuration(configuration)
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
        locale: str = "fr",
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
        return self.engine.calculate(chain, self.get_localized_catalog(locale))

    def _validate_chain_configuration(
        self,
        configuration: RefinedPowerChainConfiguration,
    ) -> RefinedPowerChainConfiguration:
        """Revalide et calcule la chaîne avant toute persistance.

        ``model_copy(update=...)`` peut contourner la validation Pydantic, même
        avec ``validate_assignment=True``. La frontière du service reconstruit
        donc toujours le modèle, puis demande au moteur de vérifier les profils,
        leurs références et leurs compatibilités physiques.
        """

        validated = RefinedPowerChainConfiguration.model_validate(
            configuration.model_dump(mode="python")
        )
        self.engine.calculate(validated, self.get_catalog())
        return validated

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
