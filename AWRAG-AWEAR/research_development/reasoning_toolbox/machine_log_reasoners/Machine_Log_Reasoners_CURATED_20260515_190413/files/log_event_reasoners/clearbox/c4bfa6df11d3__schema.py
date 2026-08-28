"""Diagnostic schema — ProbeResult and RunManifest dataclasses.

ProbeResult is the atomic unit of evidence. Every probe returns a list of them.
RunManifest is the diffable summary written once per diagnostic run.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ProbeResult:
    """Atomic unit of diagnostic evidence."""

    probe_id: str = ""          # "api_smoke", "environment", etc.
    check_id: str = ""          # "api_smoke.GET./api/stats", "env.lexicon"
    verdict: str = ""           # CONFIRMED | DENIED | SKIPPED | ERROR
    ts_utc: str = ""            # temporal doctrine
    mono_ns: int = 0
    boot_id: str = ""
    seq: int = 0                # strictly increasing across all probes in a run
    lat_ms: float = 0.0
    detail: Dict[str, Any] = field(default_factory=dict)
    skip_reason: str = ""       # only when SKIPPED
    error_detail: str = ""      # only when ERROR

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunManifest:
    """Diffable summary of a complete diagnostic run."""

    schema_version: str = "1.0"
    run_id: str = ""
    boot_id: str = ""
    ts_start: str = ""
    ts_end: str = ""
    elapsed_s: float = 0.0
    probes_run: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=lambda: {
        "confirmed": 0, "denied": 0, "skipped": 0, "error": 0, "total": 0,
    })
    all_skipped: bool = False
    by_probe: Dict[str, Dict[str, int]] = field(default_factory=dict)
    denied_details: List[Dict[str, Any]] = field(default_factory=list)
    error_details: List[Dict[str, Any]] = field(default_factory=list)
    skip_details: List[Dict[str, Any]] = field(default_factory=list)
    temporal_warnings: List[str] = field(default_factory=list)
    previous_run_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_results(
        run_id: str,
        boot_id: str,
        ts_start: str,
        ts_end: str,
        elapsed_s: float,
        results: List[ProbeResult],
        temporal_warnings: List[str],
        previous_run_id: str = "",
    ) -> "RunManifest":
        """Build manifest from a list of ProbeResults."""
        probes_seen: List[str] = []
        by_probe: Dict[str, Dict[str, int]] = {}
        counts = {"confirmed": 0, "denied": 0, "skipped": 0, "error": 0, "total": 0}
        denied_details: List[Dict[str, Any]] = []
        error_details: List[Dict[str, Any]] = []
        skip_details: List[Dict[str, Any]] = []

        for r in results:
            counts["total"] += 1
            v = r.verdict.lower()
            if v in counts:
                counts[v] += 1

            # Track probe-level counts
            if r.probe_id not in by_probe:
                by_probe[r.probe_id] = {"confirmed": 0, "denied": 0, "skipped": 0, "error": 0, "total": 0}
                probes_seen.append(r.probe_id)
            by_probe[r.probe_id]["total"] += 1
            if v in by_probe[r.probe_id]:
                by_probe[r.probe_id][v] += 1

            # Capture denial/error details
            if r.verdict == "DENIED":
                detail_entry: Dict[str, Any] = {"check_id": r.check_id}
                http_obs = r.detail.get("http", {})
                if isinstance(http_obs, dict):
                    detail_entry["http_code"] = http_obs.get("code", 0)
                    preview = http_obs.get("body_preview", "")
                    if preview:
                        detail_entry["body_preview"] = preview[:256]
                denied_details.append(detail_entry)

            elif r.verdict == "ERROR":
                error_details.append({
                    "check_id": r.check_id,
                    "exception": r.error_detail,
                })

            elif r.verdict == "SKIPPED":
                skip_details.append({
                    "check_id": r.check_id,
                    "reason": r.skip_reason or "no reason given",
                })

        non_skipped = counts["total"] - counts["skipped"]
        all_skipped = non_skipped == 0 and counts["total"] > 0

        return RunManifest(
            run_id=run_id,
            boot_id=boot_id,
            ts_start=ts_start,
            ts_end=ts_end,
            elapsed_s=round(elapsed_s, 2),
            probes_run=probes_seen,
            counts=counts,
            all_skipped=all_skipped,
            by_probe=by_probe,
            denied_details=denied_details,
            error_details=error_details,
            skip_details=skip_details,
            temporal_warnings=temporal_warnings,
            previous_run_id=previous_run_id,
        )
