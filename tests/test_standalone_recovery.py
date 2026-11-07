"""Behavioral contracts introduced by the extraction, without application imports."""

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread

import pytest

from kkrunner import (
    CorruptRunRecord,
    ExecutionOutcome,
    ExecutionSpec,
    FileEntry,
    FileManifest,
    LocalExecutor,
    RunState,
    RunStore,
)
from kkrunner.manager import ExecutionManager
from kkrunner.postprocessing import ProcessingPending


def pending(manager, directory):
    output = directory / "stdout.txt"
    output.write_text("answer")
    record = manager.new_record(
        directory=directory,
        processing_required=True,
        files=FileManifest(stdout=FileEntry(local_path=str(output))),
        metadata={"example": {"label": "answer", "tags": ["one"]}},
    )
    return manager.complete(
        record,
        state=RunState.POSTPROCESSING,
        return_code=0,
        execution=record.execution.submitted("test-backend"),
        artifacts_available=True,
    )


def test_opaque_metadata_is_json_and_recursively_immutable(tmp_path):
    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    record = pending(manager, tmp_path)
    with pytest.raises(TypeError):
        record.metadata["example"]["label"] = "changed"
    with pytest.raises(ValueError, match="identity or metadata"):
        manager.store.update(record, lambda current: replace(current, metadata={"other": {}}))
    assert manager.store.get(record.id) == record
    with pytest.raises(ValueError, match="Backend identity"):
        manager.store.update(
            record, lambda current: replace(current, execution=replace(current.execution, backend_id="different"))
        )
    with pytest.raises(TypeError):
        manager.new_record(directory=tmp_path, metadata={"example": object()})
    with pytest.raises(ValueError):
        manager.new_record(directory=tmp_path, metadata={"example": float("nan")})


def test_corrupt_record_is_not_hidden_during_enumeration(tmp_path):
    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    record = pending(manager, tmp_path)
    path = manager.store._path(record)
    data = json.loads(path.read_text())
    data["schema_version"] = 99
    path.write_text(json.dumps(data))
    with pytest.raises(CorruptRunRecord):
        manager.store.runs()


def test_processing_claim_excludes_other_clients(tmp_path):
    store = RunStore(tmp_path / "runs")
    manager = ExecutionManager(store)
    record = pending(manager, tmp_path)
    entered, release = Event(), Event()
    results = []

    def callback(outcome):
        entered.set()
        assert release.wait(5)
        return 42

    thread = Thread(target=lambda: results.append(manager.retry_postprocessing(record.id, callback)))
    thread.start()
    assert entered.wait(5)
    try:
        other = ExecutionManager(RunStore(store.directory))
        with pytest.raises(ProcessingPending):
            other.retry_postprocessing(record.id, lambda outcome: pytest.fail("duplicate callback"))
    finally:
        release.set()
        thread.join(5)
    assert results == [42]
    assert store.get(record.id).state == RunState.FINISHED


def test_process_death_releases_processing_claim(tmp_path):
    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    record = pending(manager, tmp_path)
    script = """
import os, sys
from kkrunner.manager import ExecutionManager, RunStore
manager = ExecutionManager(RunStore(sys.argv[1]))
manager.retry_postprocessing(sys.argv[2], lambda outcome: os._exit(17))
"""
    child = subprocess.run([sys.executable, "-c", script, str(manager.store.directory), record.id], timeout=15)
    assert child.returncode == 17
    interrupted = manager.store.get(record.id)
    assert interrupted.state == RunState.POSTPROCESSING
    attempt = interrupted.processing_attempt
    assert manager.retry_postprocessing(record.id, lambda outcome: Path(outcome.output_file).read_text()) == "answer"
    completed = manager.store.get(record.id)
    assert completed.state == RunState.FINISHED
    assert completed.processing_attempt != attempt


def test_modified_artifacts_are_not_reprocessed(tmp_path):
    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    record = pending(manager, tmp_path)
    Path(record.files.output_file).write_text("different")
    with pytest.raises(ValueError, match="unchanged historical artifacts"):
        manager.retry_postprocessing(record.id, lambda outcome: pytest.fail("unverified callback"))
    assert manager.store.get(record.id).state == RunState.POSTPROCESSING


def test_managed_execution_needs_no_result_processor(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    run = manager.create_run(
        LocalExecutor(),
        ExecutionSpec([sys.executable, "-c", "print(42)"], directory=tmp_path, output_file=tmp_path / "stdout.txt"),
    )
    assert isinstance(run.run(), ExecutionOutcome)
    record = manager.store.get(run.id)
    assert record.state == RunState.FINISHED
    assert record.files.captured_at is not None


def test_required_processing_can_be_supplied_after_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    run = manager.create_run(
        LocalExecutor(),
        ExecutionSpec([sys.executable, "-c", "print(42)"], directory=tmp_path, output_file=tmp_path / "stdout.txt"),
        processing_required=True,
    )
    run.run()
    assert manager.store.get(run.id).state == RunState.POSTPROCESSING
    other = ExecutionManager(RunStore(manager.store.directory))
    attached = other.attach(run.id, process_result=lambda outcome: int(Path(outcome.output_file).read_text()))
    assert attached.wait() == 42
    assert other.store.get(run.id).state == RunState.FINISHED


def test_local_observation_detaches_without_stopping_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    run = manager.create_run(
        LocalExecutor(),
        ExecutionSpec(
            [sys.executable, "-c", "import time; time.sleep(.4); print(42)"],
            directory=tmp_path,
            output_file=tmp_path / "stdout.txt",
        ),
    )
    run.submit()
    identity = run.backend_id
    run.stop_observation()
    run.wait()
    assert manager.store.get(run.id).state == RunState.UNKNOWN
    other = ExecutionManager(RunStore(manager.store.directory))
    attached = other.attach(run.id)
    assert attached.wait().return_code == 0
    assert attached.backend_id == identity
    assert other.store.get(run.id).state == RunState.FINISHED


def test_refresh_captures_artifacts_without_result_processor(tmp_path):
    from kkrunner import RunStatus

    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    output = tmp_path / "stdout.txt"
    output.write_text("42")
    record = manager.new_record(directory=tmp_path, files=FileManifest(stdout=FileEntry(local_path=str(output))))
    manager.store.save(record)
    completed = manager.update(record, RunStatus(RunState.FINISHED, return_code=0))
    assert completed.state == RunState.FINISHED
    assert completed.files.captured_at is not None
    output.write_text("changed")
    assert not manager.output_file_is_current(completed)


@pytest.mark.parametrize(
    "field,value",
    [
        ("execution", "not an execution"),
        ("files", None),
        ("created_at", "yesterday"),
        ("id", "../another-record"),
        ("return_code", "0"),
        ("message", {}),
        ("processing_attempt", 17),
    ],
)
def test_current_schema_rejects_invalid_field_types(tmp_path, field, value):
    manager = ExecutionManager(RunStore(tmp_path / "runs"))
    record = pending(manager, tmp_path)
    path = manager.store._path(record)
    data = json.loads(path.read_text())
    assert data["schema_version"] == 1
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(CorruptRunRecord) as error:
        manager.store.get(record.id)
    assert str(path) in str(error.value)
