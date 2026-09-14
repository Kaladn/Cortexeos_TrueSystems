"""Bounded read-only filesystem observation for TrueCore workers.

Callers bind an absolute root. Requests contain only paths relative to that root.
Symlinks are reported by directory listings but are never followed as targets or
during recursive traversal.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Iterator


SCHEMA = "truemachine.navigation@1"
OPERATIONS = frozenset({
    "fs.list", "fs.find", "fs.read_metadata", "fs.hash",
    "fs.disk_usage", "fs.duplicate_scan",
})


class NavigationError(ValueError):
    """A request violated the bounded navigation contract."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise NavigationError(f"INVALID_{name.upper()}")
    return value


def _relative(value: object) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise NavigationError("INVALID_RELATIVE_PATH")
    if value == ".":
        return Path(".")
    path = Path(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise NavigationError("INVALID_RELATIVE_PATH")
    return path


def _root(path: str | Path) -> Path:
    root = Path(path)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise NavigationError("INVALID_BOUND_ROOT")
    return root.resolve()


def _target(root: Path, relative: object, *, require_regular: bool = False) -> Path:
    rel = _relative(relative)
    current = root
    for part in rel.parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            raise
        if stat.S_ISLNK(info.st_mode):
            raise NavigationError("SYMLINK_TARGET_FORBIDDEN")
    resolved = current.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise NavigationError("TARGET_ESCAPES_BOUND_ROOT")
    if require_regular and not resolved.is_file():
        raise NavigationError("REGULAR_FILE_REQUIRED")
    return resolved


def _location(root: Path, path: Path, info: os.stat_result | None = None) -> dict[str, Any]:
    item = info or path.lstat()
    mode = item.st_mode
    kind = (
        "file" if stat.S_ISREG(mode) else
        "directory" if stat.S_ISDIR(mode) else
        "symlink" if stat.S_ISLNK(mode) else
        "other"
    )
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "kind": kind,
        "size_bytes": item.st_size,
        "mode": stat.S_IMODE(mode),
        "modified_time_ns": item.st_mtime_ns,
        "device": item.st_dev,
        "inode": item.st_ino,
    }


def _walk(root: Path, start: Path, max_depth: int, max_entries: int) -> tuple[list[Path], list[dict[str, Any]], bool]:
    found: list[Path] = []
    unresolved: list[dict[str, Any]] = []
    pending: list[tuple[Path, int]] = [(start, 0)]
    truncated = False
    while pending:
        directory, depth = pending.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except (PermissionError, FileNotFoundError, NotADirectoryError) as error:
            unresolved.append({
                "relative_path": directory.relative_to(root).as_posix(),
                "state": type(error).__name__.upper(),
            })
            continue
        for entry in entries:
            if len(found) >= max_entries:
                truncated = True
                return found, unresolved, truncated
            found.append(entry)
            try:
                info = entry.lstat()
            except (PermissionError, FileNotFoundError) as error:
                unresolved.append({
                    "relative_path": entry.relative_to(root).as_posix(),
                    "state": type(error).__name__.upper(),
                })
                continue
            if depth < max_depth and stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
                pending.append((entry, depth + 1))
    return found, unresolved, truncated


def _hash_file(path: Path, maximum: int) -> tuple[str, int]:
    info = path.stat()
    if info.st_size > maximum:
        raise NavigationError("FILE_BUDGET_EXCEEDED")
    digest = hashlib.sha256()
    consumed = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            consumed += len(chunk)
            if consumed > maximum:
                raise NavigationError("FILE_CHANGED_BEYOND_BUDGET")
            digest.update(chunk)
    return "sha256:" + digest.hexdigest(), consumed


def _packet(
    *, operation: str, root: Path, locations: list[dict[str, Any]],
    measurements: dict[str, Any], unresolved: list[dict[str, Any]] | None = None,
    truncated: bool = False,
) -> dict[str, Any]:
    root_info = root.stat()
    packet = {
        "schema": SCHEMA,
        "operation": operation,
        "root_identity": {"device": root_info.st_dev, "inode": root_info.st_ino},
        "locations": locations,
        "measurements": measurements,
        "unresolved": unresolved or [],
        "truncated": truncated,
        "answer": None,
    }
    packet["receipt_sha256"] = _digest(packet)
    return packet


