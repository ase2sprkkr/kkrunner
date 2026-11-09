"""An opaque handle identifies a backend, not its working directory or files."""

from kkrunner.remote.service import _decode_handle, _encode_handle


def test_psij_handle_has_only_backend_identity():
    handle = _encode_handle({
        "kind": "psij", "backend": "slurm", "url": None, "native_id": "123",
    })
    assert _decode_handle(handle) == {
        "kind": "psij", "backend": "slurm", "url": None, "native_id": "123",
    }


def test_legacy_handle_with_extra_fields_remains_decodable():
    handle = _encode_handle({
        "kind": "psij", "backend": "slurm", "url": None, "native_id": "123",
        "directory": "/scratch/work", "output_file": "run.out",
    })
    assert _decode_handle(handle)["native_id"] == "123"
