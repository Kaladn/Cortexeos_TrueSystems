#!/usr/bin/env python3
"""Clearbox AI Studio — State Machine Installer

Two-phase install with prerequisite checking before any pip work:

  PREFLIGHT → INSTALLING → STARTING_SERVICES → DONE

Phase 1 (Preflight):  Check Python, Git, and repo structure BEFORE
                      creating .venv.  Missing required prerequisites →
                      print list and exit (fix them, then re-run).
                      Recommended deps (Ollama, Windows Biometric) print
                      a warning but do not block the install.

Phase 2 (Install):    venv → deps → data dirs → config → nltk → models →
                      platform → smoke → validate → start.
                      Each sub-step checkpoints to install_state.json so
                      a crash or reboot can resume from the last good step.

GPU support (auto by default — no flags needed):
  The installer auto-detects NVIDIA (CUDA) or AMD (ROCm) and selects the
  correct PyTorch and llama-cpp-python wheels automatically.
  GPU is used for local LLM inference (llama-cpp-python) only.
  Override with:
    --gpu auto   Detect at install time (default)
    --gpu rocm   Force AMD ROCm 7.1 torch wheel
    --gpu cuda   Force NVIDIA CUDA 12.4 torch wheel
    --gpu cpu    CPU-only (no GPU acceleration)

Usage:
    python scripts/clearbox_install.py
    python scripts/clearbox_install.py --gpu cuda
    python scripts/clearbox_install.py --gpu cpu
    python scripts/clearbox_install.py --resume          # after reboot
    python scripts/clearbox_install.py --skip-preflight  # advanced
    python scripts/clearbox_install.py --write-lock
    python scripts/clearbox_install.py --manifest-only
    python scripts/clearbox_install.py --no-start --no-browser
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import re
import textwrap
import time
import webbrowser
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Tuple

if os.name == "nt":
    import winreg

# ── Constants ──────────────────────────────────────────────────

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR       = ".venv"
PREFERRED_WINDOWS_DATA_ROOT = Path("D:/Clearbox AI Data Root")
LEGACY_WINDOWS_DATA_ROOT = Path("D:/CLEARBOX")
LOCK_FILE      = "requirements.lock.txt"
REQ_FILE       = "requirements.txt"
CONFIG_FILE    = "clearbox.config.json"

CLEARBOX_PORTS      = {"Bridge": 5050, "Citations": 5052, "Node": 5060, "UI": 8080, "LLM": 11435}
MIN_PYTHON        = (3, 11)
INSTALLER_VERSION = "2.5.0"
_DATA_ROOT_OVERRIDE: Optional[Path] = None

# Repo markers — if any are missing, this isn't a Clearbox AI workspace
REPO_MARKERS = [CONFIG_FILE, REQ_FILE, "security/data_paths.py",
                "bridges/clearbox_bridge_server.py", "ui/clearbox_ai_production.html"]

# Critical directories that must exist in the repo
CRITICAL_DIRS = ["security", "bridges", "scripts", "ui", "routing",
                 "core/lakespeak"]

# Data directories under the selected data root.
# This list is the authoritative installer mirror of security/data_paths.py.
# Keep in sync — every path created by data_paths.py must appear here.
DATA_SUBDIRS = [
    # Chat threads + summaries (chats are ENCRYPTED)
    "data/chats",
    "data/summaries/week",
    "data/summaries/month",
    "data/summaries/year",
    # Conversation artifacts
    "data/citations",
    "data/notes",
    "data/maps",
    "data/archive",
    # Structural memory
    "data/memory",
    "data/memory/structural",
    "data/memory/structural/anchor_observations",
    "data/memory/structural/relation_observations",
    "data/memory/structural/lifecycle",
    "data/memory/structural/views",
    # Chat packs + tool creation
    "data/chat_packs/packs",
    "data/chat_packs/sessions",
    "data/tool creation",
    "data/tool creation/ledger",
    "data/tool creation/sessions",
    "data/tool creation/drafts",
    "data/tool creation/tools",
    "data/tool creation/tests",
    # Misc data
    "data/packs",
    "data/modules",
    "data/ideas",
    # Secrets (ENCRYPTED — API keys, WebAuthn, Ed25519 node pairs, profiles)
    "data/secrets",
    "data/secrets/tls",
    "data/secrets/node_pairs",
    "data/secrets/mobile_keys",
    # LakeSpeak index (BM25 + dense + per-corpus chunk dirs)
    "data/indexes/lakespeak/index/chunks/general",
    "data/indexes/lakespeak/index/chunks/chats",
    "data/indexes/lakespeak/index/chunks/gutenberg",
    "data/indexes/lakespeak/index/bm25",
    "data/indexes/lakespeak/index/dense",
    "data/indexes/lakespeak/events",
    "data/indexes/lakespeak/eval",
    # Genesis + reasoning indexes
    "data/indexes/genesis",
    "data/indexes/reasoning",
    # Logs
    "data/logs/observe",
    "data/logs/audit",
    "data/logs/diagnostic",
    # Config
    "config",
    "config/tools",
    "config/help/tutorials",
    # Runtime
    "runtime/temp",
    "runtime/cache",
    "runtime/jobs",
    "runtime/routing/profiles",
]

# Smoke-test imports: module name → human label
SMOKE_IMPORTS = [
    ("fastapi",          "FastAPI"),
    ("uvicorn",          "Uvicorn"),
    ("pydantic",         "Pydantic"),
    ("torch",            "PyTorch"),
    ("numpy",            "NumPy"),
    ("httpx",            "HTTPX"),
    ("cryptography",     "Cryptography"),
    ("nltk",             "NLTK"),
    ("websockets",       "WebSockets"),
    ("sklearn",          "scikit-learn"),
    ("sentence_transformers", "Sentence Transformers"),
    ("cv2",              "OpenCV"),
    ("psutil",           "psutil"),
    ("rich",             "Rich"),
]


# ── State Machine ─────────────────────────────────────────────

class InstallState(str, Enum):
    """Installer state machine phases."""
    PREFLIGHT         = "PREFLIGHT"
    WAITING_ON_USER   = "WAITING_ON_USER"
    INSTALLING        = "INSTALLING"
    STARTING_SERVICES = "STARTING_SERVICES"
    DONE              = "DONE"


@dataclass
class Requirement:
    """A single prerequisite that must (or should) be satisfied."""
    id: str                              # e.g. "python", "git", "ollama"
    label: str                           # Human-readable name
    type: str                            # "tool" | "port" | "service"
    detect: Callable[[], bool]           # Returns True if satisfied
    help_url: str                        # URL to install guide
    reboot_hint: bool = False            # Installing may require reboot
    severity: str = "required"           # "required" | "recommended"
    _cached: Optional[bool] = field(default=None, repr=False)

    def check(self) -> bool:
        self._cached = self.detect()
        return self._cached

    @property
    def passed(self) -> bool:
        if self._cached is None:
            return self.check()
        return self._cached

    def reset(self) -> None:
        self._cached = None


def _legacy_state_file_path() -> Path:
    """Legacy state file path from pre-D:/CLEARBOX installers."""
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "ClearboxAI" / "install_state.json"
    return Path.home() / ".clearbox_ai" / "install_state.json"


def _state_file_path() -> Path:
    """Installer state path under the runtime root."""
    return _data_root() / "runtime" / "install_state.json"


@dataclass
class InstallerPersist:
    """Persisted installer state — survives crashes and reboots."""
    state: InstallState = InstallState.PREFLIGHT
    timestamp: str = ""
    passed_checks: List[str] = field(default_factory=list)
    gpu_enabled: bool = False
    gpu_type: str = "cpu"
    error_log: List[str] = field(default_factory=list)
    upgrade_mode: str = ""  # "", "meld", "backup", "replace"

    def save(self) -> None:
        self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        path = _state_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "state": self.state.value,
            "timestamp": self.timestamp,
            "passed_checks": self.passed_checks,
            "gpu_enabled": self.gpu_enabled,
            "gpu_type": self.gpu_type,
            "error_log": self.error_log[-50:],
            "upgrade_mode": self.upgrade_mode,
        }, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> Optional["InstallerPersist"]:
        path = _state_file_path()
        if not path.exists():
            legacy = _legacy_state_file_path()
            if legacy.exists():
                path = legacy
            else:
                return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                state=InstallState(data["state"]),
                timestamp=data.get("timestamp", ""),
                passed_checks=data.get("passed_checks", []),
                gpu_enabled=data.get("gpu_enabled", False),
                gpu_type=data.get("gpu_type", "cpu"),
                error_log=data.get("error_log", []),
                upgrade_mode=data.get("upgrade_mode", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    @staticmethod
    def clear() -> None:
        for path in (_state_file_path(), _legacy_state_file_path()):
            if path.exists():
                path.unlink()


# ── Helpers ────────────────────────────────────────────────────

class _C:
    """ANSI colors for terminal output."""
    OK   = "\033[92m"  # green
    WARN = "\033[93m"  # yellow
    ERR  = "\033[91m"  # red
    DIM  = "\033[90m"  # gray
    BOLD = "\033[1m"
    END  = "\033[0m"


def _print_step(n: int, total: int, label: str) -> None:
    print(f"\n{_C.BOLD}{n}/{total}  {label}{_C.END}\n")


def _ok(msg: str) -> None:
    print(f"   {_C.OK}OK{_C.END}  {msg}")


def _warn(msg: str) -> None:
    print(f"   {_C.WARN}!!{_C.END}  {msg}")


def _err(msg: str) -> None:
    print(f"   {_C.ERR}XX{_C.END}  {msg}")


def _info(msg: str) -> None:
    print(f"   {_C.DIM}--{_C.END}  {msg}")


# Torch index URLs — tried in order until one yields a wheel for the running
# Python version.  cu124 has no cp314 wheels; cu128/cu126 do.
_TORCH_INDEX = {
    "rocm": ["https://download.pytorch.org/whl/rocm7.1"],
    "cuda": [
        "https://download.pytorch.org/whl/cu128",  # CUDA 12.8 — cp314 wheels exist
        "https://download.pytorch.org/whl/cu126",  # CUDA 12.6 fallback
        "https://download.pytorch.org/whl/cu124",  # CUDA 12.4 fallback (no cp314)
    ],
}

# llama_cpp_python: pre-built wheel indexes tried first.
# If none yield a compatible wheel, fall back to source build with CUDA
# enabled via CMAKE_ARGS (requires MSVC + CUDA toolkit — confirmed present).
_LLAMA_CPP_WHEEL_INDEX = {
    "cuda": [
        "https://abetlen.github.io/llama-cpp-python/whl/cu128",
        "https://abetlen.github.io/llama-cpp-python/whl/cu124",
    ],
    "rocm": ["https://abetlen.github.io/llama-cpp-python/whl/rocm"],
    "cpu":  ["https://abetlen.github.io/llama-cpp-python/whl/cpu"],
}



def _detect_gpu_type() -> str:
    """Auto-detect GPU backend.  Returns 'rocm', 'cuda', or 'cpu'."""
    # --- NVIDIA: probe nvidia-smi ---
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            return "cuda"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # --- AMD on Windows: probe WMI ---
    if os.name == "nt":
        try:
            r = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "Name"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                names = r.stdout.lower()
                if "amd" in names or "radeon" in names:
                    return "rocm"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    else:
        # --- AMD on Linux/WSL: probe rocm-smi ---
        try:
            r = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                return "rocm"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return "cpu"


# ── Prerequisite detect functions ─────────────────────────────

def _detect_python() -> bool:
    return sys.version_info >= (3, 10)


def _detect_git() -> bool:
    try:
        r = subprocess.run(["git", "--version"],
                           capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _detect_msvc_or_cmake() -> bool:
    """Check for cl.exe (MSVC) or cmake on PATH — needed for source builds."""
    for args in [["cmake", "--version"], ["where", "cl"]]:
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


def _detect_cmake() -> bool:
    """Detect cmake on PATH or in common Windows install locations.

    CMake is often installed via Visual Studio but not added to the system
    PATH.  Check the known VS bundled locations before giving up.
    """
    if shutil.which("cmake"):
        return True

    if os.name != "nt":
        return False

    # Visual Studio bundles cmake under Common7/IDE/CommonExtensions/Microsoft/CMake
    # across multiple VS versions and editions.
    import glob as _glob
    vs_patterns = [
        "C:/Program Files/Microsoft Visual Studio/*/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe",
        "C:/Program Files/Microsoft Visual Studio/*/Professional/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe",
        "C:/Program Files/Microsoft Visual Studio/*/Enterprise/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe",
        "C:/Program Files (x86)/Microsoft Visual Studio/*/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe",
    ]
    for pattern in vs_patterns:
        if _glob.glob(pattern):
            return True

    return False


def _detect_ollama() -> bool:
    """Ollama: try CLI, then HTTP probe on 11434."""
    try:
        r = subprocess.run(["ollama", "--version"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(("127.0.0.1", 11434))
        return True
    except OSError:
        return False


def _detect_cuda_toolkit() -> bool:
    for cmd in [["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                ["nvcc", "--version"]]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


def _has_nvidia_gpu() -> bool:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10)
        return r.returncode == 0 and bool(r.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _detect_wbiosrvc() -> bool:
    """Windows Biometric Service — needed for Windows Hello auth."""
    try:
        r = subprocess.run(["sc", "query", "WbioSrvc"],
                           capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _build_requirements(include_gpu_checks: bool = False) -> List[Requirement]:
    """Build the prerequisite manifest.

    Only Python and Git are required — missing either stops the install.
    Ollama and Windows Biometric Service are recommended (feature deps);
    they print a warning but do not block install.
    MSVC/CMake is not checked: llama-cpp-python is installed from
    pre-built wheels, so no compiler is needed.
    """
    reqs: List[Requirement] = [
        Requirement(
            id="python", label="Python 3.10+", type="tool",
            detect=_detect_python,
            help_url="https://www.python.org/downloads/",
        ),
        Requirement(
            id="git", label="Git", type="tool",
            detect=_detect_git,
            help_url="https://git-scm.com/download/win",
        ),
        Requirement(
            id="cmake", label="CMake (required by mapping engine)", type="tool",
            detect=_detect_cmake,
            help_url="https://cmake.org/download/",
        ),
        Requirement(
            id="ollama", label="Ollama (for grounded/LLM chat modes)", type="service",
            detect=_detect_ollama,
            help_url="https://ollama.com/download",
            reboot_hint=False,
            severity="recommended",
        ),
        Requirement(
            id="wbiosrvc", label="Windows Biometric Service (Windows Hello auth)", type="service",
            detect=_detect_wbiosrvc,
            help_url="https://support.microsoft.com/en-us/windows/learn-about-windows-hello",
            severity="recommended",
        ),
    ]
    if include_gpu_checks and _has_nvidia_gpu():
        reqs.append(Requirement(
            id="cuda", label="CUDA Toolkit", type="tool",
            detect=_detect_cuda_toolkit,
            help_url="https://developer.nvidia.com/cuda-downloads",
            reboot_hint=True, severity="recommended",
        ))
    return reqs


def _run(cmd: List[str], timeout: int = 300,
         stream: bool = False,
         env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run a subprocess, print the command, raise on failure.

    stream=True — print output live (use for large pip downloads so the
    terminal doesn't appear frozen).  stdout+stderr are merged and still
    returned in CompletedProcess.stdout for error reporting.
    env — optional environment dict (e.g. to inject CMAKE_ARGS).
    """
    _info(f"$ {' '.join(cmd)}")
    if stream:
        proc = subprocess.Popen(
            cmd, cwd=str(WORKSPACE_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, encoding="utf-8", errors="replace",
            env=env,
        )
        lines: List[str] = []
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                print(f"       {line}", end="", flush=True)
                lines.append(line)
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise
        return subprocess.CompletedProcess(
            cmd, proc.returncode, "".join(lines), ""
        )
    return subprocess.run(
        cmd, cwd=str(WORKSPACE_ROOT),
        capture_output=True, text=True, timeout=timeout,
        env=env,
    )


def _data_root() -> Path:
    """Installer/runtime data root (must match security/data_paths.py)."""
    global _DATA_ROOT_OVERRIDE
    if _DATA_ROOT_OVERRIDE is not None:
        return _DATA_ROOT_OVERRIDE
    env_root = os.environ.get("CLEARBOX_DATA_ROOT")
    if env_root:
        return Path(env_root.strip().strip('"')).expanduser()
    saved = _read_bootstrap_data_root()
    if saved is not None:
        return saved
    return PREFERRED_WINDOWS_DATA_ROOT


def _bootstrap_storage_file() -> Path:
    """Path for persisted storage-root selection before data_paths import."""
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "ClearboxAI" / "storage_paths.json"
    return Path.home() / ".clearbox_ai" / "storage_paths.json"


def _read_bootstrap_data_root() -> Optional[Path]:
    cfg = _bootstrap_storage_file()
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    root = data.get("data_root")
    if not root or not isinstance(root, str):
        return None
    return Path(root).expanduser()


def _persist_bootstrap_data_root(path: Path) -> None:
    cfg = _bootstrap_storage_file()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "data_root": str(path),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "installer_version": INSTALLER_VERSION,
    }
    cfg.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _set_data_root(path: Path, *, persist: bool) -> None:
    global _DATA_ROOT_OVERRIDE
    resolved = path.expanduser()
    _DATA_ROOT_OVERRIDE = resolved
    os.environ["CLEARBOX_DATA_ROOT"] = str(resolved)
    if persist:
        _persist_bootstrap_data_root(resolved)


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".install_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _pick_data_root_windows(default_path: Path) -> Optional[Path]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            title="Select Clearbox data root folder",
            initialdir=str(default_path),
            mustexist=False,
        )
        root.destroy()
        if not selected:
            return None
        return Path(selected)
    except Exception as e:
        _warn(f"Folder picker unavailable ({e})")
        return None


