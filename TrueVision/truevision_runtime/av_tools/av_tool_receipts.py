from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    # Shared media-format primitive: retain its existing bytes and semantics.
    data = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def safe_slug(value: str) -> str:
    clean = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in str(value)).strip("_")
    return clean[:80] or "av_tool"


_ACTIVE_JOB: ContextVar[Any] = ContextVar('truevision_av_receipt_job', default=None)
READ_INVENTORIES = frozenset({'storage_list_artifacts', 'storage_list_templates'})
PROVENANCE_FIELDS = ('sha256', 'state_sha256', 'manifest_sha256', 'profile_sha256',
                     'receipt_hash', 'scene_sha256', 'wav_sha256', 'receipt_sha256')
IMPLEMENTATION_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _provenance(result):
    # Reuse identities supplied by the owning tool; do not hash raw arguments,
    # secrets, errors, inventories, or an entire media payload for housekeeping.
    return {key: result[key] for key in PROVENANCE_FIELDS if isinstance(result.get(key), str)
            and re.fullmatch(r'(?:sha256:)?[0-9a-fA-F]{64}', result[key])}


def _publish(path: Path, payload: dict) -> None:
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, sort_keys=True, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


class AVReceiptJob:
    """One finite host-selected AV job; native media proof remains separate.

    Pending state reserves the identity before execution. An interrupted identity
    cannot be replayed as a new job. Reconciliation is deliberately not inferred.
    The bounded step records stay in memory; no per-step receipt files are made.
    """
    def __init__(self, storage_root: Path, *, job_id: str | None = None, max_calls: int = 64):
        original = Path(storage_root).absolute()
        if any(p.is_symlink() for p in (original, *original.parents)):
            raise ValueError('UNSAFE_AV_JOB_ROOT')
        self.root = Path(storage_root).resolve()
        self.job_id = job_id or uuid.uuid4().hex
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', self.job_id) or type(max_calls) is not int or not 1 <= max_calls <= 64:
            raise ValueError('INVALID_AV_JOB_BOUND')
        self.maximum = max_calls
        self.reserved = 0
        self.records = []
        self.receipt = None

    def __enter__(self):
        if _ACTIVE_JOB.get() is not None:
            raise ValueError('NESTED_AV_JOB_REFUSED')
        root = self.root / 'receipts' / 'jobs'
        root.mkdir(parents=True, exist_ok=True)
        if any(p.is_symlink() for p in (root, *root.parents)):
            raise ValueError('UNSAFE_AV_JOB_ROOT')
        self.path = root / f'{self.job_id}.json'
        self.pending = root / f'{self.job_id}.pending'
        if self.path.exists():
            raise ValueError('AV_JOB_ID_ALREADY_COMPLETED')
        descriptor = os.open(self.pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump({'schema': 'truevision_av_job_pending@1', 'job_id': self.job_id,
                       'status': 'IN_PROGRESS_OR_INTERRUPTED_OUTCOME_UNRESOLVED'}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        self.started = utc_now()
        self.token = _ACTIVE_JOB.set(self)
        return self

    def reserve(self, storage_root):
        if Path(storage_root).resolve() != self.root:
            raise ValueError('AV_JOB_ROOT_MISMATCH')
        if self.reserved >= self.maximum:
            raise ValueError('AV_JOB_CALL_BUDGET_EXCEEDED')
        self.reserved += 1

    def record(self, tool, status, result):
        if len(self.records) >= self.reserved:
            raise ValueError('AV_JOB_CALL_NOT_RESERVED')
        self.records.append({'tool': tool, 'status': status, 'provenance': _provenance(result or {})})
        return {'kind': 'job_reference', 'job_id': self.job_id, 'status': status, 'publication': 'pending'}

    def __exit__(self, exc_type, exc, tb):
        _ACTIVE_JOB.reset(self.token)
        verified = exc_type is None and len(self.records) == self.reserved
        payload = {'receipt_kind': 'truevision_av_job_receipt_v1', 'job_id': self.job_id,
            'receipt_writer_sha256': IMPLEMENTATION_SHA256,
            'started_at_utc': self.started, 'completed_at_utc': utc_now(),
            'execution_status': 'completed' if verified and all(r['status'] == 'ok' for r in self.records) else 'partial',
            'verification_scope': 'TOOL_RETURN_STATUS_AND_NATIVE_PROVENANCE_REFERENCES',
            'reserved_calls': self.reserved, 'recorded_calls': len(self.records),
            'steps': self.records, 'raw_payloads_retained': False}
        try:
            _publish(self.path, payload)
            self.receipt = {'kind': 'job_receipt', 'job_id': self.job_id, 'path': str(self.path),
                            'sha256': stable_hash(payload), 'status': payload['execution_status'], 'publication': 'published'}
            self.pending.unlink()
        except Exception:
            # Preserve pending identity and completed outputs. Never retry tools
            # merely because their terminal bookkeeping could not be published.
            self.receipt = {'kind': 'job_reference', 'job_id': self.job_id,
                            'status': payload['execution_status'], 'publication': 'unverified'}
        return False


def reserve_job_call(storage_root: Path) -> None:
    job = _ACTIVE_JOB.get()
    if job is not None:
        job.reserve(storage_root)


def write_tool_receipt(*, storage_root: Path, tool: str, status: str,
                       call: dict[str, Any], result: dict[str, Any] | None = None,
                       error: str | None = None) -> dict[str, Any]:
    job = _ACTIVE_JOB.get()
    if job is not None:
        return job.record(tool, status, result)
    if status == 'ok' and tool in READ_INVENTORIES:
        return {'kind': 'ephemeral_read_result', 'status': 'ok', 'publication': 'not_required'}
    receipts = Path(storage_root) / 'receipts'
    receipts.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    payload = {'receipt_kind': 'truevision_av_tool_receipt_v2', 'written_at_utc': now,
        'receipt_writer_sha256': IMPLEMENTATION_SHA256,
        'tool': tool, 'status': status, 'provenance': _provenance(result or {}),
        'provenance_status': 'native_references_present' if _provenance(result or {}) else 'not_supplied_by_tool',
        'reason_code': 'OPERATION_REJECTED_OR_FAILED' if status != 'ok' else None,
        'raw_payloads_retained': False,
        'verification_scope': 'TOOL_RETURN_STATUS_NOT_INDEPENDENT_MEDIA_VALIDATION'}
    path = receipts / f'{now.replace(":", "").replace(".", "_")}_{safe_slug(tool)}_{uuid.uuid4().hex}.json'
    _publish(path, payload)
    return {'kind': 'operation_receipt', 'name': path.name, 'path': str(path),
            'sha256': stable_hash(payload), 'status': status, 'publication': 'published'}
