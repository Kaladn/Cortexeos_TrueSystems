from __future__ import annotations

import json
import struct
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from .anchors import anchorize, assert_no_symbol_collisions, symbol_bytes, symbol_for
from .base import COUNT_BACKEND, SYMBOL_BYTES, SYMBOL_SYSTEM, safe_id, utc_now, unique_stamp, write_json
from .hardware import MIN_RUNTIME_WORKERS, detect_system_resources, enforce_minimum_runtime_requirements
from .pipeline import split_blocks
from .storage import ANCHOR_RECORD, RELATION_RECORD

COUNT_MAGIC = b"AWLTCOUNT1\n"


def laptop_temp_intake(
    source: str | Path,
    *,
    state_root: str | Path = "State/laptop_temp_intake",
    run_id: str | None = None,
    chunk_mb: int = 50,
    max_chunks: int | None = None,
    window: int = 6,
    workers: int | str = 4,
    reserve_ram_fraction: float = 0.15,
    reserve_ram_gb: float | None = None,
    ram_budget_gb: float | None = 8.0,
    refuse_below_reserve: bool = False,
    max_file_mb: float | None = None,
    oversized_file_policy: str = "chunk",
    progress_snapshot_interval_sec: float = 5.0,
    show_progress: bool = True,
    resume: bool = True,
) -> dict[str, Any]:
    """Prepare bounded, disposable chunk artifacts without touching production counts."""
    if chunk_mb <= 0:
        raise ValueError("chunk_mb must be positive")
    if max_chunks is not None and max_chunks < 0:
        raise ValueError("max_chunks cannot be negative")
    if window <= 0:
        raise ValueError("window must be positive")
    if progress_snapshot_interval_sec < 0:
        raise ValueError("progress_snapshot_interval_sec cannot be negative")
    if max_file_mb is not None and max_file_mb <= 0:
        raise ValueError("max_file_mb must be positive")
    if oversized_file_policy not in {"chunk", "skip", "fail"}:
        raise ValueError("oversized_file_policy must be chunk, skip, or fail")

    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    run_name = safe_id(run_id or unique_stamp())
    root = Path(state_root).expanduser().resolve() / run_name
    chunks_root = root / "chunks"
    chunks_root.mkdir(parents=True, exist_ok=True)

    files = list(_iter_source_files(source_path))
    if not files:
        raise FileNotFoundError(f"no source files found under {source_path}")
    files, file_failures = _apply_file_policy(
        files,
        max_file_mb=max_file_mb,
        oversized_file_policy=oversized_file_policy,
    )

    chunk_limit = chunk_mb * 1024 * 1024
    progress_path = root / "progress.json"
    run_events_path = root / "run_events.jsonl"
    run_events_path.parent.mkdir(parents=True, exist_ok=True)
    run_events_path.write_text("", encoding="utf-8")
    resource_plan = _build_resource_plan(
        chunk_limit=chunk_limit,
        requested_workers=workers,
        reserve_ram_fraction=reserve_ram_fraction,
        reserve_ram_gb=reserve_ram_gb,
        ram_budget_gb=ram_budget_gb,
        refuse_below_reserve=refuse_below_reserve,
    )
    manifest = {
        "schema": "awrag_laptop_temp_intake_manifest@1",
        "created_at": utc_now(),
        "run_id": run_name,
        "source": str(source_path),
        "state_root": str(root),
        "mode": "laptop_temp_chunk_prep",
        "production_merge": False,
        "global_lifetime_write": False,
        "count_backend": COUNT_BACKEND,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "chunk_mb": int(chunk_mb),
        "max_chunks": max_chunks,
        "window": int(window),
        "resume": bool(resume),
        "files_found": len(files),
        "resource_plan": resource_plan,
        "progress_snapshot_interval_sec": float(progress_snapshot_interval_sec),
        "max_file_mb": float(max_file_mb) if max_file_mb is not None else None,
        "oversized_file_policy": oversized_file_policy,
        "file_failures": len(file_failures),
    }
    write_json(root / "manifest.json", manifest)
    write_json(root / "resource_receipt.json", {
        "schema": "awrag_laptop_temp_intake_resource_receipt@1",
        "created_at": utc_now(),
        "run_id": run_name,
        "resource_plan": resource_plan,
        "production_merge": False,
        "global_lifetime_write": False,
    })
    source_receipt = {
        "schema": "awrag_laptop_temp_intake_source_receipt@1",
        "created_at": utc_now(),
        "run_id": run_name,
        "source": str(source_path),
        "files": [{"path": str(path), "bytes": path.stat().st_size} for path in files],
        "file_failures": file_failures,
    }
    write_json(root / "source_receipt.json", source_receipt)
    _write_jsonl(root / "file_failures.jsonl", file_failures)

    total_chunks = _estimate_chunks(files, chunk_limit, max_chunks)
    bar = tqdm(total=total_chunks, unit="chunk", desc="laptop-temp-intake", disable=not show_progress)

    chunk_receipts: list[dict[str, Any]] = []
    chunk_failures: list[dict[str, Any]] = []
    aggregate = Counter()
    processed_chunks = 0
    skipped_chunks = 0
    failed_chunks = 0
    chunk_index = 0
    effective_workers = int(resource_plan["effective_workers"])
    last_progress_write = 0.0

    def write_event(event: str, **fields: Any) -> None:
        row = {
            "schema": "awrag_laptop_temp_intake_event@1",
            "created_at": utc_now(),
            "run_id": run_name,
            "event": event,
            "production_merge": False,
            "global_lifetime_write": False,
        }
        row.update(fields)
        with run_events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    def write_progress_snapshot(phase: str, *, force: bool = False) -> None:
        nonlocal last_progress_write
        now = time.monotonic()
        if not force and progress_snapshot_interval_sec > 0 and now - last_progress_write < progress_snapshot_interval_sec:
            return
        last_progress_write = now
        write_json(progress_path, {
            "schema": "awrag_laptop_temp_intake_progress@1",
            "created_at": utc_now(),
            "run_id": run_name,
            "phase": phase,
            "chunks_total": int(total_chunks),
            "chunks_seen": int(len(chunk_receipts) + len(chunk_failures)),
            "chunks_created": int(processed_chunks),
            "chunks_skipped": int(skipped_chunks),
            "chunks_failed": int(failed_chunks),
            "file_failures": int(len(file_failures)),
            "raw_bytes": int(aggregate["raw_bytes"]),
            "anchor_observations": int(aggregate["anchors"]),
            "unique_anchor_sum_by_chunk": int(aggregate["unique_anchors"]),
            "relation_observations": int(aggregate["relations"]),
            "symbol_bytes_written": int(aggregate["symbol_bytes_written"]),
            "effective_workers": int(effective_workers),
            "production_merge": False,
            "global_lifetime_write": False,
            "artifacts": {
                "progress": str(progress_path),
                "manifest": str(root / "manifest.json"),
                "resource_receipt": str(root / "resource_receipt.json"),
                "chunk_receipts": str(root / "chunk_receipts.jsonl"),
                "chunk_failures": str(root / "chunk_failures.jsonl"),
                "file_failures": str(root / "file_failures.jsonl"),
                "run_events": str(run_events_path),
            },
        })

    def record_receipt(receipt: dict[str, Any], *, skipped: bool) -> None:
        nonlocal processed_chunks, skipped_chunks
        chunk_receipts.append(receipt)
        aggregate["raw_bytes"] += int(receipt["raw_bytes"])
        aggregate["anchors"] += int(receipt["anchor_observations"])
        aggregate["unique_anchors"] += int(receipt["unique_anchors"])
        aggregate["relations"] += int(receipt["relation_observations"])
        aggregate["symbol_bytes_written"] += int(receipt["symbol_bytes_written"])
        if skipped:
            skipped_chunks += 1
            write_event("chunk_skipped_completed", chunk_index=int(receipt["chunk_index"]), source_file=receipt["source_file"])
        else:
            processed_chunks += 1
            write_event(
                "chunk_processed",
                chunk_index=int(receipt["chunk_index"]),
                source_file=receipt["source_file"],
                raw_bytes=int(receipt["raw_bytes"]),
                anchor_observations=int(receipt["anchor_observations"]),
                relation_observations=int(receipt["relation_observations"]),
            )
        bar.update(1)
        bar.set_postfix({
            "anchors": aggregate["anchors"],
            "skipped": skipped_chunks,
            "failed": failed_chunks,
            "workers": effective_workers,
        })
        write_progress_snapshot("running")

    def record_failure(*, chunk_number: int, source_file: Path, error: BaseException) -> None:
        nonlocal failed_chunks
        failed_chunks += 1
        failure = _chunk_failure_receipt(
            chunk_index=chunk_number,
            source_file=source_file,
            chunks_root=chunks_root,
            error=error,
        )
        chunk_failures.append(failure)
        write_event(
            "chunk_failed",
            chunk_index=int(chunk_number),
            source_file=str(source_file),
            error_type=type(error).__name__,
            error=str(error),
        )
        bar.update(1)
        bar.set_postfix({
            "anchors": aggregate["anchors"],
            "skipped": skipped_chunks,
            "failed": failed_chunks,
            "workers": effective_workers,
        })
        write_progress_snapshot("running")

    def process_result(chunk_number: int, source_file: Path, future: Future[dict[str, Any]]) -> None:
        try:
            receipt = future.result()
            if not _verify_chunk_receipt(receipt):
                raise RuntimeError(f"chunk receipt verification failed for chunk {chunk_number}")
            receipt["resume_status"] = "processed"
            record_receipt(receipt, skipped=False)
        except Exception as exc:  # noqa: BLE001 - failure receipt must preserve the problem and keep the lane moving.
            record_failure(chunk_number=chunk_number, source_file=source_file, error=exc)

    try:
        write_event(
            "run_started",
            source=str(source_path),
            files_selected=len(files),
            file_failures=len(file_failures),
            total_chunks=int(total_chunks),
            effective_workers=int(effective_workers),
        )
        if file_failures:
            write_event("file_policy_applied", file_failures=len(file_failures), policy=oversized_file_policy)
        write_progress_snapshot("running", force=True)
        if effective_workers < MIN_RUNTIME_WORKERS:
            raise RuntimeError(f"laptop-temp-intake requires at least {MIN_RUNTIME_WORKERS} workers; single-core/low-core execution is not allowed")
        pending: dict[Future[dict[str, Any]], tuple[int, Path]] = {}
        with ProcessPoolExecutor(max_workers=effective_workers) as pool:
            for chunk_index, file_path, chunk_bytes in _iter_chunk_jobs(files, chunk_limit, max_chunks):
                existing_receipt = _load_verified_chunk_receipt(chunks_root, chunk_index) if resume else None
                if existing_receipt is not None:
                    receipt = dict(existing_receipt)
                    receipt["resume_status"] = "skipped_completed"
                    record_receipt(receipt, skipped=True)
                    continue
                future = pool.submit(
                    _process_chunk,
                    chunk_index=chunk_index,
                    chunk_bytes=chunk_bytes,
                    source_file=file_path,
                    chunks_root=chunks_root,
                    window=window,
                )
                pending[future] = (chunk_index, file_path)
                while len(pending) >= effective_workers:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for completed in done:
                        chunk_number, completed_file = pending.pop(completed)
                        process_result(chunk_number, completed_file, completed)
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for completed in done:
                    chunk_number, completed_file = pending.pop(completed)
                    process_result(chunk_number, completed_file, completed)
    finally:
        bar.close()

    chunk_receipts = sorted(chunk_receipts, key=lambda row: int(row["chunk_index"]))
    chunk_failures = sorted(chunk_failures, key=lambda row: int(row["chunk_index"]))
    write_progress_snapshot("complete", force=True)
    write_event(
        "run_complete",
        chunks_seen=len(chunk_receipts) + len(chunk_failures),
        chunks_created=int(processed_chunks),
        chunks_skipped=int(skipped_chunks),
        chunks_failed=int(failed_chunks),
        file_failures=int(len(file_failures)),
    )
    summary = {
        "schema": "awrag_laptop_temp_intake_summary@1",
        "created_at": utc_now(),
        "run_id": run_name,
        "state_root": str(root),
        "chunks_seen": len(chunk_receipts) + len(chunk_failures),
        "chunks_created": int(processed_chunks),
        "chunks_skipped": int(skipped_chunks),
        "chunks_failed": int(failed_chunks),
        "file_failures": int(len(file_failures)),
        "raw_bytes": int(aggregate["raw_bytes"]),
        "anchor_observations": int(aggregate["anchors"]),
        "unique_anchor_sum_by_chunk": int(aggregate["unique_anchors"]),
        "relation_observations": int(aggregate["relations"]),
        "symbol_bytes_written": int(aggregate["symbol_bytes_written"]),
        "receipt_verification": "passed" if failed_chunks == 0 else "passed_with_failed_chunks",
        "resource_plan": resource_plan,
        "production_merge": False,
        "global_lifetime_write": False,
        "artifacts": {
            "manifest": str(root / "manifest.json"),
            "summary": str(root / "run_summary.json"),
            "resource_receipt": str(root / "resource_receipt.json"),
            "progress": str(progress_path),
            "run_events": str(run_events_path),
            "source_receipt": str(root / "source_receipt.json"),
            "chunk_receipts": str(root / "chunk_receipts.jsonl"),
            "chunk_failures": str(root / "chunk_failures.jsonl"),
            "file_failures": str(root / "file_failures.jsonl"),
            "chunks": str(chunks_root),
        },
    }
    _write_jsonl(root / "chunk_receipts.jsonl", chunk_receipts)
    _write_jsonl(root / "chunk_failures.jsonl", chunk_failures)
    write_json(root / "run_summary.json", summary)
    return summary