def _configure_data_root(requested_path: Optional[str], *, interactive: bool) -> bool:
    """Choose and persist data root before installer writes state/files."""
    if requested_path:
        chosen = Path(requested_path).expanduser()
        if len(chosen.parts) == 1:
            chosen = chosen / "Clearbox AI Data Root"
            _warn(f"Bare drive root supplied — using named subdirectory: {chosen}")
        if not _is_writable_dir(chosen):
            _err(f"Data root is not writable: {chosen}")
            return False
        _set_data_root(chosen, persist=True)
        _ok(f"Data root selected: {chosen}")
        return True

    saved = _read_bootstrap_data_root()
    if not interactive:
        if saved is not None and _is_writable_dir(saved):
            _set_data_root(saved, persist=False)
            _ok(f"Using saved data root: {saved}")
            return True
        if saved is not None:
            _warn(f"Saved data root is not writable: {saved}")
        _err("No saved data root available for non-interactive install.")
        _info("Re-run interactively so the installer can ask where to store data, or pass --data-root.")
        return False

    # Determine the default suggestion shown in the picker.
    # Prefer D:/Clearbox AI Data Root; if D:/ doesn't exist fall back to
    # a dedicated subdirectory on the largest available drive rather than
    # bare home — landing in home itself would scatter data files there.
    if saved:
        default_root = saved
    elif PREFERRED_WINDOWS_DATA_ROOT.drive and Path(PREFERRED_WINDOWS_DATA_ROOT.drive + "/").exists():
        default_root = PREFERRED_WINDOWS_DATA_ROOT
    else:
        # Find the drive with the most free space (excluding the OS drive where
        # possible) and suggest a named subdirectory on it.
        best: Optional[Path] = None
        best_free = -1
        for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{drive_letter}:/")
            if not drive.exists():
                continue
            try:
                free = shutil.disk_usage(drive).free
                if free > best_free:
                    best_free = free
                    best = drive
            except OSError:
                continue
        default_root = (best or Path.home()) / "Clearbox AI Data Root"

    if os.name == "nt":
        initial_dir = default_root.parent if default_root.parent.exists() else Path.home()
        _info(f"Suggested data root: {default_root}")
        chosen = _pick_data_root_windows(initial_dir)
        if chosen is None:
            _err("Data root selection cancelled.")
            return False
    else:
        chosen = default_root

    if not _is_writable_dir(chosen):
        _err(f"Selected folder is not writable: {chosen}")
        return False

    # Never accept a bare drive root (e.g. E:\) — always require a named subdir.
    # If the user picked a drive root directly, append the standard subdir name.
    chosen_parts = chosen.parts  # e.g. ('E:\\',) for bare root
    if len(chosen_parts) == 1:
        chosen = chosen / "Clearbox AI Data Root"
        _warn(f"Bare drive root selected — using named subdirectory: {chosen}")

    _set_data_root(chosen, persist=True)
    _ok(f"Data root selected: {chosen}")
    _info(f"Saved in: {_bootstrap_storage_file()}")
    return True


