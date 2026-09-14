"""Read-only Linux machine-state collectors using procfs and sysfs."""

from __future__ import annotations

from pathlib import Path
import os
import platform
import socket


def _read_key_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key] = value.strip()
    return values


class IdentityCollector:
    name = "linux.identity"
    schema = "truemachine.linux.identity@1"
    source_coordinates = ("uname(2)", "gethostname(2)")

    def collect(self) -> dict:
        return {
            "hostname": socket.gethostname(),
            "machine": platform.machine(),
            "kernel_release": platform.release(),
            "kernel_version": platform.version(),
            "operating_system": platform.system(),
        }


class MemoryCollector:
    name = "linux.memory"
    schema = "truemachine.linux.memory@1"
    source_coordinates = ("/proc/meminfo",)

    def collect(self) -> dict:
        info = _read_key_values(Path("/proc/meminfo"))
        keys = ("MemTotal", "MemAvailable", "Buffers", "Cached", "SwapTotal", "SwapFree")
        return {key: info.get(key) for key in keys}


class ProcessCollector:
    name = "linux.processes"
    schema = "truemachine.linux.processes@1"
    source_coordinates = ("/proc/<pid>/status",)

    def collect(self) -> dict:
        processes = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                status = _read_key_values(entry / "status")
                processes.append({
                    "pid": int(entry.name),
                    "ppid": int(status.get("PPid", "0")),
                    "name": status.get("Name", ""),
                    "state": status.get("State", ""),
                    "uid": int(status.get("Uid", "0").split()[0]),
                })
            except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
                continue
        processes.sort(key=lambda item: item["pid"])
        return {"count": len(processes), "processes": processes}


class NetworkCollector:
    name = "linux.network"
    schema = "truemachine.linux.network@1"
    source_coordinates = ("/sys/class/net/<interface>", "getloadavg(3)")

    def collect(self) -> dict:
        interfaces = []
        for entry in sorted(Path("/sys/class/net").iterdir(), key=lambda path: path.name):
            try:
                interfaces.append({
                    "name": entry.name,
                    "operstate": (entry / "operstate").read_text().strip(),
                    "mtu": int((entry / "mtu").read_text().strip()),
                    "rx_bytes": int((entry / "statistics/rx_bytes").read_text().strip()),
                    "tx_bytes": int((entry / "statistics/tx_bytes").read_text().strip()),
                })
            except (FileNotFoundError, PermissionError, ValueError):
                continue
        load = os.getloadavg()
        return {"interfaces": interfaces, "load_average": list(load)}