def _process_chunk(
    *,
    chunk_index: int,
    chunk_bytes: bytes,
    source_file: Path,
    chunks_root: Path,
    window: int,
) -> dict[str, Any]:
    stem = f"chunk_{chunk_index:06d}"
    raw_path = chunks_root / f"{stem}.raw"
    symbols_path = chunks_root / f"{stem}.symbols.bin"
    lexicon_path = chunks_root / f"{stem}.lexicon_delta.json"
    counts_path = chunks_root / f"{stem}.counts.bin"
    receipt_path = chunks_root / f"{stem}.receipt.json"

    raw_path.write_bytes(chunk_bytes)
    input_mode = "symbolized_binary" if _looks_symbolized(source_file, chunk_bytes) else "raw_text"

    if input_mode == "symbolized_binary":
        symbols = _symbol_stream(chunk_bytes)
        symbols_path.write_bytes(b"".join(symbols))
        anchor_counts: Counter[str] = Counter()
        _write_symbol_count_artifact(counts_path, symbols, window=window)
        write_json(lexicon_path, {
            "schema": "awrag_laptop_temp_chunk_lexicon_delta@1",
            "chunk_index": chunk_index,
            "source_file": str(source_file),
            "input_mode": input_mode,
            "symbol_system": SYMBOL_SYSTEM,
            "symbol_bytes": SYMBOL_BYTES,
            "anchor_count": 0,
            "anchors": [],
            "note": "Input was already symbolized; no anchor strings were assigned in this chunk.",
        })
        anchor_observations = len(symbols)
        relation_observations = _symbol_relation_observation_count(len(symbols), window=window)
    else:
        text = chunk_bytes.decode("utf-8", errors="replace")
        anchors = _anchors_from_text(text)
        anchor_counts = Counter(anchors)
        assert_no_symbol_collisions(anchor_counts)
        relations = _relation_counts(anchors, window=window)
        with symbols_path.open("wb") as handle:
            for anchor in anchors:
                handle.write(symbol_bytes(anchor))
        write_json(lexicon_path, {
            "schema": "awrag_laptop_temp_chunk_lexicon_delta@1",
            "chunk_index": chunk_index,
            "source_file": str(source_file),
            "input_mode": input_mode,
            "symbol_system": SYMBOL_SYSTEM,
            "symbol_bytes": SYMBOL_BYTES,
            "anchor_count": len(anchor_counts),
            "anchors": [
                {
                    "anchor": anchor,
                    "symbol": symbol_for(anchor),
                    "observations": int(count),
                    "scope": "chunk_local_temp",
                }
                for anchor, count in sorted(anchor_counts.items())
            ],
        })
        _write_count_artifact(counts_path, anchor_counts, relations)
        anchor_observations = len(anchors)
        relation_observations = sum(relations.values())

    receipt = {
        "schema": "awrag_laptop_temp_chunk_receipt@1",
        "created_at": utc_now(),
        "chunk_index": chunk_index,
        "source_file": str(source_file),
        "input_mode": input_mode,
        "raw_bytes": len(chunk_bytes),
        "raw_path": str(raw_path),
        "symbols_path": str(symbols_path),
        "lexicon_delta_path": str(lexicon_path),
        "counts_path": str(counts_path),
        "receipt_path": str(receipt_path),
        "anchor_observations": anchor_observations,
        "unique_anchors": len(anchor_counts),
        "relation_observations": relation_observations,
        "symbol_bytes_written": symbols_path.stat().st_size,
        "counts_bytes_written": counts_path.stat().st_size,
        "production_merge": False,
        "global_lifetime_write": False,
    }
    write_json(receipt_path, receipt)
    return receipt


