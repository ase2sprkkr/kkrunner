from types import SimpleNamespace

import pytest

from kkrunner.runs import Execution, FailurePhase, RunRecord, WorkingDirectory
from kkrunner.backends import ExecutorEndpoint, LocalExecutor
from kkrunner.files import FileEntry, FileManifest
from kkrunner import RunState
from kkrunner.backends import local_managed as local_project
from kkrunner.remote import service as remote_service


def test_disappeared_local_process_is_unknown(monkeypatch):
    from kkrunner.remote import service as remote_service

    executor = LocalExecutor()
    handle = remote_service._encode_handle(
        {
            "kind": "process",
            "identity": {"pid": 12345, "start_time": 0, "time_basis": "linux-boot"},
            "receipt_id": "a" * 32,
            "socket_path": "/missing/socket",
        }
    )
    run = RunRecord(
        id="run",
        state=RunState.RUNNING,
        created_at="2026-10-13T08:00:00+00:00",
        updated_at="2026-10-13T08:00:00+00:00",
        execution=Execution(ExecutorEndpoint(), WorkingDirectory("/tmp"), handle),
        files=FileManifest(),
        metadata={"test": {"task": "SCF"}},
        processing_required=True,
    )
    monkeypatch.setattr(remote_service, "_process_outcome", lambda receipt_id: None)
    monkeypatch.setattr(remote_service.ProcessIdentity, "read", classmethod(lambda cls, pid: None))
    (status,) = executor.status(run)
    assert status.state == RunState.UNKNOWN


def test_lost_is_not_a_run_state():
    with pytest.raises(ValueError):
        RunState("lost")


@pytest.mark.parametrize(
    "state, phase, stream_state",
    [
        (RunState.RUNNING, None, None),
        (RunState.UNKNOWN, None, None),
        (RunState.FINISHED, None, "available"),
        (RunState.CANCELLED, None, "available"),
        (RunState.FAILED, FailurePhase.EXECUTION, "available"),
        (RunState.FAILED, FailurePhase.LAUNCH, "skipped"),
        (RunState.FAILED, FailurePhase.ARTIFACTS, "failed"),
    ],
)
def test_local_recovery_and_status_share_projection_without_extra_query(
    monkeypatch, tmp_path, state, phase, stream_state
):
    output = tmp_path / "run.out"
    output.write_bytes(b"partial output")
    files = FileManifest(stdout=FileEntry(local_path=str(output), availability_state="pending"))
    facts = {
        "state": state.value,
        "return_code": 0 if state == RunState.FINISHED else 7,
        "error": "backend message",
        "failure_phase": None if phase is None else phase.value,
    }
    remote_id = "opaque-backend-reference"
    reply = {"remote_id": remote_id, **facts}
    monkeypatch.setattr(
        local_project,
        "status_remote",
        lambda backend_id: facts if backend_id == remote_id else pytest.fail("Unexpected backend identity"),
    )
    queried = local_project.local_status(remote_id, files)

    def no_second_status_query(_backend_id):
        pytest.fail("Recovery must not query backend status again")

    monkeypatch.setattr(local_project, "status_remote", no_second_status_query)

    def recover(run_id, request):
        assert run_id == "test-run"
        assert request == {"executor": "local", "directory": str(tmp_path)}
        return reply

    monkeypatch.setattr(remote_service, "recover_remote", recover)
    submission = SimpleNamespace(execution=SimpleNamespace(directory=SimpleNamespace(local=str(tmp_path))), files=files)
    recovered = LocalExecutor().recover_submission("test-run", submission)
    assert recovered == queried
    assert recovered.backend_id == remote_id
    assert recovered.message == "backend message"
    assert recovered.failure_phase == phase
    if stream_state is None:
        assert recovered.files is None
        assert files.stdout.availability_state == "pending"
    else:
        assert recovered.files.stdout.availability_state == stream_state
        assert files.stdout.availability_state == "pending"


def test_local_status_without_manifest_keeps_backend_facts(monkeypatch):
    facts = {"state": "finished", "return_code": 0, "error": None, "failure_phase": None}
    monkeypatch.setattr(local_project, "status_remote", lambda backend_id: facts)
    status = local_project.local_status("opaque", files=None)
    assert status.state == RunState.FINISHED
    assert status.backend_id == "opaque"
    assert status.files is None
