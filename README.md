# KKRunner

Program-independent Python execution, durable run history, file manifests,
local/MPI processes, SSH transport and optional PSI/J scheduler support.
No ASE, ASE2SPRKKR, scientific parser, NumPy or compiler is required.

```sh
python -m pip install .
python -m pip install '.[psij]'  # optional scheduler support
kkrunner remote --help
kkrunner-remote --help  # equivalent standalone protocol executable
```

For a source checkout alongside ASE2SPRKKR, install this project first:

```sh
python -m pip install -e ../kkrunner
python -m pip install -e .  # from the ASE2SPRKKR checkout
```

## Raw execution

```python
import sys
from kkrunner import ExecutionSpec, LocalExecutor

run = LocalExecutor().create_run(ExecutionSpec([sys.executable, '-c', 'print(42)']))
outcome = run.run()
assert outcome.return_code == 0
```

## Persistent execution

```python
import sys
from pathlib import Path
from kkrunner import ExecutionManager, ExecutionSpec, LocalExecutor, ProjectRepository

root = Path('example').absolute()
root.mkdir(exist_ok=True)
projects = ProjectRepository(root / 'projects')
project = projects.create('Example', directory=root)
manager = ExecutionManager(project_repository=projects, project=project)
run = manager.create_run(
    LocalExecutor(),
    ExecutionSpec([sys.executable, '-c', 'print(42)'],
                  directory=root, output_file=root / 'stdout.txt'),
    metadata={'example': {'label': 'answer'}},
)
outcome = run.run()
assert manager.store.get(run.id).state.value == 'finished'
```

`manager.attach(run_id)` resumes monitoring and required transfers. A result
callback is optional; when supplied it receives an `ExecutionOutcome` and may
return any Python object. To defer processing, create a run with
`processing_required=True`, then supply `process_result=` on a later attach.
Without that callback the durable state remains `postprocessing` and `wait()`
raises `ProcessingPending`. The same exception tells an application observer
that another client owns/already performed processing; load the historical
application result instead of treating a raw outcome as a parsed result.

`manager.retry_postprocessing(run_id, callback)` retries failed/interrupted
processing against the captured files without submitting another process.
`manager.resume_download(run_id)` reopens a failed download before attach.
`run.stop_observation()` detaches observation without cancelling the backend;
`run.cancel()` requests backend cancellation. Untracked raw local runs have no
restart/reconnect guarantee; managed local runs use the same supervisor as SSH.

See [architecture](docs/architecture.md) for ownership, recovery and format rules.

## End-user commands from ASE2SPRKKR

`ase2sprkkr remote status HANDLE`, `ase2sprkkr remote follow HANDLE` and
`ase2sprkkr remote cancel HANDLE` invoke the same service on the current host,
without requiring users to supply a protocol version. Internal submit,
recovery, acknowledgements and MPI discovery belong to KKRunner's protocol CLI.
Execution clients always supply `--protocol-version` explicitly.

## Source provenance

Extracted from ASE2SPRKKR commit
`b711659b794e911a2356fca8d53d7c5a27775891`, primarily
`src/ase2sprkkr/execution/`, plus file identity/locking/async utilities from
`src/ase2sprkkr/common/` and the generic data portion of `TaskFile`.
The source remains available in that repository's history; its license is
preserved in LICENCE. Application preparation, parser and GUI tests remain
with their respective applications.

Existing profiles with an explicit `remote_command = ["ase2sprkkr", "remote"]`
need `remote_command = ["kkrunner", "remote"]` for execution. Profiles using the
default command select KKRunner automatically.

## Build and test the distribution

```sh
python -m pip install build
python -m build
# Wheel is built from the generated sdist, not directly from the checkout.
python -m pip install dist/kkrunner-*.whl
python -m pip check
# Run from outside the checkout, with no source PYTHONPATH:
python /path/to/kkrunner/tests/smoke_distribution.py
```

The source archive includes docs, test package/fixtures and Docker configuration.
CI builds the distributions, exercises the installed core without ASE, and runs
the unpacked source archive's tests against the installed wheel on Python 3.9,
3.12 and 3.14. The Docker test image also executes only the installed artifact.

Use `RunManager` for a project-free store and `ProjectExecutionManager` for
project-bound runs. The previous ExecutionManager names are compatibility aliases.
See the architecture document for processing ownership, filesystem identities
and the Linux requirement for managed local execution.
