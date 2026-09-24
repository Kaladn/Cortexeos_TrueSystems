"""Development repository lock owned by TrueMachine and requested through SecureCore.

The lock hashes every regular file beneath the repository except Git's own
metadata, removes ordinary write bits, and records its baseline outside the
repository. It is not a same-user or privileged-process security boundary.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from datetime import datetime, timezone
from typing import Any

from .repository_integrity import canonical, digest_file


SCHEMA = "truesystems.repository_lock@1"
MANIFEST_SCHEMA = "truemachine.repository_lock_manifest@1"
STATE_NAME = "REPOSITORY_LOCK.json"


class RepositoryLockError(ValueError):
    pass


def _atomic_json(path: Path, value: dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name("." + path.name + ".partial")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _repo(repository: str | Path) -> Path:
    root = Path(repository).resolve(strict=True)
    if not root.is_dir():
        raise RepositoryLockError("GIT_REPOSITORY_REQUIRED")
    probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                           capture_output=True, check=False)
    if probe.returncode or Path(os.fsdecode(probe.stdout).strip()).resolve() != root:
        raise RepositoryLockError("GIT_REPOSITORY_REQUIRED")
    return root


def _state(root: Path) -> str:
    path = root / STATE_NAME
    if not path.is_file() or path.is_symlink():
        raise RepositoryLockError("REPOSITORY_LOCK_STATE_MISSING")
    value = json.loads(path.read_bytes())
    if (not isinstance(value, dict) or set(value) != {"schema", "locked"}
            or value["schema"] != SCHEMA or not isinstance(value["locked"], str)
            or value["locked"] not in {"yes", "no"}):
        raise RepositoryLockError("INVALID_REPOSITORY_LOCK_STATE")
    return value["locked"]


def _paths(root: Path) -> tuple[list[Path], list[Path]]:
    directories = [root]
    files: list[Path] = []
    for parent, names, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(parent)
        if base == root and ".git" in names:
            names.remove(".git")
        if base == root and ".git" in filenames:
            filenames.remove(".git")
        for name in sorted(names):
            path = base / name
            if path.is_symlink() or not path.is_dir():
                raise RepositoryLockError(f"NON_DIRECTORY_OR_SYMLINK:{path.relative_to(root)}")
            directories.append(path)
        for name in sorted(filenames):
            path = base / name
            if path.is_symlink() or not path.is_file():
                raise RepositoryLockError(f"NON_FILE_OR_SYMLINK:{path.relative_to(root)}")
            files.append(path)
    files.sort(key=lambda path: path.relative_to(root).as_posix())
    directories.sort(key=lambda path: (len(path.parts), path.as_posix()), reverse=True)
    return files, directories


def _baseline(root: Path) -> dict[str, Any]:
    files, directories = _paths(root)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          check=True, capture_output=True).stdout.decode().strip()
    return {
        "schema": MANIFEST_SCHEMA,
        "repository": str(root),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": head,
        "files": [
            {"path": path.relative_to(root).as_posix(), "sha256": digest_file(path),
             "mode": stat.S_IMODE(path.stat().st_mode)}
            for path in files
        ],
        "directories": [
            {"path": path.relative_to(root).as_posix(), "mode": stat.S_IMODE(path.stat().st_mode)}
            for path in directories
        ],
        "git_metadata_excluded": True,
        "security_scope": "DEVELOPMENT_WRITE_BITS_AND_HASHES_NOT_OWNER_IMMUTABILITY",
    }


def _store(root: Path, state_root: str | Path) -> Path:
    base = Path(state_root).expanduser().resolve()
    if base == root or root in base.parents:
        raise RepositoryLockError("LOCK_STATE_MUST_BE_OUTSIDE_REPOSITORY")
    identity = hashlib.sha256(os.fsencode(str(root))).hexdigest()[:20]
    return base / identity


def _manifest(store: Path) -> dict[str, Any]:
    pointer = json.loads((store / "current.json").read_bytes())
    if (not isinstance(pointer, dict) or set(pointer) != {"manifest", "sha256"}
            or not isinstance(pointer["sha256"], str)):
        raise RepositoryLockError("INVALID_LOCK_POINTER")
    name = pointer["manifest"]
    if (not isinstance(name, str) or not name.startswith("manifest-")
            or not name.endswith(".json") or Path(name).name != name):
        raise RepositoryLockError("INVALID_LOCK_MANIFEST_NAME")
    raw = (store / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != pointer["sha256"]:
        raise RepositoryLockError("LOCK_MANIFEST_HASH_MISMATCH")
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("schema") != MANIFEST_SCHEMA:
        raise RepositoryLockError("INVALID_LOCK_MANIFEST")
    for field in ("files", "directories"):
        if not isinstance(value.get(field), list):
            raise RepositoryLockError("INVALID_LOCK_MANIFEST_ENTRIES")
        seen: set[str] = set()
        for row in value[field]:
            if (not isinstance(row, dict) or not isinstance(row.get("path"), str)
                    or type(row.get("mode")) is not int or not 0 <= row["mode"] <= 0o777
                    or row["path"] in seen):
                raise RepositoryLockError("INVALID_LOCK_MANIFEST_ENTRY")
            seen.add(row["path"])
            if field == "files" and (not isinstance(row.get("sha256"), str)
                                     or len(row["sha256"]) != 64):
                raise RepositoryLockError("INVALID_LOCK_MANIFEST_HASH")
    return value


def _bound_path(root: Path, relative: str) -> Path:
    if relative == ".":
        return root
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise RepositoryLockError("LOCK_MANIFEST_PATH_ESCAPE")
    if ".git" in candidate.parts:
        raise RepositoryLockError("GIT_METADATA_NOT_LOCK_TARGET")
    path = root
    for part in candidate.parts:
        path = path / part
        if path.is_symlink():
            raise RepositoryLockError("LOCK_MANIFEST_SYMLINK")
    if path.resolve(strict=False) != root and root not in path.resolve(strict=False).parents:
        raise RepositoryLockError("LOCK_MANIFEST_PATH_ESCAPE")
    return path


def _differences(root: Path, baseline: dict[str, Any]) -> list[dict[str, str]]:
    expected = {row["path"]: row for row in baseline["files"]}
    files, directories = _paths(root)
    observed = {path.relative_to(root).as_posix(): path for path in files}
    differences: list[dict[str, str]] = []
    for relative in sorted(expected.keys() | observed.keys()):
        row, path = expected.get(relative), observed.get(relative)
        if row is None:
            differences.append({"path": relative, "state": "ADDED"})
        elif path is None:
            differences.append({"path": relative, "state": "MISSING"})
        elif digest_file(path) != row["sha256"]:
            differences.append({"path": relative, "state": "HASH_MISMATCH"})
        elif stat.S_IMODE(path.stat().st_mode) & 0o222:
            differences.append({"path": relative, "state": "WRITE_BITS_PRESENT"})
    expected_directories = {row["path"] for row in baseline["directories"]}
    observed_directories = {path.relative_to(root).as_posix() for path in directories}
    for relative in sorted(expected_directories - observed_directories):
        differences.append({"path": relative, "state": "MISSING_DIRECTORY"})
    for relative in sorted(observed_directories - expected_directories):
        differences.append({"path": relative, "state": "ADDED_DIRECTORY"})
    for path in directories:
        if stat.S_IMODE(path.stat().st_mode) & 0o222:
            differences.append({"path": path.relative_to(root).as_posix(), "state": "DIRECTORY_WRITE_BITS_PRESENT"})
    return differences


def status(repository: str | Path, state_root: str | Path) -> dict[str, Any]:
    root = _repo(repository)
    locked = _state(root)
    result: dict[str, Any] = {"schema": SCHEMA, "repository": str(root), "locked": locked}
    if locked == "yes":
        baseline = _manifest(_store(root, state_root))
        if baseline["repository"] != str(root):
            raise RepositoryLockError("LOCK_MANIFEST_REPOSITORY_MISMATCH")
        differences = _differences(root, baseline)
        result.update({"integrity": "VERIFIED" if not differences else "SAFE_MODE_REQUIRED",
                       "differences": differences, "file_count": len(baseline["files"])})
    return result


def transition(repository: str | Path, state_root: str | Path, locked: str, *, actor_id: str) -> dict[str, Any]:
    if locked not in {"yes", "no"}:
        raise RepositoryLockError("LOCK_VALUE_MUST_BE_YES_OR_NO")
    if not isinstance(actor_id, str) or not actor_id:
        raise RepositoryLockError("AUTHENTICATED_ACTOR_REQUIRED")
    root = _repo(repository)
    store = _store(root, state_root)
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (store / "transition.lock").open("a+b") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        before = _state(root)
        if before == locked:
            return {**status(root, state_root), "transition": "UNCHANGED"}
        if locked == "yes":
            original = _baseline(root)
            try:
                _atomic_json(root / STATE_NAME, {"schema": SCHEMA, "locked": "yes"}, 0o644)
                baseline = _baseline(root)
                originals = {row["path"]: row for row in original["files"]}
                for row in baseline["files"]:
                    row["mode"] = originals[row["path"]]["mode"]
                name = "manifest-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
                manifest_path = store / name
                _atomic_json(manifest_path, baseline)
                _atomic_json(store / "current.json", {"manifest": name, "sha256": digest_file(manifest_path)})
                for row in baseline["files"]:
                    path = _bound_path(root, row["path"])
                    os.chmod(path, row["mode"] & ~0o222, follow_symlinks=False)
                for row in baseline["directories"]:
                    path = _bound_path(root, row["path"])
                    os.chmod(path, row["mode"] & ~0o222, follow_symlinks=False)
                observed = status(root, state_root)
                if observed["integrity"] != "VERIFIED":
                    raise RepositoryLockError("LOCK_POSTCONDITION_FAILED")
            except BaseException:
                for row in reversed(original["directories"]):
                    _bound_path(root, row["path"]).chmod(row["mode"])
                for row in original["files"]:
                    _bound_path(root, row["path"]).chmod(row["mode"])
                _atomic_json(root / STATE_NAME, {"schema": SCHEMA, "locked": "no"}, 0o644)
                raise
            return _record(store, actor_id, {**observed, "transition": "LOCKED",
                                             "manifest_sha256": digest_file(manifest_path)})

        baseline = _manifest(store)
        if baseline["repository"] != str(root):
            raise RepositoryLockError("LOCK_MANIFEST_REPOSITORY_MISMATCH")
        differences = _differences(root, baseline)
        for row in reversed(baseline["directories"]):
            path = _bound_path(root, row["path"])
            if path.is_dir() and not path.is_symlink():
                path.chmod(row["mode"])
        for row in baseline["files"]:
            path = _bound_path(root, row["path"])
            if path.is_file() and not path.is_symlink():
                path.chmod(row["mode"])
        _atomic_json(root / STATE_NAME, {"schema": SCHEMA, "locked": "no"}, 0o644)
        return _record(store, actor_id, {**status(root, state_root), "transition": "UNLOCKED",
                                         "integrity_before_unlock": "VERIFIED" if not differences else "SAFE_MODE_REQUIRED",
                                         "differences_before_unlock": differences})


def _record(store: Path, actor_id: str, result: dict[str, Any]) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    receipt = {"schema": "truemachine.repository_lock_receipt@1", "at_utc": timestamp,
               "authenticated_admin_id": actor_id, "result": result}
    path = store / "receipts" / (timestamp + ".json")
    _atomic_json(path, receipt)
    return {**result, "receipt": str(path), "receipt_sha256": digest_file(path)}
