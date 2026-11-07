import pytest
from kkrunner import ExecutionSpec
from kkrunner.remote import RemoteRunner


def test_remote_cancel_before_submit_is_rejected(tmp_path):
    spec = ExecutionSpec(argv=(), input_file=None, output_file=None, directory=str(tmp_path))
    runner = RemoteRunner(object(), spec)
    with pytest.raises(RuntimeError, match="not been submitted"):
        runner.cancel()
