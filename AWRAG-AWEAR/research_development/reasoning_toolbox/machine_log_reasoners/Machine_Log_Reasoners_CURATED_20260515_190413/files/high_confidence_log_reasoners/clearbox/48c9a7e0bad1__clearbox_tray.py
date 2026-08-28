#!/usr/bin/env python3
"""Clearbox AI — System Tray Application.

Manages all services as hidden child processes from a system tray icon.
No PowerShell windows, no temp scripts, no delegation to external scripts.

Usage:
    python  scripts/clearbox_tray.py          (with console)
    pythonw scripts/clearbox_tray.py          (no console window)

Tray icon color:
    Green  = all 3 services healthy
    Yellow = partial (some up)
    Red    = all down

Menu:
    Double-click / "Open Clearbox AI" = open browser
    Start All    = launch services (tray stays)
    Restart All  = stop + relaunch all services
    Stop All     = stop all services (tray stays, icon goes red)
    Quit         = stop all services, then exit tray

Shutdown contract:
    1. Tray stays alive while shutting down services
    2. Ordered: Bridge/LLM first, UI last
    3. 3-pass escalation: graceful → terminate → kill
    4. Port-free verification after each process death
    5. Blocking diagnostic dialog if anything refuses to die
"""

import atexit
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).resolve().parent.parent
# Platform-specific venv: NVIDIA_venv (NVIDIA), AMD_venv (ROCm), my_venv (legacy), .venv (fallback)
VENV_PYTHON = next(
    (p for p in (
        WORKSPACE / "NVIDIA_venv" / "Scripts" / "python.exe",
        WORKSPACE / "AMD_venv" / "Scripts" / "python.exe",
        WORKSPACE / "my_venv" / "Scripts" / "python.exe",
        WORKSPACE / ".venv" / "Scripts" / "python.exe",
    ) if p.exists()),
    WORKSPACE / ".venv" / "Scripts" / "python.exe",
)

# ── Config (single source of truth: governed clearbox.config.json) ──
_CFG = {}
try:
    if str(WORKSPACE) not in sys.path:
        sys.path.insert(0, str(WORKSPACE))
    from security.data_paths import CLEARBOX_CONFIG_PATH
    from security.secure_storage import secure_json_load
    _CFG = secure_json_load(CLEARBOX_CONFIG_PATH)
except Exception:
    pass

_srv = _CFG.get("server", {})
_HOST = _srv.get("host", "127.0.0.1")
_TLS = _srv.get("tls", False)
_PROTO = "https" if _TLS else "http"
_BRIDGE_PORT = _srv.get("port", 5050)
_UI_PORT = 8080
_LLM_PORT = 11435
_CITE_PORT = 5052

# SSL context for health probes against self-signed certs
_NO_VERIFY = ssl.create_default_context()
_NO_VERIFY.check_hostname = False
_NO_VERIFY.verify_mode = ssl.CERT_NONE

UI_URL = f"{_PROTO}://localhost:{_UI_PORT}/clearbox_ai_production.html"

# ── Service definitions ─────────────────────────────────────────
# Shutdown order: Bridge and LLM first (they hold model state),
# UI last (so logs/status stay visible as long as possible).
SERVICES = [
    {
        "name": "Bridge",
        "script": "bridges/clearbox_bridge_server.py",
        "args": [],
        "port": _BRIDGE_PORT,
        "health": f"{_PROTO}://127.0.0.1:{_BRIDGE_PORT}/api/stats",
        "shutdown_order": 1,
    },
    {
        "name": "LLM",
        "script": "scripts/local_llm_server.py",
        "args": [],
        "port": _LLM_PORT,
        "health": f"{_PROTO}://127.0.0.1:{_LLM_PORT}/health",
        "shutdown_order": 1,
    },
    {
        "name": "Citations",
        "script": "scripts/citation_server.py",
        "args": [],
        "port": _CITE_PORT,
        "health": f"{_PROTO}://127.0.0.1:{_CITE_PORT}/api/status",
        "shutdown_order": 1,
    },
    {
        "name": "UI",
        "script": "ui/launch_ui_internal.py",
        "args": [],
        "port": _UI_PORT,
        "health": f"{_PROTO}://127.0.0.1:{_UI_PORT}/",
        "shutdown_order": 2,
    },
]

