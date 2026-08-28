"""
Wolf Engine — Start the Command Center.

Usage:
    python start.py                  # foreground, localhost:5000
    python start.py --port 8080      # custom port
    python start.py --bg             # background mode (writes PID file)
    python start.py --db-dir ./data  # persist data to specific directory
"""

import argparse
import logging
import os
import signal
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ROOT))  # Parent dir so "wolf_engine" is importable
PID_FILE = os.path.join(ROOT, ".wolf.pid")


def _write_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def _is_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # signal 0 = check if alive
        return True
    except (OSError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Start Wolf Engine Command Center")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--db-dir", default=None, help="Database directory (default: temp)")
    parser.add_argument("--bg", action="store_true", help="Run in background")
    args = parser.parse_args()

    if _is_running():
        print("Wolf Engine is already running. Use stop.py first, or restart.py.")
        sys.exit(1)

    if args.bg:
        # Launch as detached subprocess
        cmd = [
            sys.executable, "-m", "wolf_engine.dashboard.app",
            "--host", args.host,
            "--port", str(args.port),
        ]
        if args.db_dir:
            cmd += ["--db-dir", args.db_dir]

        # Ensure PYTHONPATH includes parent so wolf_engine is importable
        env = os.environ.copy()
        parent = os.path.dirname(ROOT)
        pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = parent + (os.pathsep + pp if pp else "")

        if sys.platform == "win32":
            # Windows: CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS
            proc = subprocess.Popen(
                cmd,
                cwd=ROOT,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            proc = subprocess.Popen(
                cmd,
                cwd=ROOT,
                env=env,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))

        print(f"Wolf Engine started in background (PID {proc.pid})")
        print(f"  Dashboard: http://localhost:{args.port}")
        print(f"  Stop:      python stop.py")
        print(f"  Restart:   python restart.py")
    else:
        # Foreground mode
        _write_pid()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )

        print()
        print("  +======================================+")
        print("  |     WOLF ENGINE COMMAND CENTER       |")
        print("  +======================================+")
        print()
        print(f"  Dashboard:  http://localhost:{args.port}")
        print(f"  API:        http://localhost:{args.port}/api/snapshot")
        print(f"  Health:     http://localhost:{args.port}/health")
        print()
        print("  Press Ctrl+C to stop.")
        print()

        try:
            from wolf_engine.dashboard.app import WolfEngine, create_app

            engine = WolfEngine(db_dir=args.db_dir)
            app = create_app(engine)
            app.run(host=args.host, port=args.port, threaded=True)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)


if __name__ == "__main__":
    main()