def _desktop() -> Path:
    """Return the user's Desktop path for backups."""
    user = os.environ.get("USERPROFILE")
    if user:
        p = Path(user) / "Desktop"
        if p.exists():
            return p
    onedrive = os.environ.get("OneDrive")
    if onedrive:
        p = Path(onedrive) / "Desktop"
        if p.exists():
            return p
    return Path.home() / "Desktop"


def _version_tuple(ver: str) -> Tuple[int, ...]:
    """Extract numeric version tuple from strings like 'clearbox-bridge-1.4.0' or '1.4.0'."""
    m = re.search(r"(\d+(?:\.\d+)+)", ver)
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split("."))


def _compare_versions(installed: str, current: str) -> str:
    """Compare installed vs current version. Returns 'same', 'older', or 'newer'."""
    iv = _version_tuple(installed)
    cv = _version_tuple(current)
    if iv == cv:
        return "same"
    return "older" if iv < cv else "newer"


def _check_existing_install() -> Tuple[Optional[str], Path]:
    """Detect an existing install. Returns (version_or_None, data_root)."""
    dr = _data_root()
    if not dr.exists():
        return None, dr

    # Check if any data subdirectories exist
    has_data = any((dr / sub).exists() for sub in DATA_SUBDIRS[:5])
    if not has_data:
        return None, dr

    # Try to read version stamp
    vf = dr / "install_version.json"
    if vf.exists():
        try:
            data = json.loads(vf.read_text(encoding="utf-8"))
            return data.get("version", "unknown"), dr
        except (json.JSONDecodeError, OSError):
            return "unknown", dr

    # Data dirs exist but no version file → legacy install
    return "unknown", dr