def _chunk_failure_receipt(*, chunk_index: int, source_file: Path, chunks_root: Path, error: BaseException) -> dict[str, Any]:
    stem = f"chunk_{chunk_index:06d}"
    failure_path = chunks_root / f"{stem}.failure.json"
    failure = {
        "schema": "awrag_laptop_temp_chunk_failure@1",
        "created_at": utc_now(),
        "chunk_index": chunk_index,
        "source_file": str(source_file),
        "error_type": type(error).__name__,
        "error": str(error),
        "failure_path": str(failure_path),
        "production_merge": False,
        "global_lifetime_write": False,
    }
    write_json(failure_path, failure)
    return failure


def _load_verified_chunk_receipt(chunks_root: Path, chunk_index: int) -> dict[str, Any] | None:
    receipt_path = chunks_root / f"chunk_{chunk_index:06d}.receipt.json"
    if not receipt_path.exists():
        return None
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not _verify_chunk_receipt(receipt):
        return None
    return receipt


def _verify_chunk_receipt(receipt: dict[str, Any]) -> bool:
    if receipt.get("schema") != "awrag_laptop_temp_chunk_receipt@1":
        return False
    if receipt.get("production_merge") is not False:
        return False
    if receipt.get("global_lifetime_write") is not False:
        return False

    raw_path = Path(str(receipt.get("raw_path", "")))
    symbols_path = Path(str(receipt.get("symbols_path", "")))
    lexicon_path = Path(str(receipt.get("lexicon_delta_path", "")))
    counts_path = Path(str(receipt.get("counts_path", "")))
    receipt_path = Path(str(receipt.get("receipt_path", "")))
    paths = [raw_path, symbols_path, lexicon_path, counts_path, receipt_path]
    if any(not path.exists() or not path.is_file() or path.stat().st_size <= 0 for path in paths):
        return False
    if int(receipt.get("symbol_bytes_written", -1)) != symbols_path.stat().st_size:
        return False
    if int(receipt.get("counts_bytes_written", -1)) != counts_path.stat().st_size:
        return False
    return True