# ── Process state ────────────────────────────────────────────────
_procs: dict[str, subprocess.Popen] = {}
_health: dict[str, bool] = {s["name"]: False for s in SERVICES}
_stopping = False
_services_running = False  # True when services are up
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Shutdown progress — read by menu label lambdas
_shutdown_status: str = ""


# ── Logging ──────────────────────────────────────────────────────
def _log(msg: str):
    """Print to console (if visible) — no-op under pythonw."""
    try:
        print(f"  {msg}")
    except Exception:
        pass


# ── Health probe ─────────────────────────────────────────────────
def _probe(url: str) -> bool:
    try:
        ctx = _NO_VERIFY if url.startswith("https://") else None
        urllib.request.urlopen(url, timeout=2, context=ctx)
        return True
    except Exception:
        return False


def _port_free(port: int) -> bool:
    """Check if a port is free (not in LISTEN state)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", port))
            return result != 0  # Non-zero = connection refused = port free
    except Exception:
        return True


def _kill_by_port(port: int):
    """Kill any process listening on the given port that we don't own.

    Handles the case where a previous tray instance left orphaned service
    processes behind.  Uses netstat to find the PID, then taskkill /F.
    """
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                try:
                    pid = int(parts[-1])
                except ValueError:
                    continue
                if pid <= 4:
                    continue  # Skip System/Idle
                # Skip if it's already ours
                owned = any(p.pid == pid for p in _procs.values() if p)
                if owned:
                    continue
                _log(f"  Killing orphaned PID {pid} on port {port}")
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=5,
                )
                time.sleep(0.5)
    except Exception as e:
        _log(f"  _kill_by_port({port}) error: {e}")


# ── 3-Pass Process Stop ─────────────────────────────────────────
def _stop_process_3pass(name: str, port: int) -> dict:
    """Stop a single process with 3-pass escalation + port verification.

    Returns: {"name": str, "dead": bool, "port_free": bool, "pass": int, "pid": int|None}
    """
    proc = _procs.get(name)
    if not proc or proc.poll() is not None:
        _procs.pop(name, None)
        pf = _port_free(port)
        return {"name": name, "dead": True, "port_free": pf, "pass": 0, "pid": None}

    pid = proc.pid

    # Pass 1: Graceful terminate
    _log(f"  [{name}] pass 1/3: terminate (PID {pid})")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass

    if proc.poll() is not None and _port_free(port):
        _procs.pop(name, None)
        _log(f"  [{name}] stopped cleanly (pass 1)")
        return {"name": name, "dead": True, "port_free": True, "pass": 1, "pid": pid}

    # Pass 2: Kill
    _log(f"  [{name}] pass 2/3: kill (PID {pid})")
    proc.kill()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass

    if proc.poll() is not None and _port_free(port):
        _procs.pop(name, None)
        _log(f"  [{name}] killed (pass 2)")
        return {"name": name, "dead": True, "port_free": True, "pass": 2, "pid": pid}

    # Pass 3: OS-level force kill via taskkill (Windows)
    _log(f"  [{name}] pass 3/3: taskkill /F (PID {pid})")
    try:
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True, timeout=5,
        )
    except Exception as e:
        _log(f"  [{name}] taskkill failed: {e}")

    time.sleep(1)
    dead = proc.poll() is not None
    pf = _port_free(port)
    if dead:
        _procs.pop(name, None)
    _log(f"  [{name}] after pass 3: dead={dead} port_free={pf}")
    return {"name": name, "dead": dead, "port_free": pf, "pass": 3, "pid": pid}


# ── Ordered shutdown ─────────────────────────────────────────────
def shutdown_all(icon=None) -> list[dict]:
    """Stop all services in order. Tray stays alive.

    Returns list of per-service results with dead/port_free status.
    """
    global _stopping, _shutdown_status, _services_running
    _stopping = True
    _services_running = False
    results = []

    # Group by shutdown_order
    phases = {}
    for svc in SERVICES:
        order = svc.get("shutdown_order", 1)
        phases.setdefault(order, []).append(svc)

    for phase_num in sorted(phases.keys()):
        phase_svcs = phases[phase_num]
        for svc in phase_svcs:
            name = svc["name"]
            _shutdown_status = f"Stopping {name}..."
            _log(f"Stopping {name} (phase {phase_num})...")
            if icon:
                icon.title = f"Clearbox  Stopping {name}..."
                icon.icon = _make_icon("yellow")

            result = _stop_process_3pass(name, svc["port"])
            results.append(result)

    # Verify all dead
    _shutdown_status = "Verifying..."
    _log("Verifying all services stopped...")
    stuck = [r for r in results if not r["dead"] or not r["port_free"]]

    if stuck:
        _shutdown_status = f"STUCK: {', '.join(r['name'] for r in stuck)}"
        _log(f"WARNING: {len(stuck)} service(s) stuck: {stuck}")
        if icon:
            icon.title = f"Clearbox  {_shutdown_status}"
            icon.icon = _make_icon("red")
        # Show diagnostic dialog
        _show_stuck_dialog(stuck)
    else:
        _shutdown_status = ""
        _log("All services stopped cleanly")
        if icon:
            icon.title = "Clearbox  Stopped"
            icon.icon = _make_icon("red")

    # Mark all health as down
    for svc in SERVICES:
        _health[svc["name"]] = False

    return results


# ── Diagnostic dialog for stuck processes ────────────────────────
def _show_stuck_dialog(stuck: list[dict]):
    """Show a blocking dialog with diagnostic info for stuck processes."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        # Build diagnostic text
        lines = ["The following services could not be stopped:\n"]
        for r in stuck:
            status_parts = []
            if not r["dead"]:
                status_parts.append(f"PID {r['pid']} still alive")
            if not r["port_free"]:
                # Find port for this service
                port = next((s["port"] for s in SERVICES if s["name"] == r["name"]), "?")
                status_parts.append(f"port {port} still held")
            lines.append(f"  {r['name']}: {', '.join(status_parts)}")

        lines.append("\nYou can try:")
        lines.append("  1. Open Task Manager and kill the PIDs above")
        lines.append("  2. Run: taskkill /F /PID <pid>")
        lines.append("  3. Restart your machine if ports are stuck in TIME_WAIT")

        diag_text = "\n".join(lines)

        root = tk.Tk()
        root.withdraw()

        def _copy_diag():
            root.clipboard_clear()
            root.clipboard_append(diag_text)
            messagebox.showinfo("Copied", "Diagnostics copied to clipboard.", parent=root)

        dialog = tk.Toplevel(root)
        dialog.title("Clearbox AI Studio — Shutdown Problem")
        dialog.geometry("520x340")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        txt = tk.Text(dialog, wrap=tk.WORD, font=("Consolas", 10), bg="#1e1e2e", fg="#cdd6f4",
                      relief=tk.FLAT, padx=12, pady=12)
        txt.insert("1.0", diag_text)
        txt.config(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(dialog, bg="#1e1e2e")
        btn_frame.pack(fill=tk.X, padx=12, pady=8)

        tk.Button(btn_frame, text="Copy Diagnostics", command=_copy_diag,
                  bg="#45475a", fg="#cdd6f4", relief=tk.FLAT, padx=12, pady=4).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Close", command=lambda: (dialog.destroy(), root.destroy()),
                  bg="#f38ba8", fg="#1e1e2e", relief=tk.FLAT, padx=12, pady=4).pack(side=tk.RIGHT)

        dialog.protocol("WM_DELETE_WINDOW", lambda: (dialog.destroy(), root.destroy()))
        root.mainloop()
    except Exception as e:
        _log(f"Could not show diagnostic dialog: {e}")


