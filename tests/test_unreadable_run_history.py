"""A damaged historical record must not poison unrelated run history."""

import json

import pytest

from kkrunner import RunManager, RunStore
from kkrunner.runs import CorruptRunRecord


def _record(manager, tmp_path, run_id):
    record = manager.new_record(
        directory=tmp_path / run_id,
        run_id=run_id,
        metadata={"ase2sprkkr": {"task": "DOS"}},
    )
    manager.store.save(record)
    return record


def _obsolete_backend(store, record):
    path = store._path(record)
    data = json.loads(path.read_text())
    data["execution"]["backend"]["name"] = "process"
    path.write_text(json.dumps(data))
    return path


def test_history_can_report_and_skip_an_unsupported_backend(tmp_path):
    store = RunStore(tmp_path / "runs")
    manager = RunManager(store)
    good = _record(manager, tmp_path, "good")
    bad = _record(manager, tmp_path, "bad")
    path = _obsolete_backend(store, bad)
    original = path.read_bytes()

    with pytest.raises(CorruptRunRecord, match="Unsupported backend: 'process'"):
        store.runs()
    with pytest.raises(CorruptRunRecord, match="Unsupported backend: 'process'"):
        store.get("bad")

    errors = []
    assert store.runs(on_error=errors.append) == (good,)
    assert len(errors) == 1
    assert isinstance(errors[0], CorruptRunRecord)
    assert errors[0].path == path
    assert path.read_bytes() == original

    # Filtering and limits count only successfully decoded records.
    assert store.runs(active=True, limit=1, on_error=errors.append) == (good,)


def test_manager_refresh_skips_bad_history_only_when_explicitly_requested(tmp_path):
    store = RunStore(tmp_path / "runs")
    manager = RunManager(store)
    good = _record(manager, tmp_path, "good")
    bad = _record(manager, tmp_path, "bad")
    _obsolete_backend(store, bad)

    with pytest.raises(CorruptRunRecord):
        manager.refresh()

    errors = []
    manager.refresh(on_error=errors.append)
    assert store.get(good.id).id == good.id
    assert errors and all(isinstance(error, CorruptRunRecord) for error in errors)
