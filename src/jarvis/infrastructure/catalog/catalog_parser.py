"""Lecture et normalisation des exports JSON de classes natives Satisfactory.

Le format exporté par le jeu contient une liste de groupes ``NativeClass``.
Les propriétés restent volontairement intactes : ce module ne tente pas de
interpréter les structures Unreal encodées dans des chaînes de caractères.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1

# Champs dont les valeurs changent entre les exports de langues analysés.
# Les propriétés non listées sont conservées dans le catalogue technique.
LOCALIZED_FIELDS = frozenset(
    {
        "mDisplayName",
        "mDescription",
        "mAbbreviatedDisplayName",
        "mUnlockName",
        "mUnlockDescription",
        "mOccupiedText",
        "mScannerDisplayText",
        "mBuildDisqualifierText",
        "mMapText",
        "mPortalName",
        "mWorkBenchOccupied",
        "mWorkBenchFree",
        "mStorageText",
        "mMamFreeText",
        "mMamOccupiedText",
        "mRepresentationText",
        "mEquipmentLookAtDescOverride",
    }
)

_LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", re.IGNORECASE)


class CatalogFormatError(ValueError):
    """L'export ne correspond pas au format NativeClass attendu."""


@dataclass(frozen=True, slots=True)
class ParsedCatalog:
    """Représentation séparée des propriétés techniques et localisées."""

    encoding: str
    core: dict[str, Any]
    localized: dict[str, dict[str, Any]]
    localized_value_count: int
    placeholder_value_count: int
    wrapped_untranslated_value_count: int

    @property
    def native_class_count(self) -> int:
        return self.core["native_class_count"]

    @property
    def class_count(self) -> int:
        return self.core["class_count"]


