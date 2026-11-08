"""Version of the remote helper's control commands and JSON payloads."""

CONTROL_PROTOCOL_VERSION = 1


def check_control_protocol(version):
    """Reject an incompatible client before performing a remote operation."""
    if type(version) is not int or version != CONTROL_PROTOCOL_VERSION:
        raise ValueError(
            f"Unsupported remote control protocol {version!r}; "
            f"expected {CONTROL_PROTOCOL_VERSION}. "
            "Use compatible KKRunner versions on the client and remote host."
        )


def control_command(command, action, *args):
    """Build a versioned stateless service command without importing a client."""
    return (*command, "--protocol-version", str(CONTROL_PROTOCOL_VERSION), action, *args)


async def json_request(transport, command, action, *args, payload=None):
    """Run one control request using any command transport."""
    import json

    data = None if payload is None else json.dumps(payload).encode("utf8")
    result = await transport.run(control_command(command, action, *args), input=data)
    return json.loads(result.stdout.decode("utf8"))
