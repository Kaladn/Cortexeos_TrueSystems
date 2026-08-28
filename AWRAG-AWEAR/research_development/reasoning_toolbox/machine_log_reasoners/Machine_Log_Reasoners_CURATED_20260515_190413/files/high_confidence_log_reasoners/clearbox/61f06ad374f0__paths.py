"""Forest Network — path validation (security boundary).

CRITICAL: This module is the only thing preventing arbitrary filesystem access.
Every file operation MUST pass through resolve_and_validate() before touching disk.

Validation pipeline:
  1. Reject raw traversal patterns (any '..' segment, backslash tricks)
  2. Strip leading slash — treat as relative to repo root
  3. Resolve to absolute path via Path.resolve(strict=False)
     - strict=False allows validating paths that don't exist yet (write case)
     - resolve() follows symlinks, so symlinks escaping the root are caught
  4. Verify the resolved path is under at least one configured allow_root
     - allow_roots must be non-empty or ALL paths are rejected (fail-closed)

HTTP response codes:
  400 — malformed/traversal path (client bug, not auth issue)
  403 — path resolves outside allowed roots (security boundary)
"""
from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, status

from .config import get_allow_roots, get_repo_root

LOGGER = logging.getLogger("forest.network.paths")


def _has_traversal(raw: str) -> bool:
    """Return True if the raw path string contains any traversal attempt.

    Checks for '..' path segments and other escape patterns.
    Normalises backslashes so Windows-style attacks are caught on POSIX too.
    """
    # Normalise separators before splitting
    normalised = raw.replace("\\", "/")
    parts = PurePosixPath(normalised).parts
    return any(p in ("..", "~") for p in parts) or ".." in normalised


def resolve_and_validate(raw_path: str) -> Path:
    """Resolve raw_path to an absolute path and verify it is within allow_roots.

    Args:
        raw_path: The path string from the API request (may be relative or /absolute).

    Returns:
        Resolved absolute Path (safe to open/stat/write).

    Raises:
        HTTPException(400): traversal pattern or unresolvable path.
        HTTPException(403): path resolves outside all configured allow_roots.
    """
    # ── Step 1: Reject traversal before any filesystem access ──────────────
    if _has_traversal(raw_path):
        LOGGER.warning("PATH_TRAVERSAL_BLOCKED | raw=%r", raw_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path contains illegal traversal components (e.g. '..')",
        )

    # ── Step 2: Treat path as relative to repo root ──────────────────────
    # Strip leading slashes — "/docs/GENESIS" → "docs/GENESIS"
    stripped = raw_path.lstrip("/\\")
    if not stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path must not be empty",
        )

    candidate = get_repo_root() / stripped

    # ── Step 3: Resolve symlinks ─────────────────────────────────────────
    # strict=False: doesn't require the path to exist (needed for pre-write validation)
    # resolve() follows all symlinks in existing path components, catching escapes
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        LOGGER.warning("PATH_RESOLVE_ERROR | raw=%r err=%s", raw_path, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resolve path: {exc}",
        )

    # ── Step 4: Validate against allow_roots ────────────────────────────
    allow_roots = get_allow_roots()

    if not allow_roots:
        # Fail-closed: no roots configured = no access
        LOGGER.error("PATH_REJECT | no allow_roots configured — all paths denied")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No allowed roots configured on this node",
        )

    for root in allow_roots:
        try:
            resolved.relative_to(root)
            # Path is within this root — accepted
            LOGGER.debug("PATH_ALLOWED | resolved=%s root=%s", resolved, root)
            return resolved
        except ValueError:
            continue

    LOGGER.warning(
        "PATH_DENIED | resolved=%s not in allow_roots=%s",
        resolved,
        [str(r) for r in allow_roots],
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Path is outside all allowed roots on this node",
    )
