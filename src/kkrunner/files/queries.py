"""Portable filesystem queries, independent of transports and job execution."""

import errno
import os
import stat
from pathlib import Path

from kkrunner.files.paths import expand_local_candidates
from kkrunner.files.versions import file_digest


def _sources(sources):
    if isinstance(sources, (str, bytes, os.PathLike)):
        return (sources,)
    return tuple(sources)


def _local_pattern(source, root):
    root = Path(os.path.abspath(os.path.expanduser(root)))
    source = os.fspath(source)
    path = Path(source).expanduser()
    if not path.is_absolute():
        path = root / path
    pattern = os.path.abspath(os.fspath(path))
    try:
        os.path.relpath(pattern, root)
    except ValueError as exc:
        raise ValueError(f"File pattern {source!r} is outside source root {root}") from exc
    relative = os.path.relpath(pattern, root)
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        raise ValueError(f"File pattern {source!r} is outside source root {root}")
    return root, pattern


def query_files(sources, *, root=None, digest=False):
    """Return JSON-ready metadata for exact paths or root-confined patterns.

    Without a root, names are literal (including wildcard characters). With a
    root, patterns use Python's recursive glob semantics and results are
    deduplicated in request order (sorted within each pattern). Symlinks are
    followed, but may not escape the source root.
    Missing exact paths have status ``missing``; other OS errors retain errno.
    A batch is a sequence of observations, not an atomic filesystem snapshot.
    """
    real_root = None if root is None else Path(root).expanduser().resolve()
    paths = []
    if root is None:
        paths = [os.fsdecode(path) for path in _sources(sources)]
    else:
        for source in _sources(sources):
            _, pattern = _local_pattern(source, root)
            for match in expand_local_candidates(pattern):
                # Preserve the requested namespace (e.g. /tmp on macOS is
                # a symlink), while checking containment using real paths.
                paths.append(os.path.abspath(match))
        paths = list(dict.fromkeys(paths))

    results = []
    for path in paths:
        try:
            info = os.stat(path)
            if root is not None:
                resolved = Path(path).resolve()
                try:
                    resolved.relative_to(real_root)
                except ValueError as exc:
                    raise ValueError(f"Expanded file {resolved} is outside source root {root}") from exc
            kind = "file" if stat.S_ISREG(info.st_mode) else "directory" if stat.S_ISDIR(info.st_mode) else "other"
            item = {"path": path, "status": "ok", "size": info.st_size, "mtime_ns": info.st_mtime_ns, "type": kind}
            if digest and kind == "file":
                item["digest"] = file_digest(path)
        except FileNotFoundError:
            item = {"path": path, "status": "missing"}
        except OSError as exc:
            item = {"path": path, "status": "error", "error": {"errno": exc.errno, "message": str(exc)}}
        results.append(item)
    return results


def checked_files(results):
    """Raise genuine filesystem errors, leaving missing entries explicit."""
    for item in results:
        if item["status"] == "error":
            error = item["error"]
            raise OSError(error.get("errno") or errno.EIO, error["message"], item["path"])
    return results


def expand_local_files(sources, root):
    """Select regular files using the same metadata/discovery path as SSH."""
    return tuple(
        dict.fromkeys(
            os.fspath(Path(item["path"]).resolve())
            for item in checked_files(query_files(sources, root=root))
            if item["status"] == "ok" and item["type"] == "file"
        )
    )


def local_file_signature(path):
    """Return ``(size, mtime_ns)`` or None for a missing local path."""
    item = checked_files(query_files([path]))[0]
    return None if item["status"] == "missing" else (item["size"], item["mtime_ns"])


def finalize_upload(temporary, destination, mtime_ns):
    """Preserve nanosecond timestamps before atomically publishing an upload."""
    info = os.stat(temporary)
    os.utime(temporary, ns=(info.st_atime_ns, mtime_ns))
    os.replace(temporary, destination)
