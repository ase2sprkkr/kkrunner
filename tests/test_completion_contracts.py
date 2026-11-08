import pytest

from kkrunner import FileEntry, FileManifest, RunState, RunStatus, RunStore
from kkrunner.runs.manager import RunManager


@pytest.mark.parametrize("optional", [False, True])
def test_missing_output_respects_optionality(tmp_path, optional):
    manager = RunManager(RunStore(tmp_path / "runs"))
    record = manager.new_record(
        directory=tmp_path,
        files=FileManifest(outputs=(FileEntry(local_path=str(tmp_path / "never-created"), optional=optional),)),
    )
    record = manager.complete(record, state=RunState.FINISHED, return_code=0, artifacts_available=True)
    assert record.state == (RunState.FINISHED if optional else RunState.FAILED)


@pytest.mark.parametrize("terminal_state", [RunState.FINISHED, RunState.FAILED, RunState.CANCELLED])
def test_refresh_acknowledges_terminal_receipt_after_commit(tmp_path, monkeypatch, terminal_state):
    manager = RunManager(RunStore(tmp_path / "runs"))
    calls = []

    class Backend:
        def acknowledge(self, record):
            assert manager.store.get(record.id).state == terminal_state
            calls.append(record.id)

    monkeypatch.setattr(manager, "executor_for", lambda record: Backend())
    record = manager.new_record(directory=tmp_path)
    manager.store.save(record)
    finished = manager.update(record, RunStatus(terminal_state, backend_id="receipt", return_code=0))
    assert finished.state == terminal_state
    assert calls == [record.id]


def test_completion_callback_can_read_its_own_finished_result(tmp_path):
    from threading import Event

    from kkrunner import ExecutionSpec, LocalExecutor

    ended, results = Event(), []
    run = None

    def completed(outcome):
        results.append(run.wait())
        ended.set()

    run = LocalExecutor().create_run(ExecutionSpec(["true"], directory=tmp_path), callback=completed)
    run.submit()
    assert ended.wait(3), "completion callback deadlocked waiting for its own completion event"
    assert results == [run.result]


def test_failed_ack_is_reconciled_without_changing_terminal_outcome(tmp_path, monkeypatch):
    manager = RunManager(RunStore(tmp_path / "runs"))
    calls = []

    class Backend:
        def acknowledge(self, record):
            calls.append(record.id)
            if len(calls) == 1:
                raise OSError("temporarily disconnected")

    monkeypatch.setattr(manager, "executor_for", lambda record: Backend())
    record = manager.new_record(directory=tmp_path)
    record = manager.complete(
        record, state=RunState.FINISHED, return_code=0, execution=record.execution.submitted("receipt")
    )
    assert record.state == RunState.FINISHED
    assert manager.reconcile_acknowledgements() == (record.id,)
    assert calls == [record.id, record.id]
    assert manager.store.get(record.id) == record


def test_failed_artifact_observation_prevents_processing_success(tmp_path):
    from kkrunner import ArtifactAvailabilityState

    # A callback cannot publish FINISHED after a concurrent artifact failure.
    manager = RunManager(RunStore(tmp_path / "runs"))
    path = tmp_path / "out"
    path.write_text("answer")
    record = manager.new_record(
        directory=tmp_path, processing_required=True, files=FileManifest(stdout=FileEntry(str(path)))
    )
    record = manager.complete(record, state=RunState.POSTPROCESSING, return_code=0, artifacts_available=True)

    def process(outcome):
        manager.update_artifact_availability(record, path, ArtifactAvailabilityState.FAILED, "lost artifact")
        return 42

    with pytest.raises(OSError, match="lost artifact"):
        manager.retry_postprocessing(record.id, process)
    assert manager.store.get(record.id).state != RunState.FINISHED


def test_download_retry_retains_backend_receipt_until_success(tmp_path, monkeypatch):
    from kkrunner import FailurePhase

    manager = RunManager(RunStore(tmp_path / "runs"))
    acknowledgements = []
    backend = type("Backend", (), {"acknowledge": lambda self, record: acknowledgements.append(record.id)})()
    monkeypatch.setattr(manager, "executor_for", lambda record: backend)
    path = tmp_path / "out"
    record = manager.new_record(
        directory=tmp_path,
        remote_directory="/remote",
        files=FileManifest(stdout=FileEntry(str(path), "/remote/out", "failed", "download interrupted")),
    )
    failed = manager.complete(
        record,
        state=RunState.FAILED,
        return_code=0,
        failure_phase=FailurePhase.DOWNLOAD,
        execution=record.execution.submitted("receipt"),
    )
    assert acknowledgements == []
    assert manager.reconcile_acknowledgements() == ()
    downloading = manager.resume_download(failed)
    path.write_text("retried output")
    completed = manager.complete(downloading, state=RunState.FINISHED, return_code=0, artifacts_available=True)
    assert completed.state == RunState.FINISHED
    assert acknowledgements == [record.id]


@pytest.mark.parametrize("state", [RunState.FINISHED, RunState.FAILED, RunState.CANCELLED])
def test_attach_rejects_durable_terminal_record_before_backend_access(tmp_path, state):
    manager = RunManager(RunStore(tmp_path / "runs"))
    stale = manager.new_record(directory=tmp_path)
    manager.complete(stale, state=state, return_code=0)
    with pytest.raises(RuntimeError, match="already terminal"):
        manager.attach(stale)


def test_other_observer_completion_cannot_deliver_raw_application_result(tmp_path):
    from kkrunner import ExecutionOutcome, ProcessingPending
    from kkrunner.runs.manager import PersistentRunner
    from kkrunner.runs.processing import PostprocessingRunner

    manager = RunManager(RunStore(tmp_path / "runs"))
    stale = manager.new_record(directory=tmp_path, processing_required=True)
    stale = manager.transition(stale, state=RunState.RUNNING)
    manager.complete(stale, state=RunState.FINISHED, return_code=0)

    class Raw:
        state = RunState.UNKNOWN
        result = ExecutionOutcome(return_code=0)
        exception = None
        backend_id = None

        def wait(self):
            return self.result

    observed = PostprocessingRunner(Raw(), None)
    run = PersistentRunner(manager, object(), observed, stale)
    delivered = []
    observed.callback = lambda result: manager._complete(run, result, delivered.append)
    run.start()
    with pytest.raises(ProcessingPending, match="another observer"):
        run.wait()
    assert delivered == [None]
    assert run.result is None
    assert run.state == RunState.FINISHED