def _anchors_from_text(text: str) -> list[str]:
    anchors: list[str] = []
    for block in split_blocks(text):
        anchors.extend(anchorize(str(block["text"])))
    return anchors


def _relation_counts(anchors: list[str], *, window: int) -> Counter[tuple[str, str, int]]:
    out: Counter[tuple[str, str, int]] = Counter()
    for position, anchor in enumerate(anchors):
        for offset in range(-window, window + 1):
            if offset == 0:
                continue
            neighbor_index = position + offset
            if 0 <= neighbor_index < len(anchors):
                out[(anchor, anchors[neighbor_index], offset)] += 1
    return out


def _write_count_artifact(path: Path, anchors: Counter[str], relations: Counter[tuple[str, str, int]]) -> None:
    header = {
        "schema": "awrag_laptop_temp_chunk_counts_bin@1",
        "count_backend": COUNT_BACKEND,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "input_mode": "raw_text",
        "anchor_record_size": ANCHOR_RECORD.size,
        "relation_record_size": RELATION_RECORD.size,
        "anchor_records": len(anchors),
        "relation_records": len(relations),
    }
    with path.open("wb") as handle:
        _write_count_header(handle, header)
        for anchor, observations in sorted(anchors.items()):
            handle.write(ANCHOR_RECORD.pack(symbol_bytes(anchor), int(observations)))
        for (anchor, neighbor, offset), observations in sorted(relations.items()):
            handle.write(RELATION_RECORD.pack(symbol_bytes(anchor), symbol_bytes(neighbor), int(offset), int(observations)))


