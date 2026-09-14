"""Explicit, bounded deletion of host-admitted, closed operational detail.

No directory discovery establishes eligibility. Admission is a host assertion;
this module is not a classifier of arbitrary AV, evidence, or user files.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import time
from uuid import uuid4

from truecore.receipt_store import atomic_json, digest, private_path, read_json, record_lock
from truecore.time import utc_now, is_canonical_utc_timestamp

MAX_FILES = 256
MAX_BYTES = 32 * 1024 * 1024


def identity(path):
    target = private_path(path)
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_BYTES:
            raise ValueError("only bounded single-link regular files are eligible")
        h = hashlib.sha256()
        consumed = 0
        for chunk in iter(lambda: os.read(fd, 1024 * 1024), b""):
            consumed += len(chunk)
            if consumed > MAX_BYTES:
                raise ValueError("file grew beyond read budget")
            h.update(chunk)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("file changed while binding")
        return {"sha256": h.hexdigest(), "size": before.st_size, "mtime_ns": before.st_mtime_ns,
                "ctime_ns": before.st_ctime_ns, "device": before.st_dev, "inode": before.st_ino}
    finally:
        os.close(fd)


def admit_detail(path, *, job_id, recorded_at_utc, completed, referenced, active):
    """Bind a host-selected immutable detail object; never infer its ownership."""
    if completed is not True or referenced is not False or active is not False or not job_id:
        raise ValueError("only closed, unreferenced, inactive job detail may be admitted")
    if not is_canonical_utc_timestamp(recorded_at_utc):
        raise ValueError("recorded time must be canonical UTC")
    return {"path": str(private_path(path)), "identity": identity(path), "job_id": job_id,
            "recorded_at_utc": recorded_at_utc, "class": "operational_detail",
            "completed": True, "referenced": False, "active": False}


def _under(path, roots):
    return any(path == root or root in path.parents for root in roots)


def execute_details(*, entries, managed_roots, protected_roots, receipt_root,
                    context, transaction_id=None, seconds=2.0):
    """One private recovery record then one terminal result; no recursive sweep.

    An interrupted inflight unlink is reported as outcome-unverified on replay,
    not counted as a successful deletion. The operator must inspect it.
    """
    if not isinstance(entries, list) or len(entries) > MAX_FILES or not 0 < seconds <= 30:
        raise ValueError("retention batch exceeds limits")
    txid = transaction_id or uuid4().hex
    if not txid or len(txid) > 128 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in txid):
        raise ValueError("invalid transaction identity")
    roots = [private_path(p) for p in managed_roots]
    protected = [private_path(p) for p in protected_roots] + [private_path(receipt_root)]
    root = private_path(receipt_root) / "transactions" / txid
    terminal, pending = root / "receipt.json", root / "pending.json"
    plan = {"entries": entries, "roots": [str(p) for p in roots],
            "protected": [str(p) for p in protected], "context": context}
    binding = digest(plan)
    seen, total = set(), 0
    # Verify the whole set before creating transaction state or deleting anything.
    for entry in entries:
        p = private_path(entry["path"])
        if p in seen or not _under(p, roots) or _under(p, protected):
            raise ValueError("duplicate or out-of-scope retention target")
        seen.add(p)
        if (entry.get("class") != "operational_detail" or entry.get("completed") is not True
                or entry.get("referenced") is not False or entry.get("active") is not False):
            raise ValueError("source, active, referenced or incomplete objects are not eligible")
        total += entry["identity"]["size"]
    if total > MAX_BYTES:
        raise ValueError("retention byte budget exceeded")
    with record_lock(root / "writer.lock"):
        if terminal.exists():
            saved = read_json(terminal)
            if saved["plan_sha256"] != binding:
                raise ValueError("transaction identity already bound")
            return {**saved, "receipt_path": str(terminal)}
        if pending.exists():
            saved = read_json(pending)
            if saved["plan_sha256"] != binding:
                raise ValueError("transaction identity already bound")
            return {**saved, "status": "interrupted_outcome_unverified", "recovery_path": str(pending)}
        state = {"schema": "truecore.retention_transaction@1", "transaction_id": txid,
                 "plan_sha256": binding, "created_at_utc": utc_now(), "context": context,
                 "status": "pending", "deleted_files": [], "skipped": [], "inflight": None,
                 "deleted_file_count": 0, "backed_up": False, "unprocessed_count": len(entries)}
        atomic_json(pending, state)
        started = time.monotonic()
        try:
            for i, entry in enumerate(entries):
                if time.monotonic() - started >= seconds:
                    break
                p = private_path(entry["path"])
                if any(Path(str(p) + marker).exists() for marker in (".preserve.json", ".active")):
                    state["skipped"].append({"path": str(p), "reason": "protected_marker"})
                elif identity(p) != entry["identity"]:
                    state["skipped"].append({"path": str(p), "reason": "identity_changed"})
                else:
                    quarantine = ".retention-" + txid + "-" + str(i)
                    state["inflight"] = {**entry, "quarantine_name": quarantine}
                    atomic_json(pending, state)
                    # Recheck after the durable intent and immediately before unlink.
                    if identity(p) != entry["identity"] or any(Path(str(p) + marker).exists() for marker in (".preserve.json", ".active")):
                        raise ValueError("identity changed before deletion")
                    fd = _open_directory(p.parent)
                    try:
                        if os.path.lexists(p.parent / quarantine):
                            raise ValueError("quarantine identity already exists")
                        os.rename(p.name, quarantine, src_dir_fd=fd, dst_dir_fd=fd)
                        # The directory handle pins the admitted parent. Rename
                        # captures a concurrent replacement before any unlink.
                        check = os.stat(quarantine, dir_fd=fd, follow_symlinks=False)
                        expected = entry["identity"]
                        unchanged = (not any(Path(str(p) + marker).exists() for marker in (".preserve.json", ".active"))
                                     and stat.S_ISREG(check.st_mode) and check.st_nlink == 1
                                     and check.st_ino == expected["inode"] and check.st_dev == expected["device"]
                                     and check.st_size == expected["size"] and check.st_mtime_ns == expected["mtime_ns"])
                        if not unchanged:
                            # Never overwrite a concurrently recreated original.
                            try:
                                os.link(quarantine, p.name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
                                os.unlink(quarantine, dir_fd=fd)
                            except FileExistsError:
                                pass
                            raise ValueError("captured target changed; preserved for inspection")
                        os.unlink(quarantine, dir_fd=fd)
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                    state["deleted_files"].append({"path": str(p), "size": entry["identity"]["size"],
                                                   "sha256_before_delete": entry["identity"]["sha256"]})
                    state["deleted_file_count"] += 1
                state["inflight"] = None
                state["unprocessed_count"] = len(entries) - i - 1
                atomic_json(pending, state)
        except Exception as exc:
            state["error_type"] = type(exc).__name__
        state["status"] = "complete" if not state["unprocessed_count"] and not state["skipped"] else "partial"
        state["elapsed_seconds"] = time.monotonic() - started
        atomic_json(terminal, state)
        pending.unlink()
        return {**state, "receipt_path": str(terminal)}


def _open_directory(path):
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(path).absolute().parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise
