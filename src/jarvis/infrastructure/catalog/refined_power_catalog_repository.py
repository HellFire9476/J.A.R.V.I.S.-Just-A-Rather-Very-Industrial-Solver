"""Chargement et validation du catalogue local Refined Power."""

from pathlib import Path

from jarvis.config.paths import REFINED_POWER_CATALOG_FILE
from jarvis.domain.entities.refined_power import RefinedPowerCatalog
from jarvis.infrastructure.persistence.json_store import read_json


class RefinedPowerCatalogRepository:
    """Fournit un catalogue Refined Power versionné et local."""

    def __init__(self, catalog_file: Path = REFINED_POWER_CATALOG_FILE):
        self.catalog_file = Path(catalog_file)

    def get_catalog(self) -> RefinedPowerCatalog:
        if not self.catalog_file.is_file():
            raise FileNotFoundError(
                f"Catalogue Refined Power introuvable : {self.catalog_file}"
            )
        return read_json(self.catalog_file, RefinedPowerCatalog)
