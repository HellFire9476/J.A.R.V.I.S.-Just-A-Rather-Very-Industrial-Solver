"""Compatibilité du modèle de parc avec les paramètres des modules."""

from uuid import uuid4

from jarvis.domain.entities.park import Park


def test_legacy_park_schema_is_migrated_without_enabling_mods():
    legacy_payload = {
        "schema_version": 1,
        "id": str(uuid4()),
        "project_id": str(uuid4()),
        "name": "Parc historique",
        "description": "Ancienne sauvegarde",
        "location": None,
    }

    park = Park.model_validate(legacy_payload)

    assert park.schema_version == 2
    assert park.mods == {}


def test_park_mod_installation_defaults_to_disabled():
    park = Park(
        project_id=uuid4(),
        name="Parc neuf",
    )

    assert park.mods == {}
    assert park.model_dump(mode="json")["mods"] == {}
