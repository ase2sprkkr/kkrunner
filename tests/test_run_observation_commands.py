"""Observation and cancellation use a stored run, not guessed handle metadata."""

import io
from types import SimpleNamespace

from kkrunner.runs.manager import RunManager
from kkrunner.runs.base import RunState


def test_observation_dispatches_to_executor_without_attaching(monkeypatch):
    run = SimpleNamespace(
        id="run-1",
        state=RunState.RUNNING,
        execution=SimpleNamespace(backend_id="opaque"),
    )
    store = SimpleNamespace(get=lambda value: run)
    manager = RunManager(store)
    seen = []
    executor = SimpleNamespace(
        follow_output=lambda record, out, err, *, from_start: (
            seen.append((record, from_start)) or {"state": "running"}
        ),
        cancel_run=lambda record: seen.append(("cancel", record)) or {"state": "running"},
    )
    monkeypatch.setattr(manager, "executor_for", lambda record: executor)

    out, err = io.BytesIO(), io.BytesIO()
    assert manager.follow_output("run-1", out, err, from_start=True) == {"state": "running"}
    assert manager.cancel_run("run-1") == {"state": "running"}
    assert seen == [(run, True), ("cancel", run)]


def test_completed_run_replays_existing_local_stream_once(tmp_path):
    stream = tmp_path / "result.out"
    stream.write_bytes(b"finished\n")
    file_entry = SimpleNamespace(local_path=str(stream))
    record = SimpleNamespace(
        id="run-1", state=RunState.FINISHED, return_code=0, message=None,
        execution=SimpleNamespace(backend_id="old-handle"),
        files=SimpleNamespace(stdout=file_entry, stderr=file_entry),
    )
    manager = RunManager(SimpleNamespace(get=lambda value: record))
    out, err = io.BytesIO(), io.BytesIO()
    assert manager.follow_output(record.id, out, err, from_start=True)["state"] == "finished"
    assert out.getvalue() == b"finished\n"
    assert err.getvalue() == b""
