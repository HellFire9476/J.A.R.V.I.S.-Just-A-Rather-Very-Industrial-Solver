import json

import pytest

from jarvis.infrastructure.catalog.catalog_parser import (
    CatalogFormatError,
    CatalogParser,
)


def sample_payload(display_name="Iron Plate", iron_cost="3.000000"):
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
            ],
        },
        {
            "NativeClass": "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptor'",
            "Classes": [
                {
                    "ClassName": "Desc_IronPlate_C",
                    "mDisplayName": "Iron Plate",
                    "mStackSize": "SS_MEDIUM",
                }
            ],
        },
    ]


def test_parser_splits_technical_and_localized_properties():
    parsed = CatalogParser().parse_payload(sample_payload())

    assert parsed.native_class_count == 2
    assert parsed.class_count == 2
    assert parsed.core["classes"]["Recipe_IronPlate_C"]["native_class"] == "FGRecipe"
    assert parsed.core["classes"]["Recipe_IronPlate_C"]["properties"][
        "mIngredients"
    ].endswith("Amount=3.000000))")
    assert parsed.localized["Recipe_IronPlate_C"]["mDisplayName"] == "Iron Plate"
    assert "mDisplayName" not in parsed.core["classes"]["Recipe_IronPlate_C"][
        "properties"
    ]


def test_parser_detects_utf16_and_utf8_encodings(tmp_path):
    payload = sample_payload(display_name="Plaque de fer")
    utf16_file = tmp_path / "fr.json"
    utf16_file.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-16"))
    utf8_file = tmp_path / "io.json"
    utf8_file.write_text(json.dumps(payload), encoding="utf-8-sig")

    parser = CatalogParser()
    assert parser.parse_file(utf16_file).encoding == "utf-16-le"
    assert parser.parse_file(utf8_file).encoding == "utf-8-sig"


def test_parser_rejects_duplicate_class_names():
    payload = sample_payload()
    payload[1]["Classes"][0]["ClassName"] = "Recipe_IronPlate_C"

    with pytest.raises(CatalogFormatError, match="ClassName dupliqué"):
        CatalogParser().parse_payload(payload)


def test_parser_rejects_duplicate_native_class_groups():
    payload = sample_payload()
    payload[1]["NativeClass"] = payload[0]["NativeClass"]

    with pytest.raises(CatalogFormatError, match="présente plusieurs fois"):
        CatalogParser().parse_payload(payload)


def test_parser_rejects_malformed_root():
    with pytest.raises(CatalogFormatError, match="racine JSON"):
        CatalogParser().parse_payload({"NativeClass": "FGRecipe"})


def test_locale_normalization_and_filename_suffix():
    parser = CatalogParser()

    assert parser.normalize_locale("EN_us") == "en-US"
    assert parser.normalize_locale("sr-cyRL") == "sr-Cyrl"
    assert parser.infer_locale("fr(6).json") == "fr"

    with pytest.raises(CatalogFormatError, match="Code de langue invalide"):
        parser.normalize_locale("../fr")


def test_parser_detects_untranslated_locale_markers():
    payload = sample_payload(display_name="#02710")
    payload[0]["Classes"][0]["mPromptText"] = "‹Iron Plate›"

    parsed = CatalogParser().parse_payload(payload)

    assert parsed.placeholder_value_count == 1
    assert parsed.wrapped_untranslated_value_count == 1
    assert "mPromptText" in parsed.localized["Recipe_IronPlate_C"]
