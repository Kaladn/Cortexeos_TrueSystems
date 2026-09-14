"""
Wolf Engine — Restart the Command Center.

Usage:
    python restart.py                  # restart foreground on :5000
    python restart.py --port 8080      # restart on custom port
    python restart.py --bg             # restart in background
"""

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(ROOT, ".wolf.pid")


def main():
    # Stop if running
    if os.path.exists(PID_FILE):
        print("Stopping current instance...")
        subprocess.run([sys.executable, os.path.join(ROOT, "stop.py")], cwd=ROOT)
        time.sleep(1)

    # Forward all args to start.py
    start_script = os.path.join(ROOT, "start.py")
    args = [sys.executable, start_script] + sys.argv[1:]
    print("Starting Wolf Engine...")
    os.execv(sys.executable, args)


if __name__ == "__main__":
    main()
