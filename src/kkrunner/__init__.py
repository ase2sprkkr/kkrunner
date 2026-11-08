"""Backend-independent entry points for execution and durable run management."""

from kkrunner._version import __version__
from kkrunner.files import TaskFile
from kkrunner.runs import ExecutionOutcome, ExecutionSpec, ProcessingPending, RunManager, RunState, RunStore

__all__ = [
    "ExecutionOutcome",
    "ExecutionSpec",
    "ProcessingPending",
    "RunManager",
    "RunState",
    "RunStore",
    "TaskFile",
    "__version__",
]
