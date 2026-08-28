"""Diagnostic runner — orchestrates probes, writes results, CLI entry point.

Usage:
    python -m tools.diagnostic                    # all probes, console output
    python -m tools.diagnostic --json             # JSON manifest to stdout
    python -m tools.diagnostic --probes environment,service_liveness
    python -m tools.diagnostic --diff             # auto-diff against last run
    python -m tools.diagnostic --list             # list available probes
    python -m tools.diagnostic --skip-llm --skip-ollama

Exit codes:
    0 — green (at least one non-skipped CONFIRMED, zero DENIED/ERROR)
    1 — failures (DENIED or ERROR present)
    2 — all skipped (no meaningful work done)
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

# Force UTF-8 on Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from .temporal import BOOT_ID, ts_utc, make_run_id
from .schema import ProbeResult, RunManifest
from .probes import discover_probes
from .probes.base import RunContext


# ── Output Paths ─────────────────────────────────────────────

def _get_output_dir() -> Path:
    from security.data_paths import DIAGNOSTIC_DIR
    return DIAGNOSTIC_DIR


# ── Index + LATEST ───────────────────────────────────────────

def _write_latest(output_dir: Path, run_id: str, manifest_path: Path) -> None:
    """Write LATEST.json pointing to the most recent run."""
    latest = {
        "run_id": run_id,
        "manifest": manifest_path.name,
    }
    latest_path = output_dir / "LATEST.json"
    latest_path.write_text(json.dumps(latest, indent=2), encoding="utf-8")


def _append_index(output_dir: Path, manifest: RunManifest) -> None:
    """Append a one-line summary to index.jsonl."""
    entry = {
        "run_id": manifest.run_id,
        "ts_start": manifest.ts_start,
        "elapsed_s": manifest.elapsed_s,
        "counts": manifest.counts,
        "all_skipped": manifest.all_skipped,
        "probes_run": manifest.probes_run,
    }
    index_path = output_dir / "index.jsonl"
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, separators=(",", ":"), sort_keys=True) + "\n")


def _read_latest(output_dir: Path) -> str:
    """Read the previous run_id from LATEST.json, or empty string."""
    latest_path = output_dir / "LATEST.json"
    if not latest_path.exists():
        return ""
    try:
        data = json.loads(latest_path.read_text(encoding="utf-8"))
        return data.get("run_id", "")
    except Exception:
        return ""


# ── Blob Writer ──────────────────────────────────────────────

def _save_blob(blobs_dir: Path, result: ProbeResult) -> None:
    """Save full body to sidecar blob on DENIED/ERROR with body_preview."""
    if result.verdict not in ("DENIED", "ERROR"):
        return
    http_obs = result.detail.get("http", {})
    if not isinstance(http_obs, dict):
        return
    preview = http_obs.get("body_preview", "")
    if not preview:
        return
    blob_name = f"{result.seq:04d}_{result.check_id.replace('/', '_').replace('.', '_')}.txt"
    blob_path = blobs_dir / blob_name
    try:
        blob_path.write_text(preview, encoding="utf-8")
    except OSError:
        pass


# ── Console Output ───────────────────────────────────────────

def _print_header(run_id: str, bridge: str, probe_names: list[str]) -> None:
    print()
    print("=" * 66)
    print("  CLEARBOX AI — DIAGNOSTIC SUITE")
    print(f"  Run:     {run_id}")
    print(f"  Boot:    {BOOT_ID}")
    print(f"  Bridge:  {bridge}")
    print(f"  Probes:  {', '.join(probe_names)}")
    print("=" * 66)


def _print_result(r: ProbeResult) -> None:
    icon = {
        "CONFIRMED": "+",
        "DENIED": "!",
        "SKIPPED": "-",
        "ERROR": "X",
    }.get(r.verdict, "?")

    tag = {
        "CONFIRMED": "CONFIRMED",
        "DENIED": "  DENIED",
        "SKIPPED": " SKIPPED",
        "ERROR": "   ERROR",
    }.get(r.verdict, " UNKNOWN")

    ms_str = f"{r.lat_ms:5.0f}ms" if r.lat_ms else "      "

    detail = ""
    if r.verdict == "SKIPPED" and r.skip_reason:
        detail = f" — {r.skip_reason}"
    elif r.verdict == "ERROR" and r.error_detail:
        detail = f" — {r.error_detail}"
    elif r.verdict == "DENIED":
        http_obs = r.detail.get("http", {})
        if isinstance(http_obs, dict) and "code" in http_obs:
            code = http_obs.get("code", 0)
            if code == 0:
                detail = " — connection refused"
            elif code == 408:
                detail = " — timeout"
            elif code:
                detail = f" — HTTP {code}"
        elif r.detail.get("problems"):
            detail = f" — {r.detail['problems'][0]}"

    print(f"  [{icon}] {tag}  {ms_str}  {r.check_id}{detail}")


def _print_summary(manifest: RunManifest, output_dir: Path) -> None:
    c = manifest.counts
    print()
    print("=" * 66)
    # Compute overall verdict
    if manifest.all_skipped:
        overall = "NO COVERAGE — all checks skipped"
    elif c["denied"] > 0 or c["error"] > 0:
        overall = f"ISSUES FOUND — {c['denied']} denied, {c['error']} errors"
    elif c["skipped"] > 0:
        coverage_pct = round(100 * c["confirmed"] / max(c["total"], 1))
        overall = f"PARTIAL — {coverage_pct}% coverage ({c['skipped']} skipped)"
    else:
        overall = "CLEAN — 100% coverage"

    print(f"  {c['confirmed']} CONFIRMED  /  {c['denied']} DENIED  /  "
          f"{c['skipped']} SKIPPED  /  {c['error']} ERROR  /  {c['total']} TOTAL")
    print(f"  Verdict: {overall}")
    print(f"  Elapsed: {manifest.elapsed_s:.1f}s")
    print("=" * 66)

    if manifest.denied_details:
        print()
        print("  DENIED checks:")
        for d in manifest.denied_details:
            code = d.get("http_code", "")
            code_str = f"  [HTTP {code}]" if code else ""
            print(f"    {d['check_id']}{code_str}")

    if manifest.error_details:
        print()
        print("  ERROR checks:")
        for d in manifest.error_details:
            print(f"    {d['check_id']} — {d.get('exception', 'unknown')}")

    if manifest.skip_details:
        # Group by reason, show counts + examples
        from collections import Counter
        reason_counts: Counter = Counter()
        reason_examples: dict[str, list[str]] = {}
        for d in manifest.skip_details:
            reason = d.get("reason", "unknown")
            reason_counts[reason] += 1
            if reason not in reason_examples:
                reason_examples[reason] = []
            if len(reason_examples[reason]) < 3:
                reason_examples[reason].append(d["check_id"])
        print()
        print(f"  SKIPPED checks ({c['skipped']} total):")
        for reason, count in reason_counts.most_common():
            examples = reason_examples[reason]
            ex_str = ", ".join(examples)
            if count > len(examples):
                ex_str += f", ... (+{count - len(examples)} more)"
            print(f"    [{count:3d}] {reason}")
            print(f"          e.g. {ex_str}")

    if manifest.temporal_warnings:
        print()
        print("  TEMPORAL WARNINGS:")
        for w in manifest.temporal_warnings:
            print(f"    {w}")

    print()
    print(f"  Manifest: {output_dir / f'{manifest.run_id}.manifest.json'}")
    print(f"  Results:  {output_dir / f'{manifest.run_id}.results.jsonl'}")
    print()


# ── Main ─────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="ClearboxAI Diagnostic Suite")
    parser.add_argument("--bridge", default="https://127.0.0.1:5050",
                        help="Bridge URL (default: https://127.0.0.1:5050)")
    parser.add_argument("--llm", default="http://127.0.0.1:11435",
                        help="LLM proxy URL (default: http://127.0.0.1:11435)")
    parser.add_argument("--probes", default="",
                        help="Comma-separated probe IDs (empty = all)")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Skip LLM proxy probes")
    parser.add_argument("--skip-ollama", action="store_true",
                        help="Skip direct Ollama probes")
    parser.add_argument("--json", action="store_true",
                        help="Output manifest as JSON to stdout")
    parser.add_argument("--diff", action="store_true",
                        help="Auto-diff against most recent previous run")
    parser.add_argument("--list", action="store_true",
                        help="List available probes and exit")
    args = parser.parse_args()

    # List mode
    all_probes = discover_probes()
    if args.list:
        for p in all_probes:
            print(f"  {p.probe_id:24s} {p.description}")
        sys.exit(0)

    # Filter probes
    if args.probes:
        requested = set(args.probes.split(","))
        probes = [p for p in all_probes if p.probe_id in requested]
        unknown = requested - {p.probe_id for p in probes}
        if unknown:
            print(f"  WARNING: Unknown probes: {', '.join(sorted(unknown))}", file=sys.stderr)
    else:
        probes = all_probes

    if not probes:
        print("  No probes selected.", file=sys.stderr)
        sys.exit(2)

    # Setup
    run_id = make_run_id()
    output_dir = _get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    blobs_dir = output_dir / f"{run_id}.blobs"

    previous_run_id = _read_latest(output_dir)

    ctx = RunContext(
        run_id=run_id,
        bridge_url=args.bridge.rstrip("/"),
        llm_url=args.llm.rstrip("/"),
        skip_llm=args.skip_llm,
        skip_ollama=args.skip_ollama,
        output_dir=output_dir,
        blobs_dir=blobs_dir,
    )

    if not args.json:
        _print_header(run_id, ctx.bridge_url, [p.probe_id for p in probes])

    # Execute probes
    ts_start = ts_utc()
    t0 = time.perf_counter()
    all_results: list[ProbeResult] = []
    temporal_warnings: list[str] = []
    current_probe_id = ""

    for probe in probes:
        if not args.json and probe.probe_id != current_probe_id:
            current_probe_id = probe.probe_id
            print(f"\n  {probe.probe_id.upper()}")
            print(f"  {'─' * 50}")

        try:
            results = probe.run(ctx)
        except Exception as e:
            # Probes should never raise, but runner catches everything
            results = [ProbeResult(
                probe_id=probe.probe_id,
                check_id=f"{probe.probe_id}.runner_catch",
                verdict="ERROR",
                ts_utc=ts_utc(),
                mono_ns=0,
                boot_id=BOOT_ID,
                seq=ctx.next_seq(),
                error_detail=f"Probe raised: {e}",
            )]

        for r in results:
            all_results.append(r)
            if not args.json:
                _print_result(r)
            # Save blob sidecar on DENIED/ERROR
            _save_blob(blobs_dir, r)

    elapsed = time.perf_counter() - t0
    ts_end = ts_utc()

    # Clean up empty blobs dir
    if blobs_dir.exists() and not any(blobs_dir.iterdir()):
        try:
            blobs_dir.rmdir()
        except OSError:
            pass

    # Build manifest
    manifest = RunManifest.from_results(
        run_id=run_id,
        boot_id=BOOT_ID,
        ts_start=ts_start,
        ts_end=ts_end,
        elapsed_s=elapsed,
        results=all_results,
        temporal_warnings=temporal_warnings,
        previous_run_id=previous_run_id,
    )

    # Write results JSONL
    results_path = output_dir / f"{run_id}.results.jsonl"
    with open(results_path, "w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r.to_dict(), separators=(",", ":"), sort_keys=True) + "\n")

    # Write manifest
    manifest_path = output_dir / f"{run_id}.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # Update LATEST.json + index.jsonl
    _write_latest(output_dir, run_id, manifest_path)
    _append_index(output_dir, manifest)

    # Output
    if args.json:
        print(json.dumps(manifest.to_dict(), indent=2))
    else:
        _print_summary(manifest, output_dir)

    # Auto-diff
    if args.diff and previous_run_id:
        try:
            from .diff import diff_manifests, print_diff
            prev_manifest_path = output_dir / f"{previous_run_id}.manifest.json"
            prev_results_path = output_dir / f"{previous_run_id}.results.jsonl"
            if prev_manifest_path.exists():
                prev_data = json.loads(prev_manifest_path.read_text(encoding="utf-8"))
                curr_data = manifest.to_dict()
                delta = diff_manifests(
                    prev_data, curr_data,
                    prev_results_path=prev_results_path,
                    curr_results_path=results_path,
                )
                # Write diff file
                diff_path = output_dir / f"{run_id}.diff.json"
                diff_path.write_text(json.dumps(delta, indent=2), encoding="utf-8")
                if not args.json:
                    print_diff(delta)
        except Exception as e:
            if not args.json:
                print(f"  DIFF ERROR: {e}")

    # Exit code: 0=green, 1=failures, 2=all-skipped
    c = manifest.counts
    if manifest.all_skipped:
        sys.exit(2)
    elif c["denied"] + c["error"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
