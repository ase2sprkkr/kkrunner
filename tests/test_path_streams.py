"""Path-valued specs work without application-owned pre-opened handles."""

from pathlib import Path
import sys

from kkrunner import ExecutionSpec, LaunchSpec, LocalExecutor, LocalTransport, RemoteEndpointExecutor


def test_raw_local_paths_and_stdin_are_materialized_at_submission(tmp_path):
    (tmp_path / "input.txt").write_text("answer")
    spec = ExecutionSpec(
        [sys.executable, "-c", 'import sys; print(sys.stdin.read()); print("err",file=sys.stderr)'],
        directory=tmp_path,
        stdin="input.txt",
        output_file="stdout.txt",
        error_file="stderr.txt",
    )
    run = LocalExecutor().create_run(spec)
    assert not (tmp_path / "stdout.txt").exists()
    assert run.run().return_code == 0
    assert (tmp_path / "stdout.txt").read_text() == "answer\n"
    assert (tmp_path / "stderr.txt").read_text() == "err\n"


def test_raw_remote_paths_work_with_only_runner_on_target(tmp_path):
    local, remote = tmp_path / "local", tmp_path / "remote"
    local.mkdir()
    remote.mkdir()
    executor = RemoteEndpointExecutor(LocalTransport(), command=(sys.executable, "-m", "kkrunner", "remote"))
    spec = ExecutionSpec(
        [sys.executable, "-c", "print(42)"],
        directory=local,
        output_file=local / "stdout.txt",
        launch=LaunchSpec(local_root=local, remote_root=remote),
    )
    run = executor.create_run(spec)
    assert not (local / "stdout.txt").exists()
    assert run.run().return_code == 0
    assert (local / "stdout.txt").read_text() == "42\n"
