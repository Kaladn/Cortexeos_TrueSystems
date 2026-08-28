"""Reader-Writer Gateway — the only door for filesystem mutations.

Design contract:
    1. ALL writes go through this module. No exceptions.
    2. AI callers can only write to ARTIFACTS.
    3. Human callers promote: artifacts → staging → implementation.
    4. Protected zones (system structure, system lexicon, config) are HARD-BLOCKED.
    5. Every mutation is logged to an append-only audit trail.

Caller types:
    "ai"     → may write to: artifacts
    "system" → may write to: artifacts, data_raw, data_mapped, sessions,
                              chat_threads, chat_summaries, chat_memory, state, lexicon_user
    "human"  → may write to: everything except protected zones
                              may promote between zones

This module delegates actual I/O to security.secure_storage (DPAPI encryption).
It does NOT replace the encryption layer — it governs what gets written WHERE.
"""

from __future__ import annotations

import enum
import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from security.data_paths import (
    CLEARBOX_ROOT,
    CLEARBOX_DATA_ROOT,
    SOURCE_ROOT,
    CHAT_THREADS_DIR,
    CHAT_SUMMARIES_DIR,
    CHAT_CITATIONS_DIR,
    CHAT_NOTES_DIR,
    CHAT_MAPS_DIR,
    CHAT_MEMORY_DIR,
    CONFIG_DIR,
    STATE_DIR,
    SESSIONS_DIR,
    AUTH_DIR,
    AUDIT_DIR,
    OBSERVE_DIR,
    LAKESPEAK_INDEX_DIR,
    LAKESPEAK_EVENTS_DIR,
    LAKESPEAK_EVAL_DIR,
    IDEAS_DIR,
)
from security.secure_storage import (
    secure_read_text,
    secure_write_text,
    secure_json_load,
    secure_json_dump,
    secure_append_line,
    secure_read_lines,
)


# ── Zone Definitions ──────────────────────────────────────────


class WriteZone(enum.Enum):
    """Zones where writes are governed but allowed (through the gateway)."""

    ARTIFACTS       = "artifacts"         # AI output drop
    STAGING         = "staging"           # Human review area
    IMPLEMENTATION  = "implementation"    # Human-activated (live)
    DATA_RAW        = "data_raw"          # Immutable input snapshots
    DATA_MAPPED     = "data_mapped"       # Mapping outputs
    SESSIONS        = "sessions"          # Session artifacts
    LEXICON_USER    = "lexicon_user"      # User-created lexicon entries
    CHAT_THREADS    = "chat_threads"      # Chat JSONL logs
    CHAT_SUMMARIES  = "chat_summaries"    # Daily summaries
    CHAT_CITATIONS  = "chat_citations"    # Citation sidecars
    CHAT_NOTES      = "chat_notes"        # Note sidecars
    STATE           = "state"             # Runtime state persistence
    CONFIG          = "config"            # Config (key-whitelisted writes only)
    # ── LakeSpeak zones ──────────────────────────────────────
    LAKESPEAK_INDEX  = "lakespeak_index"    # Retrieval indexes
    LAKESPEAK_EVENTS = "lakespeak_events"   # Training event JSONL
    LAKESPEAK_EVAL   = "lakespeak_eval"     # Evaluation reports
    # ── Memory zone ─────────────────────────────────────────
    CHAT_MEMORY        = "chat_memory"          # Lessons, reasoning logs
    # ── Ideas zone (AI-writable) ─────────────────────────────
    IDEAS              = "ideas"                # Future feature proposals


class ProtectedZone(enum.Enum):
    """Zones where writes are HARD-BLOCKED. No caller may mutate these."""

    SYSTEM          = "system"            # Directory structure itself
    LEXICON_SYSTEM  = "lexicon_system"    # Base/system lexicon (read-only)
    CONFIG          = "config"            # Configuration files
    AUTH            = "auth"              # Auth credentials (managed by auth.py only)


# ── Caller Permissions ────────────────────────────────────────

