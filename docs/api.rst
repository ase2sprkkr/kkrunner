API reference
===============

The root package exports these principal types from their defining modules.
Use :class:`~kkrunner.RunManager` for project-free persistence and
:class:`~kkrunner.ProjectExecutionManager` for project-bound runs.
Backend jobs report execution facts; the managed run owns end-to-end completion.

.. py:module:: kkrunner

.. currentmodule:: kkrunner

Execution contracts
---------------------

.. autosummary::
   :toctree: _generated

   ExecutionSpec
   ExecutionOutcome
   LaunchSpec
   MpiSpec
   MpiNotFoundWarning
   RunState
   RunStatus
   FailurePhase
   Runner
   BackendRunner
   ManagedRunner
   Executor

Durable runs and processing
-----------------------------

.. autosummary::
   :toctree: _generated

   RunManager
   PersistentRunner
   RunRecord
   RunStore
   CorruptRunRecord
   DuplicateSubmissionError
   HistoricalFileMismatchError
   PostprocessingRunner
   ProcessingPending

Declared files and identity
-----------------------------

.. autosummary::
   :toctree: _generated

   TaskFile
   FileEntry
   CacheEntry
   FileMapping
   FileManifest
   FileSyncPolicy
   ArtifactAvailabilityState
   FileFingerprint
   FileState
   FileVersion
   FileVersionCaptureError

Backends and transport
------------------------

.. autosummary::
   :toctree: _generated

   LocalExecutor
   LocalRunner
   PsijExecutor
   PsijRunner
   RemoteEndpointExecutor
   RemoteRunner
   ExecutorEndpoint
   ExecutorPool
   default_executor_pool
   Transport
   RunningCommand
   LocalTransport
   SshTransport

Projects
----------

.. autosummary::
   :toctree: _generated

   Project
   ProjectRepository
   ProjectRepositoryError
   ProjectConflictError
   ProjectDeleteError
   ProjectExecutionManager
   default_projects_directory

Execution identity and resource ownership
-------------------------------------------

.. autosummary::
   :toctree: _generated

   Execution
   WorkingDirectory
   ExecutionResources
   ResourceOwnedRunner
