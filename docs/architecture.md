# Execution boundary and public contract

KKRunner owns ExecutionSpec/ExecutionOutcome, TaskFile, ExecutorEndpoint,
RunState/FailurePhase, Execution/WorkingDirectory, RunRecord/RunStore,
FileEntry/FileMapping/FileManifest, FileState/FileVersion/FileFingerprint,
ExecutionResources and ResourceOwnedRunner. Public exports live in `kkrunner`.
`RunManager` tracks runs in an explicit RunStore without requiring a project.
`ProjectExecutionManager` and ProjectRepository organize runs in projects.
Both managers use the same lifecycle. Each public class has one name that
describes its role.

Applications own input preparation, executable selection, file-template
resolution, parsers, result types and their own metadata namespace. KKRunner
depends only on platformdirs, plus optional psij-python.

TaskFile is an immutable declaration. Its `type` and `info` are opaque strings;
KKRunner does not resolve application templates or consult format registries.
FileEntry is a resolved persistent location plus transfer/publication state.
FileManifest owns the authoritative declarations, cache baselines and captured
versions. `input_file` identifies the main input for tracking and transfer;
`stdin` selects the file connected to the process's standard input.
Read/write conflicts derive exclusively from the manifest; task names
have no locking meaning. Clients must declare every read/write/cache footprint.

RunRecord owns persistent run identity, backend identity, manifest, namespaced
JSON metadata, `processing_required` and the latest processing-attempt ID.
Metadata is recursively immutable and cannot change through RunStore.update.
RunStore.save creates a globally unique ID (or repeats an identical save); all
subsequent changes use its atomic update API. Date sharding does not permit
multiple records with the same ID.
RunRecord schema_version is 1 throughout pre-release development, even when
its structure changes. Only the current shape is accepted. Development records
are not migrated. Earlier record formats are unsupported; copying their JSON
into the current store raises CorruptRunRecord. User configuration
and Project generation/versioning are separate contracts.

Lifecycle: new -> submitting -> queued/running -> downloading (if required) ->
postprocessing (if required) -> finished. Any phase can fail or be cancelled as
supported by the backend. UNKNOWN is recoverable uncertainty, never completion.
Download and processing failures can be explicitly reopened without resubmission.
When processing is required but its callback is unavailable or another observer
owns it, the run remains POSTPROCESSING and wait() raises ProcessingPending.
It never returns a raw outcome as a substitute for the application result.
The callback return object is not persisted; historical applications reconstruct
it from the recorded application metadata and verified files.

Postprocessing claims a per-run filesystem lock, captures/verifies artifacts,
publishes the attempt, calls the processor and commits success/failure before
releasing ownership. Other clients may monitor but cannot process concurrently.
OS lock release after process death makes an interrupted POSTPROCESSING attempt
recoverable. A live owner is never displaced based on a timeout. All clients of
a store must share the same reliable file-locking namespace. Callbacks may be
repeated after a crash and must tolerate that (idempotence or transactional side
effects); exactly-once side effects are not promised.

Backend facts and durable submission/outcome receipts are not a second run
record. RunRecord remains the authority for end-to-end completion. All completion paths share the same durable commit and result ACK.
RunManager.refresh also reconciles terminal receipts; the explicit
reconcile_acknowledgements() method retries lost ACKs without changing outcomes.
Recoverable download failures retain their backend outcome receipt until retry
finishes; otherwise a later attach would lose authoritative backend completion. JSON writes use atomic replacement, file and directory
fsync on POSIX; portable Windows directory durability is weaker as documented
in `kkrunner.support.durability`. Invalid records raise errors, including during enumeration.

Callers own the streams and resources they supply. To transfer their lifetime
to a run, wrap its runner in ResourceOwnedRunner with ExecutionResources. The
wrapper closes owned resources on completion and when submission is cancelled
before launch. Borrowed handles retain their existing ownership semantics.
Managed execution uses file paths on the execution host; the supervisor owns
process lifetime beyond client detach.
Temporary directories must remain available for backend execution and processing;
clients must not delete them on mere loss of observation.

The target-side protocol command is `kkrunner remote`; it rejects incompatible
control protocol versions. A remote host needs KKRunner and the desired
executable, plus PSI/J for scheduler use. Application-specific command wrappers
belong to the application; the protocol implementation remains in KKRunner.

Application-specific preparation and historical result loading stay outside the
runner. Applications retain their own parser and result-format registries and
reconstruct results from namespaced metadata and verified files. They must retain
working directories and artifacts for as long as execution or processing needs
them. See the application guide for its storage policy and temporary-file rules.

## Reservations and filesystems

For runs managed through the same RunStore, submission reserves declared file
paths until the run reaches a terminal state. This applies with or without
projects; raw executor runs do not take these reservations.

Before reservation the remote executor resolves absolute target paths without
staging or opening outputs. Only after the complete footprint has been durably
reserved may uploads and submission begin. Reservations check local read/write
paths (including uploads and downloaded/streamed results) independently of the
backend, and check the target filesystem as well. Local process and local PSI/J
therefore share the local filesystem namespace. SSH connections to the same
host share a target namespace regardless of SSH flags, remote command or backend.

For host aliases or shared mounts, pass filesystem_id to RemoteEndpointExecutor
or ExecutorEndpoint. Matching IDs declare one shared target filesystem; distinct
IDs declare distinct ones. A client must use the same identity consistently.
The API does not infer that different host aliases refer to the same mount.

Required output files must exist after successful execution. A missing optional
output is skipped; a missing required local output is an ARTIFACTS failure.
A transfer failure remains a DOWNLOAD failure. The backend's return code remains
an execution fact and is not changed to conceal an artifact/processing failure.

## Completion callbacks and platform support

A completion callback may call its own runner's wait() to inspect the result;
this does not wait for the callback itself. Other waiters still await callback
completion and receive its exception. Required processing is a separate callback
from this observation-completion notification.

Managed local execution and the direct-process remote service currently require
Linux because their process identity check reads `/proc/<pid>/stat`. They reject
unsupported platforms before launching a process. macOS has Unix sockets and
process groups; the missing piece is a port of the identity check and validation
of durable supervision. CI covers the macOS client and raw local execution.
Windows-specific locking/durability code alone does not imply support for a
managed local supervisor on Windows.

## Package ownership

| Package | Responsibility |
| --- | --- |
| `kkrunner.runs` | Run contracts, execution identity, immutable metadata, durable records, reservations and processing lifecycle. |
| `kkrunner.backends` | Local and PSI/J implementations, endpoint identity, MPI launch and reusable executor pools. |
| `kkrunner.remote` | Remote runner and executor, transports, wire framing, target service, receipts and worker supervision. |
| `kkrunner.projects` | Project repository, project-bound manager and explicit project-manager resolution. |
| `kkrunner.files` | TaskFile, manifests, transfer policy, pathname declarations, captured versions and artifact availability. |
| `kkrunner.support` | Shared durability, locking, asynchronous and growing-stream utilities. |

The root package exports the principal types from their defining modules;
it does not implement a second API or provide compatibility classes. Imports
inside the implementation use their defining modules. The former flat module
paths are removed. The remote worker starts as `kkrunner.remote.worker`.

`files` and `support` do not import the run lifecycle, projects, backends or
remote service. File reservations use generic local path expansion without
importing a transport. The manifest and execution identity are separate models.
`runs` owns persistence and end-to-end completion; backend implementations report
execution facts. `projects` adds project membership to that existing lifecycle.
A scheduler job is the backend part of a run, while a run also includes staging,
transfer and any required result processing.
