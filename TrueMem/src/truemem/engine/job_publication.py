"""Atomic publication for the compact overview and resonance proof contracts."""
import json
import os
from pathlib import Path
import tempfile
from .base import with_protected_notice


def write_job_receipt(path: Path, payload: dict) -> None:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("receipt path contains a symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(with_protected_notice(payload), handle, ensure_ascii=True, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
