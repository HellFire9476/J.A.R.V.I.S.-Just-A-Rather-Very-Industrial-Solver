"""Import local et contrôlé des exports de données Satisfactory."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jarvis.infrastructure.catalog.catalog_parser import (
    FORMAT_VERSION,
    CatalogFormatError,
    CatalogParser,
)


class CatalogCompatibilityError(ValueError):
    """L'export importé ne correspond pas au catalogue technique existant."""


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Résumé vérifiable d'une opération d'import."""

    source_file: str
    locale: str
    encoding: str
    native_class_count: int
    class_count: int
    localized_value_count: int
    placeholder_value_count: int
    wrapped_untranslated_value_count: int
    core_created: bool
    locale_file: str


class SatisfactoryImporter:
    """Importe les exports dans un catalogue technique et des fichiers de langue."""

    def __init__(
        self,
        catalog_dir: str | Path,
        *,
        parser: CatalogParser | None = None,
    ) -> None:
        self.catalog_dir = Path(catalog_dir)
        self.locales_dir = self.catalog_dir / "locales"
        self.core_path = self.catalog_dir / "core.json"
        self.manifest_path = self.catalog_dir / "manifest.json"
        self.parser = parser or CatalogParser()

    def import_file(
        self,
        source: str | Path,
        *,
        locale: str | None = None,
        overwrite_locale: bool = True,
    ) -> ImportResult:
        """Valide puis importe un export sans jamais modifier le fichier source."""

        source_path = Path(source)
        parsed = self.parser.parse_file(source_path)
        locale_code = (
            self.parser.normalize_locale(locale)
            if locale
            else self.parser.infer_locale(source_path)
        )

        self.catalog_dir.mkdir(parents=True, exist_ok=True)
        self.locales_dir.mkdir(parents=True, exist_ok=True)

        locale_path = self.locales_dir / f"{locale_code}.json"
        if locale_path.exists() and not overwrite_locale:
            raise FileExistsError(
                f"La langue {locale_code} existe déjà dans le catalogue."
            )

        core_created = not self.core_path.exists()
        if core_created:
            self._atomic_write_json(self.core_path, parsed.core)
        else:
            existing_core = self._read_json(self.core_path)
            self._ensure_compatible(existing_core, parsed.core)

        locale_payload = {
            "format_version": FORMAT_VERSION,
            "locale": locale_code,
            "class_count": parsed.class_count,
            "localized_value_count": parsed.localized_value_count,
            "placeholder_value_count": parsed.placeholder_value_count,
            "wrapped_untranslated_value_count": parsed.wrapped_untranslated_value_count,
            "entries": parsed.localized,
        }
        self._atomic_write_json(locale_path, locale_payload)
        self._update_manifest(
            source_path=source_path,
            locale=locale_code,
            encoding=parsed.encoding,
            native_class_count=parsed.native_class_count,
            class_count=parsed.class_count,
            localized_value_count=parsed.localized_value_count,
            placeholder_value_count=parsed.placeholder_value_count,
            wrapped_untranslated_value_count=parsed.wrapped_untranslated_value_count,
        )

        return ImportResult(
            source_file=source_path.name,
            locale=locale_code,
            encoding=parsed.encoding,
            native_class_count=parsed.native_class_count,
            class_count=parsed.class_count,
            localized_value_count=parsed.localized_value_count,
            placeholder_value_count=parsed.placeholder_value_count,
            wrapped_untranslated_value_count=parsed.wrapped_untranslated_value_count,
            core_created=core_created,
            locale_file=str(locale_path),
        )

    def _update_manifest(
        self,
        *,
        source_path: Path,
        locale: str,
        encoding: str,
        native_class_count: int,
        class_count: int,
        localized_value_count: int,
        placeholder_value_count: int,
        wrapped_untranslated_value_count: int,
    ) -> None:
        if self.manifest_path.exists():
            manifest = self._read_json(self.manifest_path)
        else:
            manifest = {
                "format_version": FORMAT_VERSION,
                "created_at": datetime.now(UTC).isoformat(),
                "locales": {},
            }

        manifest.setdefault("locales", {})[locale] = {
            "file": f"locales/{locale}.json",
            "source_file": source_path.name,
            "encoding": encoding,
            "native_class_count": native_class_count,
            "class_count": class_count,
            "localized_value_count": localized_value_count,
            "placeholder_value_count": placeholder_value_count,
            "wrapped_untranslated_value_count": wrapped_untranslated_value_count,
            "imported_at": datetime.now(UTC).isoformat(),
        }
        self._atomic_write_json(self.manifest_path, manifest)

    @staticmethod
    def _ensure_compatible(
        existing_core: dict[str, Any],
        incoming_core: dict[str, Any],
    ) -> None:
        if existing_core.get("format_version") != FORMAT_VERSION:
            raise CatalogCompatibilityError(
                "La version du catalogue technique existant n'est pas compatible."
            )
        if existing_core.get("classes") != incoming_core.get("classes"):
            raise CatalogCompatibilityError(
                "Les propriétés techniques ou les identifiants de classes diffèrent "
                "du catalogue déjà installé. Aucun fichier existant n'a été remplacé."
            )
        if existing_core.get("native_classes") != incoming_core.get("native_classes"):
            raise CatalogCompatibilityError(
                "Les catégories NativeClass diffèrent du catalogue déjà installé. "
                "Aucun fichier existant n'a été remplacé."
            )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogFormatError(
                f"Impossible de lire le fichier de catalogue {path}."
            ) from exc
        if not isinstance(payload, dict):
            raise CatalogFormatError(
                f"Le fichier de catalogue {path.name} doit contenir un objet JSON."
            )
        return payload

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
