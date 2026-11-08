"""Public names and dependency boundaries for the standalone package."""

import ast
import importlib
import pkgutil
from pathlib import Path

import kkrunner


def test_public_managers_have_one_unambiguous_name():
    assert kkrunner.RunManager.__module__ == "kkrunner.runs.manager"
    assert kkrunner.ProjectExecutionManager.__module__ == "kkrunner.projects.manager"
    assert kkrunner.RemoteEndpointExecutor.__module__ == "kkrunner.remote.executor"
    assert not hasattr(kkrunner, "ExecutionManager")
    assert not hasattr(kkrunner, "RemoteExecutor")
    assert not hasattr(importlib.import_module("kkrunner.runs.manager"), "ExecutionManager")
    assert not hasattr(importlib.import_module("kkrunner.projects.manager"), "ExecutionManager")


def test_persistent_runner_names_do_not_imply_project_membership():
    from kkrunner.backends.local_managed import ManagedLocalRunner

    assert kkrunner.PersistentRunner.__module__ == "kkrunner.runs.manager"
    assert ManagedLocalRunner.__module__ == "kkrunner.backends.local_managed"
    assert not hasattr(kkrunner, "ProjectRunner")
    assert not hasattr(importlib.import_module("kkrunner.runs.manager"), "ProjectRunner")
    assert not hasattr(importlib.import_module("kkrunner.backends.local_managed"), "LocalProjectRunner")
    for executor in (kkrunner.LocalExecutor, kkrunner.PsijExecutor, kkrunner.RemoteEndpointExecutor):
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
