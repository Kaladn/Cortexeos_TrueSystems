"""Masher + Witness Smoke Test — orchestration runner.

Two actors, two logs, one run_id:
  - Masher declares intent (ACTION events)
  - Witness executes, captures evidence, writes verdicts (PROOF events)

Usage:
    python -m tests.smoke.run
    python -m tests.smoke.run --bridge http://127.0.0.1:5050
    python -m tests.smoke.run --allow-ingest --watch-fs
    python -m tests.smoke.run --skip-llm --skip-ollama
    python -m tests.smoke.run --session-cookie "<clearbox_session>"
    python -m tests.smoke.run --rate-limit-retries 2 --rate-limit-backoff-ms 300
    python -m tests.smoke.run --max-skipped 0 --max-rate-limited 0
    python -m tests.smoke.run --max-unexpected-skips 0
    python -m tests.smoke.run --bridge-preflight-timeout-ms 3000
    python -m tests.smoke.run --json
"""

from __future__ import annotations

import argparse
from collections import Counter
import io
import json
import os
import socket
import sys
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Force UTF-8 on Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from .masher import Masher, discover_endpoints, Action
from .temporal import BOOT_ID
from .witness import Witness, Proof


# ── Run ID ───────────────────────────────────────────────────────

def _make_run_id() -> str:
    """Temporal-doctrine-compliant run ID: R_{UTC date}_{HHMMSS}Z"""
    now = datetime.now(timezone.utc)
    return f"R_{now.strftime('%Y_%m_%d_%H%M%S')}Z"


# ── Console Output ───────────────────────────────────────────────

def _print_header(run_id: str, bridge: str, llm: str, mode: str):
    print()
    print("=" * 66)
    print("  CLEARBOX AI — MASHER + WITNESS SMOKE TEST")
    print(f"  Run:     {run_id}")
    print(f"  Boot:    {BOOT_ID}")
    print(f"  Bridge:  {bridge}")
    print(f"  LLM:     {llm}")
    print(f"  Mode:    {mode}")
    print("=" * 66)