def _port_free(port: int) -> bool:
    """Check if a TCP port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def _venv_python() -> Path:
    """Path to the venv Python executable."""
    if os.name == "nt":
        return WORKSPACE_ROOT / VENV_DIR / "Scripts" / "python.exe"
    return WORKSPACE_ROOT / VENV_DIR / "bin" / "python"


# ── Preflight & recheck loop ──────────────────────────────────

def run_preflight(requirements: List[Requirement],
                  ) -> Tuple[List[Requirement], List[Requirement]]:
    """Run all detect() checks.  Returns (failures, warnings).

    failures = severity="required" that failed
    warnings = severity="recommended" that failed
    """
    failures: List[Requirement] = []
    warnings: List[Requirement] = []
    for req in requirements:
        passed = req.check()
        status = f"{_C.OK}OK{_C.END}" if passed else (
            f"{_C.ERR}MISSING{_C.END}" if req.severity == "required"
            else f"{_C.WARN}MISSING{_C.END}")
        print(f"   {status}  {req.label}")
        if not passed:
            (failures if req.severity == "required" else warnings).append(req)
    return failures, warnings


def print_missing_requirements(failures: List[Requirement],
                               warnings: List[Requirement]) -> None:
    """Print a formatted table of missing prerequisites."""
    print()
    if failures:
        print(f"  {_C.ERR}{_C.BOLD}MISSING (required):{_C.END}")
        print()
        print(f"   {'Requirement':<30s}  {'Type':<8s}  {'Reboot?':<8s}  URL")
        print(f"   {'-'*30}  {'-'*8}  {'-'*8}  {'-'*40}")
        for req in failures:
            rb = "yes" if req.reboot_hint else ""
            print(f"   {_C.ERR}{req.label:<30s}{_C.END}"
                  f"  {req.type:<8s}  {rb:<8s}  {req.help_url}")
        print()
    if warnings:
        print(f"  {_C.WARN}{_C.BOLD}MISSING (recommended):{_C.END}")
        print()
        for req in warnings:
            print(f"   {_C.WARN}{req.label:<30s}{_C.END}  {req.help_url}")
        print()


def wait_for_user_recheck_loop(requirements: List[Requirement],
                               state: InstallerPersist) -> bool:
    """Interactive [R]/[O]/[B]/[Q] loop.  Returns True when all required pass."""
    first_pass = True
    while True:
        if first_pass:
            # Use cached results from the PREFLIGHT phase — don't re-run
            first_pass = False
            failures = [r for r in requirements
                        if r._cached is not None and not r._cached
                        and r.severity == "required"]
            warnings = [r for r in requirements
                        if r._cached is not None and not r._cached
                        and r.severity != "required"]
        else:
            failures, warnings = run_preflight(requirements)
        if not failures:
            if warnings:
                print_missing_requirements([], warnings)
                print(f"  {_C.WARN}Recommended prerequisites missing"
                      f" (install may still succeed).{_C.END}")
            return True

        print_missing_requirements(failures, warnings)

        needs_reboot = any(r.reboot_hint for r in failures)
        if needs_reboot:
            print(f"  {_C.DIM}Some prerequisites may require a reboot"
                  f" after installation.{_C.END}")

        opts = ["[R] Recheck", "[O] Open all help links"]
        if needs_reboot:
            opts.append("[B] Set resume hook & reboot")
        opts.append("[Q] Quit")
        print()
        print("  " + "  ".join(opts))
        print()

        try:
            choice = input("  > ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            return False

        if choice == "R":
            print()
            _info("Rechecking prerequisites...")
            for req in requirements:
                req.reset()

        elif choice == "O":
            urls = sorted({r.help_url for r in failures + warnings})
            for url in urls:
                _info(f"Opening: {url}")
                webbrowser.open(url)
            print()
            _info("Install the missing tools, then press [R] to recheck.")

        elif choice == "B" and needs_reboot:
            ensure_resume_hook()
            state.state = InstallState.PREFLIGHT
            state.save()
            print()
            print(f"  {_C.OK}Resume hook set.{_C.END}")
            print("  The installer will re-run automatically after logon.")
            print("  Reboot when ready.")
            return False

        elif choice == "Q":
            return False

        else:
            _warn(f"Unknown choice: {choice}")


# ── Resume hook (Windows Registry Run key) ───────────────────

_RESUME_HOOK_NAME = "ClearboxAI_Install_Resume"
_RESUME_HOOK_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"


def ensure_resume_hook() -> None:
    """Set a Registry Run key to re-run installer at next logon."""
    if os.name != "nt":
        _warn("Resume hook only supported on Windows")
        return
    python_exe = sys.executable
    script_path = Path(__file__).resolve()
    cmd = f'"{python_exe}" "{script_path}" --resume'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RESUME_HOOK_KEY,
                            0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _RESUME_HOOK_NAME, 0, winreg.REG_SZ, cmd)
        _ok(f"Resume hook set: HKCU\\...\\Run\\{_RESUME_HOOK_NAME}")
    except OSError as e:
        _err(f"Could not set resume hook: {e}")
        _info("You can manually re-run: python scripts/clearbox_install.py --resume")


def remove_resume_hook() -> None:
    """Remove the Registry Run key (idempotent)."""
    if os.name != "nt":
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RESUME_HOOK_KEY,
                            0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _RESUME_HOOK_NAME)
        _info("Resume hook removed")
    except FileNotFoundError:
        pass
    except OSError as e:
        _warn(f"Could not remove resume hook: {e}")


# ── Step 1: Detect ─────────────────────────────────────────────

def step_detect() -> bool:
    _print_step(1, 2, "Detect environment")

    # Python version
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) < MIN_PYTHON:
        _err(f"Python {ver_str} — need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
        return False
    _ok(f"Python {ver_str}")

    # OS
    _ok(f"OS: {platform.platform()}")

    # Workspace
    _ok(f"Workspace: {WORKSPACE_ROOT}")

    # Data root
    _ok(f"Data root: {_data_root()}")

    return True


# ── Step 2: Preflight ──────────────────────────────────────────

def step_preflight() -> bool:
    _print_step(2, 2, "Preflight — verify repo structure")

    ok = True

    # Repo markers
    for marker in REPO_MARKERS:
        path = WORKSPACE_ROOT / marker
        if path.exists():
            _ok(marker)
        else:
            _err(f"Missing: {marker}")
            ok = False

    # Critical dirs
    for d in CRITICAL_DIRS:
        path = WORKSPACE_ROOT / d
        if path.is_dir():
            _ok(d)
        else:
            _err(f"Missing directory: {d}")
            ok = False

    # Write test on workspace
    test_file = WORKSPACE_ROOT / ".install_write_test"
    try:
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        _ok("Workspace writable")
    except OSError as e:
        _err(f"Workspace not writable: {e}")
        ok = False

    # Write test on data root
    dr = _data_root()
    try:
        dr.mkdir(parents=True, exist_ok=True)
        test_file = dr / ".install_write_test"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        _ok(f"Data root writable: {dr}")
    except OSError as e:
        _err(f"Data root not writable ({dr}): {e}")
        ok = False

    if not ok:
        _err("Preflight FAILED — fix the above before continuing")
    return ok


# ── Step 3: Venv ───────────────────────────────────────────────

def step_venv() -> bool:
    _print_step(1, 9, "Virtual environment")

    venv_py = _venv_python()

    if venv_py.exists():
        # Verify it works
        r = _run([str(venv_py), "--version"])
        if r.returncode == 0:
            _ok(f"Existing venv: {r.stdout.strip()}")
            return True
        else:
            _warn("Venv exists but Python is broken — recreating")
            shutil.rmtree(WORKSPACE_ROOT / VENV_DIR, ignore_errors=True)

    _info("Creating virtual environment...")
    r = _run([sys.executable, "-m", "venv", str(WORKSPACE_ROOT / VENV_DIR)])
    if r.returncode != 0:
        _err(f"venv creation failed: {r.stderr}")
        return False

    if not venv_py.exists():
        _err("venv created but python executable not found")
        return False

    _ok(f"Created: {WORKSPACE_ROOT / VENV_DIR}")
    return True


# ── Step 4: Dependencies ──────────────────────────────────────

def step_deps(gpu_type: str = "cpu") -> bool:
    _print_step(2, 9, "Install dependencies")

    venv_py = _venv_python()

    # Upgrade pip first
    _info("Upgrading pip...")
    r = _run([str(venv_py), "-m", "pip", "install", "--upgrade",
              "pip", "setuptools", "wheel"], timeout=120, stream=True)
    if r.returncode != 0:
        _warn(f"pip upgrade warning: {r.stdout[:200]}")

    # ── Torch: try each GPU wheel index in priority order ────────────────────
    # Indexes are ordered newest → oldest so the best available CUDA version
    # for this Python tag is selected first.  cu124 has no cp314 wheels;
    # cu128/cu126 do.  We stop at the first successful install.
    _info(f"GPU backend selected: {gpu_type.upper()}")
    torch_installed = False
    indexes = _TORCH_INDEX.get(gpu_type, [])
    for index_url in indexes:
        _info(f"Trying PyTorch {gpu_type.upper()} — {index_url}")
        r = _run(
            [str(venv_py), "-m", "pip", "install", "torch>=2.4.0",
             "--index-url", index_url],
            timeout=600, stream=True,
        )
        if r.returncode == 0:
            _ok(f"PyTorch ({gpu_type.upper()}) installed from {index_url}")
            torch_installed = True
            break
        _warn(f"No wheel at {index_url} — trying next")

    if not torch_installed:
        if gpu_type != "cpu":
            _err(f"No CUDA torch wheel found for Python {sys.version.split()[0]} "
                 f"across all {gpu_type.upper()} indexes.")
            _err("Cannot proceed without GPU-enabled PyTorch.")
            _info("Check https://pytorch.org/get-started/locally/ for supported Python versions.")
            return False
        else:
            _ok("PyTorch (CPU-only build)")

    # ── llama_cpp_python ──────────────────────────────────────────────────────
    # Try pre-built wheel indexes first (no compiler needed).
    # If none have a wheel for this Python version + CUDA version, build from
    # source with CUDA enabled — VS + CMake + CUDA toolkit are confirmed present.
    llama_indexes = _LLAMA_CPP_WHEEL_INDEX.get(gpu_type, [])
    llama_installed = False

    for llama_index in llama_indexes:
        _info(f"Trying llama-cpp-python pre-built wheel ({gpu_type.upper()}) — {llama_index}")
        r = _run(
            [str(venv_py), "-m", "pip", "install", "llama-cpp-python",
             "--extra-index-url", llama_index, "--prefer-binary", "--no-deps"],
            timeout=300, stream=True,
        )
        if r.returncode == 0:
            _ok("llama-cpp-python installed (pre-built)")
            llama_installed = True
            break
        _warn(f"No pre-built wheel at {llama_index}")

    if not llama_installed and gpu_type == "cuda":
        # Source build with CUDA enabled.  CMAKE_ARGS tells the build system to
        # compile the GGML CUDA backend.  Requires MSVC + CUDA toolkit headers.
        _info("Building llama-cpp-python from source with CUDA support...")
        _info("This takes several minutes — MSVC is compiling the GGML CUDA backend.")
        env = os.environ.copy()
        env["CMAKE_ARGS"] = "-DGGML_CUDA=on"
        env["FORCE_CMAKE"] = "1"
        r = _run(
            [str(venv_py), "-m", "pip", "install", "llama-cpp-python",
             "--no-binary", "llama-cpp-python", "--no-deps"],
            timeout=1800, stream=True, env=env,
        )
        if r.returncode == 0:
            _ok("llama-cpp-python built from source with CUDA support")
            llama_installed = True
        else:
            _warn("llama-cpp-python CUDA source build failed — will install CPU fallback")
            r = _run(
                [str(venv_py), "-m", "pip", "install", "llama-cpp-python", "--no-deps"],
                timeout=300, stream=True,
            )
            if r.returncode == 0:
                _warn("llama-cpp-python installed (CPU fallback — no GPU inference)")
                llama_installed = True
            else:
                _err("llama-cpp-python install failed entirely")

    if not llama_installed and gpu_type not in ("cuda",):
        # CPU / ROCm pre-built path
        _warn("llama-cpp-python pre-built wheel unavailable — source build will be attempted")
        llama_installed = False  # lock file will handle it

    # ── Rest of dependencies ─────────────────────────────────────────────────
    # Pick requirements file: lock > requirements
    lock_path = WORKSPACE_ROOT / LOCK_FILE
    req_path = WORKSPACE_ROOT / REQ_FILE

    if lock_path.exists():
        target = lock_path
        _ok(f"Using pinned lock file: {LOCK_FILE} ({_count_lines(lock_path)} packages)")
    else:
        target = req_path
        _warn(f"No {LOCK_FILE} found — using {REQ_FILE} (unpinned, may drift)")

    # Filter packages from lock file that were already handled above:
    #  • pip / setuptools / wheel — just upgraded, don't let lock file downgrade
    #  • llama-cpp-python — pre-installed from GPU wheel index (version tag mismatch)
    #  • torch — pre-installed from GPU-specific index
    _SKIP_IN_LOCK = {"pip", "setuptools", "wheel", "torch"}
    if llama_installed:
        _SKIP_IN_LOCK.add("llama-cpp-python")

    install_target = target
    tmp_req = WORKSPACE_ROOT / ".install_tmp_req.txt"
    if _SKIP_IN_LOCK:
        raw = target.read_text(encoding="utf-8")
        filtered = []
        for ln in raw.splitlines():
            name = ln.strip().lower().replace("_", "-").split("==")[0].split(">=")[0]
            if name in _SKIP_IN_LOCK:
                continue
            filtered.append(ln)
        tmp_req.write_text("\n".join(filtered), encoding="utf-8")
        install_target = tmp_req
        _info(f"(skipping {', '.join(sorted(_SKIP_IN_LOCK))} — already handled)")

    _info(f"Installing from {target.name}...")
    r = _run([str(venv_py), "-m", "pip", "install", "-r", str(install_target)],
             timeout=600, stream=True)

    if tmp_req.exists():
        tmp_req.unlink()

    if r.returncode != 0:
        _err(f"pip install failed:\n{r.stdout[-2000:]}")
        return False

    _ok(f"Dependencies installed from {target.name}")
    return True


def _count_lines(path: Path) -> int:
    """Count non-comment, non-empty lines."""
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.strip().startswith("#"))


# ── Step 5: Data directories ──────────────────────────────────

def step_data_dirs() -> bool:
    _print_step(3, 9, "Create data directories")

    dr = _data_root()
    created = 0
    existed = 0

    for sub in DATA_SUBDIRS:
        path = dr / sub
        if path.exists():
            existed += 1
        else:
            path.mkdir(parents=True, exist_ok=True)
            created += 1

    _ok(f"Data root: {dr}")
    _ok(f"{created} directories created, {existed} already existed")
    _info(f"Total: {len(DATA_SUBDIRS)} directories under {dr}/")
    return True


# ── Step 6: Config ─────────────────────────────────────────────

def step_config() -> bool:
    _print_step(4, 9, "Configuration")

    dr = _data_root()
    src = WORKSPACE_ROOT / CONFIG_FILE
    dst = dr / "config" / CONFIG_FILE

    if not src.exists():
        _err(f"Template missing: {src}")
        return False

    if dst.exists():
        _ok(f"Config already exists: {dst}")
        _info("(keeping existing — no overwrite)")
    else:
        shutil.copy2(str(src), str(dst))
        _ok(f"Config copied: {dst}")

    # Validate — config may be DPAPI-encrypted (production) or plain JSON (fresh)
    try:
        raw = dst.read_bytes()
        data = json.loads(raw.decode("utf-8"))
        _ok(f"Valid JSON (plain) — {len(data)} top-level keys")
    except (json.JSONDecodeError, UnicodeDecodeError):
        # DPAPI-encrypted config — that's fine, means it's a live system
        _ok(f"Config present (DPAPI-encrypted) — {len(raw)} bytes")
    except OSError as e:
        _err(f"Config read failed: {e}")
        return False

    return True


# ── Step 7: NLTK ──────────────────────────────────────────────

def step_nltk() -> bool:
    _print_step(5, 9, "NLTK data (punkt tokenizer)")

    venv_py = _venv_python()
    code = textwrap.dedent("""\
        import nltk, os
        # Check if punkt_tab already exists
        try:
            nltk.data.find("tokenizers/punkt_tab")
            print("ALREADY_EXISTS")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)
            print("DOWNLOADED")
    """)
    r = _run([str(venv_py), "-c", code], timeout=60)
    if r.returncode != 0:
        _warn(f"NLTK download failed (non-critical): {r.stderr[:200]}")
        _info("System will work but tokenization may fall back to split()")
        return True  # non-fatal

    out = r.stdout.strip()
    if "ALREADY_EXISTS" in out:
        _ok("punkt_tab already downloaded")
    else:
        _ok("punkt_tab downloaded")
    return True


# ── Step 8: Models ─────────────────────────────────────────────

def step_models() -> bool:
    _print_step(6, 9, "Model files")

    models_dir = WORKSPACE_ROOT / "models"
    if not models_dir.exists():
        _warn("models/ directory not found")
        _info("LLM features require .gguf model files in models/")
        _info("System will run but local inference won't work")
        return True  # non-fatal

    gguf_files = sorted(models_dir.glob("*.gguf"))
    if not gguf_files:
        _warn("No .gguf model files found in models/")
        _info("Download a model (e.g., Qwen2.5-7B) to enable local inference")
        return True  # non-fatal

    for f in gguf_files:
        size_gb = f.stat().st_size / (1024 ** 3)
        _ok(f"{f.name} ({size_gb:.1f} GB)")

    _ok(f"{len(gguf_files)} model(s) found")
    return True


# ── Step 9: Platform ───────────────────────────────────────────

def step_platform(gpu_type: str = "cpu") -> bool:
    _print_step(7, 9, "Platform-specific setup")

    if os.name != "nt":
        _info("Non-Windows — skipping platform setup")
        return True

    if gpu_type != "cpu":
        # Check for GPU only when GPU mode is explicitly requested.
        venv_py = _venv_python()
        r = _run([str(venv_py), "-c",
                  "from bridges.gpu_backend import gpu_available, gpu_device_name, gpu_version_string; print(gpu_available(), gpu_device_name(0) + ' (' + gpu_version_string() + ')' if gpu_available() else 'none')"],
                 timeout=30)
        if r.returncode == 0:
            parts = r.stdout.strip().split(maxsplit=1)
            if parts[0] == "True":
                _ok(f"GPU available: {parts[1] if len(parts) > 1 else 'yes'}")
            else:
                _warn("GPU not detected — install will continue in CPU-compatible mode")
        else:
            _warn("Could not check GPU (non-critical)")
    else:
        _info("GPU checks skipped (CPU-first install)")

    # Check Ollama
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(("127.0.0.1", 11434))
        _ok("Ollama detected on port 11434")
    except OSError:
        _warn("Ollama not running on port 11434")
        _info("Install Ollama and pull a model for grounded/LLM chat modes")

    return True


# ── Step 10: Smoke tests ──────────────────────────────────────

def step_smoke() -> bool:
    _print_step(8, 9, "Smoke tests — verify imports")

    venv_py = _venv_python()
    passed = 0
    failed = 0

    for mod, label in SMOKE_IMPORTS:
        r = _run([str(venv_py), "-c", f"import {mod}"], timeout=30)
        if r.returncode == 0:
            _ok(label)
            passed += 1
        else:
            _warn(f"{label} ({mod}) — import failed")
            failed += 1

    _ok(f"{passed}/{passed + failed} imports passed")
    if failed > 0:
        _warn(f"{failed} imports failed — some features may not work")
    return True  # non-fatal (warn only)


# ── Step 11: Validate ─────────────────────────────────────────

def step_validate() -> bool:
    _print_step(9, 9, "Validate — pre-launch checks")

    ok = True

    # Venv python works
    venv_py = _venv_python()
    r = _run([str(venv_py), "--version"])
    if r.returncode == 0:
        _ok(f"venv Python: {r.stdout.strip()}")
    else:
        _err("venv Python not working")
        ok = False

    # Config exists (may be DPAPI-encrypted or plain JSON)
    dr = _data_root()
    cfg = dr / "config" / CONFIG_FILE
    if cfg.exists():
        try:
            raw = cfg.read_bytes()
            json.loads(raw.decode("utf-8"))
            _ok(f"Config valid (plain JSON): {cfg}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            _ok(f"Config present (DPAPI-encrypted): {cfg}")
        except OSError as e:
            _err(f"Config unreadable: {e}")
            ok = False
    else:
        _err(f"Config missing: {cfg}")
        ok = False

    # Data dirs exist
    missing_dirs = [sub for sub in DATA_SUBDIRS if not (dr / sub).exists()]
    if missing_dirs:
        _err(f"{len(missing_dirs)} data directories missing")
        for d in missing_dirs[:5]:
            _info(f"  {d}")
        ok = False
    else:
        _ok(f"All {len(DATA_SUBDIRS)} data directories present")

    # Ports free
    for name, port in CLEARBOX_PORTS.items():
        if _port_free(port):
            _ok(f"Port {port} ({name}) — free")
        else:
            _warn(f"Port {port} ({name}) — in use (service may already be running)")

    # Critical source files
    critical_files = [
        # Bridge (must boot)
        "bridges/clearbox_bridge_server.py",
        "bridges/clearbox_bridge.py",
        "bridges/clearbox_gpu.py",
        "bridges/tool_defs.py",
        # Security (must resolve paths + govern writes)
        "security/data_paths.py",
        "security/gateway.py",
        "security/secure_storage.py",
        "security/middleware.py",
        # Service lifecycle (clearbox_tray.py is the orchestrator)
        "scripts/clearbox_tray.py",
        "scripts/local_llm_server.py",
        # UI (must serve — JS split into ui/js/ modules)
        "ui/clearbox_ai_production.html",
        "ui/js/core.js",
        "ui/launch_ui_internal.py",
        # Config template (needed for fresh installs)
        "clearbox.config.json",
        # Routing (pipeline control)
        "routing/config.py",
        "routing/engine.py",
    ]
    missing_files = [f for f in critical_files if not (WORKSPACE_ROOT / f).exists()]
    if missing_files:
        _err(f"{len(missing_files)} critical files missing:")
        for f in missing_files:
            _info(f"  {f}")
        ok = False
    else:
        _ok(f"All {len(critical_files)} critical source files present")

    if ok:
        _ok("All validation checks passed")
    else:
        _err("Validation FAILED — fix the above before starting")
    return ok


# ── Step 12: Start ─────────────────────────────────────────────

def step_shortcuts() -> bool:
    """Create desktop shortcut (Clearbox AI.bat) pointing to start.bat."""
    _print_step(1, 1, "Desktop shortcut")
    start_bat = WORKSPACE_ROOT / "start.bat"
    if not start_bat.exists():
        _warn("start.bat not found — skipping shortcut")
        return True

    # Resolve desktop via shell API (handles OneDrive-relocated desktops)
    desktop: Optional[Path] = None
    try:
        import subprocess as _sp
        result = _sp.run(
            ["powershell", "-c", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True, timeout=10,
        )
        p = Path(result.stdout.strip())
        if p.exists():
            desktop = p
    except Exception:
        pass
    if not desktop:
        for candidate in (
            Path.home() / "Desktop",
            Path.home() / "OneDrive" / "Desktop",
            Path.home() / "OneDrive" / "Documents" / "Desktop",
        ):
            if candidate.exists():
                desktop = candidate
                break
    if not desktop:
        _warn("Could not locate Desktop folder — skipping shortcut")
        return True

    shortcut = desktop / "Clearbox AI.bat"
    shortcut.write_text(
        f'@echo off\ncall "{start_bat}"\n',
        encoding="utf-8",
    )
    _info(f"Desktop shortcut: {shortcut}")
    return True


def step_start(no_browser: bool = False) -> bool:
    _print_step(1, 1, "Launch Clearbox AI Studio")

    start_script = WORKSPACE_ROOT / "scripts" / "clearbox_tray.py"
    if not start_script.exists():
        _err("scripts/clearbox_tray.py not found")
        return False

    venv_py = _venv_python()
    cmd = [str(venv_py), str(start_script)]
    if no_browser:
        cmd.append("--no-browser")

    _info("Handing off to clearbox_tray.py...")
    print()

    # Run in foreground — clearbox_tray.py manages all services
    result = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT))
    return result.returncode == 0


# ── Install wrapper (sub-step checkpointing) ─────────────────

_INSTALL_SUBSTEPS: List[Tuple[str, Callable[[str], bool]]] = [
    ("install:venv",      lambda _gpu: step_venv()),
    ("install:deps",      lambda gpu:  step_deps(gpu)),
    ("install:data_dirs", lambda _gpu: step_data_dirs()),
    ("install:config",    lambda _gpu: step_config()),
    ("install:nltk",      lambda _gpu: step_nltk()),
    ("install:models",    lambda _gpu: step_models()),
    ("install:platform",  lambda gpu:  step_platform(gpu)),
    ("install:smoke",     lambda _gpu: step_smoke()),
    ("install:validate",  lambda _gpu: step_validate()),
    ("install:shortcuts", lambda _gpu: step_shortcuts()),
]


def run_install(state: InstallerPersist) -> bool:
    """Execute all install sub-steps, skipping completed ones on resume."""
    for step_id, step_fn in _INSTALL_SUBSTEPS:
        # Meld upgrade: skip data dirs and config (already exist)
        if step_id in ("install:data_dirs", "install:config") \
           and state.upgrade_mode == "meld":
            _info(f"Skipping {step_id} (meld upgrade — keeping existing data)")
            continue

        if step_id in state.passed_checks:
            # Guard: verify venv still exists if we think it's done
            if step_id == "install:venv" and not _venv_python().exists():
                _warn("Venv missing despite previous pass — re-running")
                state.passed_checks.remove(step_id)
            else:
                _info(f"Skipping {step_id} (already completed)")
                continue

        try:
            success = step_fn(state.gpu_type)
        except Exception as e:
            _err(f"Step {step_id} raised: {e}")
            state.error_log.append(f"{step_id}: {e}")
            state.save()
            return False

        if not success:
            state.error_log.append(f"{step_id}: returned False")
            state.save()
            return False

        state.passed_checks.append(step_id)
        state.save()  # checkpoint after every sub-step

    return True


# ── Lock file generation ──────────────────────────────────────

def write_lock() -> None:
    """Snapshot the current venv to requirements.lock.txt."""
    venv_py = _venv_python()
    r = subprocess.run(
        [str(venv_py), "-m", "pip", "freeze"],
        capture_output=True, text=True, cwd=str(WORKSPACE_ROOT),
    )
    if r.returncode != 0:
        _err(f"pip freeze failed: {r.stderr[:200]}")
        return

    lines = sorted(r.stdout.strip().splitlines())
    header = (
        "# Clearbox AI Studio — Pinned dependencies (known-good)\n"
        f"# Generated: {time.strftime('%Y-%m-%d %H:%M')}\n"
        f"# Python: {sys.version.split()[0]}\n"
        f"# Platform: {platform.platform()}\n"
    )
    lock_path = WORKSPACE_ROOT / LOCK_FILE
    lock_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    _ok(f"Wrote {LOCK_FILE} ({len(lines)} packages)")


# ── Manifest summary ──────────────────────────────────────────

def print_manifest() -> None:
    """Print repo file inventory."""
    print(f"\n{'=' * 55}")
    print("  CLEARBOX AI STUDIO — FILE MANIFEST")
    print(f"{'=' * 55}\n")

    categories = [
        ("security/",    "security",    (".py",)),
        ("bridges/",     "bridges",     (".py",)),
        ("scripts/",     "scripts",     (".py",)),
        ("routing/",     "routing",     (".py",)),
        ("core/observe/",     "core/observe",     (".py",)),
        ("tools/",       "tools",       (".py",)),
        ("Conversations/", "Conversations", (".py", ".jsonl")),
        ("core/lakespeak/",           "core/lakespeak",           (".py",)),
        ("core/reasoning_engine/",    "core/reasoning_engine",    (".py",)),
        ("core/chat_packs/",          "core/chat_packs",          (".py",)),
        ("core/clearbox_node/",         "core/clearbox_node",         (".py",)),
        ("core/help_system/",         "core/help_system",         (".py",)),
        ("ui/",          "ui",          (".html", ".js", ".css", ".py")),
    ]

    total = 0
    for label, rel, exts in categories:
        base = WORKSPACE_ROOT / rel
        if not base.exists():
            print(f"   {label:36s}  (missing)")
            continue
        n = 0
        for p in base.rglob("*"):
            if p.is_file() and "__pycache__" not in str(p):
                if any(p.name.endswith(e) for e in exts):
                    n += 1
        print(f"   {label:36s}  {n:4d} files")
        total += n

    # Models
    models_dir = WORKSPACE_ROOT / "models"
    if models_dir.exists():
        model_files = [f for f in models_dir.iterdir() if f.is_file()]
        print(f"   {'models/':36s}  {len(model_files):4d} files")
        total += len(model_files)

    print(f"\n   {'TOTAL':36s}  {total:4d} files")
    print()


# ── Config backup ─────────────────────────────────────────────

def backup_config() -> None:
    """Snapshot the data-root config dir before a risky operation."""
    dr = _data_root()
    cfg_dir = dr / "config"
    if not cfg_dir.exists():
        _warn("No config directory to back up")
        return

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = dr / f"config_backup_{stamp}"
    shutil.copytree(str(cfg_dir), str(backup_dir))
    _ok(f"Config backed up to: {backup_dir}")


# ── Upgrade awareness ─────────────────────────────────────────

def _upgrade_meld(state: InstallerPersist) -> bool:
    """Meld upgrade: keep user data, update code + venv only."""
    backup_config()
    state.upgrade_mode = "meld"
    state.save()
    _ok("Meld upgrade — existing data and config will be preserved")
    return True


def _upgrade_backup(data_root: Path) -> bool:
    """Backup & replace: zip user data, then allow fresh install."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    zip_path = _desktop() / f"ClearboxAI_backup_{stamp}.zip"
    _info(f"Zipping user data to: {zip_path}")
    try:
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(str(data_root)):
                for fn in files:
                    fp = os.path.join(root, fn)
                    arcname = os.path.relpath(fp, str(data_root.parent))
                    zf.write(fp, arcname)
        _ok(f"Backup saved: {zip_path}")
    except OSError as e:
        _err(f"Backup failed: {e}")
        return False

    # Clear data directory contents (keep the dir itself)
    for child in data_root.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(str(child))
            else:
                child.unlink()
        except OSError:
            pass
    _ok("Old data cleared — fresh install will follow")
    return True


