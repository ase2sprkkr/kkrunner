import argparse
import io
import json
from types import SimpleNamespace

import pytest

import kkrunner.remote.service as remote_service
from kkrunner_cli import main as remote_command
from kkrunner.remote.protocol import CONTROL_PROTOCOL_VERSION


def remote_args(**kwargs):
    return SimpleNamespace(**({"protocol_version": CONTROL_PROTOCOL_VERSION} | kwargs))


def test_status_command_forwards_opaque_remote_handle(monkeypatch):
    remote_id = "opaque-handle"
    calls = []
    monkeypatch.setattr(
        remote_service,
        "status_remote",
        lambda value: calls.append(value) or {"state": "running"},
    )
    output = []
    monkeypatch.setattr(remote_command, "_print_json", output.append)

    remote_command.run(
        remote_args(remote_action="status", remote_id=remote_id),
        None,
    )

    assert calls == [remote_id]
    assert output == [{"state": "running"}]


def test_submit_command_passes_complete_request_to_stateless_service(monkeypatch):
    calls = []
    monkeypatch.setattr(
        remote_service,
        "submit_remote",
        lambda request: calls.append(dict(request)) or {"remote_id": "opaque", "state": "running"},
    )
    monkeypatch.setattr(
        remote_command.sys,
        "stdin",
        io.StringIO(json.dumps({"id": "run-1", "argv": ["true"]})),
    )
    output = []
    monkeypatch.setattr(remote_command, "_print_json", output.append)

    remote_command.run(
        remote_args(remote_action="submit", directory="/remote/work"),
        None,
    )

    assert calls == [{"id": "run-1", "argv": ["true"], "directory": "/remote/work"}]
    assert output == [{"remote_id": "opaque", "state": "running"}]


def test_resolve_mpi_command_preserves_integer_process_count(monkeypatch):
    monkeypatch.setattr(
        "kkrunner.backends.mpi.find_default_mpi_launcher",
        lambda: ("mpirun",),
    )
    monkeypatch.setattr(remote_command.sys, "stdin", io.StringIO('{"mpi": 4}'))
    output = []
    monkeypatch.setattr(remote_command, "_print_json", output.append)

    remote_command.run(remote_args(remote_action="resolve-mpi"), None)

    assert output == [{"mpi": ("mpirun", "-np", "4")}]


@pytest.mark.parametrize("action", ["submit", "query-files", "finalize-upload"])
def test_incompatible_protocol_rejected_before_request_is_read(monkeypatch, action):
    monkeypatch.setattr(remote_command.sys, "stdin", io.StringIO("not JSON"))
    args = SimpleNamespace(remote_action=action, protocol_version=CONTROL_PROTOCOL_VERSION + 1)
    with pytest.raises(ValueError, match="Unsupported remote control protocol"):
        remote_command.run(args, None)


def test_direct_parser_accepts_user_commands_without_protocol_version():
    parser = argparse.ArgumentParser()
    remote_command.parser(parser)
    parsed = parser.parse_args(["status", "opaque"])
    assert parsed.protocol_version is None
    assert parsed.remote_action == "status"
    parsed = parser.parse_args(["--protocol-version", str(CONTROL_PROTOCOL_VERSION), "status", "opaque"])
    assert parsed.protocol_version == CONTROL_PROTOCOL_VERSION


def test_internal_actions_require_explicit_protocol_version(monkeypatch):
    monkeypatch.setattr(remote_command.sys, "stdin", io.StringIO("not JSON"))
    with pytest.raises(ValueError, match="explicit --protocol-version"):
        remote_command.run(SimpleNamespace(remote_action="submit", protocol_version=None))


def test_user_status_infers_local_protocol_version(monkeypatch):
    calls = []
    monkeypatch.setattr(remote_service, "status_remote",
                        lambda remote_id: calls.append(remote_id) or {"state": "running"})
    output = []
    monkeypatch.setattr(remote_command, "_print_json", output.append)
    remote_command.run(remote_args(remote_action="status", remote_id="opaque", protocol_version=None))
    assert calls == ["opaque"]
    assert output == [{"state": "running"}]


def test_help_does_not_import_kkrunner():
    import subprocess
    import sys

    code = """\
import sys
from kkrunner_cli.main import main
try:
    main(["--help"])
except SystemExit as exc:
    assert exc.code == 0
else:
    raise AssertionError("help should exit")
assert not any(name == "kkrunner" or name.startswith("kkrunner.") for name in sys.modules)
"""
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)