def _print_action_proof(action: Action, proof: Proof):
    icon = {
        "CONFIRMED": "+",
        "DENIED": "!",
        "SKIPPED": "-",
        "ERROR": "X",
    }.get(proof.verdict, "?")

    tag = {
        "CONFIRMED": "CONFIRMED",
        "DENIED": "  DENIED",
        "SKIPPED": "  SKIPPED",
        "ERROR": "   ERROR",
    }.get(proof.verdict, " UNKNOWN")

    # Extract latency
    http_obs = proof.observations.get("http", {})
    lat = http_obs.get("lat_ms", 0) if isinstance(http_obs, dict) else 0
    ms_str = f"{lat:5.0f}ms" if lat else "      "

    # Extract path from URL
    url = action.url
    for prefix in ("https://127.0.0.1:5050", "http://127.0.0.1:5050",
                    "https://127.0.0.1:11435", "http://127.0.0.1:11435",
                    "http://127.0.0.1:11434", "http://127.0.0.1:8080",
                    "https://127.0.0.1:8080",
                    "wss://127.0.0.1:5050", "ws://127.0.0.1:5050"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break

    # Target tag for non-bridge
    target_tag = ""
    if action.target != "bridge":
        target_tag = f" ({action.target})"

    # Detail
    detail = ""
    if proof.verdict == "DENIED":
        code = http_obs.get("code", 0) if isinstance(http_obs, dict) else 0
        if code == 0:
            detail = " — connection refused"
        elif code == -1:
            detail = " — connection refused"
        elif code == -2:
            detail = " — websocket-client not installed"
        elif code == 408:
            detail = " — timeout"
        else:
            detail = f" — HTTP {code}"
    elif proof.verdict == "SKIPPED":
        detail = f" — {action.skip_reason}" if action.skip_reason else ""
    elif proof.verdict == "ERROR":
        exc = proof.observations.get("exception", "")
        detail = f" — {exc}" if exc else ""

    print(f"  [{icon}] {tag}  {ms_str}  {action.action:5s}  {url}{target_tag}{detail}")


def _group_actions(actions: list[Action]) -> dict[str, list[int]]:
    """Group action indices by URL path prefix for section headers."""
    groups: dict[str, list[int]] = {}
    for i, a in enumerate(actions):
        # Determine area from URL path
        url = a.url
        for prefix in ("http://127.0.0.1:5050", "http://127.0.0.1:11435",
                        "http://127.0.0.1:11434", "http://127.0.0.1:8080",
                        "ws://127.0.0.1:5050"):
            if url.startswith(prefix):
                url = url[len(prefix):]
                break

        if a.target in ("ollama", "llm", "ui"):
            area = a.target.upper()
        elif url.startswith("/ws"):
            area = "WEBSOCKET"
        elif url.startswith("/api/"):
            parts = url.split("/")
            if len(parts) >= 3:
                area = parts[2].upper().replace("-", "_")
            else:
                area = "API"
        else:
            area = "OTHER"

        groups.setdefault(area, []).append(i)
    return groups


def _http_code(proof: Proof) -> int | None:
    http_obs = proof.observations.get("http")
    if not isinstance(http_obs, dict):
        return None
    code = http_obs.get("code")
    return code if isinstance(code, int) else None


def _print_summary(
    actions: list[Action],
    proofs: list[Proof],
    run_id: str,
    logs_dir: Path,
    elapsed: float,
):
    confirmed = sum(1 for p in proofs if p.verdict == "CONFIRMED")
    denied = sum(1 for p in proofs if p.verdict == "DENIED")
    skipped = sum(1 for p in proofs if p.verdict == "SKIPPED")
    errors = sum(1 for p in proofs if p.verdict == "ERROR")
    rate_limited = sum(
        1 for p in proofs if _http_code(p) == 429
    )
    auth_denied = sum(
        1 for p in proofs if _http_code(p) in (401, 403)
    )
    transport_flake = sum(
        1 for p in proofs if _http_code(p) in (0, -1, 408)
    )
    server_errors = sum(
        1 for p in proofs if (_http_code(p) or -1) >= 500
    )
    total_http_retries = sum(
        int(p.observations.get("http", {}).get("retries", 0) or 0)
        for p in proofs
    )
    skip_reason_counts: Counter[str] = Counter()
    for action, proof in zip(actions, proofs):
        if proof.verdict != "SKIPPED":
            continue
        reason = (
            proof.observations.get("reason")
            or action.skip_reason
            or "unspecified"
        )
        skip_reason_counts[str(reason)] += 1
    expected_skip_reasons = {
        "--skip-llm",
        "--skip-ollama",
        "POST requires --allow-writes",
        "needs --allow-ingest",
        "DELETE method",
        "destructive keyword",
        "unfilled path param",
        "websocket-client not installed",
        "rate_limited",
    }
    unexpected_skip_count = sum(
        count for reason, count in skip_reason_counts.items()
        if reason not in expected_skip_reasons
    )

    print()
    print("=" * 66)
    print(f"  {confirmed} CONFIRMED  /  {denied} DENIED  /  {skipped} SKIPPED  /  {errors} ERROR  /  {len(proofs)} TOTAL")
    print(f"  Rate-limited responses: {rate_limited}")
    print(f"  Auth denials (401/403): {auth_denied}")
    print(f"  Transport flake (0/-1/408): {transport_flake}")
    print(f"  Server 5xx responses: {server_errors}")
    print(f"  Total 429 retries: {total_http_retries}")
    print(f"  Unexpected skips: {unexpected_skip_count}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print("=" * 66)
    if skip_reason_counts:
        print("  Skip Reasons:")
        for reason, count in skip_reason_counts.most_common(5):
            print(f"    {reason}: {count}")

    if denied:
        print()
        print("  DENIED endpoints:")
        for a, p in zip(actions, proofs):
            if p.verdict == "DENIED":
                http_obs = p.observations.get("http", {})
                code = http_obs.get("code", 0) if isinstance(http_obs, dict) else 0
                print(f"    {a.action:5s} {a.url}  [{code}]")

    if errors:
        print()
        print("  ERROR probes:")
        for a, p in zip(actions, proofs):
            if p.verdict == "ERROR":
                exc = p.observations.get("exception", "unknown")
                print(f"    {a.action:5s} {a.url}  — {exc}")

    print()
    print(f"  Actions: {logs_dir / f'{run_id}.actions.jsonl'}")
    print(f"  Proofs:  {logs_dir / f'{run_id}.proof.jsonl'}")
    print()


def _bridge_tcp_preflight(bridge_url: str, timeout_ms: int) -> tuple[bool, str]:
    parsed = urlparse(bridge_url)
    host = (parsed.hostname or "").strip()
    if not host:
        return False, "invalid bridge URL (missing host)"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    timeout_s = max(0.1, float(timeout_ms) / 1000.0)
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True, ""
    except OSError as exc:
        return False, f"{type(exc).__name__}: {exc}"


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Clearbox AI Masher + Witness Smoke Test")
    parser.add_argument("--bridge", default="https://127.0.0.1:5050",
                        help="Bridge URL (default: https://127.0.0.1:5050)")
    parser.add_argument("--llm", default="http://127.0.0.1:11435",
                        help="LLM proxy URL (default: http://127.0.0.1:11435)")
    parser.add_argument("--allow-writes", action="store_true",
                        help="Enable mutation endpoints")
    parser.add_argument("--allow-ingest", action="store_true",
                        help="Enable dry_run ingest endpoints")
    parser.add_argument("--watch-fs", action="store_true",
                        help="Enable filesystem delta scanning (slower)")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Skip LLM proxy probes")
    parser.add_argument("--skip-ollama", action="store_true",
                        help="Skip direct Ollama probes")
    parser.add_argument("--session-cookie", default=os.environ.get("CLEARBOX_SMOKE_SESSION", ""),
                        help="Optional clearbox_session cookie value for authenticated bridge probes")
    parser.add_argument("--rate-limit-retries", type=int,
                        default=int(os.environ.get("CLEARBOX_SMOKE_RL_RETRIES", "2")),
                        help="Retries for HTTP 429 responses (default: 2)")
    parser.add_argument("--rate-limit-backoff-ms", type=int,
                        default=int(os.environ.get("CLEARBOX_SMOKE_RL_BACKOFF_MS", "300")),
                        help="Base backoff in ms for 429 retries (default: 300)")
    parser.add_argument("--rate-limit-deny", action="store_true",
                        help="Treat persistent 429 as DENIED (default behavior treats as SKIPPED)")
    parser.add_argument("--max-skipped", type=int,
                        default=int(os.environ.get("CLEARBOX_SMOKE_MAX_SKIPPED", "-1")),
                        help="Fail run if skipped count exceeds this value (-1 disables check)")
    parser.add_argument("--max-rate-limited", type=int,
                        default=int(os.environ.get("CLEARBOX_SMOKE_MAX_RATE_LIMITED", "-1")),
                        help="Fail run if 429 count exceeds this value (-1 disables check)")
    parser.add_argument("--max-unexpected-skips", type=int,
                        default=int(os.environ.get("CLEARBOX_SMOKE_MAX_UNEXPECTED_SKIPS", "-1")),
                        help="Fail run if unexpected skip reasons exceed this value (-1 disables check)")
    parser.add_argument("--bridge-preflight-timeout-ms", type=int,
                        default=int(os.environ.get("CLEARBOX_SMOKE_PREFLIGHT_TIMEOUT_MS", "2000")),
                        help="TCP preflight timeout for bridge availability check in ms (default: 2000)")
    parser.add_argument("--json", action="store_true",
                        help="Output summary as JSON")
    args = parser.parse_args()

    bridge = args.bridge.rstrip("/")
    llm = args.llm.rstrip("/")
    run_id = _make_run_id()
    session_cookie = (args.session_cookie or "").strip()
    bridge_auth_headers = {"X-Clearbox-CSRF": "smoke-test"}
    bridge_auth_cookies = {"clearbox_session": session_cookie} if session_cookie else {}

    # Mode label
    mode_parts = ["READ_ONLY"]
    if args.allow_writes:
        mode_parts = ["WRITES_ENABLED"]
    if args.allow_ingest:
        mode_parts.append("+INGEST")
    if args.watch_fs:
        mode_parts.append("+FS_WATCH")
    if session_cookie:
        mode_parts.append("+AUTH")
    mode_parts.append(f"+RLx{max(0, args.rate_limit_retries)}")
    if args.rate_limit_deny:
        mode_parts.append("+RL_DENY")
    mode = " ".join(mode_parts)

    # Directories
    smoke_dir = Path(__file__).parent
    logs_dir = smoke_dir / "logs"
    artifacts_dir = smoke_dir / "artifacts" / run_id
    logs_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    preflight_ok, preflight_error = _bridge_tcp_preflight(
        bridge,
        args.bridge_preflight_timeout_ms,
    )
    preflight_status = {
        "ok": preflight_ok,
        "target": "bridge",
        "url": bridge,
        "timeout_ms": args.bridge_preflight_timeout_ms,
        "error": preflight_error,
    }
    if not preflight_ok:
        failure = (
            f"bridge preflight failed for {bridge} "
            f"(timeout_ms={args.bridge_preflight_timeout_ms}): {preflight_error}"
        )
        if args.json:
            summary = {
                "run_id": run_id,
                "boot_id": BOOT_ID,
                "elapsed_s": 0.0,
                "confirmed": 0,
                "denied": 0,
                "skipped": 0,
                "error": 0,
                "rate_limited": 0,
                "auth_denied": 0,
                "transport_flake": 0,
                "server_errors": 0,
                "total_http_retries": 0,
                "skip_reasons": {},
                "unexpected_skips": {
                    "count": 0,
                    "reasons": {},
                    "sample_endpoints": [],
                },
                "total": 0,
                "all_skipped": False,
                "temporal_warnings": [],
                "thresholds": {
                    "max_skipped": args.max_skipped,
                    "max_rate_limited": args.max_rate_limited,
                    "max_unexpected_skips": args.max_unexpected_skips,
                    "ok": False,
                },
                "threshold_failures": [failure],
                "preflight": preflight_status,
                "logs": {
                    "actions": str(logs_dir / f"{run_id}.actions.jsonl"),
                    "proofs": str(logs_dir / f"{run_id}.proof.jsonl"),
                },
                "denied_endpoints": [],
                "error_endpoints": [],
            }
            print(json.dumps(summary, indent=2))
        else:
            _print_header(run_id, bridge, llm, mode)
            print()
            print("  PRE-FLIGHT FAILURE")
            print(f"  {failure}")
            print()
        sys.exit(1)

    if not args.json:
        _print_header(run_id, bridge, llm, mode)

    # ── Phase 1: OpenAPI Discovery ───────────────────────────

    if not args.json:
        print()
        print("  Discovering endpoints via /openapi.json ...")

    spec = discover_endpoints(
        bridge,
        auth_headers=bridge_auth_headers,
        auth_cookies=bridge_auth_cookies,
    )
    from .masher import FALLBACK_ROUTES
    if spec:
        path_count = sum(len(methods) for methods in spec.get("paths", {}).values())
        if not args.json:
            print(f"  Found {path_count} operations across {len(spec.get('paths', {}))} paths")
    else:
        if not args.json:
            print("  WARNING: /openapi.json unavailable (500 or unreachable)")
            print(f"  Using fallback endpoint list ({len(FALLBACK_ROUTES)} known routes)")

    # ── Phase 2: Initialize Actors ───────────────────────────

    masher = Masher(
        run_id=run_id,
        bridge_url=bridge,
        llm_url=llm,
        logs_dir=logs_dir,
        allow_writes=args.allow_writes,
        allow_ingest=args.allow_ingest,
        skip_llm=args.skip_llm,
        skip_ollama=args.skip_ollama,
    )

    witness = Witness(
        run_id=run_id,
        logs_dir=logs_dir,
        artifacts_dir=artifacts_dir,
        watch_fs=args.watch_fs,
        bridge_auth_headers=bridge_auth_headers,
        bridge_auth_cookies=bridge_auth_cookies,
        rate_limit_retries=args.rate_limit_retries,
        rate_limit_backoff_ms=args.rate_limit_backoff_ms,
        rate_limit_as_skip=not args.rate_limit_deny,
    )

    # Witness captures OpenAPI snapshot as first artifact
    if spec:
        witness.capture_openapi(bridge)

    # ── Phase 3: Build Queue ─────────────────────────────────

    actions = masher.build_queue(spec)

    if not args.json:
        total = len(actions)
        skips = sum(1 for a in actions if a.intent == "SKIP")
        print(f"  Queue: {total} actions ({total - skips} to execute, {skips} to skip)")

    # ── Phase 4: Execute ─────────────────────────────────────

    t0 = time.perf_counter()
    proofs: list[Proof] = []
    groups = _group_actions(actions)
    printed_areas: set[str] = set()

    for i, action in enumerate(actions):
        # Section header
        if not args.json:
            for area, indices in groups.items():
                if i in indices and area not in printed_areas:
                    printed_areas.add(area)
                    print(f"\n  {area}")
                    print(f"  {'─' * 50}")
                    break

        # Masher writes intent
        masher.write_action(action)

        # Witness observes and proves
        proof = witness.observe(asdict(action))
        proofs.append(proof)

        if not args.json:
            _print_action_proof(action, proof)

    elapsed = time.perf_counter() - t0

    # ── Phase 5: Summary ─────────────────────────────────────

    # Collect temporal warnings
    temporal_warnings = witness._temporal_warnings

    confirmed = sum(1 for p in proofs if p.verdict == "CONFIRMED")
    denied = sum(1 for p in proofs if p.verdict == "DENIED")
    skipped = sum(1 for p in proofs if p.verdict == "SKIPPED")
    errors = sum(1 for p in proofs if p.verdict == "ERROR")
    rate_limited = sum(
        1 for p in proofs if _http_code(p) == 429
    )
    auth_denied = sum(
        1 for p in proofs if _http_code(p) in (401, 403)
    )
    transport_flake = sum(
        1 for p in proofs if _http_code(p) in (0, -1, 408)
    )
    server_errors = sum(
        1 for p in proofs if (_http_code(p) or -1) >= 500
    )
    total_http_retries = sum(
        int(p.observations.get("http", {}).get("retries", 0) or 0)
        for p in proofs
    )
    skip_reason_counts: Counter[str] = Counter()
    for action, proof in zip(actions, proofs):
        if proof.verdict != "SKIPPED":
            continue
        reason = (
            proof.observations.get("reason")
            or action.skip_reason
            or "unspecified"
        )
        skip_reason_counts[str(reason)] += 1
    expected_skip_reasons = {
        "--skip-llm",
        "--skip-ollama",
        "POST requires --allow-writes",
        "needs --allow-ingest",
        "DELETE method",
        "destructive keyword",
        "unfilled path param",
        "websocket-client not installed",
        "rate_limited",
    }
    unexpected_skip_count = sum(
        count for reason, count in skip_reason_counts.items()
        if reason not in expected_skip_reasons
    )
    unexpected_skip_reasons = {
        reason: count for reason, count in skip_reason_counts.items()
        if reason not in expected_skip_reasons
    }
    unexpected_skip_endpoints = []
    for action, proof in zip(actions, proofs):
        if proof.verdict != "SKIPPED":
            continue
        reason = (
            proof.observations.get("reason")
            or action.skip_reason
            or "unspecified"
        )
        if reason in expected_skip_reasons:
            continue
        unexpected_skip_endpoints.append({
            "method": action.action,
            "url": action.url,
            "reason": str(reason),
        })
    threshold_failures = []
    if args.max_skipped >= 0 and skipped > args.max_skipped:
        threshold_failures.append(
            f"skipped {skipped} exceeds max_skipped {args.max_skipped}"
        )
    if args.max_rate_limited >= 0 and rate_limited > args.max_rate_limited:
        threshold_failures.append(
            f"rate_limited {rate_limited} exceeds max_rate_limited {args.max_rate_limited}"
        )
    if args.max_unexpected_skips >= 0 and unexpected_skip_count > args.max_unexpected_skips:
        threshold_failures.append(
            f"unexpected_skips {unexpected_skip_count} exceeds max_unexpected_skips {args.max_unexpected_skips}"
        )
    thresholds_ok = len(threshold_failures) == 0

    if args.json:
        summary = {
            "run_id": run_id,
            "boot_id": BOOT_ID,
            "elapsed_s": round(elapsed, 2),
            "confirmed": confirmed,
            "denied": denied,
            "skipped": skipped,
            "error": errors,
            "rate_limited": rate_limited,
            "auth_denied": auth_denied,
            "transport_flake": transport_flake,
            "server_errors": server_errors,
            "total_http_retries": total_http_retries,
            "skip_reasons": dict(skip_reason_counts),
            "unexpected_skips": {
                "count": unexpected_skip_count,
                "reasons": unexpected_skip_reasons,
                "sample_endpoints": unexpected_skip_endpoints[:20],
            },
            "total": len(proofs),
            "all_skipped": (confirmed + denied + errors == 0 and skipped > 0),
            "temporal_warnings": temporal_warnings,
            "thresholds": {
                "max_skipped": args.max_skipped,
                "max_rate_limited": args.max_rate_limited,
                "max_unexpected_skips": args.max_unexpected_skips,
                "ok": thresholds_ok,
            },
            "threshold_failures": threshold_failures,
            "preflight": preflight_status,
            "logs": {
                "actions": str(logs_dir / f"{run_id}.actions.jsonl"),
                "proofs": str(logs_dir / f"{run_id}.proof.jsonl"),
            },
            "denied_endpoints": [
                {"method": a.action, "url": a.url, "http_code": p.observations.get("http", {}).get("code", 0)}
                for a, p in zip(actions, proofs)
                if p.verdict == "DENIED"
            ],
            "error_endpoints": [
                {"method": a.action, "url": a.url, "exception": p.observations.get("exception", "")}
                for a, p in zip(actions, proofs)
                if p.verdict == "ERROR"
            ],
        }
        print(json.dumps(summary, indent=2))
    else:
        _print_summary(actions, proofs, run_id, logs_dir, elapsed)
        if temporal_warnings:
            print("  TEMPORAL WARNINGS:")
            for w in temporal_warnings:
                print(f"    {w}")
            print()
        if threshold_failures:
            print("  THRESHOLD FAILURES:")
            for failure in threshold_failures:
                print(f"    {failure}")
            print()

    # Exit code: 0=green, 1=failures, 2=all-skipped
    temporal_fail = len(temporal_warnings) > 0
    all_skipped = (confirmed + denied + errors == 0 and skipped > 0)
    if temporal_fail and not args.json:
        print("  TEMPORAL DOCTRINE VIOLATION — run marked FAIL")
        print()
    if all_skipped:
        sys.exit(2)
    elif denied + errors > 0 or temporal_fail or not thresholds_ok:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