def _write_symbol_count_artifact(path: Path, symbols: list[bytes], *, window: int) -> None:
    symbol_counts = Counter(symbols)
    relation_counts: Counter[tuple[bytes, bytes, int]] = Counter()
    for position, symbol in enumerate(symbols):
        for offset in range(-window, window + 1):
            if offset == 0:
                continue
            neighbor_index = position + offset
            if 0 <= neighbor_index < len(symbols):
                relation_counts[(symbol, symbols[neighbor_index], offset)] += 1
    header = {
        "schema": "awrag_laptop_temp_chunk_counts_bin@1",
        "count_backend": COUNT_BACKEND,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "input_mode": "symbolized_binary",
        "anchor_record_size": ANCHOR_RECORD.size,
        "relation_record_size": RELATION_RECORD.size,
        "anchor_records": len(symbol_counts),
        "relation_records": len(relation_counts),
    }
    with path.open("wb") as handle:
        _write_count_header(handle, header)
        for symbol, observations in sorted(symbol_counts.items()):
            handle.write(ANCHOR_RECORD.pack(symbol, int(observations)))
        for (symbol, neighbor, offset), observations in sorted(relation_counts.items()):
            handle.write(RELATION_RECORD.pack(symbol, neighbor, int(offset), int(observations)))


def _write_count_header(handle: Any, header: dict[str, Any]) -> None:
    header_bytes = json.dumps(header, ensure_ascii=True, sort_keys=True).encode("utf-8")
    handle.write(COUNT_MAGIC)
    handle.write(struct.pack(">I", len(header_bytes)))
    handle.write(header_bytes)


