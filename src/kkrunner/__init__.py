"""Calculation execution subsystem."""

from .file_fingerprints import FileFingerprint
from .file_versions import FileState, FileVersion, FileVersionCaptureError
from .task_file import TaskFile
from .base import (
    ExecutionOutcome,
    BackendRunner,
    ManagedRunner,
    ExecutionResources,
    ExecutionSpec,
    Executor,
    FailurePhase,
    LaunchSpec,
    MpiNotFoundWarning,
    MpiSpec,
    ResourceOwnedRunner,
    Runner,
    RunState,
    RunStatus,
)
from .run_model import (
    ArtifactAvailabilityState, Execution, WorkingDirectory, FileEntry,
    CacheEntry, FileMapping, FileManifest,
)
from .endpoint import ExecutorEndpoint
from .local import LocalExecutor, LocalRunner
from .manager import (
    CorruptRunRecord,
    HistoricalFileMismatchError,
    DuplicateSubmissionError,
    ProjectRunner,
    RunRecord,
    RunStore,
    RunManager,
)
from .pool import ExecutorPool, default_executor_pool
from .postprocessing import PostprocessingRunner, ProcessingPending
from .projects import (
    Project,
    ProjectConflictError,
    ProjectDeleteError,
    ProjectRepository,
    ProjectRepositoryError,
    default_projects_directory,
)
from .project_manager import ExecutionManager, ProjectExecutionManager
from .psij import PsijExecutor, PsijRunner
from .remote import FileSyncPolicy, RemoteRunner
from .remote_endpoint import RemoteEndpointExecutor
from .transport import LocalTransport, RunningCommand, SshTransport, Transport

RemoteExecutor = RemoteEndpointExecutor

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
    "ExecutionManager",
    "RunManager",
    "ProjectExecutionManager",
    "ProjectRunner",
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
    "RemoteExecutor",
    "RemoteEndpointExecutor",
    "RemoteRunner",
    "Transport",
    "RunningCommand",
    "LocalTransport",
    "SshTransport",
]


__version__ = "0.1.0.dev0"
__all__ += ["TaskFile", "ProcessingPending", "HistoricalFileMismatchError"]