def _upgrade_replace(data_root: Path) -> bool:
    """Replace: delete data after explicit confirmation."""
    print()
    _warn("This will DELETE all existing user data (conversations,")
    _warn("config, indexes, sessions). This cannot be undone.")
    print()
    confirm = input("  Type YES to confirm data loss: ").strip()
    if confirm != "YES":
        _info("Cancelled — no data was deleted.")
        return False

    for child in data_root.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(str(child))
            else:
                child.unlink()
        except OSError:
            pass
    _ok("Old data deleted — fresh install will follow")
    return True


def _handle_existing_install(state: InstallerPersist) -> bool:
    """Check for prior install and present upgrade options.

    Returns True to proceed with install, False to quit.
    """
    # Already chose an upgrade mode (resume after crash)
    if state.upgrade_mode:
        _info(f"Resuming with upgrade mode: {state.upgrade_mode}")
        return True

    installed_ver, data_root = _check_existing_install()
    if installed_ver is None:
        # No existing install — fresh install, nothing to do
        return True

    cur = INSTALLER_VERSION
    print()
    print("=" * 55)
    print("  EXISTING INSTALLATION DETECTED")
    print("=" * 55)
    print()
    print(f"  Data directory: {data_root}")

    # Determine scenario
    if installed_ver == "unknown":
        # Legacy install (no version stamp)
        print("  Version:        unknown (pre-stamp install)")
        print()
        print("  Upgrade options:")
        print("    [M] Meld    — keep all user data, update code + venv")
        print("    [B] Backup  — zip user data, then fresh install")
        print("    [R] Replace — delete everything, fresh install (DATA LOSS)")
        print("    [Q] Quit")
        valid = {"m", "b", "r", "q"}
    else:
        cmp = _compare_versions(installed_ver, cur)
        iv_display = ".".join(str(x) for x in _version_tuple(installed_ver))
        cv_display = ".".join(str(x) for x in _version_tuple(cur))

        if cmp == "same":
            print(f"  Version:        v{cv_display} (same as installer)")
            print()
            choice = input("  Already installed. Reinstall? [y/N]: ").strip().lower()
            if choice != "y":
                _info("Nothing to do — exiting.")
                return False
            # Reinstall = fresh, no special upgrade mode
            return True

        elif cmp == "older":
            # Installed is older → upgrade available
            print(f"  Installed:      v{iv_display}")
            print(f"  Available:      v{cv_display}")
            print()
            print("  Upgrade options:")
            print("    [M] Meld    — keep all user data, update code + venv")
            print("    [B] Backup  — zip user data, then fresh install")
            print("    [R] Replace — delete everything, fresh install (DATA LOSS)")
            print("    [Q] Quit")
            valid = {"m", "b", "r", "q"}

        else:
            # Installed is newer → downgrade warning
            print(f"  Installed:      v{iv_display}")
            print(f"  This installer: v{cv_display}")
            print()
            _warn("Installed version is NEWER than this installer.")
            _warn("Downgrading may cause data incompatibility.")
            print()
            print("  Options:")
            print("    [B] Backup & Replace — zip data, then fresh install")
            print("    [R] Replace          — delete everything (DATA LOSS)")
            print("    [Q] Quit")
            valid = {"b", "r", "q"}

    # Prompt loop
    print()
    while True:
        choice = input(f"  Choice [{'/'.join(sorted(valid)).upper()}]: ").strip().lower()
        if choice in valid:
            break
        print(f"  Invalid choice. Enter one of: {', '.join(sorted(valid)).upper()}")

    if choice == "q":
        _info("Exiting — no changes made.")
        return False

    if choice == "m":
        return _upgrade_meld(state)
    elif choice == "b":
        if not _upgrade_backup(data_root):
            return False
        state.upgrade_mode = "backup"
        state.save()
        return True
    elif choice == "r":
        if not _upgrade_replace(data_root):
            return False
        state.upgrade_mode = "replace"
        state.save()
        return True

    return False


