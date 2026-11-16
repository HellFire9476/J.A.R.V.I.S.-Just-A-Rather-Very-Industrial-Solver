import json

from jarvis.infrastructure.persistence import atomic_writer


def test_atomic_writer_uses_a_short_temporary_filename_prefix(tmp_path, monkeypatch):
    original_mkstemp = atomic_writer.tempfile.mkstemp
    observed_prefixes = []

    def recording_mkstemp(*args, **kwargs):
        observed_prefixes.append(kwargs.get("prefix"))
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(atomic_writer.tempfile, "mkstemp", recording_mkstemp)

    destination = tmp_path / "Projects" / "factory" / "scenarios.json"
    atomic_writer.write_json_atomic(destination, {"schema_version": 1, "scenarios": []})

    assert observed_prefixes == [".tmp-"]
    assert json.loads(destination.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "scenarios": [],
    }
