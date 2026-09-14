"""Bounded read-only Linux state observations over host-bound roots."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .collectors import NetworkCollector, ProcessCollector
from .navigation import NavigationError, _integer, _packet, _root, _target


OPERATIONS = frozenset({
    "process.list", "package.inventory", "device.inventory",
    "mount.inspect", "network.status", "log.query",
})


def _text(value: object, field: str, maximum: int = 512) -> str:
    if not isinstance(value, str) or len(value) > maximum or "\x00" in value:
        raise NavigationError(f"INVALID_{field.upper()}")
    return value


def _read_text(path: Path, maximum: int) -> tuple[str, int]:
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise NavigationError("FILE_BUDGET_EXCEEDED")
    return raw.decode("utf-8"), len(raw)


def _pacman_fields(text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("%") and line.endswith("%") and len(line) > 2:
            current = line[1:-1]
            fields.setdefault(current, [])
        elif current is not None and line:
            fields[current].append(line)
    return fields


def _mount_unescape(value: str) -> str:
    return re.sub(
        r"\\(040|011|012|134)",
        lambda match: {"040": " ", "011": "\t", "012": "\n", "134": "\\"}[match.group(1)],
        value,
    )


def run(
    operation: str,
    root_path: str | Path,
    parameters: dict[str, Any],
    *,
    max_entries: int = 10_000,
    max_file_bytes: int = 256 * 1024 * 1024,
    max_total_bytes: int = 1024 * 1024 * 1024,
) -> dict[str, Any]:
    if operation not in OPERATIONS:
        raise NavigationError("UNKNOWN_SYSTEM_OBSERVATION")
    if not isinstance(parameters, dict):
        raise NavigationError("INVALID_PARAMETERS")
    entry_budget = _integer(max_entries, "host_entry_budget", 1, 1_000_000)
    file_budget = _integer(max_file_bytes, "host_file_budget", 1, 1 << 50)
    total_budget = _integer(max_total_bytes, "host_total_budget", 1, 1 << 60)
    root = _root(root_path)

    if operation == "process.list":
        if set(parameters) != {"name_contains", "uid", "limit"}:
            raise NavigationError("INVALID_PARAMETERS")
        needle = _text(parameters["name_contains"], "name_filter", 256)
        uid = parameters["uid"]
        if uid is not None and (type(uid) is not int or uid < 0):
            raise NavigationError("INVALID_UID")
        limit = _integer(parameters["limit"], "limit", 1, min(entry_budget, 100_000))
        observed = ProcessCollector(root, max_entries=entry_budget).collect()
        matches = [
            item for item in observed["processes"]
            if needle in item["name"] and (uid is None or item["uid"] == uid)
        ]
        selected = matches[:limit]
        locations = [{"relative_path": f"{item['pid']}/status", "kind": "process_status", **item} for item in selected]
        return _packet(
            operation=operation, root=root, locations=locations,
            measurements={
                "observed": observed["count"], "matched": len(matches), "returned": len(selected),
                "collection_status": observed["collection_status"],
            },
            unresolved=observed["unresolved"],
            truncated=observed["truncated"] or len(matches) > limit,
        )

    if operation == "network.status":
        if set(parameters) != {"name_contains", "limit"}:
            raise NavigationError("INVALID_PARAMETERS")
        needle = _text(parameters["name_contains"], "name_filter", 256)
        limit = _integer(parameters["limit"], "limit", 1, min(entry_budget, 10_000))
        observed = NetworkCollector(root, max_entries=entry_budget).collect()
        matches = [item for item in observed["interfaces"] if needle in item["name"]]
        selected = matches[:limit]
        locations = [{"relative_path": item["name"], "kind": "network_interface", **item} for item in selected]
        return _packet(
            operation=operation, root=root, locations=locations,
            measurements={
                "observed": len(observed["interfaces"]), "matched": len(matches), "returned": len(selected),
                "collection_status": observed["collection_status"],
            },
            unresolved=observed["unresolved"],
            truncated=observed["truncated"] or len(matches) > limit,
        )

    if operation == "package.inventory":
        if set(parameters) != {"name_contains", "limit"}:
            raise NavigationError("INVALID_PARAMETERS")
        needle = _text(parameters["name_contains"], "name_filter", 256)
        limit = _integer(parameters["limit"], "limit", 1, min(entry_budget, 100_000))
        locations = []
        unresolved = []
        consumed = 0
        entries = sorted(root.iterdir(), key=lambda item: item.name)
        truncated = len(entries) > entry_budget
        for package_dir in entries[:entry_budget]:
            desc = package_dir / "desc"
            try:
                if package_dir.is_symlink() or not desc.is_file() or desc.is_symlink():
                    continue
                text, size = _read_text(desc, file_budget)
                if consumed + size > total_budget:
                    truncated = True
                    break
                consumed += size
                fields = _pacman_fields(text)
                name = (fields.get("NAME") or [package_dir.name])[0]
                if needle not in name:
                    continue
                locations.append({
                    "relative_path": desc.relative_to(root).as_posix(),
                    "kind": "pacman_package_record", "name": name,
                    "version": (fields.get("VERSION") or [None])[0],
                    "description": (fields.get("DESC") or [None])[0],
                    "installed_size": (fields.get("SIZE") or [None])[0],
                    "install_reason": (fields.get("REASON") or [None])[0],
                })
            except (OSError, UnicodeError, NavigationError) as error:
                unresolved.append({"relative_path": package_dir.relative_to(root).as_posix(), "state": type(error).__name__.upper()})
            if len(locations) >= limit:
                truncated = True
                break
        return _packet(
            operation=operation, root=root, locations=locations,
            measurements={"records_scanned": min(len(entries), entry_budget), "returned": len(locations), "bytes_read": consumed},
            unresolved=unresolved, truncated=truncated,
        )

    if operation == "mount.inspect":
        if set(parameters) != {"limit"}:
            raise NavigationError("INVALID_PARAMETERS")
        limit = _integer(parameters["limit"], "limit", 1, min(entry_budget, 100_000))
        mountinfo = _target(root, "self/mountinfo", require_regular=True)
        text, consumed = _read_text(mountinfo, file_budget)
        locations = []
        unresolved = []
        for line_number, line in enumerate(text.splitlines(), 1):
            before, separator, after = line.partition(" - ")
            left = before.split()
            right = after.split()
            if not separator or len(left) < 6 or len(right) < 3:
                unresolved.append({"line": line_number, "state": "INVALID_MOUNTINFO_RECORD"})
                continue
            locations.append({
                "relative_path": "self/mountinfo", "kind": "mount_record", "line": line_number,
                "mount_id": left[0], "parent_id": left[1], "major_minor": left[2],
                "root": _mount_unescape(left[3]), "mountpoint": _mount_unescape(left[4]),
                "mount_options": left[5].split(","), "filesystem": right[0],
                "source": _mount_unescape(right[1]), "super_options": right[2].split(","),
                "uuid": None,
            })
        selected = locations[:limit]
        if locations:
            unresolved.append({"field": "uuid", "state": "DEVICE_IDENTITY_RESOURCE_NOT_BOUND"})
        return _packet(
            operation=operation, root=root, locations=selected,
            measurements={"records": len(locations), "returned": len(selected), "bytes_read": consumed},
            unresolved=unresolved, truncated=len(locations) > limit,
        )

    if operation == "log.query":
        if set(parameters) != {"relative_path", "contains", "tail_lines"}:
            raise NavigationError("INVALID_PARAMETERS")
        contains = _text(parameters["contains"], "contains", 4096)
        tail_lines = _integer(parameters["tail_lines"], "tail_lines", 1, min(entry_budget, 100_000))
        source = _target(root, parameters["relative_path"], require_regular=True)
        text, consumed = _read_text(source, min(file_budget, total_budget))
        matches = [
            {"relative_path": source.relative_to(root).as_posix(), "kind": "log_line", "line": number, "text": line}
            for number, line in enumerate(text.splitlines(), 1) if contains in line
        ]
        selected = matches[-tail_lines:]
        return _packet(
            operation=operation, root=root, locations=selected,
            measurements={"matched": len(matches), "returned": len(selected), "bytes_read": consumed},
            truncated=len(matches) > tail_lines,
        )

    if set(parameters) != {"name_contains", "limit"}:
        raise NavigationError("INVALID_PARAMETERS")
    needle = _text(parameters["name_contains"], "name_filter", 256)
    limit = _integer(parameters["limit"], "limit", 1, min(entry_budget, 100_000))
    block_root = _target(root, "class/block")
    if not block_root.is_dir():
        raise NavigationError("SYSFS_BLOCK_ROOT_REQUIRED")
    locations = []
    unresolved = []
    entries = sorted(block_root.iterdir(), key=lambda item: item.name)
    truncated = len(entries) > entry_budget
    for entry in entries[:entry_budget]:
        if needle not in entry.name:
            continue
        resolved = entry.resolve(strict=True)
        if not resolved.is_relative_to(root):
            unresolved.append({"relative_path": entry.relative_to(root).as_posix(), "state": "SYSFS_TARGET_ESCAPES_ROOT"})
            continue
        fields = {}
        for key, relative in (
            ("major_minor", "dev"), ("size_sectors", "size"), ("removable", "removable"),
            ("read_only", "ro"), ("rotational", "queue/rotational"),
            ("model", "device/model"), ("vendor", "device/vendor"), ("serial", "device/serial"),
            ("partition", "partition"),
        ):
            path = resolved / relative
            try:
                fields[key] = path.read_text(encoding="utf-8").strip()
            except (FileNotFoundError, PermissionError, UnicodeError):
                fields[key] = None
        locations.append({
            "relative_path": entry.relative_to(root).as_posix(), "kind": "block_device",
            "name": entry.name, **fields,
        })
        if len(locations) >= limit:
            truncated = True
            break
    return _packet(
        operation=operation, root=root, locations=locations,
        measurements={"observed": min(len(entries), entry_budget), "returned": len(locations)},
        unresolved=unresolved, truncated=truncated,
    )
