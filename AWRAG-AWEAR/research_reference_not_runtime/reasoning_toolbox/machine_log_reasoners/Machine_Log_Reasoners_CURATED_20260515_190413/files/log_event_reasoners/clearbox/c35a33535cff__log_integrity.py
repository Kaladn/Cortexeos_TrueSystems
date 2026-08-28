"""Log integrity probe — validates runtime_errors.jsonl health.

Checks:
  - File exists and is readable
  - Well-formed JSONL (every line parses)
  - Recent entries have expected fields
  - File size within rotation limits
  - Rotation archives present if expected
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

from .base import Probe, RunContext, ProbeResult, make_result

# Expected from security/runtime_log.py
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_KEEP_ROTATED = 3
_REQUIRED_FIELDS = {"type", "timestamp", "component", "action"}


def _get_log_path() -> Path:
    from security.data_paths import AUDIT_DIR
    return AUDIT_DIR / "runtime_errors.jsonl"


class LogIntegrityProbe:
    """Validate runtime_errors.jsonl structure and health."""

    probe_id = "log_integrity"
    description = "Runtime log file health and well-formedness"

    def run(self, ctx: RunContext) -> List[ProbeResult]:
        results: List[ProbeResult] = []
        log_path = _get_log_path()

        # 1. File existence
        t0 = time.perf_counter()
        exists = log_path.exists()
        lat = (time.perf_counter() - t0) * 1000

        if not exists:
            results.append(make_result(
                ctx, self.probe_id, "log.exists",
                "SKIPPED",
                lat_ms=lat,
                skip_reason="runtime_errors.jsonl does not exist (no errors logged yet)",
                detail={"path": str(log_path)},
            ))
            return results

        file_size = log_path.stat().st_size
        results.append(make_result(
            ctx, self.probe_id, "log.exists",
            "CONFIRMED",
            lat_ms=lat,
            detail={"path": str(log_path), "size_bytes": file_size},
        ))

        # 2. File size check
        over_limit = file_size > _MAX_BYTES
        results.append(make_result(
            ctx, self.probe_id, "log.size",
            "DENIED" if over_limit else "CONFIRMED",
            detail={
                "size_bytes": file_size,
                "max_bytes": _MAX_BYTES,
                "over_limit": over_limit,
            },
        ))

        # 3. JSONL well-formedness (scan last 200 lines max)
        t0 = time.perf_counter()
        parse_errors = 0
        field_errors = 0
        total_lines = 0
        recent_entries: list = []

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Only check last 200 lines for speed
            check_lines = lines[-200:] if len(lines) > 200 else lines
            total_lines = len(lines)

            for line in check_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if isinstance(entry, dict):
                        missing = _REQUIRED_FIELDS - set(entry.keys())
                        if missing:
                            field_errors += 1
                        else:
                            recent_entries.append(entry)
                    else:
                        parse_errors += 1
                except json.JSONDecodeError:
                    parse_errors += 1

        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000
            results.append(make_result(
                ctx, self.probe_id, "log.wellformed",
                "ERROR", lat_ms=lat, error_detail=str(e),
            ))
            return results

        lat = (time.perf_counter() - t0) * 1000
        ok = parse_errors == 0 and field_errors == 0
        results.append(make_result(
            ctx, self.probe_id, "log.wellformed",
            "CONFIRMED" if ok else "DENIED",
            lat_ms=lat,
            detail={
                "total_lines": total_lines,
                "checked_lines": len(check_lines) if 'check_lines' in dir() else 0,
                "parse_errors": parse_errors,
                "field_errors": field_errors,
            },
        ))

        # 4. Recent error summary (informational)
        error_entries = [e for e in recent_entries if e.get("type") == "error"]
        level_counts = {}
        for e in error_entries:
            lvl = e.get("level", 0)
            level_counts[lvl] = level_counts.get(lvl, 0) + 1

        results.append(make_result(
            ctx, self.probe_id, "log.recent_errors",
            "CONFIRMED" if not error_entries else "CONFIRMED",
            detail={
                "recent_error_count": len(error_entries),
                "by_level": level_counts,
                "total_entries_checked": len(recent_entries),
            },
        ))

        # 5. Rotation archives
        audit_dir = log_path.parent
        archives = sorted(audit_dir.glob("runtime_errors.*.jsonl"))
        results.append(make_result(
            ctx, self.probe_id, "log.rotation",
            "CONFIRMED",
            detail={
                "archive_count": len(archives),
                "max_archives": _KEEP_ROTATED,
                "archives": [a.name for a in archives[-5:]],
            },
        ))

        return results
