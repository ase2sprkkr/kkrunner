"""Human-facing stream hints must not change the backend status protocol."""

from kkrunner.remote.service import _encode_handle, remote_stream_paths


def test_remote_stream_paths_resolve_relative_paths():
    handle = _encode_handle({
        "kind": "psij", "backend": "slurm", "url": None, "native_id": "123",
        "directory": "/scratch/work", "output_file": "run.out",
        "error_file": "/scratch/errors/run.err",
    })
    assert remote_stream_paths(handle) == {
        "output_file": "/scratch/work/run.out",
        "error_file": "/scratch/errors/run.err",
    }


def test_old_handle_has_no_stream_hints():
    handle = _encode_handle({"kind": "psij", "backend": "slurm", "url": None, "native_id": "123"})
    assert remote_stream_paths(handle) == {"output_file": None, "error_file": None}
