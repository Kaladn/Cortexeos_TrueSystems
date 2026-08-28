#!/usr/bin/env python3
"""Single-command release gate: regression slice + strict smoke verdict."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE = os.environ.get("CLEARBOX_BRIDGE", "http://127.0.0.1:5050")
DEFAULT_SESSION = os.environ.get("CLEARBOX_SMOKE_SESSION", "")
DEFAULT_MAX_SKIPPED = int(os.environ.get("CLEARBOX_SMOKE_MAX_SKIPPED", "200"))
DEFAULT_MAX_RATE_LIMITED = int(os.environ.get("CLEARBOX_SMOKE_MAX_RATE_LIMITED", "50"))
DEFAULT_MAX_UNEXPECTED = int(os.environ.get("CLEARBOX_SMOKE_MAX_UNEXPECTED_SKIPS", "0"))
DEFAULT_RL_RETRIES = int(os.environ.get("CLEARBOX_SMOKE_RL_RETRIES", "2"))
DEFAULT_RL_BACKOFF_MS = int(os.environ.get("CLEARBOX_SMOKE_RL_BACKOFF_MS", "300"))


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)


def _print_streams(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)


def _extract_json(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Smoke output does not contain JSON payload")
    return json.loads(stdout[start : end + 1])


def main() -> int:
    parser = argparse.ArgumentParser(description="Clearbox release gate")
    parser.add_argument("--bridge", default=DEFAULT_BRIDGE, help="Bridge URL")
    parser.add_argument(
        "--session-cookie",
        default=DEFAULT_SESSION,
        help="Optional clearbox_session cookie value",
    )
    parser.add_argument("--skip-llm", action="store_true", default=True, help="Skip LLM proxy probes (default: on)")
    parser.add_argument("--with-llm", action="store_true", help="Disable --skip-llm")
    parser.add_argument("--skip-ollama", action="store_true", default=True, help="Skip Ollama probes (default: on)")
    parser.add_argument("--with-ollama", action="store_true", help="Disable --skip-ollama")
    parser.add_argument("--max-skipped", type=int, default=DEFAULT_MAX_SKIPPED)
    parser.add_argument("--max-rate-limited", type=int, default=DEFAULT_MAX_RATE_LIMITED)
    parser.add_argument("--max-unexpected-skips", type=int, default=DEFAULT_MAX_UNEXPECTED)
    parser.add_argument("--rate-limit-retries", type=int, default=DEFAULT_RL_RETRIES)
    parser.add_argument("--rate-limit-backoff-ms", type=int, default=DEFAULT_RL_BACKOFF_MS)
    parser.add_argument("--rate-limit-deny", action="store_true", help="Treat persistent 429 as DENIED")
    parser.add_argument(
        "--json-out",
        default=str(ROOT / "tests" / "smoke" / "artifacts" / "release_gate_latest.json"),
        help="Path to write combined release-gate JSON result",
    )
    args = parser.parse_args()

    if args.with_llm:
        args.skip_llm = False
    if args.with_ollama:
        args.skip_ollama = False

    # 1) Regression slice
    pytest_cmd = [
        "pytest",
        "tests\\test_helpers_ssrf.py",
        "tests\\test_config_writer.py",
        "tests\\test_chain_executor_simple.py",
        "tests\\test_chain_executor_tool_boundary.py",
        "-q",
    ]
    reg = _run(pytest_cmd, cwd=ROOT)
    _print_streams(reg)

    # 2) Strict smoke
    smoke_cmd = [
        sys.executable,
        "-m",
        "tests.smoke.run",
        "--bridge",
        args.bridge,
        "--max-skipped",
        str(args.max_skipped),
        "--max-rate-limited",
        str(args.max_rate_limited),
        "--max-unexpected-skips",
        str(args.max_unexpected_skips),
        "--rate-limit-retries",
        str(args.rate_limit_retries),
        "--rate-limit-backoff-ms",
        str(args.rate_limit_backoff_ms),
        "--json",
    ]
    if args.skip_llm:
        smoke_cmd.append("--skip-llm")
    if args.skip_ollama:
        smoke_cmd.append("--skip-ollama")
    if args.session_cookie:
        smoke_cmd.extend(["--session-cookie", args.session_cookie])
    if args.rate_limit_deny:
        smoke_cmd.append("--rate-limit-deny")

    smoke = _run(smoke_cmd, cwd=ROOT)
    _print_streams(smoke)

    smoke_json: dict[str, Any] = {}
    smoke_parse_error = ""
    try:
        smoke_json = _extract_json(smoke.stdout or "")
    except Exception as exc:
        smoke_parse_error = str(exc)

    reasons: list[str] = []
    if reg.returncode != 0:
        reasons.append(f"regression tests failed (exit={reg.returncode})")
    if smoke.returncode != 0:
        reasons.append(f"smoke run failed (exit={smoke.returncode})")
    if smoke_parse_error:
        reasons.append(f"smoke JSON parse failed: {smoke_parse_error}")

    if smoke_json:
        if int(smoke_json.get("denied", 0)) != 0:
            reasons.append(f"denied={smoke_json.get('denied')}")
        if int(smoke_json.get("error", 0)) != 0:
            reasons.append(f"error={smoke_json.get('error')}")
        unexpected = int((smoke_json.get("unexpected_skips") or {}).get("count", 0))
        if unexpected != 0:
            reasons.append(f"unexpected_skips={unexpected}")
        if bool(smoke_json.get("all_skipped", False)):
            reasons.append("all probes skipped")
        thresholds_ok = bool((smoke_json.get("thresholds") or {}).get("ok", False))
        if not thresholds_ok:
            failures = smoke_json.get("threshold_failures") or []
            if failures:
                reasons.append("thresholds failed: " + "; ".join(str(x) for x in failures))
            else:
                reasons.append("thresholds failed")

    passed = len(reasons) == 0
    verdict = "PASS" if passed else "FAIL"
    stamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    combined = {
        "timestamp_utc": stamp,
        "verdict": verdict,
        "reasons": reasons,
        "commands": {
            "regression": pytest_cmd,
            "smoke": smoke_cmd,
        },
        "regression": {
            "exit_code": reg.returncode,
        },
        "smoke": {
            "exit_code": smoke.returncode,
            "parse_error": smoke_parse_error,
            "summary": smoke_json,
        },
    }

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")

    print()
    print("=" * 72)
    print(f"RELEASE GATE VERDICT: {verdict}")
    if reasons:
        for r in reasons:
            print(f"- {r}")
    if smoke_json:
        print(
            "Smoke summary: "
            f"confirmed={smoke_json.get('confirmed', 0)} "
            f"denied={smoke_json.get('denied', 0)} "
            f"skipped={smoke_json.get('skipped', 0)} "
            f"error={smoke_json.get('error', 0)} "
            f"rate_limited={smoke_json.get('rate_limited', 0)} "
            f"unexpected_skips={(smoke_json.get('unexpected_skips') or {}).get('count', 0)}"
        )
    print(f"Report: {out_path}")
    print("=" * 72)

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