class CatalogParser:
    """Décode et valide un export JSON Satisfactory."""

    def parse_file(self, source: str | Path) -> ParsedCatalog:
        """Parse un fichier en détectant son encodage à partir de ses octets."""

        path = Path(source)
        raw = path.read_bytes()
        text, encoding = self._decode(raw, path)
        try:
            payload = json.loads(text, object_pairs_hook=self._unique_object)
        except CatalogFormatError:
            raise
        except json.JSONDecodeError as exc:
            raise CatalogFormatError(
                f"JSON invalide dans {path.name}, ligne {exc.lineno}, "
                f"colonne {exc.colno} : {exc.msg}"
            ) from exc

        return self.parse_payload(payload, encoding=encoding)

    def parse_payload(
        self,
        payload: Any,
        *,
        encoding: str = "in-memory",
    ) -> ParsedCatalog:
        """Valide un objet JSON déjà chargé et construit les deux catalogues."""

        if not isinstance(payload, list):
            raise CatalogFormatError(
                "La racine JSON doit être une liste de groupes NativeClass."
            )
        if not payload:
            raise CatalogFormatError("L'export ne contient aucun groupe NativeClass.")

        native_classes: dict[str, dict[str, Any]] = {}
        technical_classes: dict[str, dict[str, Any]] = {}
        localized_classes: dict[str, dict[str, Any]] = {}
        localized_value_count = 0
        placeholder_value_count = 0
        wrapped_untranslated_value_count = 0
        seen_class_names: set[str] = set()

        for group_index, group in enumerate(payload):
            if not isinstance(group, dict):
                raise CatalogFormatError(
                    f"Le groupe NativeClass à l'index {group_index} n'est pas un objet."
                )

            native_class_path = group.get("NativeClass")
            classes = group.get("Classes")
            if not isinstance(native_class_path, str) or not native_class_path.strip():
                raise CatalogFormatError(
                    f"Le groupe à l'index {group_index} ne possède pas de NativeClass valide."
                )
            if not isinstance(classes, list):
                raise CatalogFormatError(
                    f"Le groupe {native_class_path!r} ne possède pas de liste Classes."
                )

            native_class_name = self._short_native_class_name(native_class_path)
            if native_class_name in native_classes:
                raise CatalogFormatError(
                    f"La catégorie NativeClass {native_class_name!r} est présente plusieurs fois."
                )

            class_names: list[str] = []
            for class_index, entry in enumerate(classes):
                if not isinstance(entry, dict):
                    raise CatalogFormatError(
                        f"Une entrée de {native_class_name} à l'index {class_index} "
                        "n'est pas un objet."
                    )

                class_name = entry.get("ClassName")
                if not isinstance(class_name, str) or not class_name.strip():
                    raise CatalogFormatError(
                        f"Une entrée de {native_class_name} ne possède pas de ClassName valide."
                    )
                if class_name in seen_class_names:
                    raise CatalogFormatError(
                        f"ClassName dupliqué dans l'export : {class_name!r}."
                    )
                seen_class_names.add(class_name)
                class_names.append(class_name)

                technical_properties: dict[str, Any] = {}
                localized_properties: dict[str, Any] = {}
                for property_name, value in entry.items():
                    if property_name == "ClassName":
                        continue
                    if not isinstance(property_name, str):
                        raise CatalogFormatError(
                            f"Nom de propriété invalide dans la classe {class_name!r}."
                        )
                    if self.is_localized_field(property_name):
                        localized_properties[property_name] = value
                        localized_value_count += 1
                        if self.is_placeholder_value(value):
                            placeholder_value_count += 1
                        elif self.is_wrapped_untranslated_value(value):
                            wrapped_untranslated_value_count += 1
                    else:
                        technical_properties[property_name] = value

                technical_classes[class_name] = {
                    "native_class": native_class_name,
                    "properties": technical_properties,
                }
                if localized_properties:
                    localized_classes[class_name] = localized_properties

            native_classes[native_class_name] = {
                "path": native_class_path,
                "class_names": class_names,
                "class_count": len(class_names),
            }

        core = {
            "format_version": FORMAT_VERSION,
            "source_format": "Satisfactory NativeClass JSON export",
            "native_class_count": len(native_classes),
            "class_count": len(technical_classes),
            "native_classes": native_classes,
            "classes": technical_classes,
        }

        return ParsedCatalog(
            encoding=encoding,
            core=core,
            localized=localized_classes,
            localized_value_count=localized_value_count,
            placeholder_value_count=placeholder_value_count,
            wrapped_untranslated_value_count=wrapped_untranslated_value_count,
        )

    @staticmethod
    def normalize_locale(locale: str) -> str:
        """Normalise un code BCP-47 simple et rejette les chemins dangereux."""

        value = locale.strip().replace("_", "-")
        if not _LOCALE_PATTERN.fullmatch(value):
            raise CatalogFormatError(f"Code de langue invalide : {locale!r}.")

        parts = value.split("-")
        normalized = [parts[0].lower()]
        for part in parts[1:]:
            if len(part) == 4 and part.isalpha():
                normalized.append(part.title())
            elif len(part) in (2, 3) and part.isalnum():
                normalized.append(part.upper())
            else:
                normalized.append(part)
        return "-".join(normalized)

    @classmethod
    def infer_locale(cls, source: str | Path) -> str:
        """Déduit la langue du nom de fichier (``fr(6).json`` devient ``fr``)."""

        stem = Path(source).stem
        stem = re.sub(r"\s*\(\d+\)$", "", stem)
        return cls.normalize_locale(stem)

    @staticmethod
    def is_localized_field(property_name: str) -> bool:
        """Repère les champs de texte connus et leurs futurs équivalents."""

        if property_name in LOCALIZED_FIELDS:
            return True
        if not property_name.startswith("m"):
            return False
        return (
            "DisplayName" in property_name
            or property_name.endswith("Description")
            or property_name.endswith("Text")
            or property_name.endswith("UnlockName")
            or property_name.endswith("PortalName")
        )

    @staticmethod
    def is_placeholder_value(value: Any) -> bool:
        """Détecte les marqueurs de traduction de type ``#02710``."""

        return isinstance(value, str) and re.fullmatch(r"#\d+", value.strip()) is not None

    @staticmethod
    def is_wrapped_untranslated_value(value: Any) -> bool:
        """Détecte les textes anglais de secours encadrés par ``‹...›``."""

        if not isinstance(value, str):
            return False
        stripped = value.strip()
        return len(stripped) >= 2 and stripped.startswith("‹") and stripped.endswith("›")

    @classmethod
    def is_usable_localized_value(cls, value: Any) -> bool:
        """Indique si une valeur localisée peut être affichée sans repli."""

        return (
            value is not None
            and value != ""
            and not cls.is_placeholder_value(value)
            and not cls.is_wrapped_untranslated_value(value)
        )

    @staticmethod
    def _short_native_class_name(native_class_path: str) -> str:
        value = native_class_path.strip().rstrip("'").rstrip('"')
        short_name = value.rsplit(".", 1)[-1].rsplit("/", 1)[-1]
        if not short_name:
            raise CatalogFormatError(
                f"Impossible de déterminer le nom de NativeClass : {native_class_path!r}."
            )
        return short_name

    @staticmethod
    def _decode(raw: bytes, path: Path) -> tuple[str, str]:
        if raw.startswith(b"\xff\xfe"):
            encoding = "utf-16-le"
            codec = "utf-16"
        elif raw.startswith(b"\xfe\xff"):
            encoding = "utf-16-be"
            codec = "utf-16"
        elif raw.startswith(b"\xef\xbb\xbf"):
            encoding = "utf-8-sig"
            codec = "utf-8-sig"
        elif len(raw) >= 4 and raw[1::2].count(0) > len(raw[1::2]) // 3:
            encoding = "utf-16-le"
            codec = "utf-16-le"
        elif len(raw) >= 4 and raw[::2].count(0) > len(raw[::2]) // 3:
            encoding = "utf-16-be"
            codec = "utf-16-be"
        else:
            encoding = "utf-8"
            codec = "utf-8"

        try:
            return raw.decode(codec), encoding
        except UnicodeDecodeError as exc:
            raise CatalogFormatError(
                f"Impossible de décoder {path.name} avec l'encodage détecté {encoding}."
            ) from exc

    @staticmethod
    def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CatalogFormatError(
                    f"Clé JSON dupliquée détectée : {key!r}."
                )
            result[key] = value
        return result
