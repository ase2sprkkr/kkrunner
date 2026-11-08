"""PersistentRunner state observation and exactly-once finalization."""

from types import SimpleNamespace

from kkrunner.runs.base import RunState
from kkrunner.runs.manager import PersistentRunner


class _Manager:
    def __init__(self):
        self.completions = 0
        self.transitions = 0
        self.record = None
        self.store = SimpleNamespace(get=lambda run_id: self.record)
        self.acknowledgements = 0

    def complete(self, record, **kwargs):
        self.completions += 1
        self.record = SimpleNamespace(**{**vars(record), "state": kwargs["state"]})
        self._acknowledge_result(self.record)
        return self.record

    def _acknowledge_result(self, record):
        self.acknowledgements += 1

    def transition(self, record, **kwargs):
        self.transitions += 1
        return record


class _Runner:
    state = RunState.RUNNING
    backend_id = "backend-id"
    result = SimpleNamespace(return_code=0)
    exception = None
    failure_phase = None
    failure_message = None
    return_code = 0
    files = None
    execution = None

    def wait(self):
        self.state = RunState.FINISHED
        return self.result


class _Executor:
    def __init__(self):
        self.acknowledgements = 0

    def acknowledge(self, record):
        self.acknowledgements += 1


def test_reading_state_does_not_write_to_store():
    manager, raw, executor = (_Manager(), _Runner(), _Executor())
    record = SimpleNamespace(
        id="run",
        state=RunState.RUNNING,
        updated_at="2026-10-20T10:00:00+00:00",
        execution=SimpleNamespace(submitted=lambda x: x),
        processing_required=False,
    )
    manager.record = record
    run = PersistentRunner(manager, executor, raw, record)
    assert run.state == RunState.RUNNING
    assert manager.transitions == 0


def test_finalization_is_once_even_if_wait_and_callback_both_request_it():
    manager, raw, executor = (_Manager(), _Runner(), _Executor())
    record = SimpleNamespace(
        id="run",
        state=RunState.RUNNING,
        updated_at="2026-10-20T10:00:00+00:00",
        execution=SimpleNamespace(submitted=lambda x: x),
        processing_required=False,
    )
    manager.record = record
    run = PersistentRunner(manager, executor, raw, record)
    raw.state = RunState.FINISHED
    run._sync_completion(raw.result)
    run._sync_completion(raw.result)
    run.wait()
    assert manager.completions == 1
    assert manager.acknowledgements == 1


def test_unknown_observation_is_written_once_but_not_finalized():
    manager, raw, executor = (_Manager(), _Runner(), _Executor())
    record = SimpleNamespace(
        id="run",
        state=RunState.RUNNING,
        updated_at="2026-10-20T10:00:00+00:00",
        execution=SimpleNamespace(submitted=lambda x: x),
        processing_required=False,
    )
    manager.record = record
    run = PersistentRunner(manager, executor, raw, record)
    raw.state = RunState.UNKNOWN
    raw.failure_message = "scheduler disconnected"
    run._sync_completion(raw.result)
    run._sync_completion(raw.result)
    run.wait = lambda: run._sync_completion(raw.result)
    run.wait()
    assert manager.transitions == 1
    assert manager.completions == 0
    assert executor.acknowledgements == 0


def test_unknown_observation_notifies_without_finishing_calculation():
    from kkrunner.runs.manager import RunManager

    manager, raw, executor = (_Manager(), _Runner(), _Executor())
    record = SimpleNamespace(
        id="run",
        state=RunState.RUNNING,
        updated_at="2026-10-20T10:00:00+00:00",
        execution=SimpleNamespace(submitted=lambda x: x),
        processing_required=False,
    )
    manager.record = record
    run = PersistentRunner(manager, executor, raw, record)
    delivered = []
    raw.state = RunState.UNKNOWN
    RunManager._complete(run, raw.result, delivered.append)
    assert delivered == [raw.result]
    raw.state = RunState.FINISHED
    new_run = PersistentRunner(manager, executor, raw, record)
    RunManager._complete(new_run, raw.result, delivered.append)
    assert delivered == [raw.result, raw.result]
