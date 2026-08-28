"""Network detection for Clearbox AI remote access.

Detects Tailscale IPs/hostnames so enrollment bundles and TLS certs
can include addresses reachable from outside the LAN.
"""

import json
import logging
import os
import shutil
import subprocess
from typing import List, Optional

LOGGER = logging.getLogger("clearbox.network")

# Tailscale CLI: resolve once at import time.
# On Windows the installer puts tailscale.exe in Program Files but does NOT
# add it to PATH, so `shutil.which("tailscale")` returns None.
_TAILSCALE_CLI: Optional[str] = shutil.which("tailscale")
if not _TAILSCALE_CLI:
    _candidate = os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                              "Tailscale", "tailscale.exe")
    if os.path.isfile(_candidate):
        _TAILSCALE_CLI = _candidate


def get_tailscale_ipv4() -> Optional[str]:
    """Get the Tailscale IPv4 address (100.x.y.z) if Tailscale is running."""
    if not _TAILSCALE_CLI:
        return None
    try:
        result = subprocess.run(
            [_TAILSCALE_CLI, "ip", "-4"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            ip = result.stdout.strip().split("\n")[0].strip()
            if ip.startswith("100."):
                LOGGER.info("Tailscale IPv4: %s", ip)
                return ip
    except FileNotFoundError:
        LOGGER.debug("Tailscale CLI not found at %s", _TAILSCALE_CLI)
    except Exception as e:
        LOGGER.debug("Tailscale IP check failed: %s", e)
    return None


def get_tailscale_hostname() -> Optional[str]:
    """Get the Tailscale MagicDNS hostname (e.g. desktop.tailnet-name.ts.net)."""
    if not _TAILSCALE_CLI:
        return None
    try:
        result = subprocess.run(
            [_TAILSCALE_CLI, "status", "--json"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            self_node = data.get("Self", {})
            dns_name = self_node.get("DNSName", "").rstrip(".")
            if dns_name:
                LOGGER.info("Tailscale hostname: %s", dns_name)
                return dns_name
    except FileNotFoundError:
        pass
    except Exception as e:
        LOGGER.debug("Tailscale hostname check failed: %s", e)
    return None


def get_tailscale_info() -> dict:
    """Get all Tailscale info in one call. Returns {} if not available."""
    ipv4 = get_tailscale_ipv4()
    if not ipv4:
        return {}
    hostname = get_tailscale_hostname()
    return {
        "ipv4": ipv4,
        "hostname": hostname,
        "available": True,
    }


def get_remote_urls(bridge_port: int = 5050, ui_port: int = 8080) -> List[dict]:
    """Get all remotely-reachable URLs (Tailscale).

    Returns list of dicts: {"type": "tailscale", "bridge": "...", "ui": "..."}.
    """
    urls = []
    ts = get_tailscale_info()
    if ts.get("available"):
        entry = {"type": "tailscale"}
        # Prefer hostname if available (MagicDNS), fall back to IP
        addr = ts.get("hostname") or ts["ipv4"]
        entry["bridge"] = f"https://{addr}:{bridge_port}"
        entry["ui"] = f"https://{addr}:{ui_port}"
        entry["ip"] = ts["ipv4"]
        if ts.get("hostname"):
            entry["hostname"] = ts["hostname"]
        urls.append(entry)
    return urls
