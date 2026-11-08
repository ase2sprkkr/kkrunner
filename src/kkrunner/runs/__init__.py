"""Run contracts, durable records and lifecycle orchestration."""

from kkrunner.runs.base import (
    BackendRunner,
    ExecutionOutcome,
    ExecutionSpec,
    Executor,
    FailurePhase,
    LaunchSpec,
    ManagedRunner,
    MpiNotFoundWarning,
    MpiSpec,
    Runner,
    RunState,
    RunStatus,
)
from kkrunner.runs.manager import DuplicateSubmissionError, HistoricalFileMismatchError, PersistentRunner, RunManager
from kkrunner.runs.model import Execution, WorkingDirectory
from kkrunner.runs.processing import ProcessingPending
from kkrunner.runs.records import CorruptRunRecord, RunRecord, RunStore

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
