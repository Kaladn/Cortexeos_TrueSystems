"""Forest Node — file access mode state machine + path validation.

Shared logic used by the package-based daemon (node_daemon.py).
The standalone daemon inlines equivalent logic.

Security invariants:
- Path.resolve() normalizes all .. and follows symlinks
- Allowlist mode checks resolved path against configured roots
- FULL mode requires explicit --allow-full CLI flag (daemon-side gate)
- Junction/reparse points have their targets validated in allowlist mode
"""

from __future__ import annotations

import ctypes
import os
import time
from enum import Enum
from pathlib import Path
from typing import List, Optional


class AccessMode(str, Enum):
    LOCKED = "locked"
    ALLOWLIST = "allowlist"
    FULL = "full"


class FileAccessState:
    """Mutable state for the daemon's file access system."""

    def __init__(self):
        self.mode: AccessMode = AccessMode.LOCKED
        self.expires_at: float = 0.0           # epoch; 0 = no TTL
        self.allow_full_flag: bool = False      # set by --allow-full CLI
        self.share_write: bool = False

        # Allowlist roots
        user_home = Path.home()
        default_roots = [
            str(user_home / "Documents"),
            str(user_home / "Desktop"),
            str(user_home / "Downloads"),
        ]
        raw = os.environ.get("ALLOWED_ROOTS", "")
        self.allowlist_roots: List[str] = (
            [r.strip() for r in raw.split(",") if r.strip()] if raw else default_roots
        )
        self.max_read_size: int = int(os.environ.get("MAX_READ_SIZE", "104857600"))
        self.max_write_size: int = int(os.environ.get("MAX_WRITE_SIZE", "10485760"))  # 10 MB

    def revert_to_locked(self):
        self.mode = AccessMode.LOCKED
        self.expires_at = 0.0
        self.share_write = False

    def check_ttl(self):
        """Auto-expire if TTL has passed."""
        if self.expires_at > 0 and time.time() > self.expires_at:
            self.revert_to_locked()


def check_mode_transition(state: FileAccessState, requested: str) -> Optional[str]:
    """Validate a mode transition. Returns error message or None if OK."""
    if requested == "locked":
        return None  # always allowed
    if requested == "allowlist":
        return None  # allowed unauthenticated
    if requested == "full":
        if not state.allow_full_flag:
            return "FULL mode requires --allow-full flag on daemon startup (operator consent)"
        return None
    return f"Unknown mode: {requested}"


def is_reparse_point(p: Path) -> bool:
    """Check if path is a Windows reparse point (junction/symlink)."""
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
        if attrs == -1:
            return False
        return bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except Exception:
        return False


def path_within_roots(resolved: Path, roots: List[str]) -> bool:
    """Check if resolved path falls within at least one root."""
    resolved_str = str(resolved)
    for root in roots:
        root_resolved = str(Path(root).resolve())
        if resolved_str.startswith(root_resolved):
            return True
    return False


def validate_path(path_str: str, state: FileAccessState) -> Path:
    """Resolve path and enforce access mode.

    Returns the validated resolved Path.
    Raises PermissionError or ValueError on violation.
    """
    state.check_ttl()

    if state.mode == AccessMode.LOCKED:
        raise PermissionError("File access is locked")

    if not path_str or not path_str.strip():
        raise ValueError("Path is required")

    resolved = Path(path_str).resolve()

    if state.mode == AccessMode.ALLOWLIST:
        if not path_within_roots(resolved, state.allowlist_roots):
            raise PermissionError("Path outside allowed roots")
        return resolved

    if state.mode == AccessMode.FULL:
        return resolved

    raise PermissionError("Unknown access mode")


def validate_write_path(path_str: str, state: FileAccessState, size: int = 0) -> Path:
    """Validate path for write. Reuses validate_path() + write-specific guards."""
    if not state.share_write:
        raise PermissionError("Write access is disabled")
    if size > state.max_write_size:
        raise PermissionError(
            f"Content too large: {size} bytes (max {state.max_write_size})"
        )
    return validate_path(path_str, state)


def list_directory(dir_path: Path, state: FileAccessState) -> list:
    """List directory entries with junction/reparse detection."""
    entries = []
    try:
        for entry in sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            try:
                entry_stat = entry.stat()
                is_dir = entry.is_dir()
                junction = is_reparse_point(entry)

                traversable = True
                if junction and state.mode == AccessMode.ALLOWLIST:
                    try:
                        target = entry.resolve()
                        if not path_within_roots(target, state.allowlist_roots):
                            traversable = False
                    except Exception:
                        traversable = False

                entries.append({
                    "name": entry.name,
                    "is_dir": is_dir,
                    "size": entry_stat.st_size if not is_dir else 0,
                    "modified": entry_stat.st_mtime,
                    "is_junction": junction,
                    "traversable": traversable if is_dir else True,
                })
            except PermissionError:
                entries.append({
                    "name": entry.name,
                    "is_dir": False,
                    "size": 0,
                    "modified": 0.0,
                    "is_junction": False,
                    "traversable": False,
                })
            except Exception:
                pass
    except PermissionError:
        raise PermissionError(f"Permission denied: {dir_path}")
    return entries
