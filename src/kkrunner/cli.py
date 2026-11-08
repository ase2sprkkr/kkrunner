"""Stateless target-side commands for remote KKRunner execution."""

import json
import sys

help = "Control KKRunner execution on this machine."
description = "Submit, inspect, follow and cancel remote execution handles."


def parser(parser, *, user=False):
    if user:
        from kkrunner.remote.protocol import CONTROL_PROTOCOL_VERSION

        parser.set_defaults(protocol_version=CONTROL_PROTOCOL_VERSION)
    else:
        parser.add_argument(
            "--protocol-version", type=int, required=True, help="remote control protocol version supplied by the client"
        )
    actions = parser.add_subparsers(dest="remote_action", required=True)

    if not user:
        submit = actions.add_parser("submit")
        submit.add_argument("directory")

    status = actions.add_parser("status")
    status.add_argument("remote_id")

    cancel = actions.add_parser("cancel")
    cancel.add_argument("remote_id")

    follow = actions.add_parser("follow")
    follow.add_argument("remote_id")
    follow.add_argument("--stdout-path")
    follow.add_argument("--stderr-path")
    follow.add_argument("--live", action="store_true", help="observe new output only, without replay")
    follow.add_argument("--stdout-offset", type=int, default=0)
    follow.add_argument("--stderr-offset", type=int, default=0)
    follow.add_argument("--live-stdout", action="store_true")
    follow.add_argument("--live-stderr", action="store_true")
    follow.add_argument(
        "--framed",
        action="store_true",
        help="multiplex calculation stdout/stderr over stdout using the binary protocol",
    )

    if not user:
        recover = actions.add_parser("recover")
        recover.add_argument("directory")
        recover.add_argument("run_id")

        ack_submit = actions.add_parser("ack-submit")
        ack_submit.add_argument("run_id")

        ack = actions.add_parser("ack")
        ack.add_argument("remote_id")

        actions.add_parser("resolve-mpi")


def _print_json(value):
    print(json.dumps(value), flush=True)


class _FramedSink:
    def __init__(self, stream, kind):
        self.stream = stream
        self.kind = kind

    def write(self, data):
        from kkrunner.remote.stream import encode_stream_frame

        self.stream.write(encode_stream_frame(self.kind, data))

    def flush(self):
        self.stream.flush()


def run(args, global_args):
    from kkrunner.remote.protocol import check_control_protocol

    check_control_protocol(args.protocol_version)
    from kkrunner.remote.service import (
        acknowledge_remote,
        acknowledge_submission,
        cancel_remote,
        follow_remote,
        recover_remote,
        status_remote,
        submit_remote,
    )

    if args.remote_action == "submit":
        request = json.load(sys.stdin)
        request["directory"] = args.directory
        _print_json(submit_remote(request))
    elif args.remote_action == "status":
        _print_json(status_remote(args.remote_id))
    elif args.remote_action == "cancel":
        _print_json(cancel_remote(args.remote_id))
    elif args.remote_action == "follow":
        if args.framed:
            from kkrunner.remote.stream import STREAM_MAGIC

            stream = sys.stdout.buffer
            stream.write(STREAM_MAGIC)
            stream.flush()
            stdout = _FramedSink(stream, "out")
            stderr = _FramedSink(stream, "err")
        else:
            stdout = sys.stdout.buffer
            stderr = sys.stderr.buffer
        outcome = follow_remote(
            args.remote_id,
            stdout,
            stderr,
            stdout_offset=None if args.live or args.live_stdout else args.stdout_offset,
            stderr_offset=None if args.live or args.live_stderr else args.stderr_offset,
            stdout_path=args.stdout_path,
            stderr_path=args.stderr_path,
        )
        if args.framed:
            from kkrunner.remote.stream import encode_terminal_frame

            stream.write(encode_terminal_frame(outcome))
            stream.flush()
    elif args.remote_action == "recover":
        request = json.load(sys.stdin)
        request["directory"] = args.directory
        submitted_at = request.pop("submitted_at", None)
        try:
            result = recover_remote(
                args.run_id,
                request,
                submitted_at=submitted_at,
            )
        except NotImplementedError as exc:
            result = {"unsupported": True, "error": str(exc)}
        _print_json(result)
    elif args.remote_action == "ack-submit":
        _print_json(acknowledge_submission(args.run_id))
    elif args.remote_action == "ack":
        _print_json(acknowledge_remote(args.remote_id))
    elif args.remote_action == "resolve-mpi":
        from kkrunner.backends.mpi import resolve_mpi_command
        from kkrunner.runs.base import LaunchSpec

        request = json.load(sys.stdin)
        launch = LaunchSpec.from_mpi(request.get("mpi"))
        _print_json({"mpi": resolve_mpi_command(launch.mpi)})
    else:
        raise ValueError("Unknown remote action: {}".format(args.remote_action))


def main():
    import argparse

    root = argparse.ArgumentParser(prog="kkrunner")
    commands = root.add_subparsers(dest="command", required=True)
    parser(commands.add_parser("remote", help=description))
    args = root.parse_args()
    run(args, None)


def user_parser(argument_parser):
    """Human-facing status/follow/cancel subset of the same remote service."""
    parser(argument_parser, user=True)
