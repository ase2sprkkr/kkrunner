import kkrunner.remote as remote_module
from kkrunner import RemoteEndpointExecutor, RemoteExecutor


def test_public_remote_executor_is_endpoint_only():
    assert RemoteExecutor is RemoteEndpointExecutor
    assert not hasattr(remote_module, "RemoteExecutor")
