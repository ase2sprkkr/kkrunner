Release notes
=============

0.2.0b1
-------

This beta consolidates execution around independent backend and transport
choices. It replaces the 0.1 client API and does not promise compatibility with
persisted development records or a stable extension API.

* Choose ``DirectBackend``, ``SupervisedBackend`` or ``PsijBackend`` independently
  of ``LocalTransport`` or ``SshTransport``. ``EndpointClient`` binds the choices
  and can serve multiple runs.
* Local calls invoke backend operations directly. SSH delivers self-contained
  direct operations as source; durable supervision and PSI/J operations use an
  installed KKRunner on the execution host.
* ``Job`` observes backend execution. ``Run`` owns output finalization,
  application postprocessing and completion; ``RunManager`` adds persistence
  and recovery. Backend identity alone does not imply reattachment support.
* ``ExecutionMetadata`` stores immutable configuration, directories and
  submission identifiers. ``RunFiles`` handles tracked file versions, snapshots
  and verified restoration through composition with ``RunManager``.
* ``Run`` accepts ``owned_resources=ExecutionResources(...)``. Resources remain
  available through postprocessing and durable completion, and survive uncertain
  execution. The ``ResourceOwnedRunner`` proxy has been removed.
* ``kkrunner`` is the client CLI; ``kkrunner-agent`` is the one-shot execution-host
  service. SSH stdout and stderr framing retains native execution outcomes
  separately from observation and transfer errors.
* Linux process identities include the kernel boot UUID. PSI/J query and follow
  reconcile scheduler state before reporting terminal execution facts.

Applications using ``RunClient`` must migrate to ``EndpointClient``. Configure
transport and backend separately and use ``Run.create()`` or
``RunManager.create_run()`` for the full client lifecycle. Both ends of an SSH
connection that uses installed helpers should run this beta.

Docker SSH/Slurm integration remains opt-in; it requires a reachable container
runtime and the appropriate scheduler environment. See :doc:`development` for
the release validation commands and :doc:`client` for the client API.