# ── Process management ───────────────────────────────────────────
def start_service(svc: dict) -> bool:
    """Start one service as a hidden child process."""
    name = svc["name"]
    port = svc["port"]
    script = WORKSPACE / svc["script"]
    if not script.exists():
        _log(f"[{name}] script not found: {svc['script']}")
        return False

    # Kill our tracked process if still alive
    _stop_process_3pass(name, port)

    # Kill any UNTRACKED process holding this port (orphan from previous run)
    if not _port_free(port):
        _log(f"[{name}] port {port} held by untracked process — clearing")
        _kill_by_port(port)
        time.sleep(1)

    cmd = [str(VENV_PYTHON), str(script)] + svc.get("args", [])
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(WORKSPACE),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
        )
        _procs[name] = proc
        _log(f"[{name}] started PID {proc.pid}")
        return True
    except Exception as e:
        _log(f"[{name}] failed: {e}")
        return False


def start_all(icon=None):
    """Start all services with staggered delay."""
    global _stopping, _services_running
    _stopping = False
    _services_running = True
    _log("Starting all services...")
    if icon:
        icon.title = "Clearbox  Starting..."
        icon.icon = _make_icon("yellow")
    for svc in SERVICES:
        start_service(svc)
        time.sleep(1.5)


# ── Icon generation ──────────────────────────────────────────────
def _make_icon(color: str = "gray"):
    """64x64 tray icon — colored circle with 'C'."""
    from PIL import Image, ImageDraw, ImageFont

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    fills = {
        "green": (34, 197, 94),
        "yellow": (234, 179, 8),
        "red": (239, 68, 68),
        "gray": (107, 114, 128),
    }
    fill = fills.get(color, fills["gray"])

    # Filled circle
    draw.ellipse([2, 2, size - 2, size - 2], fill=fill)

    # Letter "C"
    try:
        font = ImageFont.truetype("segoeui.ttf", 38)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 38)
        except Exception:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "C", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - tw) // 2, (size - th) // 2 - bbox[1]),
        "C", fill=(255, 255, 255), font=font,
    )
    return img


