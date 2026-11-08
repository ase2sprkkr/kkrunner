from kkrunner import ExecutionSpec
from kkrunner.runs import LaunchSpec
from kkrunner.remote.executor import RemoteEndpointExecutor


class _Transport:
    host = "cluster"


def test_remote_project_runner_uses_manager_run_id(tmp_path):
    executor = RemoteEndpointExecutor(_Transport())
    spec = ExecutionSpec(
        argv=("true",),
        input_file=None,
        output_file=None,
        directory=str(tmp_path),
        launch=LaunchSpec(local_root=tmp_path, remote_root="/scratch/work"),
    )
    runner = executor.create_managed_run(spec, run_id="kkrunner-run-id")
    assert runner._run_id == "kkrunner-run-id"
