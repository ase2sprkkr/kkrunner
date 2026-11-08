"""Execution backends and their reusable endpoint identities."""

from importlib import import_module
from typing import TYPE_CHECKING

from kkrunner.backends.endpoint import ExecutorEndpoint

if TYPE_CHECKING:
    from kkrunner.backends.local import LocalExecutor
    from kkrunner.backends.pool import ExecutorPool, default_executor_pool
    from kkrunner.backends.psij import PsijExecutor

# Run contracts use endpoint metadata. Load implementations only on request so
# importing those contracts does not load backends or create an import cycle.
_EXPORTS = {
    "LocalExecutor": "kkrunner.backends.local",
    "PsijExecutor": "kkrunner.backends.psij",
    "ExecutorPool": "kkrunner.backends.pool",
    "default_executor_pool": "kkrunner.backends.pool",
}

__all__ = ["ExecutorEndpoint", "ExecutorPool", "LocalExecutor", "PsijExecutor", "default_executor_pool"]


def __getattr__(name):
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