# Which zones each caller type may write to
_CALLER_PERMISSIONS: dict[str, set[WriteZone]] = {
    "ai": {
        WriteZone.ARTIFACTS,
        WriteZone.IDEAS,
    },
    "system": {
        WriteZone.ARTIFACTS,
        WriteZone.IDEAS,
        WriteZone.DATA_RAW,
        WriteZone.DATA_MAPPED,
        WriteZone.SESSIONS,
        WriteZone.LEXICON_USER,
        WriteZone.CHAT_THREADS,
        WriteZone.CHAT_SUMMARIES,
        WriteZone.CHAT_CITATIONS,
        WriteZone.CHAT_NOTES,
        WriteZone.CHAT_MEMORY,
        WriteZone.STATE,
        WriteZone.CONFIG,
        WriteZone.LAKESPEAK_INDEX,
        WriteZone.LAKESPEAK_EVENTS,
        WriteZone.LAKESPEAK_EVAL,
    },
    "human": {
        WriteZone.ARTIFACTS,
        WriteZone.IDEAS,
        WriteZone.STAGING,
        WriteZone.IMPLEMENTATION,
        WriteZone.DATA_RAW,
        WriteZone.DATA_MAPPED,
        WriteZone.SESSIONS,
        WriteZone.LEXICON_USER,
        WriteZone.CHAT_THREADS,
        WriteZone.CHAT_SUMMARIES,
        WriteZone.CHAT_CITATIONS,
        WriteZone.CHAT_NOTES,
        WriteZone.CHAT_MEMORY,
        WriteZone.STATE,
        WriteZone.CONFIG,
        WriteZone.LAKESPEAK_INDEX,
        WriteZone.LAKESPEAK_EVENTS,
        WriteZone.LAKESPEAK_EVAL,
    },
}

# Which zone transitions (promotions) are legal
_PROMOTION_RULES: dict[WriteZone, WriteZone] = {
    WriteZone.ARTIFACTS:  WriteZone.STAGING,
    WriteZone.STAGING:    WriteZone.IMPLEMENTATION,
}


# ── Zone Path Resolution ─────────────────────────────────────

def _zone_root(zone: WriteZone) -> Path:
    """Resolve a WriteZone to its absolute filesystem path."""
    _map = {
        WriteZone.ARTIFACTS:       CLEARBOX_ROOT / "data" / "artifacts",
        WriteZone.STAGING:         CLEARBOX_ROOT / "data" / "staging",
        WriteZone.IMPLEMENTATION:  CLEARBOX_ROOT / "data" / "implementation",
        WriteZone.DATA_RAW:        CLEARBOX_ROOT / "data" / "raw",
        WriteZone.DATA_MAPPED:     CHAT_MAPS_DIR,
        WriteZone.SESSIONS:        SESSIONS_DIR,
        WriteZone.LEXICON_USER:    SOURCE_ROOT / "Lexicon_Canonical" / "user",
        WriteZone.CHAT_THREADS:    CHAT_THREADS_DIR,
        WriteZone.CHAT_SUMMARIES:  CHAT_SUMMARIES_DIR,
        WriteZone.CHAT_CITATIONS:  CHAT_CITATIONS_DIR,
        WriteZone.CHAT_NOTES:      CHAT_NOTES_DIR,
        WriteZone.STATE:           STATE_DIR,
        WriteZone.CHAT_MEMORY:     CHAT_MEMORY_DIR,
        WriteZone.CONFIG:          CONFIG_DIR,
        WriteZone.LAKESPEAK_INDEX:   LAKESPEAK_INDEX_DIR,
        WriteZone.LAKESPEAK_EVENTS:  LAKESPEAK_EVENTS_DIR,
        WriteZone.LAKESPEAK_EVAL:    LAKESPEAK_EVAL_DIR,
        WriteZone.IDEAS:               IDEAS_DIR,
    }
    return _map[zone]


def _protected_roots() -> list[Path]:
    """Return absolute paths of all protected zones."""
    return [
        SOURCE_ROOT / "Lexicon_Canonical",     # system lexicon (read-only reference)
        CONFIG_DIR,                            # config
        AUTH_DIR,                              # auth credentials / secrets
    ]


