"""Services applicatifs pour l'import et la consultation du catalogue."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jarvis.config.paths import CATALOG_DIR
from jarvis.infrastructure.catalog.satisfactory_importer import (
    ImportResult,
    SatisfactoryImporter,
)
from jarvis.infrastructure.persistence.catalog_repository import CatalogRepository


class CatalogService:
    """Façade applicative entre les écrans et les composants du catalogue."""

    def __init__(
        self,
        catalog_dir: str | Path = CATALOG_DIR,
        *,
        repository: CatalogRepository | None = None,
        importer: SatisfactoryImporter | None = None,
    ) -> None:
        self.catalog_dir = Path(catalog_dir)
        self.repository = repository or CatalogRepository(self.catalog_dir)
        self.importer = importer or SatisfactoryImporter(self.catalog_dir)

    def import_game_data(
        self,
        source: str | Path,
        *,
        locale: str | None = None,
        overwrite_locale: bool = True,
    ) -> ImportResult:
        """Importe un export local et invalide le cache de lecture."""

        result = self.importer.import_file(
            source,
            locale=locale,
            overwrite_locale=overwrite_locale,
        )
        self.repository = CatalogRepository(self.catalog_dir)
        return result

    def get_summary(self) -> dict[str, int | list[str]]:
        return self.repository.get_summary()

    def get_class(self, class_name: str) -> dict[str, Any] | None:
        return self.repository.get_class(class_name)

    def list_classes(self, native_class: str | None = None) -> list[str]:
        return self.repository.list_classes(native_class)

    def get_display_name(self, class_name: str, locale: str) -> str:
        return self.repository.get_display_name(class_name, locale)

    def get_description(self, class_name: str, locale: str) -> str:
        return self.repository.get_description(class_name, locale)
