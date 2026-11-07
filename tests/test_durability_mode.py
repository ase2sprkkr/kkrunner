import os
import stat
import pytest
import kkrunner._durability as durability

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX creation-mode semantics are required by this test")


def test_durable_write_keeps_chmod_best_effort(tmp_path, monkeypatch):
    path = tmp_path / "state.json"

    def fail_chmod(*_args, **_kwargs):
        raise OSError("chmod unsupported")

    monkeypatch.setattr(durability.os, "chmod", fail_chmod)
    durability.durable_write_text(path, "state", mode=384)
    assert path.read_text() == "state"
    assert stat.S_IMODE(path.stat().st_mode) & 63 == 0
