"""Importe un ou plusieurs exports JSON de Satisfactory dans le profil local."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.config.paths import CATALOG_DIR  # noqa: E402
from jarvis.infrastructure.catalog.satisfactory_importer import (  # noqa: E402
    SatisfactoryImporter,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Importe les exports NativeClass JSON de Satisfactory. "
            "Les fichiers d'origine ne sont jamais modifiés."
        )
    )
    parser.add_argument(
        "sources",
        nargs="*",
        type=Path,
        help="Un ou plusieurs fichiers JSON exportés depuis Satisfactory.",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        help="Importe tous les fichiers .json d'un dossier, dans l'ordre alphabétique.",
    )
    parser.add_argument(
        "--catalog-dir",
        type=Path,
        default=CATALOG_DIR,
        help=f"Dossier de destination (défaut : {CATALOG_DIR}).",
    )
    parser.add_argument(
        "--locale",
        help="Force le code de langue pour un seul fichier (ex. fr ou en-GB).",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Refuse de remplacer un fichier de langue déjà importé.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.locale and (args.directory or len(args.sources) != 1):
        print("--locale ne peut être utilisé qu'avec un seul fichier source.", file=sys.stderr)
        return 2

    if args.directory:
        if not args.directory.is_dir():
            print(f"Dossier introuvable : {args.directory}", file=sys.stderr)
            return 2
        sources = sorted(args.directory.glob("*.json"))
    else:
        sources = args.sources

    if not sources:
        print("Aucun fichier JSON à importer.", file=sys.stderr)
        return 2

    importer = SatisfactoryImporter(args.catalog_dir)
    failures = 0
    for source in sources:
        if not source.is_file():
            print(f"[ERREUR] Fichier introuvable : {source}", file=sys.stderr)
            failures += 1
            continue
        try:
            result = importer.import_file(
                source,
                locale=args.locale,
                overwrite_locale=not args.no_overwrite,
            )
        except (OSError, ValueError) as exc:
            failures += 1
            print(f"[ERREUR] {source.name} : {exc}", file=sys.stderr)
            continue
        print(
            f"[OK] {result.locale:8} | {result.class_count:5} classes | "
            f"{result.native_class_count:3} catégories | {result.encoding} | "
            f"{source.name}"
        )
        if result.placeholder_value_count or result.wrapped_untranslated_value_count:
            print(
                "     [AVERTISSEMENT] "
                f"{result.placeholder_value_count} marqueur(s) #ID et "
                f"{result.wrapped_untranslated_value_count} texte(s) encadré(s) "
                "détecté(s) ; ces valeurs utiliseront la langue de repli à l'affichage."
            )

    print(f"\nCatalogue : {args.catalog_dir}")
    print(f"Import(s) réussi(s) : {len(sources) - failures}/{len(sources)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
