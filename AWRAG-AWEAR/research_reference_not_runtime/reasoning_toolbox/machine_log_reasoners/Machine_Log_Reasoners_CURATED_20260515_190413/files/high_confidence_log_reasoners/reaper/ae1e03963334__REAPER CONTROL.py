# control.py
# Universal Service Controller for R.E.A.P.E.R. Phase 4

import subprocess
import sys
import time
import os
import signal

# Define all services with correct filenames and paths
services = [
    {
        "name": "Reaper API",
        "cwd": "./reaper-engine",
        "cmd": [sys.executable, "reaper_network_analyzer.py"]
    },
    {
        "name": "Cognitive Engine",
        "cwd": ".",
        "cmd": [sys.executable, "reaper_cognitive_engine.py"]
    },
    {
        "name": "Live Monitor",
        "cwd": ".",
        "cmd": [sys.executable, "reaper_phase4_preemptive_engine.py"]
    },
    {
        "name": "React Dashboard",
        "cwd": "./reaper-phase4-dashboard",
        "cmd": ["npm", "start"]
    }
]

processes = []

def start_services():
    for svc in services:
        print(f"Starting {svc['name']}...")
        proc = subprocess.Popen(svc['cmd'], cwd=svc['cwd'], shell=os.name == 'nt')
        processes.append((svc['name'], proc))
        time.sleep(1)  # slight delay for stability

def stop_services():
    print("\nStopping all services...")
    for name, proc in processes:
        try:
            print(f"Terminating {name} (PID {proc.pid})")
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    print("All services stopped.")

if __name__ == '__main__':
    try:
        start_services()
        print("\nAll services running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_services()
        print("Shutdown complete.")
