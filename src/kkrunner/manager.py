"""Project run history and lifecycle orchestration."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


from .file_versions import FileState, FileVersion, file_digest
from ._durability import sync_file
from .base import (
    Executor,
    FailurePhase,
    RunState,
    RunStatus,
    SubmissionNotStarted,
)
from .endpoint import ExecutorEndpoint, endpoint_for_executor
from .pool import default_executor_pool
from .records import RunRecord
from .records import CorruptRunRecord as CorruptRunRecord, RunStore as RunStore
from .conflicts import submission_conflicts
from .postprocessing import PostprocessingRunner, ProcessingPending
from .run_model import (
    ArtifactAvailabilityState,
    Execution,
    WorkingDirectory,
    FileManifest,
)
from .transport import expand_local_candidates, has_file_magic


class HistoricalFileMismatchError(OSError):
    """Restored contents differ from a run's captured SHA-256 digest."""


_STATE_RANK = {
    RunState.NEW: 0,
    RunState.SUBMITTING: 1,
    RunState.QUEUED: 2,
    RunState.RUNNING: 3,
    RunState.DOWNLOADING: 4,
    RunState.POSTPROCESSING: 5,
    RunState.FINISHED: 6,
    RunState.FAILED: 6,
    RunState.CANCELLED: 6,
}
_UNCHANGED = object()
_NO_ARTIFACTS_FAILURES = {
    FailurePhase.SUBMISSION,
    FailurePhase.LAUNCH,
    FailurePhase.ARTIFACTS,
    FailurePhase.DOWNLOAD,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _unique(values):
    return tuple(dict.fromkeys(value for value in values if value is not None))


def _failure_phase(value):
    if value is None or isinstance(value, FailurePhase):
        return value
    return FailurePhase(value)


class DuplicateSubmissionError(RuntimeError):
    """A project run would duplicate an active calculation namespace."""

    def __init__(self, record, conflicts):
        self.record = record
        self.conflicts = tuple(conflicts)
        super().__init__(
            "Run conflicts with {} active project run{}".format(
                len(self.conflicts), "" if len(self.conflicts) == 1 else "s"
            )
        )


class RunManager:
    """Persist public run lifecycle without task-specific knowledge."""

    def __init__(self, store=None, *, executor_pool=None, submitting_grace=60.0):
        if submitting_grace < 0:
            raise ValueError("submitting_grace must be non-negative")
        self.store = store
        self.executor_pool = executor_pool if executor_pool is not None else default_executor_pool()
        self._ack_lock = Lock()
        self._acknowledged_results = set()
        self.submitting_grace = float(submitting_grace)

    def register_executor(self, executor: Executor, endpoint=None):
        endpoint = endpoint or endpoint_for_executor(executor)
        self.executor_pool.get(endpoint, lambda: executor)
        return endpoint

    def executor_for(self, record):
        return self.executor_pool.for_endpoint(record.execution.endpoint)

    @staticmethod
    def _concrete_result_files(manifests):
        paths = []
        seen = set()
        for manifest in manifests:
            for path in expand_local_candidates(manifest):
                path = os.path.abspath(path)
                if path in seen or not os.path.isfile(path):
                    continue
                seen.add(path)
                paths.append(path)
        return tuple(paths)

    @classmethod
    def _result_files_snapshot(cls, manifests, *, sync=False):
        versions = []
        for path in cls._concrete_result_files(manifests):
            if sync:
                sync_file(path)
            versions.append(FileVersion.capture(path, require_digest=True))
        return tuple(sorted(versions, key=lambda value: os.fspath(value.path)))

    @classmethod
    def _sync_result_files(cls, manifests):
        for path in cls._concrete_result_files(manifests):
            sync_file(path)

    @classmethod
    def _file_is_current(cls, result_files, path, versions):
        if result_files is None or path is None:
            return False
        path = os.path.abspath(path)
        if result_files.captured_at is None:
            return os.path.isfile(path)
        for version in versions:
            if os.path.abspath(os.fspath(version.path)) == path:
                return version.is_current()
        return False

    @staticmethod
    def _missing_result_files(result_files):
        if result_files is None:
            return ()
        if result_files.captured_at is not None:
            return tuple(
                os.fspath(item.path) for item in result_files.all_versions if item.state() is FileState.MISSING
            )

        missing = []
        for manifest in result_files.manifests:
            if has_file_magic(manifest):
                if not expand_local_candidates(manifest):
                    missing.append(manifest)
            elif not os.path.isfile(manifest):
                missing.append(manifest)
        return _unique(missing)

    def _capture_result_files(self, result_files):
        if result_files is None or result_files.captured_at is not None:
            return result_files
        from .file_availability import discover_local_files

        captured = replace(
            result_files,
            input_versions=self._result_files_snapshot(result_files.input_files),
            output_versions=self._result_files_snapshot(result_files.output_files, sync=True),
            captured_at=_now(),
        )
        return discover_local_files(captured)

    def input_file_is_current(self, run):
        record = self.store.get(run) if isinstance(run, str) else self.store.get(run.id)
        result_files = record.files
        return self._file_is_current(
            result_files,
            None if result_files is None else result_files.input_file,
            () if result_files is None else result_files.input_versions,
        )

    def output_file_is_current(self, run):
        record = self.store.get(run) if isinstance(run, str) else self.store.get(run.id)
        result_files = record.files
        return self._file_is_current(
            result_files,
            None if result_files is None else result_files.output_file,
            () if result_files is None else result_files.output_versions,
        )

    def new_record(
        self,
        *,
        directory,
        endpoint=None,
        remote_directory=None,
        files=None,
        run_id=None,
        project_id=None,
        metadata=None,
        processing_required=False,
    ):
        now = _now()
        local = os.path.abspath(os.fspath(directory))
        return RunRecord(
            id=run_id or uuid4().hex,
            state=RunState.NEW,
            created_at=now,
            updated_at=now,
            metadata={} if metadata is None else metadata,
            processing_required=processing_required,
            execution=Execution(endpoint or ExecutorEndpoint(), WorkingDirectory(local, remote_directory)),
            files=files if files is not None else FileManifest(),
            project_id=project_id,
        )

    @staticmethod
    def _merged_state(latest, requested):
        if requested is None:
            return latest.state
        requested = RunState(requested)
        if latest.state.is_terminal:
            return latest.state
        if requested == RunState.UNKNOWN:
            # Uncertainty cannot retract confirmed execution completion.
            if latest.state in (RunState.POSTPROCESSING, RunState.DOWNLOADING):
                return latest.state
            return requested
        if latest.state == RunState.UNKNOWN:
            return requested
        if _STATE_RANK[requested] < _STATE_RANK[latest.state]:
            return latest.state
        return requested

    @staticmethod
    def _merged_result_files(latest, requested):
        if requested is _UNCHANGED or requested is None:
            return latest.files
        if isinstance(requested, dict):
            requested = FileManifest(**requested)
        current = latest.files
        if current is None:
            return requested
        if current.captured_at is not None:
            # Immutable historical evidence: an old runner must not replace
            # the captured digests with its uncaptured in-memory manifest.
            return current
        return requested

    def transition(
        self,
        record,
        *,
        state=None,
        execution=_UNCHANGED,
        return_code=_UNCHANGED,
        message=_UNCHANGED,
        failure_phase=_UNCHANGED,
        files=_UNCHANGED,
        expected_updated_at=_UNCHANGED,
        expected_record=None,
        expected_processing_attempt=None,
    ):
        def merge(latest):
            if expected_processing_attempt is not None and (
                latest.processing_attempt != expected_processing_attempt or latest.state != RunState.POSTPROCESSING
            ):
                raise ProcessingPending("Processing attempt no longer owns completion")
            if expected_processing_attempt is not None and state == RunState.FINISHED and latest.files.failed_artifacts:
                raise OSError(latest.files.availability_message or "Artifacts became unavailable during processing")
            if expected_record is not None and latest != expected_record:
                raise RuntimeError("Run changed during postprocessing retry")
            if expected_updated_at is not _UNCHANGED and latest.updated_at != expected_updated_at:
                # An independent refresh has superseded this observation.
                return latest
            final_locked = latest.state.is_terminal
            now = _now()
            merged_state = self._merged_state(latest, state)
            if state is not None and RunState(state) == RunState.UNKNOWN and merged_state != RunState.UNKNOWN:
                # Ignore the entire stale observation, including its message
                # and artifact metadata, not merely its proposed state.
                return latest
            changes = {"state": merged_state, "updated_at": now}
            if not latest.state.is_terminal and merged_state.is_terminal:
                changes["finished_at"] = now
            merged_result_files = self._merged_result_files(latest, files)
            if merged_result_files is not latest.files:
                changes["files"] = merged_result_files
            if execution is not _UNCHANGED and execution is not None:
                if latest.execution.backend_id is not None and execution.backend_id != latest.execution.backend_id:
                    raise ValueError("Backend identity cannot change")
                changes["execution"] = execution
            if return_code is not _UNCHANGED and return_code is not None:
                if not final_locked or latest.return_code is None:
                    changes["return_code"] = return_code
            if message is not _UNCHANGED:
                if message is None and latest.state == RunState.UNKNOWN and merged_state != RunState.UNKNOWN:
                    # A later scheduler observation supersedes the stale
                    # connection-error diagnostic.
                    changes["message"] = None
                elif message is not None and (not final_locked or latest.message is None):
                    changes["message"] = message
            if failure_phase is not _UNCHANGED:
                normalized = _failure_phase(failure_phase)
                if not final_locked or latest.failure_phase is None:
                    changes["failure_phase"] = normalized
            if all(getattr(latest, key) == value for key, value in changes.items() if key != "updated_at"):
                return latest
            return replace(latest, **changes)

        return self.store.update(record, merge)

    def update_artifact_availability(self, record, path, state, message=None):
        """Persist availability of one artifact without changing the run outcome."""
        state = ArtifactAvailabilityState(state)

        def update(latest):
            return replace(
                latest,
                updated_at=_now(),
                files=latest.files.with_file_availability(path, state.value, message),
            )

        return self.store.update(record, update)

    def _is_stale_submitting(self, record, *, now=None):
        if record.state != RunState.SUBMITTING or record.execution.backend_id is not None:
            return False
        now = now or datetime.now(timezone.utc)
        return (now - _timestamp(record.updated_at)).total_seconds() >= self.submitting_grace

    def recover_submitting(self, record):
        record = self.store.get(record.id)
        if not self._is_stale_submitting(record):
            return record
        executor = self.executor_for(record)
        try:
            status = executor.recover_submission(
                record.id,
                record,
                submitted_at=record.updated_at,
            )
        except NotImplementedError:
            return record
        if status is not None:
            return self.update(record, status)

        def mark_absent(latest):
            if latest.state != RunState.SUBMITTING or latest.execution.backend_id is not None:
                return latest
            now = _now()
            return replace(
                latest,
                state=RunState.FAILED,
                updated_at=now,
                finished_at=now,
                message="Stale submission was not found by its execution backend",
                failure_phase=FailurePhase.SUBMISSION,
            )

        return self.store.update(record, mark_absent)

    def reserve(self, record):
        attempted_recovery = set()
        while True:
            with self.store.submission_lock():
                try:
                    existing = self.store.get(record.id)
                except FileNotFoundError:
                    existing = None
                if existing is not None and (existing != record or existing.state != RunState.NEW):
                    raise ValueError(f"Run id {record.id!r} already exists; use attach()")
                conflicts = tuple(
                    active
                    for active in self.store.runs(active=True)
                    if active.id != record.id and submission_conflicts(record, active)
                )
                if not conflicts:
                    if record.files is not None:
                        self._sync_result_files(record.files.input_files)
                    return self.transition(
                        record,
                        state=RunState.SUBMITTING,
                    )
                stale = tuple(
                    conflict
                    for conflict in conflicts
                    if conflict.id not in attempted_recovery and self._is_stale_submitting(conflict)
                )

            if not stale:
                raise DuplicateSubmissionError(record, conflicts)
            progressed = False
            for conflict in stale:
                attempted_recovery.add(conflict.id)
                recovered = self.recover_submitting(conflict)
                if recovered.state != RunState.SUBMITTING or recovered.execution.backend_id is not None:
                    progressed = True
            if not progressed:
                raise DuplicateSubmissionError(record, conflicts)

    def update(self, record, status: RunStatus):
        phase = _failure_phase(status.failure_phase)
        return_code = status.return_code
        state = (
            (RunState.POSTPROCESSING if record.processing_required else RunState.FINISHED)
            if status.state == RunState.FINISHED
            else status.state
        )
        execution = status.execution
        if execution is None and status.backend_id is not None:
            execution = record.execution.submitted(status.backend_id)
        if status.state == RunState.FINISHED:
            updated = self.complete(
                record,
                state=state,
                execution=execution,
                files=status.files if status.files is not None else record.files,
                return_code=return_code,
                message=status.message,
                failure_phase=phase,
                artifacts_available=True,
            )
        else:
            updated = self.transition(
                record,
                state=state,
                execution=execution,
                files=status.files if status.files is not None else _UNCHANGED,
                return_code=return_code,
                message=status.message,
                failure_phase=phase,
            )
        self._acknowledge_submission(self.executor_for(updated), updated)
        self._acknowledge_result(updated)
        return updated

    def complete(
        self,
        record,
        *,
        state,
        execution=None,
        return_code=None,
        message=None,
        failure_phase=None,
        artifacts_available=False,
        files=None,
        expected_record=None,
        expected_processing_attempt=None,
    ):
        state = RunState(state)
        phase = _failure_phase(failure_phase)
        result_files = record.files if files is None else files

        if result_files is not None and result_files.failed_artifacts:
            artifacts_available = False
            if state == RunState.FINISHED or phase == FailurePhase.POSTPROCESSING:
                # The successful backend does not excuse a required download
                # failure; the failed file retains the specific diagnostics.
                state = RunState.FAILED
                phase = (
                    FailurePhase.DOWNLOAD if record.execution.directory.remote is not None else FailurePhase.ARTIFACTS
                )
                message = result_files.availability_message or message

        if artifacts_available and result_files is not None:
            try:
                result_files = self._capture_result_files(result_files)
            except OSError as exc:
                state = RunState.FAILED
                phase = FailurePhase.ARTIFACTS
                message = str(exc)
                result_files = result_files._map_artifacts(
                    lambda item: (
                        replace(
                            item,
                            availability_state="failed",
                            availability_message=message,
                        )
                        if item.availability_state in (None, "pending")
                        else item
                    )
                )

        if (
            result_files is not None
            and result_files.failed_artifacts
            and state in (RunState.FINISHED, RunState.POSTPROCESSING)
        ):
            state, phase = RunState.FAILED, FailurePhase.ARTIFACTS
            message = result_files.availability_message or message

        updated = self.transition(
            record,
            state=state,
            execution=execution,
            return_code=return_code,
            message=message,
            failure_phase=phase,
            files=result_files,
            expected_record=expected_record,
            expected_processing_attempt=expected_processing_attempt,
        )
        self._acknowledge_result(updated)
        return updated

    def resume_download(self, run):
        """Explicitly reopen a failed post-execution transfer for retry.

        This is not an execution resubmit. The original backend handle remains
        authoritative and the attached raw runner replays/synchronizes files
        before task postprocessing can finish.
        """
        record = self.store.get(run) if isinstance(run, str) else self.store.get(run.id)

        def reopen(latest):
            if (
                latest.state != RunState.FAILED
                or latest.failure_phase != FailurePhase.DOWNLOAD
                or latest.return_code != 0
                or latest.execution.backend_id is None
                or latest.files is None
                or latest.files.captured_at is not None
            ):
                raise ValueError("Only failed downloads of successful backend jobs can be retried")
            # Keep already transferred artifacts and all bytes on disk.
            # Only failed transfers become eligible for a fresh attempt.
            files = latest.files._map_artifacts(
                lambda item: (
                    replace(
                        item,
                        availability_state="pending",
                        availability_message=None,
                    )
                    if item.availability_state == "failed"
                    else item
                )
            )
            return replace(
                latest,
                state=RunState.DOWNLOADING,
                finished_at=None,
                failure_phase=None,
                message=None,
                files=files,
                updated_at=_now(),
            )

        return self.store.update(record, reopen)

    def _process_outcome(self, record, outcome, process_result, *, files=None, execution=None, retry=False):
        """Claim processing until its durable completion, including across clients.

        All clients of a store must share its filesystem lock namespace. The OS
        releases this lock when a client dies; POSTPROCESSING then remains
        attachable/retryable. A live owner is never displaced by a timeout.
        """
        lock = self.store.processing_lock(record)
        if not lock.acquire(blocking=False):
            raise ProcessingPending("Another client owns postprocessing")
        try:
            latest = self.store.get(record.id)
            if latest.state == RunState.FINISHED:
                # A different observer already completed it; no second callback.
                raise ProcessingPending("Result already processed by another observer; load its historical result")
            if latest.state.is_terminal and not (
                retry and latest.state == RunState.FAILED and latest.failure_phase == FailurePhase.POSTPROCESSING
            ):
                raise RuntimeError("Run is already terminal")
            manifest = latest.files if files is None else files
            if latest.files.captured_at is not None:
                manifest = latest.files
            manifest = self._capture_result_files(manifest)
            if manifest.failed_artifacts:
                raise OSError(manifest.availability_message or "Output artifacts unavailable")
            if any(v.state() is not FileState.CURRENT for v in manifest.output_versions):
                if retry:
                    raise ValueError("Postprocessing retry requires unchanged historical artifacts")
                raise OSError("Historical artifacts changed before postprocessing")

            def claim(current):
                if current.state.is_terminal and not (
                    retry and current.state == RunState.FAILED and current.failure_phase == FailurePhase.POSTPROCESSING
                ):
                    raise ProcessingPending("Run completed before processing claim")
                return replace(
                    current,
                    state=RunState.POSTPROCESSING,
                    files=manifest,
                    processing_attempt=uuid4().hex,
                    updated_at=_now(),
                    finished_at=None,
                    failure_phase=None,
                    message=None,
                    return_code=outcome.return_code,
                    execution=current.execution if execution is None else execution,
                )

            claimed = self.store.update(latest, claim)
            if process_result is None:
                raise ProcessingPending("Postprocessing requires a client callback")
            try:
                result = process_result(outcome)
                if any(v.state() is not FileState.CURRENT for v in manifest.output_versions):
                    raise RuntimeError("Historical artifacts changed during postprocessing retry")
            except BaseException as exc:
                self.complete(
                    claimed,
                    state=RunState.FAILED,
                    return_code=outcome.return_code,
                    message=str(exc),
                    failure_phase=FailurePhase.POSTPROCESSING,
                    expected_processing_attempt=claimed.processing_attempt,
                )
                raise
            self.complete(
                claimed,
                state=RunState.FINISHED,
                return_code=outcome.return_code,
                files=manifest,
                expected_processing_attempt=claimed.processing_attempt,
            )
            return result
        finally:
            lock.release()

    def retry_postprocessing(self, run, process_result):
        """Retry a failed or interrupted processing attempt without rerunning a job."""
        from .base import ExecutionOutcome

        record = self.store.get(run) if isinstance(run, str) else self.store.get(run.id)
        if (
            not record.processing_required
            or record.return_code != 0
            or not (
                record.state == RunState.POSTPROCESSING
                or (record.state == RunState.FAILED and record.failure_phase == FailurePhase.POSTPROCESSING)
            )
        ):
            raise ValueError("Only postprocessing failures or interrupted processing can be retried")
        files = record.files
        if files.captured_at is None:
            raise ValueError("Postprocessing retry requires captured artifacts")
        outcome = ExecutionOutcome(
            input_file=(
                files.input_file if self._file_is_current(files, files.input_file, files.input_versions) else None
            ),
            output_file=files.output_file,
            error_file=None if files.stderr is None else files.stderr.local_path,
            return_code=record.return_code,
        )
        return self._process_outcome(record, outcome, process_result, retry=True)

    def retrieve_result_files(self, run):
        record = self.store.get(run) if isinstance(run, str) else self.store.get(run.id)
        if not record.state.is_terminal:
            raise RuntimeError(f"Run {record.id} is not finished")

        missing = self._missing_result_files(record.files)
        if not missing or record.execution.backend_id is None:
            return record

        executor = self.executor_for(record)
        if not executor.supports_result_file_retrieval:
            return record

        versions = {
            os.path.abspath(os.fspath(version.path)): version
            for version in (() if record.files is None else record.files.all_versions)
        }
        for path in missing:
            path = os.path.abspath(os.fspath(path))
            version = versions.get(path)
            staged = (
                Path(path).with_name(f".{Path(path).name}.{uuid4().hex}.tmp")
                if version is not None and version.digest is not None
                else None
            )
            try:
                if staged is None:
                    executor.fetch_result_files(record, (path,))
                else:
                    executor.fetch_result_files(
                        record,
                        (path,),
                        destinations={path: os.fspath(staged)},
                    )
                    if not staged.is_file():
                        raise FileNotFoundError(f"Historical artifact was not retrieved: {path}")
                    if file_digest(staged) != version.digest:
                        raise HistoricalFileMismatchError(f"Historical result files have been overwritten: {path}")
                    os.replace(staged, path)
            except OSError as exc:
                self.update_artifact_availability(
                    record,
                    path,
                    ArtifactAvailabilityState.FAILED,
                    str(exc),
                )
                raise
            finally:
                if staged is not None:
                    staged.unlink(missing_ok=True)
            refreshed = self.store.get(record.id)
            if path in self._missing_result_files(refreshed.files):
                record = self.update_artifact_availability(
                    refreshed,
                    path,
                    ArtifactAvailabilityState.FAILED,
                    "Historical artifact is still missing",
                )
            else:
                record = self.update_artifact_availability(
                    refreshed,
                    path,
                    ArtifactAvailabilityState.AVAILABLE,
                )
        return record

    def _acknowledge_result(self, record):
        """Best-effort ACK after durable completion; failed ACKs remain retryable."""
        if not record.state.is_terminal or record.execution.backend_id is None:
            return False
        if record.failure_phase == FailurePhase.DOWNLOAD and record.return_code == 0:
            # Retry will reattach to download preserved output. Retain the
            # terminal backend receipt until that end-to-end attempt settles.
            return False
        key = (record.id, record.execution.backend_id)
        with self._ack_lock:
            if key in self._acknowledged_results:
                return True
            try:
                executor = self.executor_for(record)
                acknowledge = getattr(executor, "acknowledge", None)
                if acknowledge is not None:
                    acknowledge(record)
            except (OSError, RuntimeError, ValueError, NotImplementedError):
                return False
            self._acknowledged_results.add(key)
            return True

    def reconcile_acknowledgements(self):
        """Retry idempotent result ACKs for durable terminal records."""
        return tuple(record.id for record in self.store.runs(active=False) if self._acknowledge_result(record))

    @staticmethod
    def _acknowledge_submission(executor, record):
        """Discard the temporary backend PID only after RunStore is durable."""
        if record.execution.backend_id is None:
            return
        acknowledge = getattr(executor, "acknowledge_submission", None)
        if acknowledge is not None:
            try:
                acknowledge(record)
            except (OSError, RuntimeError):
                # The receipt remains recoverable until a subsequent refresh.
                pass

    @staticmethod
    def _complete(project_run, result, callback):
        project_run._sync_completion(result)
        if (
            project_run.record.state == RunState.FINISHED
            and project_run.record.processing_required
            and project_run._runner.state != RunState.FINISHED
        ):
            # Another observer finished while this one lost backend observation.
            # Completion notification must not substitute a raw application result.
            result = None
            project_run._runner.result = None
        if callback is not None:
            # Completion of observation, including UNKNOWN, is notification.
            # It is not proof that the backend calculation finished.
            callback(result)

    def create_run(
        self,
        executor,
        spec,
        *,
        process_result=None,
        metadata=None,
        processing_required=None,
        callback=None,
        run_id=None,
    ):
        """Create a project run from raw execution plus generic processing."""
        if processing_required is False and process_result is not None:
            raise ValueError("A result callback requires processing_required=True")
        endpoint = endpoint_for_executor(executor)
        record = self.new_record(
            metadata=metadata,
            processing_required=(process_result is not None if processing_required is None else processing_required),
            directory=spec.directory,
            endpoint=endpoint,
            remote_directory=(executor.submission_directory(spec) if endpoint.executor == "ssh" else None),
            files=FileManifest.from_spec(spec),
            run_id=run_id,
        )
        self.register_executor(executor, endpoint)

        raw = executor.create_project_run(spec, run_id=record.id)
        # The manifest is owned by RunRecord. Local execution observes its
        # publication outcomes, without persisting an independent file list.
        set_manifest = getattr(raw, "set_manifest", None)
        if set_manifest is not None:
            set_manifest(record.files)
        processor = None
        if record.processing_required:

            def processor(outcome):
                return self._process_outcome(
                    record,
                    outcome,
                    process_result,
                    files=getattr(raw, "files", None),
                    execution=(getattr(raw, "execution", None) or record.execution.submitted(raw.backend_id)),
                )

        processed = PostprocessingRunner(raw, processor)
        project_run = ProjectRunner(self, executor, processed, record)
        processed.callback = lambda result: self._complete(project_run, result, callback)
        return project_run

    def refresh(self, records=None):
        self.reconcile_acknowledgements()
        records = tuple(self.store.runs(active=True) if records is None else records)
        current = {record.id: record for record in records}
        groups = {}
        for record in records:
            if record.execution.backend_id is None:
                continue
            executor = self.executor_for(record)
            groups.setdefault(executor, []).append(record)

        for executor, group in groups.items():
            statuses = executor.status(*group)
            if len(statuses) != len(group):
                raise RuntimeError("Executor returned wrong number of run statuses")
            for record, status in zip(group, statuses):
                current[record.id] = self.update(record, status)
        return tuple(current[record.id] for record in records)

    def attach(
        self,
        run,
        *,
        process_result=None,
        executor=None,
        callback=None,
        output_listener=None,
    ):
        """Attach raw execution, then resume client-side postprocessing."""
        record = self.store.get(run) if isinstance(run, str) else self.store.get(run.id)
        if record.state.is_terminal:
            raise RuntimeError("Run is already terminal; load its historical result or use an explicit retry")
        if process_result is not None and not record.processing_required:
            raise ValueError("This run did not request postprocessing")
        if record.execution.backend_id is None:
            raise RuntimeError(f"Run {record.id} has no backend reference")
        if executor is None:
            executor = self.executor_for(record)
        else:
            endpoint = record.execution.endpoint
            self.register_executor(executor, endpoint)

        raw = executor.attach(
            record,
            output_listener=output_listener,
            start=False,
        )
        processor = None
        if record.processing_required:

            def processor(outcome):
                return self._process_outcome(
                    record,
                    outcome,
                    process_result,
                    files=getattr(raw, "files", None),
                    execution=(getattr(raw, "execution", None) or record.execution.submitted(raw.backend_id)),
                )

        processed = PostprocessingRunner(raw, processor)
        project_run = ProjectRunner(self, executor, processed, record)
        processed.callback = lambda result: self._complete(project_run, result, callback)
        project_run.start()
        return project_run


class ProjectRunner:
    """Caller-owned runner that persists the public lifecycle directly."""

    def __init__(self, manager, executor, runner, record):
        self.manager = manager
        self.executor = executor
        self._runner = runner
        self._record = record
        self._completion_lock = Lock()
        self._completion_persisted = False
        self._monitor_record_version = record.updated_at

    @property
    def id(self):
        return self._record.id

    @property
    def record(self):
        return self._record

    @property
    def result(self):
        return self._runner.result

    @property
    def backend_id(self):
        return self._runner.backend_id

    @property
    def execution(self):
        proposed = getattr(self._runner, "execution", None)
        if proposed is not None:
            return proposed
        if self.backend_id is None:
            return None
        return self._record.execution.submitted(self.backend_id)

    @property
    def files(self):
        return getattr(self._runner, "files", None)

    @property
    def exception(self):
        return self._runner.exception

    @property
    def failure_phase(self):
        return _failure_phase(getattr(self._runner, "failure_phase", None))

    @property
    def state(self):
        """Observe runner state without persisting a transition."""
        state = self._runner.state
        if state == RunState.NEW and self._record.state != RunState.NEW:
            return self._record.state
        if state == RunState.UNKNOWN and self._record.state != RunState.NEW:
            # The completed observer cannot overwrite a newer refresh.
            return self._record.state
        return self._record.state if self._record.state.is_terminal else state

    def add_output_listener(self, callback):
        return self._runner.add_output_listener(callback)

    def add_output_error_listener(self, callback):
        return self._runner.add_output_error_listener(callback)

    def submit(self):
        if self._record.state != RunState.NEW:
            raise RuntimeError(f"Run is already {self._record.state.value}")
        resolve = getattr(self.executor, "resolve_submission", None)
        if resolve is not None:
            self._record = resolve(self._record, self._runner.spec)
        self._record = self.manager.reserve(self._record)
        self._monitor_record_version = self._record.updated_at
        try:
            prepare = getattr(self._runner, "prepare_submission", None)
            if prepare is not None and prepare():
                # Persist the exact staged file map and target directory before
                # calling the backend. A lost submit reply can then be recovered
                # without depending on live runner state.
                self._record = self.manager.transition(
                    self._record,
                    execution=self.execution,
                    files=self.files if self.files is not None else _UNCHANGED,
                )
                self._monitor_record_version = self._record.updated_at
            result = self._runner.submit()
        except SubmissionNotStarted as exc:
            phase = self.failure_phase or FailurePhase.SUBMISSION
            message = getattr(self._runner, "failure_message", None) or str(exc)
            self._record = self.manager.complete(
                self._record,
                state=RunState.FAILED,
                message=message,
                failure_phase=phase,
                artifacts_available=False,
            )
            raise
        except BaseException:
            # No backend ID means submission may be uncertain. Keep SUBMITTING so
            # recover_submitting() can resolve it instead of inventing failure.
            backend_id = self.backend_id
            if backend_id is not None:
                self._record = self.manager.transition(
                    self._record,
                    state=self._runner.state,
                    execution=self.execution,
                    failure_phase=self.failure_phase,
                )
            raise

        backend_id = self.backend_id
        if backend_id is None:
            raise RuntimeError("Executor submit returned without a backend ID")
        self.manager.register_executor(self.executor, self._record.execution.endpoint)
        with self._completion_lock:
            # A fast monitor may have already persisted an UNKNOWN or
            # terminal result. Do not overwrite that result with an older
            # status observed during submission.
            if not self._completion_persisted:
                self._record = self.manager.transition(
                    self._record,
                    state=self._runner.state,
                    execution=self.execution,
                    failure_phase=self.failure_phase,
                    files=self.files if self.files is not None else _UNCHANGED,
                )
                self._monitor_record_version = self._record.updated_at
        self.manager._acknowledge_submission(self.executor, self._record)
        return result

    def start(self):
        self._runner.start()
        with self._completion_lock:
            # An attached PSI/J job can initially report NEW before the
            # scheduler provides its actual state.
            state = self._runner.state
            if not self._completion_persisted and self.backend_id is not None and state != RunState.NEW:
                self._record = self.manager.transition(
                    self._record,
                    state=state,
                    execution=self.execution,
                    failure_phase=self.failure_phase,
                )
                self._monitor_record_version = self._record.updated_at

    def _sync_completion(self, result):
        # Callback and wait() can reach this path concurrently. Only the
        # first successful durable completion may publish and acknowledge it.
        with self._completion_lock:
            if self._completion_persisted:
                return
            latest = self.manager.store.get(self.id)
            if latest.state.is_terminal:
                self._record = latest
                self._completion_persisted = True
                self.manager._acknowledge_result(latest)
                return
            state = self._runner.state
            phase = self.failure_phase
            message = getattr(self._runner, "failure_message", None)
            error = self._runner.exception
            if message is None and error is not None:
                message = str(error)
            if state == RunState.UNKNOWN:
                # The observer ended, not necessarily the calculation.
                # No final artifact publication or completion timestamp.
                self._record = self.manager.transition(
                    self._record,
                    state=state,
                    execution=self.execution,
                    message=message,
                    expected_updated_at=self._monitor_record_version,
                )
                self._completion_persisted = True
                return
            if not state.is_terminal:
                return
            if state == RunState.FAILED and phase is None:
                phase = FailurePhase.EXECUTION

            artifacts_available = phase not in _NO_ARTIFACTS_FAILURES
            self._record = self.manager.complete(
                self._record,
                state=state,
                execution=self.execution,
                return_code=getattr(self._runner, "return_code", None),
                message=message,
                failure_phase=phase,
                artifacts_available=artifacts_available,
                files=self.files,
            )
            if self._record.state.is_terminal:
                self._completion_persisted = True

    def wait(self):
        try:
            result = self._runner.wait()
        finally:
            if self._record.state != RunState.NEW:
                self._sync_completion(self.result)
        if (
            self._record.state == RunState.FINISHED
            and self._record.processing_required
            and self._runner.state != RunState.FINISHED
        ):
            raise ProcessingPending("Result was processed by another observer; load its historical result")
        return result

    def run(self):
        if self._record.state == RunState.NEW:
            self.submit()
        return self.wait()

    async def run_async(self):
        return await asyncio.to_thread(self.run)

    def refresh(self):
        with self._completion_lock:
            self._record = self.manager.refresh((self._record,))[0]
            return self._record

    def stop_observation(self):
        """Detach this client without cancelling its still-running job.

        The completion callback persists a recoverable UNKNOWN observation.
        Call wait() to ensure the monitor has finished and been detached.
        """
        return self._runner.stop_observation()

    def cancel(self):
        try:
            return self._runner.cancel()
        finally:
            with self._completion_lock:
                if self._record.state != RunState.NEW and not self._completion_persisted:
                    self._record = self.manager.transition(
                        self._record,
                        state=self._runner.state,
                        execution=self.execution,
                        failure_phase=self.failure_phase,
                    )


# Compatibility name: the project-free API is explicitly RunManager.
ExecutionManager = RunManager
