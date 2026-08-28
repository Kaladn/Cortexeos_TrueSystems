"""Temporal audit probe — validates temporal doctrine on recent JSONL files.

Scoped narrowly: checks P5's own results.jsonl files and optionally
tests/smoke/ proof/action JSONL files if they exist.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List

from .base import Probe, RunContext, ProbeResult, make_result
from ..temporal import validate_temporal


def _get_diagnostic_dir() -> Path:
    from security.data_paths import DIAGNOSTIC_DIR
    return DIAGNOSTIC_DIR


def _validate_jsonl(path: Path, label: str) -> tuple[int, int, List[str]]:
    """Validate temporal ordering in a JSONL file.

    Returns (total_records, valid_records, warnings).
    """
    if not path.exists():
        return 0, 0, []

    warnings: List[str] = []
    total = 0
    valid = 0
    last_seq = 0
    last_mono_ns = 0
    last_ts_utc = ""

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"{label}: line {total} is not valid JSON")
                continue

            w, last_seq, last_mono_ns, last_ts_utc = validate_temporal(
                record, last_seq, last_mono_ns, last_ts_utc, label=label,
            )
            warnings.extend(w)
            if not w:
                valid += 1

    return total, valid, warnings


class TemporalAuditProbe:
    """Validates temporal doctrine on recent diagnostic JSONL files."""

    probe_id = "temporal_audit"
    description = "Temporal doctrine validation on recent JSONL"

    def run(self, ctx: RunContext) -> List[ProbeResult]:
        results: List[ProbeResult] = []
        diag_dir = _get_diagnostic_dir()

        # Find the most recent results.jsonl
        if not diag_dir.exists():
            results.append(make_result(
                ctx, self.probe_id, "temporal.diagnostic_dir",
                "SKIPPED",
                skip_reason="Diagnostic output directory does not exist",
            ))
            return results

        result_files = sorted(diag_dir.glob("R_*.results.jsonl"), reverse=True)
        if not result_files:
            results.append(make_result(
                ctx, self.probe_id, "temporal.results_files",
                "SKIPPED",
                skip_reason="No results JSONL files found",
            ))
            return results

        # Validate the most recent 3 results files
        for path in result_files[:3]:
            label = path.stem
            t0 = time.perf_counter()
            total, valid, warnings = _validate_jsonl(path, label)
            lat = (time.perf_counter() - t0) * 1000

            if warnings:
                results.append(make_result(
                    ctx, self.probe_id, f"temporal.{label}",
                    "DENIED",
                    lat_ms=lat,
                    detail={
                        "file": path.name,
                        "total_records": total,
                        "valid_records": valid,
                        "warning_count": len(warnings),
                        "warnings": warnings[:10],
                    },
                ))
            else:
                results.append(make_result(
                    ctx, self.probe_id, f"temporal.{label}",
                    "CONFIRMED",
                    lat_ms=lat,
                    detail={
                        "file": path.name,
                        "total_records": total,
                        "valid_records": valid,
                    },
                ))

        # Optionally check smoke test logs
        smoke_dir = Path(__file__).resolve().parents[3] / "tests" / "smoke" / "logs"
        if smoke_dir.exists():
            proof_files = sorted(smoke_dir.glob("R_*.proof.jsonl"), reverse=True)
            for path in proof_files[:1]:
                label = f"smoke.{path.stem}"
                t0 = time.perf_counter()
                total, valid, warnings = _validate_jsonl(path, label)
                lat = (time.perf_counter() - t0) * 1000

                if warnings:
                    results.append(make_result(
                        ctx, self.probe_id, f"temporal.{label}",
                        "DENIED", lat_ms=lat,
                        detail={"file": str(path), "warnings": warnings[:5]},
                    ))
                else:
                    results.append(make_result(
                        ctx, self.probe_id, f"temporal.{label}",
                        "CONFIRMED", lat_ms=lat,
                        detail={"file": str(path), "total_records": total},
                    ))

        return results
