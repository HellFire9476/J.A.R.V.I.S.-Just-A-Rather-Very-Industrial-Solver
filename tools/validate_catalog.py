"""Vérifie la cohérence du catalogue Satisfactory local."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.config.paths import CATALOG_DIR  # noqa: E402
from jarvis.infrastructure.catalog.catalog_validator import (  # noqa: E402
    CatalogValidator,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valide core.json, manifest.json et les langues importées."
    )
    parser.add_argument(
        "--catalog-dir",
        type=Path,
        default=CATALOG_DIR,
        help=f"Dossier du catalogue (défaut : {CATALOG_DIR}).",
    )
    args = parser.parse_args()

    result = CatalogValidator(args.catalog_dir).validate()
    print(f"Catalogue : {args.catalog_dir}")
    print(f"Catégories NativeClass : {result.native_class_count}")
    print(f"Classes : {result.class_count}")
    print(f"Langues : {result.locale_count}")
    if result.is_valid:
        print("[OK] Aucun problème de cohérence détecté.")
        return 0

    print(f"[ERREUR] {len(result.errors)} problème(s) détecté(s) :")
    for issue in result.errors:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
