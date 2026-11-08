Declare the file footprint
============================

The manifest is the complete declaration of what a run may read or write.
KKRunner reserves these paths before staging or opening outputs. It does not
reserve a whole directory merely because two calculations share it.

``input_file`` is the primary input; ``stdin`` is a separate read declaration.
``output_file`` and ``error_file`` are stdout/stderr destinations. Use
``input_files`` and ``output_files`` for other files, and ``cache_files`` for
files read and potentially rewritten by the executable.

.. testcode::

   import sys
   import tempfile
   from pathlib import Path
   from kkrunner import ExecutionSpec, FileManifest, TaskFile

   workspace = tempfile.TemporaryDirectory()
   directory = Path(workspace.name)
   (directory / "input.txt").write_text("input")
   spec = ExecutionSpec(
       [sys.executable, "-c", "print('example')"],
       directory=directory,
       input_file=directory / "input.txt",
       output_file=directory / "stdout.txt",
       output_files=(TaskFile(directory / "optional.log", optional=True),),
       cache_files=(directory / "cache.bin",),
   )
   manifest = FileManifest.from_spec(spec)
   print(len(manifest.inputs), len(manifest.outputs), len(manifest.caches))
   print(manifest.outputs[0].optional)

.. testoutput::

   1 1 1
   True

.. testcleanup::

   workspace.cleanup()

``TaskFile`` is immutable. Its ``type`` and ``info`` strings belong to the
application; KKRunner does not look up scientific formats. Applications must
resolve pathname templates and callbacks before handing a concrete execution
specification to the runner. A callback returning ``None`` means no declaration;
an optional declared file may be absent after successful execution.

Reservations
--------------

Two active runs may read the same file. A write conflicts with another run's
read or write. Cache declarations participate in both roles. Local uploads,
download destinations and streamed output paths are checked independently of
the backend. Remote paths are also checked in their target filesystem namespace.
A :class:`~kkrunner.DuplicateSubmissionError` reports an active conflict.

For host aliases or shared mounts, supply the same ``filesystem_id`` to
:class:`~kkrunner.RemoteEndpointExecutor`. KKRunner does not infer shared mounts
from different hostnames. Distinct IDs declare distinct target filesystems.

Transfers and captured contents
---------------------------------

:class:`~kkrunner.LaunchSpec` provides the local/remote roots and transfer
policies. ``changed`` transfers differing contents; ``always`` transfers every
existing source; ``missing`` fills only missing destinations; ``never`` disables
that transfer direction. Missing required inputs remain errors.

Successful durable completion captures file versions and SHA-256 digests.
Historical applications should verify captured files before interpreting them.
:class:`~kkrunner.HistoricalFileMismatchError` indicates that historical content
was replaced. A missing required local output is an ``ARTIFACTS`` failure;
a failed remote transfer is a ``DOWNLOAD`` failure. Optional missing outputs
are recorded as skipped.
