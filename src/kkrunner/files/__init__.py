"""File declarations, transfer manifests and captured file identity."""

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

__all__ = [
    "ArtifactAvailabilityState",
    "CacheEntry",
    "FileEntry",
    "FileFingerprint",
    "FileManifest",
    "FileMapping",
    "FileState",
    "FileSyncPolicy",
    "FileVersion",
    "FileVersionCaptureError",
    "TaskFile",
]
