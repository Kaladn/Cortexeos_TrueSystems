"""Diff — compare two diagnostic manifests for regression detection.

Detects:
  - Regressions: CONFIRMED → DENIED/ERROR
  - Improvements: DENIED/ERROR → CONFIRMED
  - New checks: only in current run
  - Removed checks: only in previous run
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _results_by_check_id(results_path: Path) -> Dict[str, dict]:
    """Load results JSONL and index by check_id."""
    index: Dict[str, dict] = {}
    if not results_path.exists():
        return index
    with open(results_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                cid = entry.get("check_id", "")
                if cid:
                    index[cid] = entry
            except json.JSONDecodeError:
                continue
    return index


def diff_manifests(
    prev: dict,
    curr: dict,
    prev_results_path: Optional[Path] = None,
    curr_results_path: Optional[Path] = None,
) -> dict:
    """Compare two manifest dicts and return a delta summary.

    Args:
        prev: Previous manifest dict
        curr: Current manifest dict
        prev_results_path: Optional path to previous results JSONL (for per-check diffs)
        curr_results_path: Optional path to current results JSONL

    Returns:
        Delta dict with regressions, improvements, new, removed, counts_delta.
    """
    delta: Dict[str, Any] = {
        "prev_run_id": prev.get("run_id", ""),
        "curr_run_id": curr.get("run_id", ""),
        "counts_delta": {},
        "regressions": [],
        "improvements": [],
        "new_checks": [],
        "removed_checks": [],
    }

    # Count deltas
    prev_counts = prev.get("counts", {})
    curr_counts = curr.get("counts", {})
    for key in ("confirmed", "denied", "skipped", "error", "total"):
        p = prev_counts.get(key, 0)
        c = curr_counts.get(key, 0)
        delta["counts_delta"][key] = c - p

    # Per-check diff (needs results JSONL)
    if prev_results_path and curr_results_path:
        prev_results = _results_by_check_id(prev_results_path)
        curr_results = _results_by_check_id(curr_results_path)

        prev_ids = set(prev_results.keys())
        curr_ids = set(curr_results.keys())

        # Regressions + Improvements
        for cid in prev_ids & curr_ids:
            pv = prev_results[cid].get("verdict", "")
            cv = curr_results[cid].get("verdict", "")
            if pv == cv:
                continue
            if pv == "CONFIRMED" and cv in ("DENIED", "ERROR"):
                delta["regressions"].append({
                    "check_id": cid,
                    "was": pv,
                    "now": cv,
                })
            elif pv in ("DENIED", "ERROR") and cv == "CONFIRMED":
                delta["improvements"].append({
                    "check_id": cid,
                    "was": pv,
                    "now": cv,
                })

        # New / Removed
        for cid in sorted(curr_ids - prev_ids):
            delta["new_checks"].append({
                "check_id": cid,
                "verdict": curr_results[cid].get("verdict", ""),
            })
        for cid in sorted(prev_ids - curr_ids):
            delta["removed_checks"].append({
                "check_id": cid,
                "verdict": prev_results[cid].get("verdict", ""),
            })

    return delta


def print_diff(delta: dict) -> None:
    """Print a human-readable diff summary to stdout."""
    print()
    print("  DIFF vs " + delta.get("prev_run_id", "unknown"))
    print("  " + "─" * 50)

    cd = delta.get("counts_delta", {})
    parts = []
    for key in ("confirmed", "denied", "error", "skipped"):
        d = cd.get(key, 0)
        if d != 0:
            sign = "+" if d > 0 else ""
            parts.append(f"{key}: {sign}{d}")
    if parts:
        print(f"  Counts: {', '.join(parts)}")

    regs = delta.get("regressions", [])
    if regs:
        print(f"\n  REGRESSIONS ({len(regs)}):")
        for r in regs:
            print(f"    {r['check_id']}: {r['was']} -> {r['now']}")

    imps = delta.get("improvements", [])
    if imps:
        print(f"\n  IMPROVEMENTS ({len(imps)}):")
        for r in imps:
            print(f"    {r['check_id']}: {r['was']} -> {r['now']}")

    new = delta.get("new_checks", [])
    if new:
        print(f"\n  NEW ({len(new)}):")
        for r in new[:10]:
            print(f"    {r['check_id']}: {r['verdict']}")
        if len(new) > 10:
            print(f"    ... and {len(new) - 10} more")

    removed = delta.get("removed_checks", [])
    if removed:
        print(f"\n  REMOVED ({len(removed)}):")
        for r in removed[:10]:
            print(f"    {r['check_id']}: {r['verdict']}")
        if len(removed) > 10:
            print(f"    ... and {len(removed) - 10} more")

    if not regs and not imps and not new and not removed:
        print("  No changes detected.")
    print()
