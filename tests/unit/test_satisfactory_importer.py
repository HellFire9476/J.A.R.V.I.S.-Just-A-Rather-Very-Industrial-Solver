import json

import pytest

from jarvis.infrastructure.catalog.satisfactory_importer import (
    CatalogCompatibilityError,
    SatisfactoryImporter,
)


def export_payload(display_name="Iron Plate", iron_cost="3.000000"):
    return [
        {
            "NativeClass": "/Script/CoreUObject.Class'/Script/FactoryGame.FGRecipe'",
            "Classes": [
                {
                    "ClassName": "Recipe_IronPlate_C",
                    "mDisplayName": display_name,
                    "mDescription": "A basic iron part.",
                    "mIngredients": f"((ItemClass=IronIngot,Amount={iron_cost}))",
                    "mManufactoringDuration": "6.000000",
                }
            ]
        }
    ]


def write_export(path, payload, encoding="utf-16"):
    path.write_bytes(json.dumps(payload, ensure_ascii=False).encode(encoding))
    return path


def test_importer_creates_core_locale_and_manifest(tmp_path):
    source = write_export(tmp_path / "fr.json", export_payload("Plaque de fer"))
    output = tmp_path / "Catalog"

    result = SatisfactoryImporter(output).import_file(source)

    assert result.locale == "fr"
    assert result.core_created is True
    assert result.class_count == 1
    assert (output / "core.json").is_file()
    assert (output / "locales" / "fr.json").is_file()
    assert (output / "manifest.json").is_file()
    locale_data = json.loads((output / "locales" / "fr.json").read_text("utf-8"))
    assert locale_data["entries"]["Recipe_IronPlate_C"]["mDisplayName"] == "Plaque de fer"


def test_importer_accepts_another_locale_with_same_technical_data(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    output = tmp_path / "Catalog"
    write_export(source_dir / "fr.json", export_payload("Plaque de fer"))
    write_export(source_dir / "en-US.json", export_payload("Iron Plate"))
    importer = SatisfactoryImporter(output)

    first = importer.import_file(source_dir / "fr.json")
    second = importer.import_file(source_dir / "en-US.json")

    assert first.core_created is True
    assert second.core_created is False
    assert sorted(path.stem for path in (output / "locales").glob("*.json")) == [
        "en-US",
        "fr",
    ]


def test_importer_rejects_technical_differences_without_overwriting_core(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    output = tmp_path / "Catalog"
    write_export(source_dir / "fr.json", export_payload("Plaque de fer"))
    write_export(source_dir / "de.json", export_payload("Eisenplatte", "4.000000"))
    importer = SatisfactoryImporter(output)
    importer.import_file(source_dir / "fr.json")
    core_before = (output / "core.json").read_bytes()

    with pytest.raises(CatalogCompatibilityError, match="propriétés techniques"):
        importer.import_file(source_dir / "de.json")

    assert (output / "core.json").read_bytes() == core_before
    assert not (output / "locales" / "de.json").exists()


def test_importer_can_prevent_replacing_an_existing_locale(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    output = tmp_path / "Catalog"
    source = write_export(source_dir / "fr.json", export_payload("Plaque de fer"))
    importer = SatisfactoryImporter(output)
    importer.import_file(source)
    locale_before = (output / "locales" / "fr.json").read_bytes()
    write_export(source, export_payload("Plaque de fer modifiée"))

    with pytest.raises(FileExistsError):
        importer.import_file(source, overwrite_locale=False)

    assert (output / "locales" / "fr.json").read_bytes() == locale_before


def test_importer_can_use_explicit_locale_for_nonstandard_filename(tmp_path):
    source = write_export(tmp_path / "game-export.json", export_payload())

    result = SatisfactoryImporter(tmp_path / "Catalog").import_file(
        source,
        locale="en_gb",
    )

    assert result.locale == "en-GB"


def test_importer_records_untranslated_markers_and_preserves_source(tmp_path):
    payload = export_payload("#02710")
    payload[0]["Classes"][0]["mDescription"] = "‹Untranslated text›"
    source = write_export(tmp_path / "io.json", payload, encoding="utf-8-sig")
    source_before = source.read_bytes()

    result = SatisfactoryImporter(tmp_path / "Catalog").import_file(source)

    assert result.placeholder_value_count == 1
    assert result.wrapped_untranslated_value_count == 1
    assert source.read_bytes() == source_before
    locale_data = json.loads(
        (tmp_path / "Catalog" / "locales" / "io.json").read_text(encoding="utf-8")
    )
    assert locale_data["placeholder_value_count"] == 1
    assert locale_data["wrapped_untranslated_value_count"] == 1