def _write_version_stamp() -> None:
    """Write install_version.json to data root."""
    dr = _data_root()
    dr.mkdir(parents=True, exist_ok=True)
    vf = dr / "install_version.json"
    vf.write_text(json.dumps({
        "version": INSTALLER_VERSION,
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "workspace": str(WORKSPACE_ROOT),
    }, indent=2), encoding="utf-8")
    _ok(f"Version stamp written: v{INSTALLER_VERSION}")


# ── State machine driver ─────────────────────────────────────

def _print_install_summary(state: InstallerPersist) -> None:
    dr = _data_root()
    mode_label = f" ({state.upgrade_mode} upgrade)" if state.upgrade_mode else ""
    print("=" * 55)
    print(f"  INSTALL COMPLETE — v{INSTALLER_VERSION}{mode_label}")
    print("=" * 55)
    print()
    print("  Installed components:")
    print(f"    Version    → {INSTALLER_VERSION}")
    print(f"    Workspace  → {WORKSPACE_ROOT}")
    print(f"    User data  → {dr}")
    print(f"    Config     → {dr / 'config' / CONFIG_FILE}")
    print(f"    Venv       → {WORKSPACE_ROOT / VENV_DIR}")
    print(f"    GPU mode   → {'ENABLED' if state.gpu_enabled else 'DISABLED'}")
    print(f"    GPU torch  → {state.gpu_type.upper()}")
    print()
    print("  Services (managed by system tray):")
    print(f"    Bridge     → http://127.0.0.1:5050  (API server)")
    print(f"    Citations  → http://127.0.0.1:5052  (citation search + auto-cite)")
    print(f"    Node       → http://0.0.0.0:5060    (LAN mesh daemon)")
    print(f"    UI         → http://127.0.0.1:8080  (web interface)")
    print(f"    LLM        → http://127.0.0.1:11435 (local inference)")
    print()
    print("  Node daemon (for remote machines):")
    print(f"    Setup guide → docs/NODE_INSTALL_GUIDE.md")
    print(f"    Package     → core/clearbox_node/")
    print(f"    Deploy      → copy clearbox_node/ to remote, pip install -r requirements.txt")
    print(f"    Run         → python -m core.clearbox_node")
    print(f"    Auto-discovery via mDNS (_clearbox._tcp.local.)")
    print()
    print("  To start:")
    print("    Run: .\\start.bat  or  python scripts/clearbox_tray.py")
    print()
    print("  To remove:")
    print("    Run: python scripts/clearbox_uninstall.py")
    print()


