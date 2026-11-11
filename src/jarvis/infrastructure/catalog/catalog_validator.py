"""Vérifications de cohérence d'un catalogue déjà importé."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jarvis.infrastructure.catalog.catalog_parser import (
    FORMAT_VERSION,
    CatalogParser,
)


@dataclass(frozen=True, slots=True)
class CatalogValidationResult:
    """Résultat d'un contrôle du catalogue local."""

    errors: tuple[str, ...]
    native_class_count: int
    class_count: int
    locale_count: int

    @property
    def is_valid(self) -> bool:
        return not self.errors


class CatalogValidator:
    """Contrôle les liens entre classes, groupes, langues et manifeste."""

    def __init__(self, catalog_dir: str | Path) -> None:
        self.catalog_dir = Path(catalog_dir)
        self.parser = CatalogParser()

    def validate(self) -> CatalogValidationResult:
        errors: list[str] = []
        core = self._read_object(self.catalog_dir / "core.json", errors)
        manifest = self._read_object(self.catalog_dir / "manifest.json", errors)
        if core is None or manifest is None:
            return CatalogValidationResult(tuple(errors), 0, 0, 0)

        if core.get("format_version") != FORMAT_VERSION:
            errors.append("Version de core.json non prise en charge.")
        if manifest.get("format_version") != FORMAT_VERSION:
            errors.append("Version de manifest.json non prise en charge.")

        classes = core.get("classes")
        native_classes = core.get("native_classes")
        if not isinstance(classes, dict):
            errors.append("core.json : le champ 'classes' doit être un objet.")
            classes = {}
        if not isinstance(native_classes, dict):
            errors.append("core.json : le champ 'native_classes' doit être un objet.")
            native_classes = {}

        declared_class_count = core.get("class_count")
        if declared_class_count != len(classes):
            errors.append(
                "core.json : class_count ne correspond pas au nombre de classes enregistrées."
            )
        if core.get("native_class_count") != len(native_classes):
            errors.append(
                "core.json : native_class_count ne correspond pas au nombre de groupes."
            )

        for class_name, record in classes.items():
            if not isinstance(record, dict):
                errors.append(f"Classe {class_name!r} : enregistrement invalide.")
                continue
            native_class_name = record.get("native_class")
            properties = record.get("properties")
            if native_class_name not in native_classes:
                errors.append(
                    f"Classe {class_name!r} : NativeClass {native_class_name!r} inconnu."
                )
            if not isinstance(properties, dict):
                errors.append(f"Classe {class_name!r} : propriétés techniques invalides.")

        for native_class_name, group in native_classes.items():
            if not isinstance(group, dict):
                errors.append(f"Groupe {native_class_name!r} : métadonnées invalides.")
                continue
            class_names = group.get("class_names")
            if not isinstance(class_names, list):
                errors.append(f"Groupe {native_class_name!r} : class_names invalide.")
                continue
            if group.get("class_count") != len(class_names):
                errors.append(
                    f"Groupe {native_class_name!r} : class_count incohérent."
                )
            for class_name in class_names:
                record = classes.get(class_name)
                if record is None:
                    errors.append(
                        f"Groupe {native_class_name!r} : classe {class_name!r} "
                        "absente de core.json."
                    )
                elif record.get("native_class") != native_class_name:
                    errors.append(
                        f"Classe {class_name!r} : groupe NativeClass incohérent."
                    )

        locale_manifest = manifest.get("locales")
        if not isinstance(locale_manifest, dict):
            errors.append("manifest.json : le champ 'locales' doit être un objet.")
            locale_manifest = {}

        locale_dir = self.catalog_dir / "locales"
        manifest_locales = set(locale_manifest)
        disk_locales = (
            {path.stem for path in locale_dir.glob("*.json")}
            if locale_dir.is_dir()
            else set()
        )
        for locale in sorted(manifest_locales - disk_locales):
            errors.append(f"Langue {locale!r} : fichier absent du dossier locales.")
        for locale in sorted(disk_locales - manifest_locales):
            errors.append(f"Langue {locale!r} : fichier non référencé dans manifest.json.")

        for locale, metadata in locale_manifest.items():
            locale_path = locale_dir / f"{locale}.json"
            locale_data = self._read_object(locale_path, errors)
            if locale_data is None:
                continue
            try:
                normalized_locale = self.parser.normalize_locale(locale)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if locale_data.get("locale") != normalized_locale:
                errors.append(f"Langue {locale!r} : code de langue interne incohérent.")
            if locale_data.get("format_version") != FORMAT_VERSION:
                errors.append(f"Langue {locale!r} : version de fichier non prise en charge.")
            if locale_data.get("class_count") != len(classes):
                errors.append(f"Langue {locale!r} : class_count ne correspond pas à core.json.")

            entries = locale_data.get("entries")
            if not isinstance(entries, dict):
                errors.append(f"Langue {locale!r} : le champ 'entries' doit être un objet.")
                continue

            placeholder_count = 0
            wrapped_count = 0
            for class_name, properties in entries.items():
                if class_name not in classes:
                    errors.append(
                        f"Langue {locale!r} : classe inconnue {class_name!r}."
                    )
                if not isinstance(properties, dict):
                    errors.append(
                        f"Langue {locale!r}, classe {class_name!r} : propriétés invalides."
                    )
                    continue
                for property_name, value in properties.items():
                    if not self.parser.is_localized_field(property_name):
                        errors.append(
                            f"Langue {locale!r}, classe {class_name!r} : "
                            f"champ non localisable {property_name!r}."
                        )
                    if self.parser.is_placeholder_value(value):
                        placeholder_count += 1
                    elif self.parser.is_wrapped_untranslated_value(value):
                        wrapped_count += 1

            if locale_data.get("placeholder_value_count", 0) != placeholder_count:
                errors.append(f"Langue {locale!r} : compteur de marqueurs #ID incohérent.")
            if locale_data.get("wrapped_untranslated_value_count", 0) != wrapped_count:
                errors.append(f"Langue {locale!r} : compteur de textes encadrés incohérent.")
            if not isinstance(metadata, dict):
                errors.append(f"Manifeste, langue {locale!r} : métadonnées invalides.")
            elif metadata.get("class_count") != len(classes):
                errors.append(
                    f"Manifeste, langue {locale!r} : class_count incohérent."
                )
            elif metadata.get("file") != f"locales/{locale}.json":
                errors.append(
                    f"Manifeste, langue {locale!r} : chemin de fichier incohérent."
                )

        return CatalogValidationResult(
            errors=tuple(errors),
            native_class_count=len(native_classes),
            class_count=len(classes),
            locale_count=len(locale_manifest),
        )

    @staticmethod
    def _read_object(path: Path, errors: list[str]) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            errors.append(f"Fichier requis introuvable : {path}.")
            return None
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Fichier JSON illisible ({path.name}) : {exc}.")
            return None
        if not isinstance(payload, dict):
            errors.append(f"Le fichier {path.name} doit contenir un objet JSON.")
            return None
        return payload
