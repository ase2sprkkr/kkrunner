"""Public names and dependency boundaries for the standalone package."""

import ast
import importlib
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest

import kkrunner
import kkrunner.projects
import kkrunner.remote


def test_public_managers_have_one_unambiguous_name():
    assert kkrunner.RunManager.__module__ == "kkrunner.runs.manager"
    assert kkrunner.projects.ProjectExecutionManager.__module__ == "kkrunner.projects.manager"
    assert kkrunner.remote.RemoteEndpointExecutor.__module__ == "kkrunner.remote.executor"
    assert not hasattr(kkrunner, "ExecutionManager")
    assert not hasattr(kkrunner, "RemoteExecutor")
    assert not hasattr(importlib.import_module("kkrunner.runs.manager"), "ExecutionManager")
    assert not hasattr(importlib.import_module("kkrunner.projects.manager"), "ExecutionManager")


def test_persistent_runner_names_do_not_imply_project_membership():
    from kkrunner.backends.local_managed import ManagedLocalRunner

    assert kkrunner.runs.PersistentRunner.__module__ == "kkrunner.runs.manager"
    assert ManagedLocalRunner.__module__ == "kkrunner.backends.local_managed"
    assert not hasattr(kkrunner, "ProjectRunner")
    assert not hasattr(importlib.import_module("kkrunner.runs.manager"), "ProjectRunner")
    assert not hasattr(importlib.import_module("kkrunner.backends.local_managed"), "LocalProjectRunner")
    for executor in (
        kkrunner.backends.LocalExecutor,
        kkrunner.backends.PsijExecutor,
        kkrunner.remote.RemoteEndpointExecutor,
    ):
        assert callable(executor.create_managed_run)
        assert not hasattr(executor, "create_project_run")


def test_all_runtime_modules_import_without_optional_scheduler_dependency():
    for module in pkgutil.walk_packages(kkrunner.__path__, kkrunner.__name__ + "."):
        if not module.name.endswith("__main__"):
            importlib.import_module(module.name)


def test_file_and_support_layers_do_not_depend_on_orchestration():
    root = Path(kkrunner.__file__).parent
    for package in ("files", "support"):
        for path in (root / package).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith(
                        (
                            "kkrunner.runs",
                            "kkrunner.projects",
                            "kkrunner.remote",
                            "kkrunner.backends",
                        )
                    ), (path.name, node.module)


def test_root_has_only_backend_independent_entry_points():
    assert set(kkrunner.__all__) - {"__version__"} == {
        "ExecutionSpec",
        "ExecutionOutcome",
        "RunManager",
        "RunStore",
        "RunState",
        "TaskFile",
        "ProcessingPending",
    }
    for name in (
        "LocalExecutor",
        "PsijExecutor",
        "RemoteEndpointExecutor",
        "ProjectRepository",
        "LocalRunner",
        "PsijRunner",
        "RemoteRunner",
        "PostprocessingRunner",
    ):
        assert not hasattr(kkrunner, name)


def test_contract_import_does_not_load_backend_implementations():
    code = """
import sys
from kkrunner.files import TaskFile
from kkrunner import ExecutionSpec, RunStore
from kkrunner import backends
assert 'LocalExecutor' in dir(backends)
assert all(name not in sys.modules for name in (
    'kkrunner.backends.local', 'kkrunner.backends.psij', 'kkrunner.remote',
    'kkrunner.projects', 'psij', 'psutil',
))
from kkrunner.backends import LocalExecutor
from kkrunner.backends.local import LocalExecutor as implementation
assert LocalExecutor is implementation
assert backends.LocalExecutor is LocalExecutor
assert 'kkrunner.backends.psij' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True, timeout=10)


def test_facade_exports_resolve_without_optional_scheduler_dependency():
    for package in (kkrunner.runs, kkrunner.files, kkrunner.backends, kkrunner.projects, kkrunner.remote):
        for name in package.__all__:
            assert getattr(package, name) is not None, (package.__name__, name)
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = kkrunner.backends.not_a_backend


def test_generic_manager_has_no_application_methods():
    from kkrunner.runs.manager import RunManager

    assert not hasattr(RunManager, "load_result")
    assert not hasattr(RunManager, "attach_sprkkr")

def test_root_import_is_lazy():
    code = """\
import kkrunner
import sys
assert all(name not in sys.modules for name in (
    'kkrunner.runs', 'kkrunner.files', 'kkrunner.backends',
    'kkrunner.remote', 'kkrunner.projects', 'psutil',
))
assert 'ExecutionSpec' in dir(kkrunner)
"""
    subprocess.run([sys.executable, "-c", code], check=True, timeout=10)