# ── Path Sanitization ─────────────────────────────────────────

import re as _re

def sanitize_artifact_path(rel_path: str) -> str | None:
    """Sanitize a relative artifact path. Returns None if invalid.

    Rules:
        - No backslash, colon, tilde, or absolute paths
        - No '..' in any segment
        - Each segment: [a-zA-Z0-9_. -] only
        - Normalizes multiple slashes
    """
    if not rel_path or rel_path.startswith("/") or rel_path.startswith("~"):
        return None
    if "\\" in rel_path or ":" in rel_path:
        return None
    # Normalize multiple slashes
    rel_path = _re.sub(r"/+", "/", rel_path).strip("/")
    if not rel_path:
        return None
    # Check each segment
    for segment in rel_path.split("/"):
        if segment == ".." or not segment:
            return None
        if not _re.match(r"^[a-zA-Z0-9_. -]+$", segment):
            return None
    return rel_path


# ── Data Structures ───────────────────────────────────────────


@dataclass
class WriteRequest:
    """Immutable record of a proposed write operation."""

    zone: WriteZone
    name: str                  # relative path within the zone
    content: str               # the data to write
    caller: str                # "ai" | "system" | "human"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_hash: str = ""     # SHA-256 of content, computed on creation

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()


@dataclass
class WriteResult:
    """Outcome of a write or promotion operation."""

    success: bool
    path: Optional[Path] = None
    error: Optional[str] = None
    audit_id: Optional[str] = None


@dataclass
class AuditEntry:
    """Single entry in the audit trail."""

    timestamp: str
    action: str                # "write" | "promote" | "delete" | "blocked"
    caller: str
    zone: str
    name: str
    content_hash: str
    result: str                # "ok" | "denied" | "error"
    detail: str = ""


# ── The Gateway ───────────────────────────────────────────────


