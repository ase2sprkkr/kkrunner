"""Program-independent execution, file manifests and durable run management."""

from kkrunner.backends.endpoint import ExecutorEndpoint
from kkrunner.backends.local import LocalExecutor, LocalRunner
from kkrunner.backends.pool import ExecutorPool, default_executor_pool
from kkrunner.backends.psij import PsijExecutor, PsijRunner
from kkrunner.files.fingerprints import FileFingerprint
from kkrunner.files.manifest import (
    ArtifactAvailabilityState,
    CacheEntry,
    FileEntry,
    FileManifest,
    FileMapping,
    FileSyncPolicy,
)
from kkrunner.files.task_file import TaskFile
from kkrunner.files.versions import FileState, FileVersion, FileVersionCaptureError
from kkrunner.projects.manager import ProjectExecutionManager
from kkrunner.projects.repository import (
    Project,
    ProjectConflictError,
    ProjectDeleteError,
    ProjectRepository,
    ProjectRepositoryError,
    default_projects_directory,
)
from kkrunner.remote.executor import RemoteEndpointExecutor
from kkrunner.remote.runner import RemoteRunner
from kkrunner.remote.transport import LocalTransport, RunningCommand, SshTransport, Transport
from kkrunner.runs.base import (
    BackendRunner,
    ExecutionOutcome,
    ExecutionResources,
    ExecutionSpec,
    Executor,
    FailurePhase,
    LaunchSpec,
    ManagedRunner,
    MpiNotFoundWarning,
    MpiSpec,
    ResourceOwnedRunner,
    Runner,
    RunState,
    RunStatus,
)
from kkrunner.runs.manager import DuplicateSubmissionError, HistoricalFileMismatchError, PersistentRunner, RunManager
from kkrunner.runs.model import Execution, WorkingDirectory
from kkrunner.runs.processing import PostprocessingRunner, ProcessingPending
from kkrunner.runs.records import CorruptRunRecord, RunRecord, RunStore

__all__ = [
    "ArtifactAvailabilityState",
    "Execution",
    "WorkingDirectory",
    "FileEntry",
    "CacheEntry",
    "FileMapping",
    "FileManifest",
    "ExecutionOutcome",
    "ExecutionResources",
    "ExecutionSpec",
    "Executor",
    "ExecutorEndpoint",
    "FailurePhase",
    "LaunchSpec",
    "MpiSpec",
    "MpiNotFoundWarning",
    "PostprocessingRunner",
    "ResourceOwnedRunner",
    "Runner",
    "BackendRunner",
    "ManagedRunner",
    "RunState",
    "RunStatus",
    "DuplicateSubmissionError",
    "FileFingerprint",
    "FileState",
    "FileVersion",
    "FileVersionCaptureError",
    "RunRecord",
    "RunStore",
    "CorruptRunRecord",
    "RunManager",
    "ProjectExecutionManager",
    "PersistentRunner",
    "Project",
    "ProjectRepository",
    "ProjectRepositoryError",
    "ProjectConflictError",
    "ProjectDeleteError",
    "default_projects_directory",
    "ExecutorPool",
    "default_executor_pool",
    "LocalExecutor",
    "LocalRunner",
    "PsijExecutor",
    "PsijRunner",
    "FileSyncPolicy",
    "RemoteEndpointExecutor",
    "RemoteRunner",
    "Transport",
    "RunningCommand",
    "LocalTransport",
    "SshTransport",
]


__version__ = "0.1.0.dev0"
__all__ += ["TaskFile", "ProcessingPending", "HistoricalFileMismatchError"]
