Installation
==============

KKRunner supports Python 3.9 and newer. The core depends on ``platformdirs``;
scheduler support and documentation tools are optional extras.

For this development alpha, install from a KKRunner checkout or a supplied
wheel. From the root of the checkout:

.. code-block:: console

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install .

This installs a copy of the package. If you are editing its source, use
``python -m pip install --editable .`` instead; changes to Python files then
apply without reinstalling. To install a supplied wheel, pass its pathname
to ``python -m pip install``.

For PSI/J scheduler backends, install the extra:

.. code-block:: console

   python -m pip install '.[psij]'

For documentation dependencies and the local HTML build, see
:ref:`build-documentation`.

For SSH execution, install the same KKRunner version on the target and make
``kkrunner remote`` available to noninteractive SSH commands. An absolute
command can be supplied as ``("/opt/kkrunner/bin/kkrunner", "remote")``.
Scheduler execution needs the PSI/J extra and a configured scheduler on the
execution host. MPI execution needs a compatible MPI launcher there.

Platforms
-----------

Managed local execution and the direct-process remote service currently require
Linux: their process identity check reads ``/proc/<pid>/stat``. macOS has Unix
sockets and process groups, but this identity check has not been ported there.

macOS CI covers installation, the CLI, raw local execution, transport and file/run
models on Apple Silicon and Intel. It does not cover the durable local supervisor
or a macOS execution target. Raw local execution has no restart guarantee; an
SSH client can submit to a supported execution host and needs the system ``ssh``
executable. A client does not need ASE or scientific parsers even when the
application that submitted its runs uses them.
