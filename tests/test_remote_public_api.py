import kkrunner.remote.runner as remote_module
from kkrunner import RemoteEndpointExecutor


def test_public_remote_executor_is_endpoint_only():
    assert RemoteEndpointExecutor is RemoteEndpointExecutor
    assert not hasattr(remote_module, "RemoteEndpointExecutor")
