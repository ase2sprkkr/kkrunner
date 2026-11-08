Installation
==============

KKRunner supports Python 3.9 and newer. The core depends on ``platformdirs``;
PSI/J and documentation tools are optional extras.

.. code-block:: console

   python -m pip install kkrunner
   python -m pip install 'kkrunner[psij]'  # Slurm, PBS and other PSI/J backends

For source development, install KKRunner before ASE2SPRKKR. Run the following
from the ASE2SPRKKR checkout:

.. code-block:: console

   python -m pip install -e "<path-to-kkrunner>"
   python -m pip install -e .

Replace ``<path-to-kkrunner>`` with the location of your KKRunner checkout.

Install the same KKRunner release on the SSH target. The remote command must
be available in the noninteractive SSH environment; an absolute path to
``kkrunner-remote`` can be supplied explicitly. Scheduler execution also needs
the optional PSI/J dependency and a configured scheduler on the execution host.
MPI execution needs an MPI launcher compatible with the application executable.

Platforms
-----------

Managed local execution and the direct-process remote service require Linux:
they use ``/proc``, Unix sockets and process groups for durable supervision.
Raw local execution uses subprocesses and has no restart guarantee. SSH clients
need the system ``ssh`` executable. A client does not need ASE or scientific
parsers even when the application that submitted its runs uses them.
