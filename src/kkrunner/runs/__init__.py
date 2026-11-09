"""Run contracts, durable records and lifecycle orchestration.

Public conveniences load on demand to avoid importing managers and backends
when only the execution contracts are required.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kkrunner.runs.base import BackendRunner, ExecutionOutcome, ExecutionSpec, Executor, FailurePhase, LaunchSpec, ManagedRunner, MpiNotFoundWarning, MpiSpec, Runner, RunState, RunStatus
    from kkrunner.runs.manager import DuplicateSubmissionError, HistoricalFileMismatchError, PersistentRunner, RunManager
    from kkrunner.runs.model import Execution, WorkingDirectory
    from kkrunner.runs.processing import ProcessingPending
    from kkrunner.runs.records import CorruptRunRecord, RunRecord, RunStore

_EXPORTS = {
    "BackendRunner": "kkrunner.runs.base",
    "CorruptRunRecord": "kkrunner.runs.records",
    "DuplicateSubmissionError": "kkrunner.runs.manager",
    "Execution": "kkrunner.runs.model",
    "ExecutionOutcome": "kkrunner.runs.base",
    "ExecutionSpec": "kkrunner.runs.base",
    "Executor": "kkrunner.runs.base",
    "FailurePhase": "kkrunner.runs.base",
    "HistoricalFileMismatchError": "kkrunner.runs.manager",
    "LaunchSpec": "kkrunner.runs.base",
    "ManagedRunner": "kkrunner.runs.base",
    "MpiNotFoundWarning": "kkrunner.runs.base",
    "MpiSpec": "kkrunner.runs.base",
    "PersistentRunner": "kkrunner.runs.manager",
    "ProcessingPending": "kkrunner.runs.processing",
    "RunManager": "kkrunner.runs.manager",
    "RunRecord": "kkrunner.runs.records",
    "RunState": "kkrunner.runs.base",
    "RunStatus": "kkrunner.runs.base",
    "RunStore": "kkrunner.runs.records",
    "Runner": "kkrunner.runs.base",
    "WorkingDirectory": "kkrunner.runs.model",
}

__all__ = [
    "BackendRunner",
    "CorruptRunRecord",
    "DuplicateSubmissionError",
    "Execution",
    "ExecutionOutcome",
    "ExecutionSpec",
    "Executor",
    "FailurePhase",
    "HistoricalFileMismatchError",
    "LaunchSpec",
    "ManagedRunner",
    "MpiNotFoundWarning",
    "MpiSpec",
    "PersistentRunner",
    "ProcessingPending",
    "RunManager",
    "RunRecord",
    "RunState",
    "RunStatus",
    "RunStore",
    "Runner",
    "WorkingDirectory",
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
