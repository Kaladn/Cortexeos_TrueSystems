"""End-to-end smoke test for the Forest bridge and control deck API."""
from __future__ import annotations

import http.client
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent.parent
BRIDGE_SCRIPT = ROOT / "bridges" / "forest_bridge_server.py"
CONFIG_PATH = ROOT / "forest.config.json"
HOST = "127.0.0.1"
PORT = 5050


class SmokeTestError(RuntimeError):
    """Raised when the smoke test encounters a failure."""


def _spawn_bridge() -> subprocess.Popen[str]:
    if not BRIDGE_SCRIPT.exists():
        raise SmokeTestError(f"Bridge script not found: {BRIDGE_SCRIPT}")
    if not CONFIG_PATH.exists():
        raise SmokeTestError(f"Config file not found: {CONFIG_PATH}")

    cmd = [
        sys.executable,
        str(BRIDGE_SCRIPT),
        "--config",
        str(CONFIG_PATH),
        "--log-level",
        "info",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    return proc


def _stream_output(proc: subprocess.Popen[str], buffer: List[str]) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        buffer.append(line.rstrip())
        print(f"[bridge] {line.rstrip()}")


def _wait_for_port(host: str, port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                time.sleep(0.5)
    return False


def _request_json(method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    conn = http.client.HTTPConnection(HOST, PORT, timeout=15)
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        data = response.read()
    finally:
        conn.close()

    text = data.decode("utf-8") if data else ""
    if response.status >= 400:
        raise SmokeTestError(f"{method} {path} failed with {response.status} {response.reason}: {text}")
    return json.loads(text) if text else {}


def _poll_job(job_id: str, timeout: float = 180.0) -> Dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        jobs = _request_json("GET", "/api/jobs")
        job_list = jobs.get("jobs", [])
        job = next((j for j in job_list if j.get("job_id") == job_id), None)
        if job and job.get("status") in {"completed", "error", "cancelled"}:
            return job
        time.sleep(1.0)
    raise SmokeTestError(f"Job {job_id} did not complete within timeout")


def run_smoke_test() -> None:
    # bridge_logs: List[str] = []
    # proc = _spawn_bridge()
    # reader = threading.Thread(target=_stream_output, args=(proc, bridge_logs), daemon=True)
    # reader.start()

    try:
        if not _wait_for_port(HOST, PORT, timeout=90.0):
            raise SmokeTestError("Bridge did not start listening on port 5050 in time")

        stats = _request_json("GET", "/api/stats")
        print("[smoke] stats", json.dumps(stats, indent=2))

        map_payload = _request_json(
            "POST",
            "/api/map",
            {"text": "forest ai smoke test verifies control deck"},
        )
        if map_payload.get("total_tokens", 0) <= 0:
            raise SmokeTestError("Inline map returned zero tokens")
        print("[smoke] inline map ok; tokens=", map_payload.get("total_tokens"))

        sample_file = (ROOT / "forest_ai_section1" / "index.html").resolve()
        if not sample_file.exists():
            raise SmokeTestError(f"Sample file missing: {sample_file}")

        job_request = _request_json(
            "POST",
            "/api/map_files",
            {
                "paths": [str(sample_file)],
                "ignore_missing": True,
            },
        )
        job_id = job_request.get("job_id")
        if not job_id:
            raise SmokeTestError("map_files response missing job_id")
        print(f"[smoke] job queued: {job_id}")

        job = _poll_job(job_id, timeout=180.0)
        status = job.get("status")
        if status != "completed":
            raise SmokeTestError(f"Job {job_id} finished with status {status}")
        result_path = job.get("result_path")
        if not result_path or not Path(result_path).exists():
            raise SmokeTestError(f"Result file missing at {result_path}")
        print(f"[smoke] job completed; report: {result_path}")

        print("[smoke] ALL CHECKS PASSED")

    finally:
        # proc.terminate()
        # try:
        #     proc.wait(timeout=10)
        # except subprocess.TimeoutExpired:
        #     proc.kill()
        # reader.join(timeout=5)
        pass


if __name__ == "__main__":
    try:
        run_smoke_test()
    except SmokeTestError as exc:
        print(f"[smoke] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)