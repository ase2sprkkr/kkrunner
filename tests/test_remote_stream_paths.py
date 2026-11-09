"""Stream-path hints for human-facing progress are optional and read-only."""

from kkrunner.remote.service import _encode_handle, remote_stream_paths


def test_resolve_stream_paths_in_new_handle():
    handle = _encode_handle({
        "kind": "psij", "backend": "slurm", "url": None, "native_id": "123",
        "directory": "/scratch/work", "output_file": "scf.out",
        "error_file": "/scratch/errors/scf.err",
    })
    assert remote_stream_paths(handle) == {
        "output_file": "/scratch/work/scf.out",
        "error_file": "/scratch/errors/scf.err",
    }


def test_prior_handle_without_stream_metadata():
    handle = _encode_handle({
        "kind": "psij", "backend": "slurm", "url": None, "native_id": "123",
    })
    assert remote_stream_paths(handle) == {
        "output_file": None,
        "error_file": None,
    }
