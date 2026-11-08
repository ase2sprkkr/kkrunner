Persistent runs and recovery
==============================

Use :class:`~kkrunner.RunManager` with an explicit :class:`~kkrunner.RunStore`
when persistence does not require projects. A managed runner writes one
:class:`~kkrunner.RunRecord` containing identity, execution facts, file manifest,
metadata and lifecycle state. The backend stores submission/outcome receipts;
it does not own the end-to-end run record.

The manager returns a :class:`~kkrunner.PersistentRunner`. Project membership is
optional, and one store can contain runs belonging to different projects as
well as runs with no project.

.. testcode::

   import sys
   import tempfile
   from pathlib import Path
   from kkrunner import (
       ExecutionSpec, LocalExecutor, ProcessingPending, RunManager, RunStore,
   )

   workspace = tempfile.TemporaryDirectory()
   directory = Path(workspace.name)
   manager = RunManager(RunStore(directory / "runs"))
   run = manager.create_run(
       LocalExecutor(),
       ExecutionSpec(
           [sys.executable, "-c", "print(43)"],
           directory=directory,
           output_file=directory / "stdout.txt",
       ),
       processing_required=True,
       metadata={"example": {"parser": "integer"}},
   )
   try:
       run.run()
   except ProcessingPending:
       print(manager.store.get(run.id).state.value)

   # Recreate the client; the processor is application-owned and not persisted.
   resumed = RunManager(RunStore(directory / "runs"))
   attached = resumed.attach(
       run.id,
       process_result=lambda outcome: int(Path(outcome.output_file).read_text()),
   )
   print(attached.wait())
   print(resumed.store.get(run.id).state.value)

.. testoutput::

   postprocessing
   43
   finished

.. testcleanup::

   workspace.cleanup()

Result processing
-------------------

``process_result`` consumes an :class:`~kkrunner.ExecutionOutcome` and returns
an application result. It is separate from the completion-notification callback.
``processing_required=True`` allows supplying the processor after reconnect.
If the processor is unavailable or another client owns/performed processing,
``wait()`` raises :class:`~kkrunner.ProcessingPending`; it must not substitute a
raw outcome for the application's result type.

Processing ownership uses an OS lock and a persisted attempt token. Observing
or refreshing a record does not take ownership. A crash can cause a later
explicit retry to repeat application side effects, so processors should be
idempotent or use their own transactions. Exactly-once external side effects
are not guaranteed. The returned Python object is not serialized in the record;
applications reconstruct historical results from metadata and verified files.

Lifecycle and recovery decisions
----------------------------------

The normal sequence is ``new -> submitting -> queued/running -> downloading``
when needed, then ``postprocessing`` when required, then ``finished``.
``failed`` and ``cancelled`` are terminal. ``unknown`` means observation is
uncertain; it is not evidence that the backend stopped.

* ``run.stop_observation()`` detaches this observer without cancelling execution.
* ``run.cancel()`` requests backend cancellation.
* ``manager.refresh()`` reconciles backend facts and durable terminal receipts.
* ``manager.attach(id, process_result=...)`` resumes a nonterminal run.
* ``manager.resume_download(id)`` reopens a recoverable failed download; attach
  afterward to resume transfer and completion.
* ``manager.retry_postprocessing(id, processor)`` retries failed/interrupted
  processing without submitting the command again.

Do not attach a terminal record. Load its historical application result, or use
the explicit retry operation for a supported failure phase. A recoverable failed
download retains its backend outcome receipt until retry settles. Other terminal
outcomes are acknowledged after the durable state is committed; refresh can
retry a lost acknowledgement.

Recovery after a crash during submission depends on the backend. See
:ref:`backend-recovery` for the distinction between reconnecting with a known
backend ID and discovering a submission whose ID was never saved.

Store and metadata contracts
------------------------------

``RunStore.save`` creates a globally unique ID or repeats an identical save.
Use its atomic update API for subsequent changes. A date shard does not create
a separate ID namespace. Invalid or duplicate records raise
:class:`~kkrunner.CorruptRunRecord`; they are not silently ignored.

Metadata is namespaced JSON data, recursively immutable after record creation.
It cannot change run identity, choose parsers, or execute code. Put the
application's reconstruction parameters in its namespace and keep executable
callbacks in the application process.
