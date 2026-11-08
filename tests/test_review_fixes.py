"""Regressions found during independent extraction review."""

import json
from threading import Event, Thread

import pytest

from kkrunner import CorruptRunRecord, ExecutionResources, ResourceOwnedRunner, RunState, RunStore
from kkrunner.runs.manager import RunManager


@pytest.mark.parametrize("data", [[], None, 42])
def test_non_object_json_root_raises_corrupt_record(tmp_path, data):
    manager = RunManager(RunStore(tmp_path / "runs"))
    record = manager.new_record(directory=tmp_path)
    manager.store.save(record)
    path = manager.store._path(record)
    path.write_text(json.dumps(data))

    with pytest.raises(CorruptRunRecord, match="must be a JSON object") as error:
        manager.store.get(record.id)
    assert error.value.path == path


def test_cancel_during_failed_submit_does_not_reenter_submission_lock():
    entered, release, finished, cancelled = Event(), Event(), Event(), Event()
    errors = []

    class Raw:
        state = RunState.NEW

        def submit(self):
            entered.set()
            assert release.wait(3)
            raise RuntimeError("submission rejected")

    resources = ExecutionResources()
    run = ResourceOwnedRunner(Raw(), resources)

    def submit():
        try:
            run.submit()
        except BaseException as exc:
            errors.append(exc)
        finally:
            finished.set()

    def cancel():
        run.cancel()
        cancelled.set()

    submitting = Thread(target=submit, daemon=True)
    cancelling = Thread(target=cancel, daemon=True)
    submitting.start()
    try:
        assert entered.wait(3)
        cancelling.start()
        assert run._cancel_requested.wait(3)
    finally:
        release.set()

    assert finished.wait(3), "failed submission deadlocked"
    assert cancelled.wait(3), "cancellation deadlocked"
    submitting.join(3)
    cancelling.join(3)
    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert str(errors[0]) == "submission rejected"
    assert resources.closed
    assert run.state == RunState.CANCELLED
