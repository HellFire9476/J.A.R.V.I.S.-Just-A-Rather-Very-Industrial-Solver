import json
from decimal import Decimal
from uuid import uuid4

import pytest

from jarvis.application.services.mod_service import ModService
from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.application.services.refined_power_service import RefinedPowerService
from jarvis.domain.entities.refined_power import RefinedPowerChainConfiguration
from jarvis.domain.entities.refined_power_optimization import (
    RefinedPowerOptimizationRequest,
)
from jarvis.infrastructure.persistence.catalog_repository import CatalogRepository
from jarvis.infrastructure.persistence.park_repository import ParkRepository
from jarvis.infrastructure.persistence.project_repository import ProjectRepository


@pytest.fixture
def environment(tmp_path):
    projects_dir = tmp_path / "Projects"
    project_repository = ProjectRepository(projects_dir)
    park_repository = ParkRepository(projects_dir)
    project = ProjectService(project_repository).create_project("RP Test")
    park_service = ParkService(park_repository, project_repository)
    park = park_service.create_park(project.id, "Parc énergie")
    mod_service = ModService(park_repository)
    refined_power_service = RefinedPowerService(park_repository)
    return project, park, mod_service, refined_power_service, park_repository, park_service


def sample_chain(name="Chaîne principale"):
    return RefinedPowerChainConfiguration(
        name=name,
        heater_id="coal",
        fuel_id="coal",
        boiler_id="mk1",
        boiler_count=1,
        turbine_id="mk1",
        turbine_count=1,
        generator_id="lv",
        generator_count=1,
        co2_chimney_count=1,
        steam_cooling_tower_count=1,
    )


def test_chains_require_refined_power_enabled(environment):
    project, park, _, service, _, _ = environment

    with pytest.raises(ValueError, match="doit être activé"):
        service.create_chain(project.id, park.id, sample_chain())


def test_create_calculate_and_reload_chain(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)

    chain = service.create_chain(project.id, park.id, sample_chain())
    reloaded = service.list_chains(project.id, park.id)
    persisted = service.get_configuration(project.id, park.id)
    result = service.calculate_chain(project.id, park.id, chain.chain_id)

    assert persisted.catalog_version == "2026.3.26"
    assert len(reloaded) == 1
    assert reloaded[0].chain_id == chain.chain_id
    assert result.estimated_power_mw == 150


