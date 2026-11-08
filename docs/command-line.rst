Command-line interface
========================

``kkrunner`` is the installed command. Its ``remote`` subcommand runs the
target-side execution protocol:

.. code-block:: console

   kkrunner remote --help

Execution clients supply ``--protocol-version`` explicitly. The commands are
``submit``, ``status``, ``follow``, ``cancel``, ``recover``, ``ack-submit``, ``ack``
and ``resolve-mpi``. Submission and recovery read JSON requests from stdin.
Status and acknowledgements return JSON; framed follow multiplexes stdout,
stderr and a terminal record. Use the Python executor API for normal submissions
instead of constructing these messages manually.

Manual inspection
-------------------

When inspecting a known handle with KKRunner directly, pass the installed control
protocol version (available as ``CONTROL_PROTOCOL_VERSION`` in the remote protocol
module):

.. code-block:: console

   kkrunner remote --protocol-version VERSION status HANDLE
   kkrunner remote --protocol-version VERSION follow HANDLE
   kkrunner remote --protocol-version VERSION cancel HANDLE

These commands operate on the machine where they execute. For a remote handle,
run them on the target, for example through SSH. ``follow`` replays output from
byte offset zero by default; ``--live`` requests only new output. It accepts
separate stdout/stderr offsets and ``--framed`` for binary multiplexing.
