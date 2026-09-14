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
    schema = "truemachine.linux.memory@2"

    def __init__(self, proc_root: str | Path = "/proc") -> None:
        self.meminfo_path = Path(proc_root) / "meminfo"
        self.source_coordinates = (str(self.meminfo_path),)

    def collect(self) -> dict:
        info = _read_key_values(self.meminfo_path)
        keys = ("MemTotal", "MemAvailable", "Buffers", "Cached", "SwapTotal", "SwapFree")
        missing = [key for key in keys if key not in info]
        return {
            "values": {key: info.get(key) for key in keys},
            "collection_status": "PARTIAL" if missing else "COMPLETE",
            "unresolved": [{"field": key, "state": "MISSING"} for key in missing],
        }


class ProcessCollector:
    name = "linux.processes"
    schema = "truemachine.linux.processes@2"

    def __init__(self, proc_root: str | Path = "/proc", max_entries: int | None = None) -> None:
        self.proc_root = Path(proc_root)
        self.max_entries = max_entries
        self.source_coordinates = (str(self.proc_root / "<pid>" / "status"),)

    def collect(self) -> dict:
        processes = []
        unresolved = []
        entries = sorted(
            (entry for entry in self.proc_root.iterdir() if entry.name.isdigit()),
            key=lambda entry: int(entry.name),
        )
        truncated = self.max_entries is not None and len(entries) > self.max_entries
        for entry in entries[:self.max_entries]:
            try:
                status = _read_key_values(entry / "status")
                processes.append({
                    "pid": int(entry.name),
                    "ppid": int(status.get("PPid", "0")),
                    "name": status.get("Name", ""),
                    "state": status.get("State", ""),
                    "uid": int(status.get("Uid", "0").split()[0]),
                })
            except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError) as error:
                unresolved.append({"pid": int(entry.name), "state": type(error).__name__.upper()})
                continue
        processes.sort(key=lambda item: item["pid"])
        unresolved.sort(key=lambda item: item["pid"])
        return {
            "count": len(processes), "processes": processes,
            "collection_status": "PARTIAL" if unresolved or truncated else "COMPLETE",
            "unresolved": unresolved,
            "truncated": truncated,
        }


class NetworkCollector:
    name = "linux.network"
    schema = "truemachine.linux.network@2"

    def __init__(self, sys_net_root: str | Path = "/sys/class/net", max_entries: int | None = None) -> None:
        self.sys_net_root = Path(sys_net_root)
        self.max_entries = max_entries
        self.source_coordinates = (str(self.sys_net_root / "<interface>"),)

    def collect(self) -> dict:
        interfaces = []
        unresolved = []
        entries = sorted(self.sys_net_root.iterdir(), key=lambda path: path.name)
        truncated = self.max_entries is not None and len(entries) > self.max_entries
        for entry in entries[:self.max_entries]:
            try:
                interfaces.append({
                    "name": entry.name,
                    "operstate": (entry / "operstate").read_text().strip(),
                    "mtu": int((entry / "mtu").read_text().strip()),
                    "rx_bytes": int((entry / "statistics/rx_bytes").read_text().strip()),
                    "tx_bytes": int((entry / "statistics/tx_bytes").read_text().strip()),
                })
            except (FileNotFoundError, PermissionError, ValueError) as error:
                unresolved.append({"interface": entry.name, "state": type(error).__name__.upper()})
                continue
        return {
            "interfaces": interfaces,
            "collection_status": "PARTIAL" if unresolved or truncated else "COMPLETE",
            "unresolved": unresolved,
            "truncated": truncated,
        }


class LoadCollector:
    name = "linux.load"
    schema = "truemachine.linux.load@1"
    source_coordinates = ("getloadavg(3)",)

    def collect(self) -> dict:
        return {"load_average": list(os.getloadavg())}
