"""Accès au catalogue Satisfactory enregistré localement en JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jarvis.config.paths import CATALOG_DIR
from jarvis.infrastructure.catalog.catalog_parser import (
    CatalogFormatError,
    CatalogParser,
)


class CatalogRepository:
    """Lit le catalogue technique et résout les textes par langue."""

    def __init__(self, catalog_dir: str | Path = CATALOG_DIR) -> None:
        self.catalog_dir = Path(catalog_dir)
        self.core_path = self.catalog_dir / "core.json"
        self.locales_dir = self.catalog_dir / "locales"
        self.parser = CatalogParser()
        self._core_cache: dict[str, Any] | None = None
        self._locale_cache: dict[str, dict[str, Any]] = {}

    @property
    def is_initialized(self) -> bool:
        return self.core_path.is_file()

    def get_summary(self) -> dict[str, int | list[str]]:
        core = self._load_core()
        return {
            "native_class_count": int(core.get("native_class_count", 0)),
            "class_count": int(core.get("class_count", 0)),
            "locales": self.list_locales(),
        }

    def list_locales(self) -> list[str]:
        if not self.locales_dir.is_dir():
            return []
        return sorted(path.stem for path in self.locales_dir.glob("*.json"))

    def get_class(self, class_name: str) -> dict[str, Any] | None:
        """Retourne les propriétés techniques d'une classe, sans texte localisé."""

        record = self._load_core().get("classes", {}).get(class_name)
        if record is None:
            return None
        return record

    def list_classes(self, native_class: str | None = None) -> list[str]:
        classes = self._load_core().get("classes", {})
        if native_class is None:
            return sorted(classes)
        return sorted(
            class_name
            for class_name, record in classes.items()
            if record.get("native_class") == native_class
        )

    def get_localized_properties(
        self,
        class_name: str,
        locale: str,
        *,
        fallback_locales: tuple[str, ...] = ("en-US", "fr"),
    ) -> dict[str, Any]:
        """Fusionne les champs localisés selon l'ordre de repli demandé."""

        candidates = self._locale_candidates(locale, fallback_locales)
        merged: dict[str, Any] = {}
        for candidate in reversed(candidates):
            locale_data = self._load_locale(candidate)
            properties = locale_data.get("entries", {}).get(class_name, {})
            for field_name, value in properties.items():
                if self.parser.is_usable_localized_value(value):
                    merged[field_name] = value
        return merged

    def get_localized_value(
        self,
        class_name: str,
        field_name: str,
        locale: str,
        *,
        fallback_locales: tuple[str, ...] = ("en-US", "fr"),
    ) -> Any | None:
        return self.get_localized_properties(
            class_name,
            locale,
            fallback_locales=fallback_locales,
        ).get(field_name)

    def get_display_name(self, class_name: str, locale: str) -> str:
        value = self.get_localized_value(class_name, "mDisplayName", locale)
        if isinstance(value, str) and value.strip():
            return value
        return class_name

    def get_description(self, class_name: str, locale: str) -> str:
        value = self.get_localized_value(class_name, "mDescription", locale)
        return value if isinstance(value, str) else ""

    def _load_core(self) -> dict[str, Any]:
        if self._core_cache is None:
            self._core_cache = self._read_object(self.core_path)
        return self._core_cache

    def _load_locale(self, locale: str) -> dict[str, Any]:
        if locale not in self._locale_cache:
            path = self.locales_dir / f"{locale}.json"
            if not path.is_file():
                self._locale_cache[locale] = {"entries": {}}
            else:
                self._locale_cache[locale] = self._read_object(path)
        return self._locale_cache[locale]

    def _locale_candidates(
        self,
        locale: str,
        fallback_locales: tuple[str, ...],
    ) -> list[str]:
        candidates: list[str] = []
        normalized = self.parser.normalize_locale(locale)
        candidates.append(normalized)
        language_only = normalized.split("-", 1)[0]
        if language_only != normalized:
            candidates.append(language_only)
        for fallback in fallback_locales:
            normalized_fallback = self.parser.normalize_locale(fallback)
            if normalized_fallback not in candidates:
                candidates.append(normalized_fallback)
        return candidates

    @staticmethod
    def _read_object(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Catalogue introuvable : {path}. Importez d'abord un export Satisfactory."
            ) from None
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogFormatError(
                f"Impossible de lire le fichier de catalogue {path}."
            ) from exc
        if not isinstance(payload, dict):
            raise CatalogFormatError(
                f"Le fichier {path.name} doit contenir un objet JSON."
            )
        return payload
