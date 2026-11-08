API reference
===============

The root package provides backend-independent entry points for ordinary runs.
Choose executors from :mod:`kkrunner.backends` or :mod:`kkrunner.remote`; projects,
file manifests and advanced run contracts have their own public subpackages.
These import paths are independent of the modules implementing each type.

Common entry points
----------------------

.. py:module:: kkrunner

.. currentmodule:: kkrunner

.. autosummary::
   :toctree: _generated

   ExecutionSpec
   ExecutionOutcome
   RunManager
   RunStore
   RunState
   TaskFile
   ProcessingPending

Execution contracts and durable records
-----------------------------------------

.. py:module:: kkrunner.runs

.. currentmodule:: kkrunner.runs

.. autosummary::
   :toctree: _generated

   LaunchSpec
   MpiSpec
   MpiNotFoundWarning
   RunStatus
   FailurePhase
   Runner
   BackendRunner
   ManagedRunner
   Executor
   PersistentRunner
   RunRecord
   CorruptRunRecord
   DuplicateSubmissionError
   HistoricalFileMismatchError
   Execution
   WorkingDirectory

Declared files and identity
-----------------------------

.. py:module:: kkrunner.files

.. currentmodule:: kkrunner.files

.. autosummary::
   :toctree: _generated

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

Execution backends
---------------------

.. py:module:: kkrunner.backends

.. currentmodule:: kkrunner.backends

.. autosummary::
   :toctree: _generated

   LocalExecutor
   PsijExecutor
   ExecutorEndpoint
   ExecutorPool
   default_executor_pool

Remote execution and transport
--------------------------------

.. py:module:: kkrunner.remote

.. currentmodule:: kkrunner.remote

.. autosummary::
   :toctree: _generated

   RemoteEndpointExecutor
   Transport
   RunningCommand
   LocalTransport
   SshTransport

Projects
----------

.. py:module:: kkrunner.projects

.. currentmodule:: kkrunner.projects

.. autosummary::
   :toctree: _generated

   Project
   ProjectRepository
   ProjectRepositoryError
   ProjectConflictError
   ProjectDeleteError
   ProjectExecutionManager
   default_projects_directory

Backend implementation interfaces
------------------------------------

These modules expose lower-level runner implementations and resource ownership
helpers for backend authors. They are not re-exported by the public facades.

.. currentmodule:: kkrunner

.. autosummary::
   :toctree: _generated

   backends.local.LocalRunner
   backends.psij.PsijRunner
   remote.runner.RemoteRunner
   runs.processing.PostprocessingRunner
   runs.base.ExecutionResources
   runs.base.ResourceOwnedRunner