# ── Health monitor thread ────────────────────────────────────────
def _health_loop(icon):
    """Poll health every 5s, update icon, auto-restart crashed processes."""
    while True:
        if _stopping:
            time.sleep(2)
            continue

        # Probe each service
        for svc in SERVICES:
            _health[svc["name"]] = _probe(svc["health"])

        # Update icon color
        up = sum(v for v in _health.values())
        if not _services_running:
            icon.icon = _make_icon("red")
        elif up == len(SERVICES):
            icon.icon = _make_icon("green")
        elif up > 0:
            icon.icon = _make_icon("yellow")
        else:
            icon.icon = _make_icon("red")

        # Update tooltip
        if _services_running:
            lines = []
            for svc in SERVICES:
                dot = "+" if _health[svc["name"]] else "x"
                lines.append(f"[{dot}] {svc['name']}:{svc['port']}")
            icon.title = "Clearbox  " + "  ".join(lines)
        elif not _stopping:
            icon.title = "Clearbox  Stopped"

        # Auto-restart crashed child processes (only when services should be running)
        if _services_running and not _stopping:
            for svc in SERVICES:
                proc = _procs.get(svc["name"])
                if proc and proc.poll() is not None:
                    _log(f"[{svc['name']}] crashed (exit {proc.returncode}), restarting")
                    start_service(svc)

        time.sleep(5)


# ── Browser launcher (Chrome first, then system default) ─────────
def _open_browser(url: str):
    """Open URL in Chrome if available, otherwise fall back to system default."""
    try:
        chrome = webbrowser.get("chrome")
        chrome.open(url)
        return
    except webbrowser.Error:
        pass
    # Chrome not registered by name — try common Windows paths
    for path in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]:
        if Path(path).exists():
            webbrowser.register("chrome", None, webbrowser.BackgroundBrowser(path))
            webbrowser.get("chrome").open(url)
            return
    # Fallback: whatever is available
    webbrowser.open(url)