def _looks_symbolized(source_file: Path, chunk_bytes: bytes) -> bool:
    return source_file.name.endswith(".symbols.bin") and len(chunk_bytes) >= SYMBOL_BYTES


def _symbol_stream(chunk_bytes: bytes) -> list[bytes]:
    usable = len(chunk_bytes) - (len(chunk_bytes) % SYMBOL_BYTES)
    return [chunk_bytes[index:index + SYMBOL_BYTES] for index in range(0, usable, SYMBOL_BYTES)]


def _symbol_relation_observation_count(symbol_count: int, *, window: int) -> int:
    total = 0
    for position in range(symbol_count):
        total += min(window, position)
        total += min(window, symbol_count - position - 1)
    return total


def _iter_source_files(source: Path) -> Iterable[Path]:
    if source.is_file():
        yield source
        return
    for path in sorted(source.rglob("*")):
        if path.is_file():
            yield path


def _apply_file_policy(
    files: list[Path],
    *,
    max_file_mb: float | None,
    oversized_file_policy: str,
) -> tuple[list[Path], list[dict[str, Any]]]:
    if max_file_mb is None:
        return files, []
    threshold = int(max_file_mb * 1024 * 1024)
    kept: list[Path] = []
    failures: list[dict[str, Any]] = []
    for path in files:
        size = path.stat().st_size
        if size <= threshold or oversized_file_policy == "chunk":
            kept.append(path)
            continue
        failures.append({
            "schema": "awrag_laptop_temp_file_failure@1",
            "created_at": utc_now(),
            "source_file": str(path),
            "file_bytes": int(size),
            "max_file_bytes": int(threshold),
            "policy": oversized_file_policy,
            "reason": "file_exceeds_max_file_mb",
            "production_merge": False,
            "global_lifetime_write": False,
        })
    return kept, failures


def _iter_chunk_jobs(files: list[Path], chunk_size: int, max_chunks: int | None) -> Iterable[tuple[int, Path, bytes]]:
    chunk_index = 0
    for file_path in files:
        for chunk_bytes in _read_byte_chunks(file_path, chunk_size):
            if max_chunks is not None and chunk_index >= max_chunks:
                return
            chunk_index += 1
            yield chunk_index, file_path, chunk_bytes


def _read_byte_chunks(path: Path, chunk_size: int) -> Iterable[bytes]:
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            yield chunk


