"""
Wolf Engine — Stop the running Command Center.

Usage:
    python stop.py
"""

import os
import signal
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(ROOT, ".wolf.pid")


def main():
    if not os.path.exists(PID_FILE):
        print("Wolf Engine is not running (no PID file).")
        sys.exit(0)

    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
    except (ValueError, OSError) as exc:
        print(f"Bad PID file: {exc}")
        os.remove(PID_FILE)
        sys.exit(1)

    print(f"Stopping Wolf Engine (PID {pid})...")

    try:
        if sys.platform == "win32":
            # Windows: taskkill with tree
            os.system(f"taskkill /F /PID {pid} /T >nul 2>&1")
        else:
            os.kill(pid, signal.SIGTERM)
            # Wait up to 5s for clean shutdown
            for _ in range(50):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except OSError:
                    break
            else:
                # Force kill if still running
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
    except OSError:
        pass  # Already dead

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    print("Wolf Engine stopped.")


if __name__ == "__main__":
    main()
