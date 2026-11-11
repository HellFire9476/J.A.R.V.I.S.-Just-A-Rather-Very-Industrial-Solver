import json

from jarvis.application.services.catalog_service import CatalogService
from jarvis.infrastructure.catalog.satisfactory_importer import SatisfactoryImporter
from jarvis.infrastructure.persistence.catalog_repository import CatalogRepository


def make_source(path, display_name, description):
    payload = [
        {
            "NativeClass": "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptor'",
            "Classes": [
                {
                    "ClassName": "Desc_IronPlate_C",
                    "mDisplayName": display_name,
                    "mDescription": description,
                    "mStackSize": "SS_MEDIUM",
                }
            ]
        }
    ]
    path.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-16"))
    return path


def test_repository_resolves_requested_locale_then_fallbacks(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    catalog_dir = tmp_path / "Catalog"
    importer = SatisfactoryImporter(catalog_dir)
    importer.import_file(make_source(source_dir / "en-US.json", "Iron Plate", "Iron part"))
    importer.import_file(make_source(source_dir / "fr.json", "Plaque de fer", "Pièce en fer"))

    repository = CatalogRepository(catalog_dir)

    assert repository.get_display_name("Desc_IronPlate_C", "fr-FR") == "Plaque de fer"
    assert repository.get_description("Desc_IronPlate_C", "fr") == "Pièce en fer"
    assert repository.get_display_name("Desc_IronPlate_C", "de-DE") == "Iron Plate"
    assert repository.get_class("Desc_IronPlate_C")["properties"]["mStackSize"] == "SS_MEDIUM"
    assert repository.list_locales() == ["en-US", "fr"]
    assert repository.get_summary()["class_count"] == 1


def test_service_import_invalidates_repository_cache(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    catalog_dir = tmp_path / "Catalog"
    service = CatalogService(catalog_dir)
    source = make_source(source_dir / "fr.json", "Plaque de fer", "Pièce en fer")

    result = service.import_game_data(source)

    assert result.locale == "fr"
    assert service.get_display_name("Desc_IronPlate_C", "fr") == "Plaque de fer"


def test_repository_falls_back_for_untranslated_marker_values(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    catalog_dir = tmp_path / "Catalog"
    importer = SatisfactoryImporter(catalog_dir)

    importer.import_file(
        make_source(source_dir / "en-US.json", "Iron Plate", "Iron part")
    )
    importer.import_file(
        make_source(source_dir / "ie.json", "‹Iron Plate›", "‹Iron part›")
    )
    importer.import_file(
        make_source(source_dir / "io.json", "#02710", "#02711")
    )

    repository = CatalogRepository(catalog_dir)

    assert repository.get_display_name("Desc_IronPlate_C", "ie") == "Iron Plate"
    assert repository.get_display_name("Desc_IronPlate_C", "io") == "Iron Plate"


def test_catalog_validator_accepts_a_consistent_catalog(tmp_path):
    from jarvis.infrastructure.catalog.catalog_validator import CatalogValidator

    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    catalog_dir = tmp_path / "Catalog"
    importer = SatisfactoryImporter(catalog_dir)
    importer.import_file(make_source(source_dir / "fr.json", "Plaque de fer", "Pièce en fer"))
    importer.import_file(make_source(source_dir / "en-US.json", "Iron Plate", "Iron part"))

    result = CatalogValidator(catalog_dir).validate()

    assert result.is_valid is True
    assert result.class_count == 1
    assert result.locale_count == 2


def test_catalog_validator_detects_an_unknown_localized_class(tmp_path):
    from jarvis.infrastructure.catalog.catalog_validator import CatalogValidator

    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    catalog_dir = tmp_path / "Catalog"
    SatisfactoryImporter(catalog_dir).import_file(
        make_source(source_dir / "fr.json", "Plaque de fer", "Pièce en fer")
    )
    locale_path = catalog_dir / "locales" / "fr.json"
    locale_data = json.loads(locale_path.read_text(encoding="utf-8"))
    locale_data["entries"]["Unknown_Class_C"] = {"mDisplayName": "Inconnu"}
    locale_path.write_text(json.dumps(locale_data), encoding="utf-8")

    result = CatalogValidator(catalog_dir).validate()

    assert result.is_valid is False
    assert any("classe inconnue" in issue for issue in result.errors)