def test_create_rejects_incompatible_configuration_without_persisting(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    invalid = sample_chain().model_copy(update={"heater_id": "biomass"})

    with pytest.raises(ValueError, match="n'est pas compatible"):
        service.create_chain(project.id, park.id, invalid)

    assert service.list_chains(project.id, park.id) == ()


def test_create_revalidates_models_copied_with_invalid_updates(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    invalid = sample_chain().model_copy(update={"boiler_count": 0})

    with pytest.raises(ValueError, match="boiler_count"):
        service.create_chain(project.id, park.id, invalid)

    assert service.list_chains(project.id, park.id) == ()


def test_update_rejects_incompatible_configuration_without_modifying_chain(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    original = service.create_chain(project.id, park.id, sample_chain())
    invalid = original.model_copy(update={"heater_id": "biomass"})

    with pytest.raises(ValueError, match="n'est pas compatible"):
        service.update_chain(project.id, park.id, original.chain_id, invalid)

    assert service.list_chains(project.id, park.id) == (original,)


def test_chains_are_scoped_to_the_selected_park(environment):
    project, park_a, mod_service, service, _, park_service = environment
    park_b = park_service.create_park(project.id, "Parc secondaire")
    mod_service.set_mod_enabled(project.id, park_a.id, "refined_power", True)
    mod_service.set_mod_enabled(project.id, park_b.id, "refined_power", True)

    service.create_chain(project.id, park_a.id, sample_chain())

    assert len(service.list_chains(project.id, park_a.id)) == 1
    assert service.list_chains(project.id, park_b.id) == ()


def test_deactivation_preserves_configuration_but_blocks_calculation(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    chain = service.create_chain(project.id, park.id, sample_chain())

    mod_service.set_mod_enabled(project.id, park.id, "refined_power", False)

    assert len(service.list_chains(project.id, park.id)) == 1
    with pytest.raises(ValueError, match="doit être activé"):
        service.calculate_chain(project.id, park.id, chain.chain_id)


def test_update_and_delete_chain(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    chain = service.create_chain(project.id, park.id, sample_chain())
    updated = chain.model_copy(update={"name": "Chaîne mise à jour"})

    service.update_chain(project.id, park.id, chain.chain_id, updated)
    assert service.list_chains(project.id, park.id)[0].name == "Chaîne mise à jour"

    service.delete_chain(project.id, park.id, chain.chain_id)
    assert service.list_chains(project.id, park.id) == ()


def test_update_rejects_changed_identifier(environment):
    project, park, mod_service, service, _, _ = environment
    mod_service.set_mod_enabled(project.id, park.id, "refined_power", True)
    chain = service.create_chain(project.id, park.id, sample_chain())
    changed = sample_chain().model_copy(update={"chain_id": uuid4()})

    with pytest.raises(ValueError, match="ne peut pas être modifié"):
        service.update_chain(project.id, park.id, chain.chain_id, changed)


def test_preview_configuration_calculates_without_persisting(environment):
    project, park, _, service, _, _ = environment

    result = service.preview_configuration(sample_chain())

    assert result.estimated_power_mw == 150
    assert service.list_chains(project.id, park.id) == ()


def test_preview_optimization_returns_proposal_without_persisting(environment):
    project, park, _, service, _, _ = environment
    reference = sample_chain().model_copy(update={"boiler_count": 2})
    request = RefinedPowerOptimizationRequest(
        mode="balance_existing",
        reference_configuration=reference,
    )

    solution = service.preview_optimization(request)

    assert solution.feasible is True
    assert solution.configuration is not None
    assert solution.configuration.turbine_count == 2
    assert solution.calculation is not None
    assert solution.calculation.estimated_power_mw == Decimal("300")
    assert service.list_chains(project.id, park.id) == ()


def test_resource_names_follow_the_selected_game_catalog_locale(tmp_path):
    catalog_dir = tmp_path / "SatisfactoryCatalog"
    locales_dir = catalog_dir / "locales"
    locales_dir.mkdir(parents=True)
    (catalog_dir / "core.json").write_text(
        json.dumps({"classes": {}}),
        encoding="utf-8",
    )
    (locales_dir / "fr.json").write_text(
        json.dumps(
            {
                "entries": {
                    "Desc_Coal_C": {"mDisplayName": "Charbon"},
                    "Desc_NuclearWaste_C": {"mDisplayName": "Déchets d'uranium"},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (locales_dir / "en-US.json").write_text(
        json.dumps(
            {
                "entries": {
                    "Desc_Coal_C": {"mDisplayName": "Coal"},
                    "Desc_NuclearWaste_C": {"mDisplayName": "Uranium Waste"},
                }
            }
        ),
        encoding="utf-8",
    )

    service = RefinedPowerService(
        game_catalog_repository=CatalogRepository(catalog_dir),
    )
    coal = service.get_catalog().get_fuel("coal")
    nuclear_waste = service.get_catalog().get_fuel("nuclear_fuel_rod").byproducts[0]

    assert service.list_locales() == ["fr", "en-US"]
    assert service.get_profile_display_name(coal, "fr") == "Charbon"
    assert service.get_profile_display_name(coal, "en-US") == "Coal"
    assert service.get_profile_display_name(nuclear_waste, "fr") == "Déchets d'uranium"
    assert service.get_localized_catalog("fr").get_fuel("coal").display_name == "Charbon"
    assert (
        service.get_localized_catalog("fr").get_fuel("nuclear_fuel_rod").byproducts[0].display_name
        == "Déchets d'uranium"
    )



def test_resource_names_resolve_regional_locale_when_base_locale_is_selected(tmp_path):
    catalog_dir = tmp_path / "RegionalCatalog"
    locales_dir = catalog_dir / "locales"
    locales_dir.mkdir(parents=True)
    (catalog_dir / "core.json").write_text(
        json.dumps({"classes": {}}),
        encoding="utf-8",
    )
    (locales_dir / "fr-FR.json").write_text(
        json.dumps(
            {"entries": {"Desc_Coal_C": {"mDisplayName": "Charbon FR"}}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    service = RefinedPowerService(
        game_catalog_repository=CatalogRepository(catalog_dir),
    )
    coal = service.get_catalog().get_fuel("coal")

    assert service.list_locales() == ["fr-FR", "en-US"]
    assert service.get_profile_display_name(coal, "fr") == "Charbon FR"
    assert service.get_profile_display_name(coal, "fr-FR") == "Charbon FR"

def test_refined_power_equipment_uses_embedded_translation_and_english_fallback(environment):
    _, _, _, service, _, _ = environment
    boiler = service.get_catalog().get_boiler("mk1")

    assert service.get_profile_display_name(boiler, "fr") == "Chaudière Mk.1"
    assert service.get_profile_display_name(boiler, "en-US") == "Boiler Mk.1"


def test_preview_configuration_uses_localized_byproduct_names(tmp_path):
    catalog_dir = tmp_path / "GameCatalog"
    locales_dir = catalog_dir / "locales"
    locales_dir.mkdir(parents=True)
    (catalog_dir / "core.json").write_text(
        json.dumps({"classes": {}}),
        encoding="utf-8",
    )
    (locales_dir / "fr.json").write_text(
        json.dumps(
            {"entries": {"Desc_NuclearWaste_C": {"mDisplayName": "Déchets d'uranium"}}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = RefinedPowerService(game_catalog_repository=CatalogRepository(catalog_dir))
    configuration = RefinedPowerChainConfiguration(
        name="Centrale nucléaire",
        heater_id="nuclear",
        fuel_id="nuclear_fuel_rod",
        boiler_id="mk2",
        boiler_count=1,
        turbine_id="mk2",
        turbine_count=5,
        generator_id="hv",
        generator_count=5,
        co2_chimney_count=0,
        steam_cooling_tower_count=2,
    )

    result = service.preview_configuration(configuration, "fr")

    assert result.byproducts[0].display_name == "Déchets d'uranium"