# ── Tray menu actions ────────────────────────────────────────────
def _on_open(icon, item):
    if _services_running:
        _open_browser(UI_URL)


def _on_start(icon, item):
    def _do():
        start_all(icon)
    threading.Thread(target=_do, daemon=True).start()


def _on_restart(icon, item):
    def _do():
        shutdown_all(icon)
        time.sleep(2)
        start_all(icon)
        # Re-open browser after services come up (old tab auto-closed on shutdown)
        for _ in range(20):
            time.sleep(2)
            if _health.get("UI") and _health.get("Bridge"):
                _open_browser(UI_URL)
                return
    threading.Thread(target=_do, daemon=True).start()


def _on_stop(icon, item):
    """Stop all services. Tray stays alive."""
    def _do():
        shutdown_all(icon)
    threading.Thread(target=_do, daemon=True).start()


def _on_quit(icon, item):
    """Stop all services, then exit the tray."""
    def _do():
        shutdown_all(icon)
        _log("Tray exiting")
        icon.stop()
    threading.Thread(target=_do, daemon=True).start()


# ── Main ─────────────────────────────────────────────────────────
def main():
    import pystray
    from pystray import MenuItem, Menu

    # Start services
    start_all()

    # Build tray
    icon = pystray.Icon(
        "ClearboxAI",
        _make_icon("yellow"),
        "Clearbox  Starting...",
        menu=Menu(
            MenuItem("Open Clearbox AI Studio", _on_open, default=True),
            Menu.SEPARATOR,
            MenuItem(
                lambda item: f"{'[+]' if _health.get('Bridge') else '[x]'} Bridge :{_BRIDGE_PORT}",
                None, enabled=False,
            ),
            MenuItem(
                lambda item: f"{'[+]' if _health.get('LLM') else '[x]'} LLM :{_LLM_PORT}",
                None, enabled=False,
            ),
            MenuItem(
                lambda item: f"{'[+]' if _health.get('Citations') else '[x]'} Citations :{_CITE_PORT}",
                None, enabled=False,
            ),
            MenuItem(
                lambda item: f"{'[+]' if _health.get('UI') else '[x]'} UI :{_UI_PORT}",
                None, enabled=False,
            ),
            Menu.SEPARATOR,
            MenuItem("Start All", _on_start, visible=lambda item: not _services_running),
            MenuItem("Restart All", _on_restart, visible=lambda item: _services_running),
            MenuItem("Stop All", _on_stop, visible=lambda item: _services_running),
            Menu.SEPARATOR,
            MenuItem("Quit", _on_quit),
        ),
    )

    # Health monitor (runs forever — survives stop/start cycles)
    threading.Thread(target=_health_loop, args=(icon,), daemon=True).start()

    # Auto-open browser after services come up
    def _delayed_open():
        for _ in range(20):
            time.sleep(2)
            if _health.get("UI") and _health.get("Bridge"):
                _open_browser(UI_URL)
                return
    threading.Thread(target=_delayed_open, daemon=True).start()

    _log("Clearbox AI Studio tray running")
    icon.run()


if __name__ == "__main__":
    # ── Single-instance guard (Windows named mutex) ───────────────────
    # Prevents a second tray process from spawning a duplicate set of
    # services, which would leave orphaned Python processes eating RAM.
    import ctypes
    _MUTEX_NAME = "Global\\ClearboxAIStudio_Tray"
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        _log("Another Clearbox AI Studio tray is already running — exiting.")
        try:
            import tkinter as tk
            from tkinter import messagebox
            _r = tk.Tk(); _r.withdraw()
            messagebox.showinfo("Clearbox AI Studio", "Tray is already running.")
            _r.destroy()
        except Exception:
            pass
        sys.exit(0)
    # ─────────────────────────────────────────────────────────────────

    atexit.register(lambda: shutdown_all() if _services_running else None)
    try:
        main()
    except KeyboardInterrupt:
        shutdown_all()