def run_state_machine(args: argparse.Namespace) -> int:
    """Main state machine driver."""

    # ── Load or create state ────────────────────────────────────
    state: Optional[InstallerPersist] = None
    if args.resume:
        remove_resume_hook()  # always remove first to prevent loops
        state = InstallerPersist.load()
        if state:
            _ok(f"Resuming install from state: {state.state.value}")
            _info(f"Last checkpoint: {state.timestamp}")
        else:
            _warn("No saved state found — starting fresh")

    if state is None:
        state = InstallerPersist()

    # ── GPU mode resolution (auto-detect by default) ────────────
    # GPU is used for local LLM inference (llama-cpp-python + torch).
    # Pass --gpu cpu to force CPU-only if you have no GPU or don't want it.
    requested_gpu = args.gpu  # "auto" | "rocm" | "cuda" | "cpu"
    wants_gpu = requested_gpu != "cpu"
    if not args.resume:
        state.gpu_enabled = wants_gpu

    if state.gpu_enabled:
        if requested_gpu in {"rocm", "cuda"}:
            state.gpu_type = requested_gpu
        else:
            # "auto" — detect at install time
            _info("Detecting GPU backend...")
            state.gpu_type = _detect_gpu_type()

        if state.gpu_type == "rocm":
            _ok("GPU backend: ROCm (AMD) — GPU-accelerated local LLM enabled")
        elif state.gpu_type == "cuda":
            _ok("GPU backend: CUDA (NVIDIA) — GPU-accelerated local LLM enabled")
        else:
            _info("No GPU detected — using CPU-only packages for local LLM")
            state.gpu_type = "cpu"
            state.gpu_enabled = False
    else:
        state.gpu_type = "cpu"
        _ok("GPU mode: CPU-only (pass --gpu auto to enable GPU acceleration)")

    # ── State machine loop ──────────────────────────────────────
    while state.state != InstallState.DONE:

        # ── PREFLIGHT ───────────────────────────────────────────
        if state.state == InstallState.PREFLIGHT:
            _print_step(1, 4, "Preflight — checking prerequisites")

            # Repo structure checks (existing logic)
            if not step_detect():
                return 1
            if not step_preflight():
                return 1

            if args.skip_preflight:
                _info("Skipping external prerequisite checks (--skip-preflight)")
                if not _handle_existing_install(state):
                    return 0
                state.state = InstallState.INSTALLING
                state.save()
                continue

            # External prerequisites
            print()
            _info("Checking external prerequisites...")
            requirements = _build_requirements(include_gpu_checks=state.gpu_enabled)
            failures, warnings = run_preflight(requirements)

            if failures:
                print_missing_requirements(failures, warnings)
                print()
                _err("Install cannot continue — required prerequisites are missing.")
                _info("Install the tools listed above, then re-run:")
                _info("  python scripts/clearbox_install.py")
                return 1
            else:
                if warnings:
                    print_missing_requirements([], warnings)
                for req in requirements:
                    if req.passed and req.id not in state.passed_checks:
                        state.passed_checks.append(req.id)
                if not _handle_existing_install(state):
                    return 0
                state.state = InstallState.INSTALLING
                state.save()
                continue

        # ── WAITING_ON_USER (legacy / resume path only) ─────────
        if state.state == InstallState.WAITING_ON_USER:
            # This state is no longer entered on a fresh run.
            # It may appear in old install_state.json files after a resume.
            # Treat it as a return to PREFLIGHT.
            state.state = InstallState.PREFLIGHT
            state.save()
            continue

        # ── INSTALLING ──────────────────────────────────────────
        if state.state == InstallState.INSTALLING:
            _print_step(2, 4, "Installing")
            if not run_install(state):
                print()
                print("=" * 55)
                print("  INSTALL FAILED — fix the error above and re-run")
                print("=" * 55)
                return 1
            state.state = InstallState.STARTING_SERVICES
            state.save()

        # ── STARTING_SERVICES ──────────────────────────────────
        if state.state == InstallState.STARTING_SERVICES:
            _print_step(3, 4, "Starting services")

            # Deferred port check
            for name, port in CLEARBOX_PORTS.items():
                if _port_free(port):
                    _ok(f"Port {port} ({name}) — free")
                else:
                    _warn(f"Port {port} ({name}) — in use"
                          " (service may already be running)")

            print_manifest()
            _print_install_summary(state)

            if args.no_start:
                _info("Skipping service launch (--no-start)")
                _info("To start: python scripts/clearbox_tray.py")
            else:
                if not step_start(no_browser=args.no_browser):
                    _warn("Service start reported an issue (non-fatal)")

            state.state = InstallState.DONE
            state.save()

    # ── DONE ────────────────────────────────────────────────────
    _print_step(4, 4, "Done")
    _write_version_stamp()
    remove_resume_hook()
    InstallerPersist.clear()
    _ok("Installation complete.")
    print()
    _info("To deploy nodes on other machines:")
    _info("  Copy core/clearbox_node/ → remote machine")
    _info("  pip install -r requirements.txt")
    _info("  python -m core.clearbox_node")
    _info("  Nodes auto-discover via mDNS — no manual IP entry needed.")
    _info("  Full guide: docs/NODE_INSTALL_GUIDE.md")
    return 0


