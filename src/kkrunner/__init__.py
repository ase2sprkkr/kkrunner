"""Backend-independent execution library with lazy root-level conveniences."""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kkrunner._version import __version__
    from kkrunner.files.task_file import TaskFile
    from kkrunner.runs.base import ExecutionOutcome, ExecutionSpec, RunState
    from kkrunner.runs.manager import RunManager
    from kkrunner.runs.processing import ProcessingPending
    from kkrunner.runs.records import RunStore

_EXPORTS = {
    "__version__": "kkrunner._version",
    "TaskFile": "kkrunner.files.task_file",
    "ExecutionOutcome": "kkrunner.runs.base",
    "ExecutionSpec": "kkrunner.runs.base",
    "RunState": "kkrunner.runs.base",
    "RunManager": "kkrunner.runs.manager",
    "ProcessingPending": "kkrunner.runs.processing",
    "RunStore": "kkrunner.runs.records",
}

__all__ = [
    "ExecutionOutcome", "ExecutionSpec", "ProcessingPending",
    "RunManager", "RunState", "RunStore", "TaskFile", "__version__",
]


def __getattr__(name):
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
