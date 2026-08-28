#!/usr/bin/env python3
"""
Forest AI Production - Unified Launcher
Starts: Bridge Server + UI Server + GPT-OSS Heartbeat
v1.1.0
"""

import os
import sys
import time
import signal
import subprocess
import requests
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Color codes for terminal output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def colored(text: str, color: str) -> str:
    """Return colored text for terminal"""
    return f"{color}{text}{Colors.RESET}"

def print_banner():
    """Print startup banner"""
    width = 80
    print("\n" + colored("=" * width, Colors.CYAN))
    print(colored("🌲 FOREST AI PRODUCTION - UNIFIED LAUNCHER 🌲", Colors.GREEN + Colors.BOLD).center(width + 20))
    print(colored("=" * width, Colors.CYAN))
    print(colored(f"\n{'Version:':<15} 1.1.0", Colors.WHITE))
    print(colored(f"{'Date:':<15} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.WHITE))
    print(colored(f"{'Platform:':<15} {platform.system()} {platform.release()}", Colors.WHITE))
    print(colored(f"{'Python:':<15} {sys.version.split()[0]}", Colors.WHITE))
    print()

def print_section(title: str):
    """Print section header"""
    print(colored(f"\n{'─' * 80}", Colors.CYAN))
    print(colored(f"  {title}", Colors.YELLOW + Colors.BOLD))
    print(colored(f"{'─' * 80}", Colors.CYAN))

def log(message: str, level: str = "INFO"):
    """Log a message with timestamp and level"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    level_colors = {
        "INFO": Colors.WHITE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED
    }
    color = level_colors.get(level, Colors.WHITE)
    print(f"{colored('[' + timestamp + ']', Colors.CYAN)} {colored(level, color):<20} {message}")

class ProcessManager:
    """Manage child processes"""
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.root_dir = Path(__file__).parent.absolute()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        log("Shutdown signal received", "WARNING")
        self.shutdown_all()
        sys.exit(0)
    
    def start_process(self, name: str, command: List[str], cwd: Optional[Path] = None) -> Optional[subprocess.Popen]:
        """Start a process and track it"""
        log(f"Starting {name}...", "INFO")
        
        try:
            # Determine shell based on platform
            is_windows = platform.system() == "Windows"
            
            if cwd is None:
                cwd = self.root_dir
            
            # Create process
            if is_windows:
                # Windows: use CREATE_NEW_PROCESS_GROUP to allow clean termination
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix: use process group
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setpgrp
                )
            
            self.processes.append(process)
            log(f"{name} started (PID: {process.pid})", "SUCCESS")
            return process
            
        except Exception as e:
            log(f"Failed to start {name}: {e}", "ERROR")
            return None
    
    def check_health(self, url: str, timeout: int = 30) -> bool:
        """Check if a service is healthy"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        return False
    
    def shutdown_all(self):
        """Gracefully shutdown all processes"""
        log("Shutting down all services...", "WARNING")
        
        for process in reversed(self.processes):
            try:
                log(f"Terminating PID {process.pid}...", "INFO")
                process.terminate()
                try:
                    process.wait(timeout=5)
                    log(f"PID {process.pid} terminated cleanly", "SUCCESS")
                except subprocess.TimeoutExpired:
                    log(f"Force killing PID {process.pid}...", "WARNING")
                    process.kill()
                    process.wait()
            except Exception as e:
                log(f"Error terminating PID {process.pid}: {e}", "ERROR")
        
        self.processes.clear()
        log("All services stopped", "SUCCESS")

def check_prerequisites(manager: ProcessManager) -> bool:
    """Check system prerequisites"""
    print_section("System Prerequisites Check")
    
    checks = []
    
    # Check Python version
    py_version = sys.version_info
    py_ok = py_version.major == 3 and py_version.minor >= 11
    checks.append(("Python 3.11+", py_ok, f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
    
    # Check virtual environment
    venv_path = manager.root_dir / ".venv" / "Scripts" / "python.exe"
    if not venv_path.exists():
        venv_path = manager.root_dir / ".venv" / "bin" / "python"
    venv_ok = venv_path.exists()
    checks.append(("Virtual environment", venv_ok, str(venv_path) if venv_ok else "Not found"))
    
    # Check lexicon
    lexicon_path = manager.root_dir.parent / "Lexicon_Canonical" / "lexicon_v2.json"
    lexicon_ok = lexicon_path.exists()
    checks.append(("Lexicon file", lexicon_ok, str(lexicon_path) if lexicon_ok else "Not found"))
    
    # Check config
    config_path = manager.root_dir / "forest.config.json"
    config_ok = config_path.exists()
    checks.append(("Config file", config_ok, str(config_path) if config_ok else "Not found"))
    
    # Check database directory
    db_dir = manager.root_dir / "data"
    db_dir.mkdir(exist_ok=True)
    checks.append(("Data directory", True, str(db_dir)))
    
    # Print results
    all_ok = True
    for name, status, detail in checks:
        status_str = colored("✅ PASS", Colors.GREEN) if status else colored("❌ FAIL", Colors.RED)
        log(f"{name:<25} {status_str}  {detail}", "INFO" if status else "ERROR")
        all_ok = all_ok and status
    
    return all_ok

def start_forest_bridge(manager: ProcessManager) -> Optional[subprocess.Popen]:
    """Start Forest AI Bridge Server"""
    print_section("Starting Forest AI Bridge Server")
    
    venv_python = manager.root_dir / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = manager.root_dir / ".venv" / "bin" / "python"
    
    bridge_script = manager.root_dir / "bridges" / "forest_bridge_server.py"
    config_file = manager.root_dir / "forest.config.json"
    
    command = [
        str(venv_python),
        str(bridge_script),
        "--config", str(config_file)
    ]
    
    process = manager.start_process("Forest Bridge", command)
    
    if process:
        log("Waiting for bridge to be ready...", "INFO")
        if manager.check_health("http://127.0.0.1:5050/api/stats", timeout=30):
            log("Bridge server is healthy ✅", "SUCCESS")
            
            # Get stats
            try:
                response = requests.get("http://127.0.0.1:5050/api/stats")
                stats = response.json()
                log(f"Lexicon entries: {stats.get('entries', 0):,}", "INFO")
                log(f"Device: {stats.get('device_used', 'unknown').upper()}", "INFO")
            except:
                pass
            
            return process
        else:
            log("Bridge server health check failed", "ERROR")
            return None
    
    return None

def start_ui_server(manager: ProcessManager) -> Optional[subprocess.Popen]:
    """Start UI Server"""
    print_section("Starting Web Console UI Server")
    
    venv_python = manager.root_dir / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = manager.root_dir / ".venv" / "bin" / "python"
    
    ui_script = manager.root_dir / "ui" / "launch_ui.py"
    
    command = [str(venv_python), str(ui_script)]
    
    process = manager.start_process("UI Server", command)
    
    if process:
        log("Waiting for UI server to be ready...", "INFO")
        if manager.check_health("http://127.0.0.1:8080", timeout=15):
            log("UI server is healthy ✅", "SUCCESS")
            log("Open browser: http://localhost:8080/forest_ai_production.html", "SUCCESS")
            return process
        else:
            log("UI server health check failed", "ERROR")
            return None
    
    return None

def check_gpt_oss(manager: ProcessManager) -> bool:
    """Check if GPT-OSS/Ollama is running"""
    print_section("Checking GPT-OSS / Ollama Heartbeat")
    
    endpoints = [
        ("Ollama", "http://localhost:11434/api/tags"),
        ("LM Studio", "http://localhost:1234/v1/models"),
        ("Text Gen WebUI", "http://localhost:5000/api/v1/model")
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                log(f"{name} detected and running ✅", "SUCCESS")
                
                # Try to get model info
                try:
                    if name == "Ollama":
                        models = response.json().get('models', [])
                        if models:
                            model_names = [m.get('name', 'unknown') for m in models]
                            log(f"Available models: {', '.join(model_names[:3])}", "INFO")
                except:
                    pass
                
                return True
        except:
            continue
    
    log("No GPT-OSS/LLM service detected", "WARNING")
    log("To enable LLM features:", "INFO")
    log("  - Install Ollama: https://ollama.ai", "INFO")
    log("  - Run: ollama serve", "INFO")
    log("  - Pull a model: ollama pull llama3.2", "INFO")
    
    return False

def start_metrics_loop(manager: ProcessManager) -> Optional[subprocess.Popen]:
    """Start background metrics collection"""
    print_section("Starting Metrics Collection Loop")
    
    venv_python = manager.root_dir / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = manager.root_dir / ".venv" / "bin" / "python"
    
    metrics_script = manager.root_dir / "scripts" / "metrics_loop.py"
    
    # Check if metrics script exists
    if not metrics_script.exists():
        log("Metrics loop script not found (optional)", "WARNING")
        return None
    
    command = [str(venv_python), str(metrics_script)]
    
    process = manager.start_process("Metrics Loop", command)
    
    if process:
        log("Metrics collection started in background", "SUCCESS")
        return process
    
    return None

def print_summary():
    """Print startup summary"""
    print_section("🚀 Forest AI Production is Ready!")
    
    print(colored("\n📊 Service Status:", Colors.YELLOW))
    print(f"  {'Forest AI Bridge:':<25} {colored('http://127.0.0.1:5050', Colors.CYAN)}")
    print(f"  {'Web Console UI:':<25} {colored('http://127.0.0.1:8080/forest_ai_production.html', Colors.CYAN)}")
    print(f"  {'GPT-OSS/Ollama:':<25} {colored('http://localhost:11434', Colors.CYAN)} (if installed)")
    
    print(colored("\n🎯 Quick Actions:", Colors.YELLOW))
    print(f"  {colored('1.', Colors.WHITE)} Open browser to Web Console")
    print(f"  {colored('2.', Colors.WHITE)} Upload a document for 6-1-6 mapping")
    print(f"  {colored('3.', Colors.WHITE)} Review unmapped tokens")
    print(f"  {colored('4.', Colors.WHITE)} Chat with GPT-OSS using 6-1-6 context")
    
    print(colored("\n📚 Documentation:", Colors.YELLOW))
    print(f"  {colored('UI Guide:', Colors.WHITE):<25} ui/UI_GUIDE.md")
    print(f"  {colored('GPT-OSS Setup:', Colors.WHITE):<25} ui/GPT_OSS_INTEGRATION.md")
    print(f"  {colored('Production Guide:', Colors.WHITE):<25} PRODUCTION_GUIDE.md")
    
    print(colored("\n⚠️  To Stop:", Colors.YELLOW))
    print(f"  Press {colored('Ctrl+C', Colors.RED)} to gracefully shutdown all services")
    
    print(colored("\n" + "=" * 80 + "\n", Colors.CYAN))

def monitor_processes(manager: ProcessManager):
    """Monitor running processes and restart if needed"""
    log("Monitoring services... (Press Ctrl+C to stop)", "INFO")
    
    try:
        while True:
            # Check if any process has died
            for i, process in enumerate(manager.processes):
                if process.poll() is not None:
                    log(f"Process {process.pid} exited with code {process.returncode}", "WARNING")
                    
                    # Read any error output
                    try:
                        stdout, stderr = process.communicate(timeout=1)
                        if stderr:
                            log(f"Error output: {stderr.decode()[:200]}", "ERROR")
                    except:
                        pass
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        log("Received shutdown signal", "WARNING")
        manager.shutdown_all()

def main():
    """Main entry point"""
    print_banner()
    
    # Create process manager
    manager = ProcessManager()
    
    try:
        # Check prerequisites
        if not check_prerequisites(manager):
            log("Prerequisites check failed. Please fix errors and try again.", "ERROR")
            return 1
        
        # Start Forest AI Bridge
        bridge = start_forest_bridge(manager)
        if not bridge:
            log("Failed to start Forest AI Bridge. Aborting.", "ERROR")
            manager.shutdown_all()
            return 1
        
        # Start UI Server
        ui = start_ui_server(manager)
        if not ui:
            log("Failed to start UI Server. Continuing without UI.", "WARNING")
        
        # Check GPT-OSS (non-blocking)
        check_gpt_oss(manager)
        
        # Start metrics loop (optional)
        start_metrics_loop(manager)
        
        # Print summary
        print_summary()
        
        # Monitor processes
        monitor_processes(manager)
        
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        manager.shutdown_all()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