# ── Main ──────────────────────────────────────────────────────

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Clearbox AI Studio Installer")
    ap.add_argument("--no-start", action="store_true",
                    help="Install only, don't launch services")
    ap.add_argument("--no-browser", action="store_true",
                    help="Don't open browser after start")
    ap.add_argument("--write-lock", action="store_true",
                    help="Write requirements.lock.txt from current venv")
    ap.add_argument("--manifest-only", action="store_true",
                    help="Print file manifest and exit")
    ap.add_argument("--backup-config", action="store_true",
                    help="Snapshot current data-root config before install")
    ap.add_argument("--uninstall", action="store_true",
                    help="Remove venv and all user data (delegates to clearbox_uninstall.py)")
    ap.add_argument("--yes", "-y", action="store_true",
                    help="Skip confirmation when used with --uninstall")
    ap.add_argument("--gpu", default="auto",
                    choices=["auto", "rocm", "cuda", "cpu"],
                    help="GPU backend for local LLM (default: auto-detect). "
                         "Use --gpu cpu to force CPU-only.")
    ap.add_argument("--enable-gpu", action="store_true",
                    help="(deprecated, ignored — GPU is now auto-detected by default)")
    ap.add_argument("--resume", action="store_true",
                    help="Resume a previously interrupted install (reboot hook)")
    ap.add_argument("--skip-preflight", action="store_true",
                    help="Skip external prerequisite checks (advanced)")
    ap.add_argument("--data-root",
                    help="Data root folder path (overrides saved selection)")
    args = ap.parse_args()

    # Uninstall mode — delegate to clearbox_uninstall.py
    if args.uninstall:
        uninstall_script = WORKSPACE_ROOT / "scripts" / "clearbox_uninstall.py"
        cmd = [sys.executable, str(uninstall_script)]
        if args.yes:
            cmd.append("--yes")
        if args.data_root:
            cmd.extend(["--data-root", args.data_root])
        return subprocess.run(cmd).returncode

    print()
    print("=" * 55)
    print("  CLEARBOX AI STUDIO — INSTALLER")
    print(f"  v{INSTALLER_VERSION}")
    print("=" * 55)
    print()
    print("  This installer will set up:")
    print("    1. Python virtual environment + dependencies")
    print("    2. GPU auto-detection → correct torch + llama-cpp-python wheels")
    print("    3. Data directories + encrypted config")
    print("    4. NLTK tokenizer data")
    print("    5. Model file verification")
    print("    6. Smoke tests + validation")
    print("    7. Service launch (Bridge, Citations, Node, UI, LLM)")
    print()
    print("  GPU note: NVIDIA/AMD is detected automatically.")
    print("  Pass --gpu cpu to disable GPU acceleration.")
    print()

    # Manifest mode
    if args.manifest_only:
        print_manifest()
        return 0

    # Write-lock mode
    if args.write_lock:
        if not _venv_python().exists():
            _err("No venv found — install first, then --write-lock")
            return 1
        write_lock()
        return 0

    # Select data root before any state/config writes.
    if not _configure_data_root(args.data_root, interactive=not args.resume):
        return 1

    # Backup config
    if args.backup_config:
        backup_config()

    # ── State machine ───────────────────────────────────────────
    return run_state_machine(args)


if __name__ == "__main__":
    raise SystemExit(main())
