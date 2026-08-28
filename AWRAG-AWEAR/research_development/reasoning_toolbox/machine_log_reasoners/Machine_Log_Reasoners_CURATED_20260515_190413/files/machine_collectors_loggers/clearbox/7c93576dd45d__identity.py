"""Machine identity — deterministic hardware fingerprint.

Produces a stable machine_id that survives reboots, IP changes, and reinstalls.
Uses platform-native identifiers with fallbacks.

Priority:
  Windows: SMBIOS UUID via wmic (motherboard-level, unique per physical box)
  Linux:   /etc/machine-id (systemd) or /sys/class/dmi/id/product_uuid (root)
  macOS:   IOPlatformUUID via ioreg
  Fallback: SHA-256(MAC + hostname) — less stable but always works

Result: 12-char hex string (truncated SHA-256 of the raw identifier).
No external dependencies — stdlib only.
"""

from __future__ import annotations

import hashlib
import platform
import socket
import subprocess
import uuid


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def _windows_uuid() -> str:
    raw = _run(["wmic", "csproduct", "get", "uuid"])
    for line in raw.splitlines():
        line = line.strip()
        if line and line.upper() != "UUID" and len(line) >= 16:
            return line
    return ""


def _linux_machine_id() -> str:
    try:
        return open("/etc/machine-id").read().strip()
    except Exception:
        pass
    try:
        return open("/sys/class/dmi/id/product_uuid").read().strip()
    except Exception:
        pass
    return ""


def _macos_uuid() -> str:
    raw = _run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
    for line in raw.splitlines():
        if "IOPlatformUUID" in line:
            parts = line.split('"')
            for p in parts:
                if len(p) >= 32 and "-" in p:
                    return p
    return ""


def _fallback_id() -> str:
    mac = uuid.getnode()
    hostname = socket.gethostname()
    return f"{mac:012x}:{hostname}"


def get_raw_machine_id() -> str:
    """Get the raw platform-specific machine identifier."""
    system = platform.system()
    if system == "Windows":
        mid = _windows_uuid()
        if mid:
            return mid
    elif system == "Linux":
        mid = _linux_machine_id()
        if mid:
            return mid
    elif system == "Darwin":
        mid = _macos_uuid()
        if mid:
            return mid
    return _fallback_id()


def get_machine_id() -> str:
    """Stable 12-char hex machine identity.

    Deterministic: same hardware always produces the same ID.
    """
    raw = get_raw_machine_id()
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def get_hostname() -> str:
    return socket.gethostname()
