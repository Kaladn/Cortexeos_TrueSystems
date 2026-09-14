"""Small private atomic records; no service, queue, or shared global lock."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path
import tempfile


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def private_path(path: str | Path) -> Path:
    path = Path(path).absolute()
    if ".." in path.parts:
        raise ValueError("parent traversal is not an admitted path")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("receipt path contains a symlink")
    return path


def atomic_json(path: str | Path, value, *, max_bytes: int = 1024 * 1024) -> None:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(raw) > max_bytes:
        raise ValueError("record exceeds publication budget")
    target = private_path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, target)
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_json(path: str | Path, *, max_bytes: int = 1024 * 1024):
    target = private_path(path)
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("record must be a regular file")
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("record exceeds read budget")
    return json.loads(raw)


@contextmanager
def record_lock(path: str | Path):
    """Local nonblocking writer lock. Busy logging never waits on another job."""
    target = private_path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(target, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)