def run(
    operation: str,
    root_path: str | Path,
    parameters: dict[str, Any],
    *,
    max_entries: int = 10_000,
    max_file_bytes: int = 256 * 1024 * 1024,
    max_total_bytes: int = 1024 * 1024 * 1024,
) -> dict[str, Any]:
    """Execute one fixed read-only observation under a caller-bound root."""
    if operation not in OPERATIONS:
        raise NavigationError("UNKNOWN_NAVIGATION_OPERATION")
    if not isinstance(parameters, dict):
        raise NavigationError("INVALID_PARAMETERS")
    entry_budget = _integer(max_entries, "host_entry_budget", 1, 1_000_000)
    file_budget = _integer(max_file_bytes, "host_file_budget", 1, 1 << 50)
    total_budget = _integer(max_total_bytes, "host_total_budget", 1, 1 << 60)
    root = _root(root_path)

    if operation == "fs.list":
        if set(parameters) != {"relative_path", "limit"}:
            raise NavigationError("INVALID_PARAMETERS")
        target = _target(root, parameters["relative_path"])
        if not target.is_dir():
            raise NavigationError("DIRECTORY_REQUIRED")
        limit = _integer(parameters["limit"], "limit", 1, min(entry_budget, 10_000))
        entries = sorted(target.iterdir(), key=lambda item: item.name)
        selected = entries[:limit]
        return _packet(
            operation=operation, root=root,
            locations=[_location(root, item) for item in selected],
            measurements={"returned": len(selected), "available": len(entries)},
            truncated=len(entries) > limit,
        )

    if operation == "fs.read_metadata":
        if set(parameters) != {"relative_path"}:
            raise NavigationError("INVALID_PARAMETERS")
        target = _target(root, parameters["relative_path"])
        return _packet(
            operation=operation, root=root, locations=[_location(root, target)],
            measurements={"returned": 1},
        )

    if operation == "fs.hash":
        if set(parameters) != {"relative_path"}:
            raise NavigationError("INVALID_PARAMETERS")
        target = _target(root, parameters["relative_path"], require_regular=True)
        sha256, consumed = _hash_file(target, file_budget)
        location = _location(root, target)
        location["sha256"] = sha256
        return _packet(
            operation=operation, root=root, locations=[location],
            measurements={"files_hashed": 1, "bytes_hashed": consumed},
        )

    if operation == "fs.find":
        if set(parameters) != {"relative_path", "name_contains", "max_depth", "limit"}:
            raise NavigationError("INVALID_PARAMETERS")
        target = _target(root, parameters["relative_path"])
        if not target.is_dir():
            raise NavigationError("DIRECTORY_REQUIRED")
        needle = parameters["name_contains"]
        if not isinstance(needle, str) or len(needle) > 512:
            raise NavigationError("INVALID_NAME_FILTER")
        depth = _integer(parameters["max_depth"], "max_depth", 0, 64)
        limit = _integer(parameters["limit"], "limit", 1, min(entry_budget, 10_000))
        walked, unresolved, walk_truncated = _walk(root, target, depth, entry_budget)
        matches = [item for item in walked if needle in item.name]
        selected = matches[:limit]
        return _packet(
            operation=operation, root=root,
            locations=[_location(root, item) for item in selected],
            measurements={"visited": len(walked), "matched": len(matches), "returned": len(selected)},
            unresolved=unresolved,
            truncated=walk_truncated or len(matches) > limit,
        )

    if set(parameters) != {"relative_path", "max_depth"} and not (
        operation == "fs.duplicate_scan" and
        set(parameters) == {"relative_path", "max_depth", "min_size_bytes"}
    ):
        raise NavigationError("INVALID_PARAMETERS")
    target = _target(root, parameters["relative_path"])
    if not target.is_dir():
        raise NavigationError("DIRECTORY_REQUIRED")
    depth = _integer(parameters["max_depth"], "max_depth", 0, 64)
    walked, unresolved, truncated = _walk(root, target, depth, entry_budget)
    files = []
    for item in walked:
        try:
            info = item.lstat()
        except (PermissionError, FileNotFoundError) as error:
            unresolved.append({"relative_path": item.relative_to(root).as_posix(), "state": type(error).__name__.upper()})
            continue
        if stat.S_ISREG(info.st_mode):
            files.append((item, info))

    if operation == "fs.disk_usage":
        total = sum(info.st_size for _, info in files)
        directories = sum(1 for item in walked if item.is_dir() and not item.is_symlink())
        return _packet(
            operation=operation, root=root, locations=[_location(root, target)],
            measurements={"files": len(files), "directories": directories, "bytes": total, "visited": len(walked)},
            unresolved=unresolved, truncated=truncated,
        )

    minimum = _integer(parameters["min_size_bytes"], "min_size_bytes", 0, 1 << 50)
    by_size: dict[int, list[Path]] = {}
    for item, info in files:
        if info.st_size >= minimum:
            by_size.setdefault(info.st_size, []).append(item)
    groups = []
    bytes_hashed = 0
    for size in sorted(by_size):
        candidates = by_size[size]
        if len(candidates) < 2:
            continue
        if size > file_budget:
            unresolved.append({"size_bytes": size, "state": "FILE_BUDGET_EXCEEDED", "count": len(candidates)})
            continue
        for item in candidates:
            if bytes_hashed + size > total_budget:
                truncated = True
                break
            sha256, consumed = _hash_file(item, file_budget)
            bytes_hashed += consumed
            groups.append((sha256, item, size))
        if truncated:
            break
    by_hash: dict[tuple[str, int], list[Path]] = {}
    for sha256, item, size in groups:
        by_hash.setdefault((sha256, size), []).append(item)
    duplicate_groups = []
    locations = []
    for (sha256, size), items in sorted(by_hash.items()):
        if len(items) < 2:
            continue
        paths = [item.relative_to(root).as_posix() for item in sorted(items)]
        duplicate_groups.append({"sha256": sha256, "size_bytes": size, "relative_paths": paths})
        locations.extend(_location(root, item) for item in sorted(items))
    return _packet(
        operation=operation, root=root, locations=locations,
        measurements={
            "files_considered": len(files), "bytes_hashed": bytes_hashed,
            "duplicate_groups": duplicate_groups,
        },
        unresolved=unresolved, truncated=truncated,
    )
