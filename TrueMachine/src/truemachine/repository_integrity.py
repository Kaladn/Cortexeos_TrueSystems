"""Deterministic repository/view snapshots and fail-closed integrity incidents.

TrueMachine observes bytes and relationships.  It does not attribute an actor
without a witnessed OS audit event and never overwrites a suspect source tree.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time
from typing import Any, Iterable


SNAPSHOT_SCHEMA = "truemachine.repository_integrity_snapshot@1"
REPORT_SCHEMA = "truemachine.repository_integrity_report@1"
INCIDENT_SCHEMA = "truemachine.repository_integrity_incident@1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True,
    ).stdout


def _repository_paths(repo: Path) -> list[Path]:
    raw = _git(repo, "ls-files", "-co", "--exclude-standard", "-z")
    return sorted(
        (repo / part.decode("utf-8", errors="surrogateescape") for part in raw.split(b"\0") if part),
        key=lambda path: path.relative_to(repo).as_posix(),
    )


def _external_paths(root: Path) -> list[Path]:
    rows = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"SYMLINK_NOT_ADMITTED:{path}")
        if path.is_file():
            rows.append(path)
    return sorted(rows, key=lambda path: path.relative_to(root).as_posix())


def _logical_entries(repo: Path, external_views: Iterable[Path]):
    for path in _repository_paths(repo):
        yield "repository/" + path.relative_to(repo).as_posix(), path, "REPOSITORY"
    names: set[str] = set()
    for root in sorted((path.resolve() for path in external_views), key=lambda path: str(path)):
        name = root.name
        if name in names:
            raise ValueError(f"DUPLICATE_EXTERNAL_VIEW_NAME:{name}")
        names.add(name)
        for path in _external_paths(root):
            yield f"external_views/{name}/{path.relative_to(root).as_posix()}", path, "EXTERNAL_VIEW"


def _copy_blob(source: Path, blob: Path) -> None:
    if blob.exists():
        if not blob.is_file() or digest_file(blob) != blob.name:
            raise ValueError(f"BLOB_COLLISION_OR_TAMPER:{blob}")
        return
    blob.parent.mkdir(parents=True, exist_ok=True)
    temporary = blob.with_name("." + blob.name + ".partial")
    if temporary.exists():
        temporary.unlink()
    shutil.copyfile(source, temporary)
    if digest_file(temporary) != blob.name:
        temporary.unlink()
        raise ValueError(f"BLOB_COPY_HASH_MISMATCH:{source}")
    os.chmod(temporary, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    os.replace(temporary, blob)


def create_snapshot(
    repository: str | Path,
    external_views: Iterable[str | Path],
    vault_root: str | Path,
    snapshot_name: str,
) -> dict[str, Any]:
    repo = Path(repository).resolve()
    vault = Path(vault_root).resolve()
    views = [Path(item).resolve() for item in external_views]
    git_kind = _git(repo, "rev-parse", "--is-inside-work-tree").decode().strip()
    if git_kind != "true":
        raise ValueError("REPOSITORY_REQUIRED")
    if _git(repo, "status", "--porcelain=v1", "-z"):
        raise ValueError("CLEAN_REPOSITORY_REQUIRED")
    if not snapshot_name or Path(snapshot_name).name != snapshot_name:
        raise ValueError("INVALID_SNAPSHOT_NAME")
    for root in views:
        if not root.is_dir() or root.is_symlink():
            raise ValueError(f"INVALID_EXTERNAL_VIEW:{root}")

    snapshot = vault / snapshot_name
    staging = vault / ("." + snapshot_name + ".partial")
    if snapshot.exists() or staging.exists():
        raise FileExistsError(snapshot)
    staging.mkdir(parents=True)
    blobs = staging / "blobs" / "sha256"
    entries = []
    roots = {"repository": str(repo), "external_views": {root.name: str(root) for root in views}}
    for logical_path, source, source_class in _logical_entries(repo, views):
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"REGULAR_FILE_REQUIRED:{source}")
        digest = digest_file(source)
        _copy_blob(source, blobs / digest[:2] / digest)
        metadata = source.stat()
        entries.append({
            "logical_path": logical_path,
            "source_class": source_class,
            "size": metadata.st_size,
            "sha256": digest,
            "mode": stat.S_IMODE(metadata.st_mode),
        })
    manifest_body = {
        "schema": SNAPSHOT_SCHEMA,
        "repository_commit": _git(repo, "rev-parse", "HEAD").decode().strip(),
        "roots": roots,
        "entries": entries,
        "entry_count": len(entries),
        "persistent_symbols": False,
        "normalization_performed": False,
        "actor_attribution_requires_os_audit_witness": True,
    }
    snapshot_id = digest_bytes(canonical(manifest_body))
    manifest = {**manifest_body, "snapshot_id": snapshot_id}
    manifest_path = staging / "manifest.json"
    manifest_path.write_bytes(canonical(manifest) + b"\n")
    manifest_digest = digest_file(manifest_path)
    (staging / "manifest.sha256").write_text(manifest_digest + "  manifest.json\n", encoding="ascii")
    for path in (manifest_path, staging / "manifest.sha256"):
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    os.replace(staging, snapshot)
    return {
        "schema": SNAPSHOT_SCHEMA + ":receipt",
        "snapshot": str(snapshot),
        "snapshot_id": snapshot_id,
        "manifest_sha256": manifest_digest,
        "entry_count": len(entries),
        "filesystem_lock": "READ_ONLY_MODE_TRIPWIRE_NOT_OWNER_IMMUTABILITY",
    }


def _load_snapshot(snapshot: Path) -> dict[str, Any]:
    expected_line = (snapshot / "manifest.sha256").read_text(encoding="ascii").strip()
    expected = expected_line.split()[0]
    manifest_path = snapshot / "manifest.json"
    if digest_file(manifest_path) != expected:
        raise ValueError("SNAPSHOT_MANIFEST_TAMPERED")
    manifest = json.loads(manifest_path.read_bytes())
    snapshot_id = manifest.pop("snapshot_id", None)
    if manifest.get("schema") != SNAPSHOT_SCHEMA or digest_bytes(canonical(manifest)) != snapshot_id:
        raise ValueError("SNAPSHOT_ID_MISMATCH")
    manifest["snapshot_id"] = snapshot_id
    return manifest


def _source_for(logical_path: str, roots: dict[str, Any]) -> Path:
    parts = Path(logical_path).parts
    if not parts:
        raise ValueError("INVALID_LOGICAL_PATH")
    if parts[0] == "repository":
        return Path(roots["repository"]).joinpath(*parts[1:])
    if len(parts) >= 3 and parts[0] == "external_views":
        root = roots["external_views"].get(parts[1])
        if root is None:
            raise ValueError("EXTERNAL_VIEW_ROOT_MISSING")
        return Path(root).joinpath(*parts[2:])
    raise ValueError("INVALID_LOGICAL_PATH")


def _text(value: bytes) -> str | None:
    if b"\0" in value:
        return None
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _line_column(text: str, offset: int) -> tuple[int, int]:
    return text.count("\n", 0, offset) + 1, offset - text.rfind("\n", 0, offset)


def _difference_locations(before: bytes, after: bytes, limit: int = 100) -> dict[str, Any]:
    old_text, new_text = _text(before), _text(after)
    if old_text is None or new_text is None:
        matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
        rows = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal" and len(rows) < limit:
                rows.append({"change": tag.upper(), "baseline_byte_start": i1, "baseline_byte_end": i2,
                             "observed_byte_start": j1, "observed_byte_end": j2})
        return {"coordinate_kind": "BYTE", "changes": rows, "truncated": len(rows) >= limit}
    matcher = difflib.SequenceMatcher(None, old_text, new_text, autojunk=False)
    rows = []
    total = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        total += 1
        if len(rows) >= limit:
            continue
        old_start = _line_column(old_text, i1)
        old_end = _line_column(old_text, i2)
        new_start = _line_column(new_text, j1)
        new_end = _line_column(new_text, j2)
        rows.append({
            "change": tag.upper(),
            "baseline": {"line": old_start[0], "column": old_start[1], "end_line": old_end[0], "end_column": old_end[1]},
            "observed": {"line": new_start[0], "column": new_start[1], "end_line": new_end[0], "end_column": new_end[1]},
            "baseline_exact": old_text[i1:i2],
            "observed_exact": new_text[j1:j2],
        })
    return {"coordinate_kind": "UTF8_LINE_COLUMN", "changes": rows, "truncated": total > limit}


def verify_snapshot(
    snapshot_root: str | Path,
    *,
    max_entries: int | None = None,
    max_file_bytes: int | None = None,
    max_total_bytes: int | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    snapshot = Path(snapshot_root).resolve()
    manifest = _load_snapshot(snapshot)
    expected = {row["logical_path"]: row for row in manifest["entries"]}
    if max_entries is not None and len(expected) > max_entries:
        raise ValueError("SNAPSHOT_ENTRY_BUDGET_EXCEEDED")
    if max_file_bytes is not None and any(row["size"] > max_file_bytes for row in expected.values()):
        raise ValueError("SNAPSHOT_FILE_BUDGET_EXCEEDED")
    if max_total_bytes is not None and sum(row["size"] for row in expected.values()) > max_total_bytes:
        raise ValueError("SNAPSHOT_TOTAL_BYTE_BUDGET_EXCEEDED")

    def check_deadline() -> None:
        if timeout_seconds is not None and time.monotonic() - started > timeout_seconds:
            raise TimeoutError("SNAPSHOT_VERIFICATION_TIMEOUT")

    observed_paths = {
        logical: path for logical, path, _ in _logical_entries(
            Path(manifest["roots"]["repository"]),
            [Path(value) for value in manifest["roots"]["external_views"].values()],
        )
        if path.is_file() and not path.is_symlink()
    }
    differences = []
    for logical_path in sorted(set(expected) | set(observed_paths)):
        check_deadline()
        row = expected.get(logical_path)
        source = observed_paths.get(logical_path)
        if row is None:
            differences.append({"logical_path": logical_path, "state": "ADDED", "observed_sha256": digest_file(source)})
            continue
        blob = snapshot / "blobs" / "sha256" / row["sha256"][:2] / row["sha256"]
        if not blob.is_file() or digest_file(blob) != row["sha256"]:
            raise ValueError(f"SNAPSHOT_BLOB_TAMPERED:{logical_path}")
        if source is None:
            differences.append({"logical_path": logical_path, "state": "MISSING", "baseline_sha256": row["sha256"]})
            continue
        metadata = source.stat()
        observed_digest = digest_file(source)
        observed_mode = stat.S_IMODE(metadata.st_mode)
        content_changed = observed_digest != row["sha256"]
        mode_changed = observed_mode != row["mode"]
        if content_changed or mode_changed:
            differences.append({
                "logical_path": logical_path,
                "state": "MODIFIED",
                "baseline_sha256": row["sha256"],
                "observed_sha256": observed_digest,
                "baseline_mode": row["mode"],
                "observed_mode": observed_mode,
                "content_changed": content_changed,
                "mode_changed": mode_changed,
                "pinpoint": _difference_locations(blob.read_bytes(), source.read_bytes()) if content_changed else {
                    "coordinate_kind": "FILE_MODE",
                    "changes": [{"baseline_mode": row["mode"], "observed_mode": observed_mode}],
                    "truncated": False,
                },
                "actor": {
                    "status": "UNRESOLVED_NO_OS_AUDIT_WITNESS",
                    "observed_owner_uid": metadata.st_uid,
                    "observed_owner_gid": metadata.st_gid,
                    "observed_mtime_ns": metadata.st_mtime_ns,
                    "ownership_is_not_actor_proof": True,
                },
            })
    report_body = {
        "schema": REPORT_SCHEMA,
        "snapshot_id": manifest["snapshot_id"],
        "status": "SAFE_MODE_REQUIRED" if differences else "VERIFIED",
        "differences": differences,
        "difference_count": len(differences),
        "source_mutated_by_verifier": False,
        "automatic_source_restore_performed": False,
    }
    report = {**report_body, "receipt_sha256": digest_bytes(canonical(report_body))}
    return report


def verify_and_enter_safe_mode(
    snapshot_root: str | Path,
    incident_parent: str | Path,
    **verification_limits: int | None,
) -> dict[str, Any]:
    """Verify once and materialize an incident only when the baseline differs."""
    report = verify_snapshot(snapshot_root, **verification_limits)
    if report["status"] == "VERIFIED":
        return report
    parent = Path(incident_parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    incident = parent / f"integrity-incident-{stamp}-{report['snapshot_id'][:12]}"
    return create_incident(snapshot_root, report, incident)


def create_incident(snapshot_root: str | Path, report: dict[str, Any], incident_root: str | Path) -> dict[str, Any]:
    snapshot = Path(snapshot_root).resolve()
    manifest = _load_snapshot(snapshot)
    if report.get("schema") != REPORT_SCHEMA or report.get("status") != "SAFE_MODE_REQUIRED":
        raise ValueError("INTEGRITY_FAILURE_REPORT_REQUIRED")
    body = dict(report)
    receipt = body.pop("receipt_sha256", None)
    if receipt != digest_bytes(canonical(body)) or body.get("snapshot_id") != manifest["snapshot_id"]:
        raise ValueError("INVALID_INTEGRITY_REPORT_RECEIPT")
    incident = Path(incident_root).resolve()
    incident.mkdir(parents=True, exist_ok=False)
    quarantine = incident / "quarantine"
    safe_tree = incident / "safe_tree"
    quarantine.mkdir()
    safe_tree.mkdir()
    entries = {row["logical_path"]: row for row in manifest["entries"]}
    quarantined = []
    for difference in report["differences"]:
        logical = difference["logical_path"]
        source = _source_for(logical, manifest["roots"])
        if difference["state"] in {"MODIFIED", "ADDED"} and source.is_file():
            destination = quarantine / logical
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            quarantined.append({"logical_path": logical, "sha256": digest_file(destination), "copy": str(destination)})
    for logical, row in entries.items():
        blob = snapshot / "blobs" / "sha256" / row["sha256"][:2] / row["sha256"]
        destination = safe_tree / logical
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(blob, destination)
        os.chmod(destination, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    incident_body = {
        "schema": INCIDENT_SCHEMA,
        "snapshot_id": manifest["snapshot_id"],
        "mode": "SAFE_SECURE",
        "quarantined_observed_copies": quarantined,
        "safe_tree": str(safe_tree),
        "suspect_source_overwritten": False,
        "safe_tree_entry_count": len(entries),
        "actor_attribution": "UNRESOLVED_UNLESS_SEPARATE_OS_AUDIT_WITNESS_EXISTS",
    }
    result = {**incident_body, "receipt_sha256": digest_bytes(canonical(incident_body))}
    (incident / "SAFE_MODE.json").write_bytes(canonical(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("snapshot")
    create.add_argument("--repo", required=True)
    create.add_argument("--external-view", action="append", default=[])
    create.add_argument("--vault", required=True)
    create.add_argument("--name", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--snapshot", required=True)
    respond = sub.add_parser("respond")
    respond.add_argument("--snapshot", required=True)
    respond.add_argument("--incident-parent", required=True)
    args = parser.parse_args()
    if args.command == "snapshot":
        result = create_snapshot(args.repo, args.external_view, args.vault, args.name)
    elif args.command == "verify":
        result = verify_snapshot(args.snapshot)
    else:
        result = verify_and_enter_safe_mode(args.snapshot, args.incident_parent)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
