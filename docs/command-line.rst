Command-line interface
======================

The installed ``kkrunner`` executable provides the target-side execution
protocol directly, without a ``remote`` prefix:

.. code-block:: console

   kkrunner --help
   kkrunner status HANDLE
   kkrunner follow HANDLE --live
   kkrunner cancel HANDLE

These three user-facing commands select the installed control protocol version
automatically. Execution clients supply ``--protocol-version`` explicitly.
For example:

.. code-block:: console

   kkrunner --protocol-version VERSION submit DIRECTORY
   kkrunner --protocol-version VERSION query-files
   kkrunner --protocol-version VERSION finalize-upload

Other internal actions are ``recover``, ``ack-submit``, ``ack``,
and ``resolve-mpi``. They also require an explicit protocol version.
Submission and recovery read JSON requests from stdin. Status and
acknowledgements return JSON; framed follow multiplexes stdout, stderr and a
terminal record. Use the Python executor API for normal submissions instead
of constructing protocol messages manually.

These commands run on the machine where they execute. For a remote handle,
run them on the target, for example through SSH. ``follow`` replays output
from byte offset zero by default; ``--live`` requests only new output.
It accepts separate stdout/stderr offsets and ``--framed`` for binary
multiplexing.

The CLI lives in a separate Python package, ``kkrunner_cli``. Help and
argument parsing do not import the execution library or backend modules.
