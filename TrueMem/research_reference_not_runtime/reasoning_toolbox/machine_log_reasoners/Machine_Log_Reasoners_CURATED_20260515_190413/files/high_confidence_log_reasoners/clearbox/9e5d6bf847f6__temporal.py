"""Temporal Doctrine — System Rule #1.

Single source of truth for time primitives used by Masher, Witness,
and any future tool that produces receipts in this process.

Rules enforced:
  - ts_utc:  RFC3339 UTC, Z suffix, exactly 3-digit milliseconds
  - mono_ns: time.monotonic_ns(), never regresses within a process
  - seq:     strictly increasing within run_id, starting at 1
  - boot_id: one GUID per OS process, shared by all actors

Canonical event_id: "{node_id}:{boot_id}:{run_id}:{seq}"
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from typing import List

# ── Process-wide identity ────────────────────────────────────────

BOOT_ID: str = uuid.uuid4().hex[:12]
"""Stable per process start. Shared by Masher + Witness."""

NODE_ID: str = "local"
"""Node identity. Override for distributed runs."""


# ── Timestamp primitives ─────────────────────────────────────────

def ts_utc() -> str:
    """RFC3339 UTC with Z suffix and exactly 3-digit milliseconds.

    Example: 2026-02-22T08:30:00.123Z
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def mono_ns() -> int:
    """Monotonic nanoseconds — process-relative, never regresses."""
    return time.monotonic_ns()


# ── Temporal Integrity Gate ──────────────────────────────────────

# Exact shape: YYYY-MM-DDTHH:MM:SS.mmmZ  (always 24 chars)
_TS_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def validate_temporal(
    record: dict,
    last_seq: int,
    last_mono_ns: int,
    last_ts_utc: str,
    label: str = "event",
) -> tuple[List[str], int, int, str]:
    """Validate temporal + causal ordering on any record (Action or Proof).

    Args:
        record:       dict with ts_utc, mono_ns, seq fields
        last_seq:     previous record's seq (0 if first)
        last_mono_ns: previous record's mono_ns (0 if first)
        last_ts_utc:  previous record's ts_utc ("" if first)
        label:        "action" or "proof" for warning messages

    Returns:
        (warnings, updated_last_seq, updated_last_mono_ns, updated_last_ts_utc)
    """
    warnings: List[str] = []
    ts = record.get("ts_utc", "")
    mono = record.get("mono_ns", 0)
    seq = record.get("seq", 0)

    # ── seq validation ───────────────────────────────────────
    if seq < 1:
        warnings.append(f"{label} seq={seq}: seq must be >= 1")
    if last_seq > 0 and seq <= last_seq:
        warnings.append(f"{label} seq={seq}: seq not strictly increasing (last={last_seq})")

    # ── ts_utc validation ────────────────────────────────────
    if not ts:
        warnings.append(f"{label} seq={seq}: ts_utc missing")
    elif not _TS_UTC_RE.match(ts):
        warnings.append(f"{label} seq={seq}: ts_utc malformed (expected YYYY-MM-DDTHH:MM:SS.mmmZ): {ts}")

    # ts_utc must not regress (lexicographic compare is safe with fixed-width format)
    if ts and last_ts_utc and ts < last_ts_utc:
        warnings.append(f"{label} seq={seq}: ts_utc regressed {last_ts_utc} -> {ts}")

    # ── mono_ns validation ───────────────────────────────────
    # Use explicit numeric check — mono_ns of 0 is valid (don't rely on truthiness)
    if last_mono_ns > 0 and mono < last_mono_ns:
        warnings.append(f"{label} seq={seq}: mono_ns regressed {last_mono_ns} -> {mono}")

    # ── Update tracking ──────────────────────────────────────
    updated_seq = seq if seq > 0 else last_seq
    updated_mono = mono if mono > 0 else last_mono_ns
    updated_ts = ts if ts else last_ts_utc

    return warnings, updated_seq, updated_mono, updated_ts
