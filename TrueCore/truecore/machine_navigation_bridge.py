"""Host-bound bridge to registered TrueMachine read-only navigation workers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable

from .agents import machine_navigation_workers as workers
from .live_agents.manifest import load_agent_manifest
from .live_agents.worker_result import validate_result


RESOURCE_KIND = "TRUEMACHINE_FILESYSTEM_ROOT"
SYSTEMCTL_KIND = "TRUEMACHINE_SYSTEMCTL_EXECUTABLE"
GIT_KIND = "TRUEMACHINE_GIT_REPOSITORY"
INTEGRITY_SNAPSHOT_KIND = "TRUEMACHINE_INTEGRITY_SNAPSHOT"
SOURCE_MODULE = "truecore.agents.machine_navigation_workers"
AGENT_DIR = Path(__file__).resolve().parent / "live_agents" / "AGENTS" / "agents"
RESOURCE_FIELDS = {
    "kind", "path", "allowed_workers", "max_entries", "max_file_bytes", "max_total_bytes",
    "timeout_seconds",
}
GIT_RESOURCE_FIELDS = RESOURCE_FIELDS | {"executable_path", "executable_sha256"}
SYSTEMCTL_RESOURCE_FIELDS = RESOURCE_FIELDS | {"executable_sha256"}
INTEGRITY_RESOURCE_FIELDS = RESOURCE_FIELDS | {"manifest_sha256"}

WORKERS: dict[str, Callable[[str, dict[str, Any], dict[str, int]], dict[str, Any]]] = {
    "fs.list": workers.filesystem_list,
    "fs.find": workers.filesystem_find,
    "fs.read_metadata": workers.filesystem_read_metadata,
    "fs.hash": workers.filesystem_hash,
    "fs.disk_usage": workers.filesystem_disk_usage,
    "fs.duplicate_scan": workers.filesystem_duplicate_scan,
    "process.list": workers.process_list,
    "package.inventory": workers.package_inventory,
    "device.inventory": workers.device_inventory,
    "mount.inspect": workers.mount_inspect,
    "network.status": workers.network_status,
    "log.query": workers.log_query,
    "service.status": workers.service_status,
    "repo.status": workers.repository_status,
    "integrity.verify": workers.repository_integrity_verify,
}


class MachineNavigationBridgeError(ValueError):
    """A model request cannot enter the bounded machine-navigation path."""


def _positive_integer(value: object, field: str, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise MachineNavigationBridgeError(f"INVALID_{field.upper()}")
    return value


def _validate_worker(worker_id: str) -> dict[str, Any]:
    if worker_id not in WORKERS:
        raise MachineNavigationBridgeError("MACHINE_WORKER_NOT_REGISTERED")
    manifest_path = AGENT_DIR / f"{worker_id}.agent.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise MachineNavigationBridgeError("MACHINE_WORKER_NOT_REGISTERED")
    manifest = load_agent_manifest(manifest_path)
    if manifest.get("source_entrypoint", "").split(":", 1)[0] != SOURCE_MODULE:
        raise MachineNavigationBridgeError("MACHINE_WORKER_SOURCE_MISMATCH")
    if (
        manifest["requires_approval"] or manifest["allowed_writes"] or
        manifest["worker_result_schema"] != "truecore.worker_result@1"
    ):
        raise MachineNavigationBridgeError("MACHINE_WORKER_NOT_READ_ONLY")
    return manifest


def _validate_resource(resource_id: str, binding: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(resource_id, str) or not resource_id:
        raise MachineNavigationBridgeError("INVALID_MACHINE_RESOURCE_ID")
    if not isinstance(binding, dict) or set(binding) not in (
        RESOURCE_FIELDS, GIT_RESOURCE_FIELDS, SYSTEMCTL_RESOURCE_FIELDS, INTEGRITY_RESOURCE_FIELDS,
    ):
        raise MachineNavigationBridgeError("INVALID_MACHINE_RESOURCE_BINDING")
    kind = binding["kind"]
    if kind not in {RESOURCE_KIND, SYSTEMCTL_KIND, GIT_KIND, INTEGRITY_SNAPSHOT_KIND}:
        raise MachineNavigationBridgeError("UNSUPPORTED_MACHINE_RESOURCE_KIND")
    path = Path(binding["path"])
    expected_file = kind == SYSTEMCTL_KIND
    if (
        not path.is_absolute() or path.is_symlink() or
        (expected_file and not path.is_file()) or (not expected_file and not path.is_dir())
    ):
        raise MachineNavigationBridgeError("INVALID_MACHINE_RESOURCE_PATH")
    resolved = path.resolve()
    info = resolved.stat()
    allowed = binding["allowed_workers"]
    if (
        not isinstance(allowed, list) or not allowed or
        not all(isinstance(item, str) and item in WORKERS for item in allowed) or
        len(allowed) != len(set(allowed))
    ):
        raise MachineNavigationBridgeError("INVALID_MACHINE_RESOURCE_WORKERS")
    result = {
        "kind": kind,
        "path": str(resolved),
        "device": info.st_dev,
        "inode": info.st_ino,
        "allowed_workers": tuple(sorted(allowed)),
        "max_entries": _positive_integer(binding["max_entries"], "max_entries", 1_000_000),
        "max_file_bytes": _positive_integer(binding["max_file_bytes"], "max_file_bytes", 1 << 50),
        "max_total_bytes": _positive_integer(binding["max_total_bytes"], "max_total_bytes", 1 << 60),
        "timeout_seconds": _positive_integer(binding["timeout_seconds"], "timeout_seconds", 60),
    }
    if kind == SYSTEMCTL_KIND:
        if set(binding) != SYSTEMCTL_RESOURCE_FIELDS or set(allowed) != {"service.status"}:
            raise MachineNavigationBridgeError("INVALID_SYSTEMCTL_RESOURCE_WORKERS")
        actual = "sha256:" + hashlib.sha256(resolved.read_bytes()).hexdigest()
        if binding["executable_sha256"] != actual:
            raise MachineNavigationBridgeError("SYSTEMCTL_EXECUTABLE_HASH_MISMATCH")
        result["executable_sha256"] = actual
    if kind == GIT_KIND:
        if set(binding) != GIT_RESOURCE_FIELDS or set(allowed) != {"repo.status"}:
            raise MachineNavigationBridgeError("INVALID_GIT_RESOURCE_WORKERS")
        executable = Path(binding["executable_path"])
        if not executable.is_absolute() or executable.is_symlink() or not executable.is_file():
            raise MachineNavigationBridgeError("INVALID_GIT_EXECUTABLE")
        actual = "sha256:" + hashlib.sha256(executable.read_bytes()).hexdigest()
        if binding["executable_sha256"] != actual:
            raise MachineNavigationBridgeError("GIT_EXECUTABLE_HASH_MISMATCH")
        executable_info = executable.stat()
        result.update({
            "executable_path": str(executable.resolve()), "executable_sha256": actual,
            "executable_device": executable_info.st_dev, "executable_inode": executable_info.st_ino,
        })
    if kind == INTEGRITY_SNAPSHOT_KIND:
        if set(binding) != INTEGRITY_RESOURCE_FIELDS or set(allowed) != {"integrity.verify"}:
            raise MachineNavigationBridgeError("INVALID_INTEGRITY_RESOURCE_WORKERS")
        manifest_path = resolved / "manifest.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise MachineNavigationBridgeError("INTEGRITY_MANIFEST_NOT_FOUND")
        actual = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if binding["manifest_sha256"] != actual:
            raise MachineNavigationBridgeError("INTEGRITY_MANIFEST_HASH_MISMATCH")
        result["manifest_sha256"] = actual
    if kind == RESOURCE_KIND and set(binding) != RESOURCE_FIELDS:
        raise MachineNavigationBridgeError("INVALID_MACHINE_RESOURCE_BINDING")
    return result


def _check_root_identity(resource: dict[str, Any]) -> None:
    path = Path(resource["path"])
    expected_file = resource["kind"] == SYSTEMCTL_KIND
    if path.is_symlink() or (expected_file and not path.is_file()) or (not expected_file and not path.is_dir()):
        raise MachineNavigationBridgeError("MACHINE_RESOURCE_CHANGED")
    info = path.stat()
    if info.st_dev != resource["device"] or info.st_ino != resource["inode"]:
        raise MachineNavigationBridgeError("MACHINE_RESOURCE_CHANGED")
    if resource["kind"] == SYSTEMCTL_KIND:
        actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != resource["executable_sha256"]:
            raise MachineNavigationBridgeError("SYSTEMCTL_EXECUTABLE_CHANGED")
    if resource["kind"] == GIT_KIND:
        executable = Path(resource["executable_path"])
        executable_info = executable.stat()
        actual = "sha256:" + hashlib.sha256(executable.read_bytes()).hexdigest()
        if (
            executable.is_symlink() or executable_info.st_dev != resource["executable_device"] or
            executable_info.st_ino != resource["executable_inode"] or actual != resource["executable_sha256"]
        ):
            raise MachineNavigationBridgeError("GIT_EXECUTABLE_CHANGED")
    if resource["kind"] == INTEGRITY_SNAPSHOT_KIND:
        manifest_path = path / "manifest.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise MachineNavigationBridgeError("INTEGRITY_SNAPSHOT_CHANGED")
        actual = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if actual != resource["manifest_sha256"]:
            raise MachineNavigationBridgeError("INTEGRITY_SNAPSHOT_CHANGED")


class MachineNavigationBridge:
    """Invoke only host-granted, registered, read-only machine workers."""

    def __init__(self, *, worker_grants=(), resources=None):
        if not isinstance(worker_grants, (list, tuple, set, frozenset)):
            raise ValueError("INVALID_MACHINE_WORKER_GRANTS")
        grants = frozenset(worker_grants)
        for worker_id in grants:
            _validate_worker(worker_id)
        if not isinstance(resources or {}, dict):
            raise ValueError("INVALID_MACHINE_RESOURCE_BINDINGS")
        checked = {
            resource_id: MappingProxyType(_validate_resource(resource_id, dict(binding)))
            for resource_id, binding in (resources or {}).items()
        }
        self.worker_grants = grants
        self.resources = MappingProxyType(checked)

    def public_contract(self) -> dict[str, Any]:
        return {
            "worker_grants": sorted(self.worker_grants),
            "resource_ids": sorted(self.resources),
            "model_supplied_paths": "RELATIVE_PATHS_WITHIN_HOST_BOUND_ROOT_ONLY",
            "model_supplied_absolute_paths": False,
            "model_supplied_commands": False,
            "model_supplied_modules": False,
            "effects": "READ_ONLY",
            "result_schema": "truecore.worker_result@1",
        }

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict) or set(arguments) != {"worker_id", "resource_id", "parameters"}:
            raise MachineNavigationBridgeError("INVALID_MACHINE_WORKER_ARGUMENTS")
        worker_id = arguments["worker_id"]
        resource_id = arguments["resource_id"]
        if worker_id not in self.worker_grants:
            raise MachineNavigationBridgeError("MACHINE_WORKER_PERMISSION_DENIED")
        _validate_worker(worker_id)
        resource = self.resources.get(resource_id)
        if resource is None:
            raise MachineNavigationBridgeError("MISSING_MACHINE_RESOURCE")
        if worker_id not in resource["allowed_workers"]:
            raise MachineNavigationBridgeError("MACHINE_RESOURCE_WORKER_DENIED")
        parameters = arguments["parameters"]
        if not isinstance(parameters, dict):
            raise MachineNavigationBridgeError("INVALID_MACHINE_WORKER_PARAMETERS")
        _check_root_identity(resource)
        limits = {
            "max_entries": resource["max_entries"],
            "max_file_bytes": resource["max_file_bytes"],
            "max_total_bytes": resource["max_total_bytes"],
            "timeout_seconds": resource["timeout_seconds"],
        }
        if "executable_path" in resource:
            limits["executable_path"] = resource["executable_path"]
        packet = WORKERS[worker_id](resource["path"], parameters, limits)
        _check_root_identity(resource)
        validate_result(packet)
        if packet["worker_id"] != worker_id:
            raise MachineNavigationBridgeError("MACHINE_WORKER_IDENTITY_MISMATCH")
        return packet
