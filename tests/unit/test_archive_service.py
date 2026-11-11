
from uuid import uuid4

from jarvis.application.services.archive_service import ArchiveService
from jarvis.infrastructure.persistence.archive_repository import (
    ArchiveRepository,
)


def create_service(tmp_path):
    return ArchiveService(
        ArchiveRepository(tmp_path / "Archives")
    )


def test_archive_directory_and_inspect_content(tmp_path):
    service = create_service(tmp_path)

    project_id = uuid4()
    source = tmp_path / "Projects" / str(project_id)
    source.mkdir(parents=True)

    (source / "project.json").write_text(
        '{"name": "Partie de test"}',
        encoding="utf-8",
    )

    record = service.archive_element(
        source_path=source,
        entity_type="project",
        entity_id=project_id,
        entity_name="Partie de test",
        original_location=f"Projects/{project_id}",
    )

    assert not source.exists()
    assert record.entity_name == "Partie de test"

    archives = service.get_archives("project")

    assert len(archives) == 1
    assert archives[0].archive_id == record.archive_id

    payload = service.get_archive_content(record.archive_id)

    assert (payload / "project.json").is_file()
    assert "Partie de test" in (
        payload / "project.json"
    ).read_text(encoding="utf-8")


def test_restore_archive(tmp_path):
    service = create_service(tmp_path)

    park_id = uuid4()
    project_id = uuid4()

    source = tmp_path / "Projects" / str(project_id) / "parks" / str(park_id)
    source.mkdir(parents=True)

    (source / "park.json").write_text(
        '{"name": "Parc minier"}',
        encoding="utf-8",
    )

    record = service.archive_element(
        source_path=source,
        entity_type="park",
        entity_id=park_id,
        entity_name="Parc minier",
        parent_project_id=project_id,
        original_location=f"Projects/{project_id}/parks/{park_id}",
    )

    destination = (
        tmp_path / "Projects" / str(project_id) / "parks" / str(park_id)
    )

    restored = service.restore_archive(
        record.archive_id,
        destination,
    )

    assert restored.entity_id == park_id
    assert destination.is_dir()
    assert (destination / "park.json").is_file()
    assert service.get_archives() == []


def test_archive_single_file(tmp_path):
    service = create_service(tmp_path)

    machine_id = uuid4()
    source = tmp_path / "machine.json"

    source.write_text(
        '{"clock_speed": 100}',
        encoding="utf-8",
    )

    record = service.archive_element(
        source_path=source,
        entity_type="machine",
        entity_id=machine_id,
        entity_name="Constructeur 01",
        original_location="Machines/machine.json",
    )

    assert not source.exists()

    payload = service.get_archive_content(record.archive_id)

    assert payload.is_file()
    assert '"clock_speed": 100' in payload.read_text(
        encoding="utf-8"
    )


def test_permanent_archive_deletion(tmp_path):
    service = create_service(tmp_path)

    park_id = uuid4()
    source = tmp_path / "park"
    source.mkdir()

    (source / "park.json").write_text(
        '{"name": "Ancien parc"}',
        encoding="utf-8",
    )

    record = service.archive_element(
        source_path=source,
        entity_type="park",
        entity_id=park_id,
        entity_name="Ancien parc",
        original_location="Projects/test/parks/park",
    )

    service.permanently_delete_archive(record.archive_id)

    assert service.get_archives() == []