class ReaderWriter:
    """Single authority for all governed filesystem operations.

    Usage:
        gw = ReaderWriter()
        
        # AI writes an artifact
        req = gw.propose("ai", WriteZone.ARTIFACTS, "plan_v1.md", content)
        result = gw.execute(req)
        
        # Human promotes artifact → staging
        result = gw.promote("human", "plan_v1.md", 
                            WriteZone.ARTIFACTS, WriteZone.STAGING)
        
        # Human promotes staging → implementation
        result = gw.promote("human", "plan_v1.md",
                            WriteZone.STAGING, WriteZone.IMPLEMENTATION)
    """

    def __init__(self, root: Optional[Path] = None):
        self.root = root or CLEARBOX_DATA_ROOT
        self._audit_path = self.root / "audit" / "gateway_audit.jsonl"
        self._ensure_zones()

    # ── Zone Setup ────────────────────────────────────────────

    def _ensure_zones(self) -> None:
        """Create all governed zone directories if they don't exist."""
        for zone in WriteZone:
            _zone_root(zone).mkdir(parents=True, exist_ok=True)
        # Audit directory
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Read Operations (unrestricted) ────────────────────────

    def read(self, zone: WriteZone, name: str) -> Optional[str]:
        """Read a file from any zone. Returns None if not found."""
        path = _zone_root(zone) / name
        if not path.exists():
            return None
        try:
            return secure_read_text(path)
        except Exception:
            # Fall back to raw read if not DPAPI-encrypted
            return path.read_text(encoding="utf-8")

    def read_json(self, zone: WriteZone, name: str) -> Optional[Any]:
        """Read and parse a JSON file from any zone."""
        path = _zone_root(zone) / name
        if not path.exists():
            return None
        try:
            return secure_json_load(path)
        except Exception:
            return json.loads(path.read_text(encoding="utf-8"))

    def list_zone(self, zone: WriteZone) -> list[str]:
        """List all files in a zone (relative names)."""
        root = _zone_root(zone)
        if not root.exists():
            return []
        return [
            str(p.relative_to(root))
            for p in root.rglob("*")
            if p.is_file()
        ]

    def exists(self, zone: WriteZone, name: str) -> bool:
        """Check if a file exists in a zone."""
        return (_zone_root(zone) / name).exists()

    # ── Write Operations (governed) ───────────────────────────

    def propose(
        self,
        caller: str,
        zone: WriteZone,
        name: str,
        content: str,
    ) -> WriteRequest:
        """Create a write request. Does NOT execute it yet.

        Raises ValueError if the caller is not recognized.
        """
        if caller not in _CALLER_PERMISSIONS:
            raise ValueError(
                f"Unknown caller type '{caller}'. Must be one of: {list(_CALLER_PERMISSIONS.keys())}"
            )
        return WriteRequest(
            zone=zone,
            name=name,
            content=content,
            caller=caller,
        )

    def execute(self, request: WriteRequest, encrypt: bool = True) -> WriteResult:
        """Execute a proposed write. Enforces zone + caller permissions.

        Args:
            request:  A WriteRequest from propose().
            encrypt:  If True, use DPAPI encryption. If False, write plaintext.
                      Default True for security.

        Returns:
            WriteResult with success/failure + audit trail ID.
        """
        # ── Permission check ──────────────────────────────────
        allowed = _CALLER_PERMISSIONS.get(request.caller, set())
        if request.zone not in allowed:
            audit_id = self._audit(
                action="blocked",
                caller=request.caller,
                zone=request.zone.value,
                name=request.name,
                content_hash=request.content_hash,
                result="denied",
                detail=f"Caller '{request.caller}' may not write to zone '{request.zone.value}'",
            )
            return WriteResult(
                success=False,
                error=f"DENIED: caller '{request.caller}' cannot write to '{request.zone.value}'. "
                      f"Allowed zones: {[z.value for z in allowed]}",
                audit_id=audit_id,
            )

        # ── Path safety check ─────────────────────────────────
        dest = _zone_root(request.zone) / request.name
        try:
            resolved = dest.resolve()
        except Exception as e:
            return WriteResult(success=False, error=f"Path resolution failed: {e}")

        zone_resolved = _zone_root(request.zone).resolve()
        _zr_str = str(zone_resolved)
        if str(resolved) != _zr_str and not str(resolved).startswith(_zr_str + os.sep):
            audit_id = self._audit(
                action="blocked",
                caller=request.caller,
                zone=request.zone.value,
                name=request.name,
                content_hash=request.content_hash,
                result="denied",
                detail=f"Path traversal attempt: {request.name} resolves outside zone",
            )
            return WriteResult(
                success=False,
                error=f"DENIED: path '{request.name}' escapes zone boundary",
                audit_id=audit_id,
            )

        # ── Protected zone check ──────────────────────────────
        for proot in _protected_roots():
            presolved = proot.resolve()
            # Don't block writes to governed CHILDREN of system/
            # (artifacts, staging, implementation are children of system/)
            # Only block direct writes to protected roots themselves
            _pr_str = str(presolved)
            if resolved == presolved or (
                str(resolved).startswith(_pr_str + os.sep)
                and resolved not in [
                    _zone_root(z).resolve() for z in WriteZone
                ]
                and not any(
                    str(resolved).startswith(str(_zone_root(z).resolve()) + os.sep)
                    for z in WriteZone
                )
            ):
                audit_id = self._audit(
                    action="blocked",
                    caller=request.caller,
                    zone=request.zone.value,
                    name=request.name,
                    content_hash=request.content_hash,
                    result="denied",
                    detail=f"Write to protected zone: {presolved}",
                )
                return WriteResult(
                    success=False,
                    error=f"DENIED: target falls within protected zone '{proot}'",
                    audit_id=audit_id,
                )

        # ── Execute write ─────────────────────────────────────
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if encrypt:
                secure_write_text(dest, request.content)
            else:
                dest.write_text(request.content, encoding="utf-8")

            audit_id = self._audit(
                action="write",
                caller=request.caller,
                zone=request.zone.value,
                name=request.name,
                content_hash=request.content_hash,
                result="ok",
            )
            return WriteResult(success=True, path=dest, audit_id=audit_id)

        except Exception as e:
            audit_id = self._audit(
                action="write",
                caller=request.caller,
                zone=request.zone.value,
                name=request.name,
                content_hash=request.content_hash,
                result="error",
                detail=str(e),
            )
            return WriteResult(success=False, error=str(e), audit_id=audit_id)

    def write(
        self,
        caller: str,
        zone: WriteZone,
        name: str,
        content: str,
        encrypt: bool = True,
    ) -> WriteResult:
        """Convenience: propose + execute in one call."""
        req = self.propose(caller, zone, name, content)
        return self.execute(req, encrypt=encrypt)

    def write_bytes(
        self,
        caller: str,
        zone: WriteZone,
        name: str,
        data: bytes,
    ) -> WriteResult:
        """Write raw bytes to a governed zone. No encryption (binary files).

        Same permission/path-safety/audit logic as execute(), but for binary data.
        """
        # ── Permission check ──────────────────────────────────
        allowed = _CALLER_PERMISSIONS.get(caller, set())
        if zone not in allowed:
            audit_id = self._audit(
                action="blocked", caller=caller, zone=zone.value, name=name,
                content_hash=hashlib.sha256(data).hexdigest()[:16],
                result="denied",
                detail=f"Caller '{caller}' may not write to zone '{zone.value}'",
            )
            return WriteResult(
                success=False,
                error=f"DENIED: caller '{caller}' cannot write to '{zone.value}'",
                audit_id=audit_id,
            )

        # ── Path safety ───────────────────────────────────────
        dest = _zone_root(zone) / name
        try:
            resolved = dest.resolve()
        except Exception as e:
            return WriteResult(success=False, error=f"Path resolution failed: {e}")

        zone_resolved = _zone_root(zone).resolve()
        _zr_str2 = str(zone_resolved)
        if str(resolved) != _zr_str2 and not str(resolved).startswith(_zr_str2 + os.sep):
            audit_id = self._audit(
                action="blocked", caller=caller, zone=zone.value, name=name,
                content_hash=hashlib.sha256(data).hexdigest()[:16],
                result="denied",
                detail=f"Path traversal attempt: {name} resolves outside zone",
            )
            return WriteResult(
                success=False,
                error=f"DENIED: path '{name}' escapes zone boundary",
                audit_id=audit_id,
            )

        # ── Execute write ─────────────────────────────────────
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

            audit_id = self._audit(
                action="write", caller=caller, zone=zone.value, name=name,
                content_hash=hashlib.sha256(data).hexdigest(),
                result="ok",
            )
            return WriteResult(success=True, path=dest, audit_id=audit_id)

        except Exception as e:
            audit_id = self._audit(
                action="write", caller=caller, zone=zone.value, name=name,
                content_hash=hashlib.sha256(data).hexdigest(),
                result="error", detail=str(e),
            )
            return WriteResult(success=False, error=str(e), audit_id=audit_id)

    def append(
        self,
        caller: str,
        zone: WriteZone,
        name: str,
        line: str,
        encrypt: bool = True,
    ) -> WriteResult:
        """Append a line to a file in a governed zone (for JSONL logs).

        Uses secure_append_line for DPAPI-encrypted append.
        Enforces the same caller/zone/path checks as write().
        """
        # ── Permission check ──────────────────────────────────
        allowed = _CALLER_PERMISSIONS.get(caller, set())
        if zone not in allowed:
            audit_id = self._audit(
                action="blocked",
                caller=caller,
                zone=zone.value,
                name=name,
                content_hash=hashlib.sha256(line.encode()).hexdigest()[:16],
                result="denied",
                detail=f"Caller '{caller}' may not append to zone '{zone.value}'",
            )
            return WriteResult(
                success=False,
                error=f"DENIED: caller '{caller}' cannot write to '{zone.value}'",
                audit_id=audit_id,
            )

        # ── Path safety ───────────────────────────────────────
        dest = _zone_root(zone) / name
        try:
            resolved = dest.resolve()
        except Exception as e:
            return WriteResult(success=False, error=f"Path resolution failed: {e}")

        zone_resolved = _zone_root(zone).resolve()
        if not str(resolved).startswith(str(zone_resolved)):
            audit_id = self._audit(
                action="blocked",
                caller=caller,
                zone=zone.value,
                name=name,
                content_hash=hashlib.sha256(line.encode()).hexdigest()[:16],
                result="denied",
                detail=f"Path traversal attempt: {name} resolves outside zone",
            )
            return WriteResult(
                success=False,
                error=f"DENIED: path '{name}' escapes zone boundary",
                audit_id=audit_id,
            )

        # ── Execute append ────────────────────────────────────
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if encrypt:
                secure_append_line(dest, line)
            else:
                with open(dest, "a", encoding="utf-8") as f:
                    f.write(line + "\n")

            audit_id = self._audit(
                action="append",
                caller=caller,
                zone=zone.value,
                name=name,
                content_hash=hashlib.sha256(line.encode()).hexdigest()[:16],
                result="ok",
            )
            return WriteResult(success=True, path=dest, audit_id=audit_id)

        except Exception as e:
            audit_id = self._audit(
                action="append",
                caller=caller,
                zone=zone.value,
                name=name,
                content_hash=hashlib.sha256(line.encode()).hexdigest()[:16],
                result="error",
                detail=str(e),
            )
            return WriteResult(success=False, error=str(e), audit_id=audit_id)

    # ── Promotion (zone transitions) ──────────────────────────

    def promote(
        self,
        caller: str,
        name: str,
        from_zone: WriteZone,
        to_zone: WriteZone,
    ) -> WriteResult:
        """Move a file from one zone to the next in the governance chain.

        Legal transitions:
            artifacts → staging       (human reviews AI output)
            staging   → implementation (human activates)

        Only 'human' callers may promote.
        """
        # ── Caller check ──────────────────────────────────────
        if caller != "human":
            audit_id = self._audit(
                action="blocked",
                caller=caller,
                zone=f"{from_zone.value}→{to_zone.value}",
                name=name,
                content_hash="",
                result="denied",
                detail="Only human callers may promote files between zones",
            )
            return WriteResult(
                success=False,
                error="DENIED: only 'human' callers may promote files",
                audit_id=audit_id,
            )

        # ── Transition legality ───────────────────────────────
        legal_dest = _PROMOTION_RULES.get(from_zone)
        if legal_dest != to_zone:
            audit_id = self._audit(
                action="blocked",
                caller=caller,
                zone=f"{from_zone.value}→{to_zone.value}",
                name=name,
                content_hash="",
                result="denied",
                detail=f"Illegal promotion: {from_zone.value} → {to_zone.value}",
            )
            return WriteResult(
                success=False,
                error=f"DENIED: cannot promote from '{from_zone.value}' to '{to_zone.value}'. "
                      f"Legal: {from_zone.value} → {legal_dest.value if legal_dest else 'nowhere'}",
                audit_id=audit_id,
            )

        # ── Source must exist ─────────────────────────────────
        src = _zone_root(from_zone) / name
        if not src.exists():
            return WriteResult(
                success=False,
                error=f"Source not found: {from_zone.value}/{name}",
            )

        # ── Execute move ──────────────────────────────────────
        dest = _zone_root(to_zone) / name
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            content_hash = hashlib.sha256(src.read_bytes()).hexdigest()
            shutil.move(str(src), str(dest))

            audit_id = self._audit(
                action="promote",
                caller=caller,
                zone=f"{from_zone.value}→{to_zone.value}",
                name=name,
                content_hash=content_hash,
                result="ok",
            )
            return WriteResult(success=True, path=dest, audit_id=audit_id)

        except Exception as e:
            audit_id = self._audit(
                action="promote",
                caller=caller,
                zone=f"{from_zone.value}→{to_zone.value}",
                name=name,
                content_hash="",
                result="error",
                detail=str(e),
            )
            return WriteResult(success=False, error=str(e), audit_id=audit_id)

    # ── Delete (governed) ─────────────────────────────────────

    def delete(self, caller: str, zone: WriteZone, name: str) -> WriteResult:
        """Delete a file from a governed zone.

        Only 'human' and 'system' callers may delete.
        AI callers cannot delete anything.
        """
        if caller == "ai":
            audit_id = self._audit(
                action="blocked",
                caller=caller,
                zone=zone.value,
                name=name,
                content_hash="",
                result="denied",
                detail="AI callers may not delete files",
            )
            return WriteResult(
                success=False,
                error="DENIED: AI callers cannot delete files",
                audit_id=audit_id,
            )

        path = _zone_root(zone) / name
        if not path.exists():
            return WriteResult(success=False, error=f"Not found: {zone.value}/{name}")

        try:
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            path.unlink()

            audit_id = self._audit(
                action="delete",
                caller=caller,
                zone=zone.value,
                name=name,
                content_hash=content_hash,
                result="ok",
            )
            return WriteResult(success=True, path=path, audit_id=audit_id)

        except Exception as e:
            return WriteResult(success=False, error=str(e))

    # ── Audit Trail ───────────────────────────────────────────

    # Rotation settings — bound the audit growth
    _AUDIT_MAX_BYTES: int = 10 * 1024 * 1024   # 10 MB triggers rotation
    _AUDIT_KEEP_LAST: int = 5                   # Keep last N rotated files

    def _maybe_rotate_audit(self) -> None:
        """Rotate audit log if it exceeds the size threshold.

        Renames current log to gateway_audit.{epoch}.jsonl, keeps last N.
        Never blocks critical writes on rotation failure.
        """
        try:
            if not self._audit_path.exists():
                return
            size = self._audit_path.stat().st_size
            if size < self._AUDIT_MAX_BYTES:
                return

            # Rotate: rename current → timestamped archive
            ts = int(time.time() * 1000)  # Millisecond precision avoids collisions
            rotated = self._audit_path.with_name(f"gateway_audit.{ts}.jsonl")
            self._audit_path.rename(rotated)

            # Prune old rotated files beyond _AUDIT_KEEP_LAST
            audit_dir = self._audit_path.parent
            archives = sorted(
                audit_dir.glob("gateway_audit.*.jsonl"),
                key=lambda p: p.stat().st_mtime,
            )
            while len(archives) > self._AUDIT_KEEP_LAST:
                oldest = archives.pop(0)
                oldest.unlink(missing_ok=True)

        except Exception:
            # Rotation failure MUST NOT block writes
            pass

    def _audit(
        self,
        action: str,
        caller: str,
        zone: str,
        name: str,
        content_hash: str,
        result: str,
        detail: str = "",
    ) -> str:
        """Append an entry to the audit trail. Returns the audit entry ID."""
        # Rotate before writing if past the size threshold
        self._maybe_rotate_audit()

        audit_id = f"{int(time.time() * 1000)}_{caller}_{action}"
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            caller=caller,
            zone=zone,
            name=name,
            content_hash=content_hash,
            result=result,
            detail=detail,
        )
        line = json.dumps(entry.__dict__, ensure_ascii=False)
        try:
            self._audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._audit_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # Audit failure must not block operations — but we log to stderr
            import sys
            print(f"⚠️  Audit write failed: {line}", file=sys.stderr)
        return audit_id

    def get_audit_trail(self, limit: int = 100) -> list[dict]:
        """Read the most recent audit entries."""
        if not self._audit_path.exists():
            return []
        lines = self._audit_path.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    # ── Status / Introspection ────────────────────────────────

    def status(self) -> dict:
        """Return current gateway status — zone file counts + audit stats."""
        zone_counts = {}
        for zone in WriteZone:
            root = _zone_root(zone)
            if root.exists():
                count = sum(1 for _ in root.rglob("*") if _.is_file())
            else:
                count = 0
            zone_counts[zone.value] = count

        audit_count = 0
        if self._audit_path.exists():
            audit_count = sum(1 for _ in open(self._audit_path, encoding="utf-8"))

        return {
            "root": str(self.root),
            "zones": zone_counts,
            "audit_entries": audit_count,
            "protected_zones": [z.value for z in ProtectedZone],
        }


# ── Module-level singleton ────────────────────────────────────
# Import and use: from security.gateway import gateway
gateway = ReaderWriter()