def _estimate_chunks(files: list[Path], chunk_size: int, max_chunks: int | None) -> int:
    total = 0
    for path in files:
        size = path.stat().st_size
        total += max(1, (size + chunk_size - 1) // chunk_size)
        if max_chunks is not None and total >= max_chunks:
            return max_chunks
    return total


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _build_resource_plan(
    *,
    chunk_limit: int,
    requested_workers: int | str,
    reserve_ram_fraction: float,
    reserve_ram_gb: float | None,
    ram_budget_gb: float | None,
    refuse_below_reserve: bool = False,
) -> dict[str, Any]:
    if not 0 <= reserve_ram_fraction < 1:
        raise ValueError("reserve_ram_fraction must be between 0 and 1")
    if reserve_ram_gb is not None and reserve_ram_gb < 0:
        raise ValueError("reserve_ram_gb cannot be negative")
    if ram_budget_gb is not None and ram_budget_gb <= 0:
        raise ValueError("ram_budget_gb must be positive")

    resources = _detect_system_resources()
    enforce_minimum_runtime_requirements(resources)
    cpu_count = max(1, int(resources.get("logical_cpu_count") or 1))
    cpu_cap = cpu_count
    requested_label = str(requested_workers)
    if isinstance(requested_workers, str):
        if requested_workers.lower() == "auto":
            requested_count = max(MIN_RUNTIME_WORKERS, cpu_cap)
            auto_workers = True
        else:
            requested_count = int(requested_workers)
            auto_workers = False
    else:
        requested_count = int(requested_workers)
        auto_workers = False
    if requested_count <= 0:
        raise ValueError("workers must be positive or auto")
    if requested_count < MIN_RUNTIME_WORKERS:
        raise ValueError(f"laptop-temp-intake requires at least {MIN_RUNTIME_WORKERS} workers; single-core/low-core execution is not allowed")

    total_ram = resources.get("total_ram_bytes")
    available_ram = resources.get("available_ram_bytes")
    reserve_fraction_bytes = int(total_ram * reserve_ram_fraction) if isinstance(total_ram, int) else None
    reserve_gb_bytes = int(reserve_ram_gb * 1024 * 1024 * 1024) if reserve_ram_gb is not None else 0
    reserve_bytes = max(reserve_fraction_bytes or 0, reserve_gb_bytes)

    # Counting can expand a chunk into strings, anchors, counters, and relation records.
    estimated_worker_bytes = int(chunk_limit * 8 + 256 * 1024 * 1024)
    ram_worker_cap: int | None
    if isinstance(available_ram, int):
        allocatable = max(0, available_ram - reserve_bytes)
        if ram_budget_gb is not None:
            allocatable = min(allocatable, int(ram_budget_gb * 1024 * 1024 * 1024))
        if refuse_below_reserve and available_ram < reserve_bytes:
            raise MemoryError("available RAM is below requested operator/system reserve")
        ram_worker_cap = max(1, allocatable // max(1, estimated_worker_bytes))
    else:
        allocatable = None
        ram_worker_cap = None

    caps = [requested_count, cpu_cap]
    if ram_worker_cap is not None:
        caps.append(int(ram_worker_cap))
    effective_workers = max(1, min(caps))
    if effective_workers < MIN_RUNTIME_WORKERS:
        raise RuntimeError(
            "laptop-temp-intake cannot honor the operator compute rule with the current CPU/RAM limits; "
            "single-core/low-core execution is not allowed"
        )
    if not auto_workers and effective_workers != requested_count:
        raise RuntimeError(
            f"requested workers={requested_count} cannot be honored under current CPU/RAM limits; "
            f"effective workers would be {effective_workers}"
        )
    safety_decisions: list[str] = []
    if auto_workers:
        safety_decisions.append("workers_auto_selected_from_cpu_and_ram")
    if requested_count > effective_workers:
        safety_decisions.append("requested_workers_capped_for_operator_safety")
    if reserve_bytes > 0:
        safety_decisions.append("ram_reserved_for_system_and_operator")
    if isinstance(available_ram, int) and available_ram < reserve_bytes:
        safety_decisions.append("available_ram_below_requested_reserve")
    if ram_worker_cap == 1 and requested_count > 1:
        safety_decisions.append("worker_count_limited_by_available_ram")

    return {
        "schema": "awrag_laptop_temp_resource_plan@1",
        "created_at": utc_now(),
        "resources": resources,
        "requested_workers": requested_label,
        "effective_workers": int(effective_workers),
        "cpu_worker_cap": int(cpu_cap),
        "ram_worker_cap": int(ram_worker_cap) if ram_worker_cap is not None else None,
        "chunk_limit_bytes": int(chunk_limit),
        "estimated_worker_bytes": int(estimated_worker_bytes),
        "reserve_ram_fraction": float(reserve_ram_fraction),
        "reserve_ram_gb": float(reserve_ram_gb) if reserve_ram_gb is not None else None,
        "ram_budget_gb": float(ram_budget_gb) if ram_budget_gb is not None else None,
        "refuse_below_reserve": bool(refuse_below_reserve),
        "reserve_ram_bytes": int(reserve_bytes),
        "allocatable_ram_bytes_after_reserve": int(allocatable) if allocatable is not None else None,
        "parallel_execution": effective_workers > 1,
        "minimum_runtime_requirements": {
            "min_workers": MIN_RUNTIME_WORKERS,
            "min_system_ram_gib": 8,
            "min_gpu_ram_gib": 8,
        },
        "single_core_allowed": False,
        "safety_decisions": safety_decisions,
    }


def _detect_system_resources() -> dict[str, Any]:
    return detect_system_resources()
