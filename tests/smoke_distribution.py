import importlib.metadata as md
import importlib.util
import json
import os
from pathlib import Path
import pkgutil
import subprocess
import sys
import tempfile

import kkrunner
from kkrunner import (
    ExecutionManager,
    ExecutionSpec,
    LaunchSpec,
    LocalExecutor,
    LocalTransport,
    ProjectRepository,
    RemoteEndpointExecutor,
    RunState,
    ProcessingPending,
)

assert not os.environ.get("PYTHONPATH")
assert importlib.util.find_spec("ase") is None
assert importlib.util.find_spec("ase2sprkkr") is None
for module in pkgutil.iter_modules(kkrunner.__path__):
    if module.name not in ("__main__",):
        __import__("kkrunner." + module.name)
assert md.version("kkrunner") == kkrunner.__version__

root = Path(tempfile.mkdtemp(prefix="kkrunner-distribution-"))
raw = LocalExecutor().create_run(
    ExecutionSpec(
        [sys.executable, "-c", "print(42)"],
        directory=root,
        output_file=root / "raw.out",
    )
)
assert raw.run().return_code == 0
assert (root / "raw.out").read_text() == "42\n"

projects = ProjectRepository(root / "projects")
project = projects.create("Wheel review", directory=root)
manager = ExecutionManager(project_repository=projects, project=project)
run = manager.create_run(
    LocalExecutor(),
    ExecutionSpec(
        [sys.executable, "-c", "print(43)"],
        directory=root,
        output_file=root / "managed.out",
    ),
    processing_required=True,
)
try:
    run.run()
except ProcessingPending:
    pass
assert manager.store.get(run.id).state == RunState.POSTPROCESSING
restarted = ExecutionManager(project_repository=projects, project=project)
attached = restarted.attach(run.id, process_result=lambda outcome: int(Path(outcome.output_file).read_text()))
assert attached.wait() == 43
assert restarted.store.get(run.id).state == RunState.FINISHED

local, remote = root / "local", root / "remote"
local.mkdir()
remote.mkdir()
executor = RemoteEndpointExecutor(LocalTransport(), command=(str(Path(sys.executable).parent / "kkrunner-remote"),))
run = executor.create_run(
    ExecutionSpec(
        [sys.executable, "-c", "print(44)"],
        directory=local,
        output_file=local / "remote.out",
        launch=LaunchSpec(local_root=local, remote_root=remote),
    )
)
assert run.run().return_code == 0
assert (local / "remote.out").read_text() == "44\n"
for command in ("kkrunner", "kkrunner-remote"):
    subprocess.run([str(Path(sys.executable).parent / command), "--help"], check=True, stdout=subprocess.DEVNULL)
print(
    json.dumps(
        {
            "distribution": md.version("kkrunner"),
            "module": kkrunner.__file__,
            "raw": "ok",
            "managed_reconnect": "ok",
            "remote_executable": "ok",
            "without_ase": True,
        }
    )
)
