"""Convenience launcher for Forest AI development.

This script ensures the FastAPI bridge is running via the local virtual
environment, waits for it to become ready, then opens the bundled UI in the
default browser. Press Ctrl+C to stop both the server and this launcher.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "forest.config.json"
VENV_PY = ROOT / ".forestvenv" / "Scripts" / "python.exe"
SERVER_SCRIPT = ROOT / "bridges" / "forest_bridge_server.py"
SERVER_URL = "http://127.0.0.1:5050"
STATS_URL = f"{SERVER_URL}/api/stats"


def get_python_executable() -> str:
    if VENV_PY.exists():
        return str(VENV_PY)
    return sys.executable


def wait_for_server(timeout: float = 30.0, interval: float = 0.5) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(STATS_URL) as resp:  # noqa: S310 (local URL)
                return resp.status == 200
        except URLError:
            time.sleep(interval)
    return False


def main() -> None:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"forest.config.json not found at {CONFIG_PATH}")
    if not SERVER_SCRIPT.exists():
        raise SystemExit("forest_bridge_server.py not found; cannot launch.")

    python_exe = get_python_executable()
    print(f"[launcher] Using Python interpreter: {python_exe}")

    server_cmd = [python_exe, str(SERVER_SCRIPT), "--config", str(CONFIG_PATH)]
    print("[launcher] Starting bridge server...")
    server_proc = subprocess.Popen(server_cmd, cwd=str(ROOT))  # noqa: S603,S607

    try:
        if not wait_for_server():
            raise SystemExit("Bridge server did not become ready in time.")
        print("[launcher] Bridge server is online.")
        ui_url = f"{SERVER_URL}/"
        print(f"[launcher] Opening UI at {ui_url}")
        webbrowser.open(ui_url)
        print("[launcher] Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[launcher] Stopping...")
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        print("[launcher] Server stopped.")


if __name__ == "__main__":
    main()
