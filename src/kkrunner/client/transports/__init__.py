"""Connection implementations, independent of execution backend selection."""

__all__ = ["Transport", "LocalTransport", "SshTransport"]


def __getattr__(name):
    if name == "Transport":
        from .base import Transport as value
    elif name == "LocalTransport":
        from .local import LocalTransport as value
    elif name == "SshTransport":
        from .ssh import SshTransport as value
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))


def require_persistable_transport(transport):
    """Accept built-in transports and read-only unsupported transport settings."""
    from .local import LocalTransport
    from .ssh import SshTransport
    from .unavailable import UnavailableTransport

    if type(transport) not in (LocalTransport, SshTransport, UnavailableTransport):
        raise TypeError("Persistent runs require a supported LocalTransport or SshTransport")
    return transport


def transport_from_dict(value):
    """Decode settings without importing stored class paths or enabling unknown kinds."""
    kind = value.get("kind")
    if kind == "local":
        from .local import LocalTransport
        return LocalTransport(**value)
    if kind == "ssh":
        from .ssh import SshTransport
        return SshTransport(**value)
    if isinstance(kind, str) and kind:
        from .unavailable import UnavailableTransport
        return UnavailableTransport(value)
    raise ValueError(f"Unknown transport kind: {kind!r}")
