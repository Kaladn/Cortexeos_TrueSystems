from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import struct
from base64 import b64encode
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
STOP_ANCHORS = {
    "a",
    "an",
    "and",
    "about",
    "are",
    "as",
    "at",
    "be",
    "by",
    "did",
    "do",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "we",
    "what",
}


def init_runtime(runtime_root: str | Path = "runtime", *, memory_profile_id: str = "default") -> dict[str, Any]:
    paths = runtime_paths(runtime_root, memory_profile_id)
    for key in ("sources", "hot", "packets", "receipts"):
        paths[key].mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "local_memory_profile_manifest@0",
        "created_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "runtime_root": str(Path(runtime_root).expanduser().resolve()),
        "private_runtime": True,
    }
    write_json(paths["profile"] / "profile_manifest.json", manifest)
    return {"schema": "local_memory_init_result@0", "memory_profile_id": memory_profile_id, "paths": public_paths(paths)}


def import_demo(
    demo_path: str | Path = "data/demo/synthetic_chat.jsonl",
    *,
    runtime_root: str | Path = "runtime",
    memory_profile_id: str = "default",
) -> dict[str, Any]:
    paths = runtime_paths(runtime_root, memory_profile_id)
    init_runtime(runtime_root, memory_profile_id=memory_profile_id)
    records = list(read_jsonl(Path(demo_path)))
    address_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    anchor_counts: Counter[str] = Counter()
    cohabitation: Counter[str] = Counter()

    for row in records:
        source_id = "SRC-" + sha256_text(str(row.get("turn_id") or row.get("text") or ""))[:16]
        text = str(row.get("text") or "")
        tag_text = " ".join(str(tag) for tag in row.get("tags", []) if isinstance(tag, str))
        anchors = anchorize(f"{text} {tag_text}")
        source_record = {
            "schema": "local_memory_source_record@0",
            "source_id": source_id,
            "memory_profile_id": memory_profile_id,
            "source_type": "synthetic_demo",
            "source_label": str(row.get("conversation_id") or "demo"),
            "timestamp": str(row.get("timestamp") or ""),
            "content_hash": sha256_text(text),
            "chunk_count": 1,
            "private": False,
            "synthetic": True,
            "turn_id": row.get("turn_id"),
            "speaker": row.get("speaker"),
            "tags": row.get("tags") if isinstance(row.get("tags"), list) else [],
        }
        memory_id = "MEM-" + sha256_text(f"{source_id}|0")[:16]
        citation = "MEMCIT-" + sha256_text(memory_id)[:10]
        address_record = {
            "schema": "local_memory_address_record@0",
            "memory_id": memory_id,
            "source_id": source_id,
            "chunk_id": "CHUNK-0001",
            "tier": "hot",
            "source_type": "synthetic_demo",
            "source_label": source_record["source_label"],
            "timestamp": source_record["timestamp"],
            "line_start": 1,
            "line_end": 1,
            "char_start": 0,
            "char_end": len(text),
            "snippet": text,
            "citation": citation,
            "anchors": anchors,
        }
        source_rows.append(source_record)
        address_rows.append(address_record)
        update_counts(anchor_counts, cohabitation, anchors)

    write_jsonl(paths["source_manifest"], source_rows)
    write_jsonl(paths["hot_address_index"], address_rows)
    hot_counts = {
        "schema": "local_memory_hot_counts@0",
        "created_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "anchors": dict(sorted(anchor_counts.items())),
        "cohabitation": dict(sorted(cohabitation.items())),
    }
    write_json(paths["hot_counts"], hot_counts)
    receipt = {
        "schema": "local_memory_intake_receipt@0",
        "created_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "source": str(Path(demo_path).resolve()),
        "source_count": len(source_rows),
        "address_count": len(address_rows),
        "anchor_count": sum(anchor_counts.values()),
        "unique_anchor_count": len(anchor_counts),
        "hot_counts_path": str(paths["hot_counts"]),
        "hot_address_index_path": str(paths["hot_address_index"]),
        "private_data_exported": False,
    }
    receipt_path = paths["receipts"] / f"intake_receipt_{stamp()}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    write_json(receipt_path, receipt)
    return receipt


def add_file(
    file_path: str | Path,
    *,
    runtime_root: str | Path = "runtime",
    memory_profile_id: str = "default",
    source_label: str | None = None,
    chunk_lines: int = 12,
) -> dict[str, Any]:
    paths = runtime_paths(runtime_root, memory_profile_id)
    init_runtime(runtime_root, memory_profile_id=memory_profile_id)
    source = Path(file_path).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    before_hash = sha256_file(source)
    text = source.read_text(encoding="utf-8", errors="replace")
    line_chunks = chunk_text_lines(text, chunk_lines=max(1, int(chunk_lines)))
    source_id = "SRC-" + sha256_text(f"{source}|{before_hash}")[:16]
    label = source_label or source.name
    source_record = {
        "schema": "local_memory_source_record@0",
        "source_id": source_id,
        "memory_profile_id": memory_profile_id,
        "source_type": "file",
        "source_label": label,
        "path": str(source),
        "timestamp": utc_now(),
        "content_hash": before_hash,
        "chunk_count": len(line_chunks),
        "private": True,
        "synthetic": False,
    }
    address_rows: list[dict[str, Any]] = []
    anchor_counts: Counter[str] = Counter()
    cohabitation: Counter[str] = Counter()
    for index, chunk in enumerate(line_chunks, start=1):
        anchors = anchorize(chunk["text"])
        memory_id = "MEM-" + sha256_text(f"{source_id}|{index}")[:16]
        citation = "MEMCIT-" + sha256_text(memory_id)[:10]
        address_rows.append({
            "schema": "local_memory_address_record@0",
            "memory_id": memory_id,
            "source_id": source_id,
            "chunk_id": f"CHUNK-{index:04d}",
            "tier": "hot",
            "source_type": "file",
            "source_label": label,
            "timestamp": source_record["timestamp"],
            "line_start": chunk["line_start"],
            "line_end": chunk["line_end"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
            "snippet": chunk["text"],
            "citation": citation,
            "anchors": anchors,
        })
        update_counts(anchor_counts, cohabitation, anchors)
    append_jsonl(paths["source_manifest"], [source_record])
    append_jsonl(paths["hot_address_index"], address_rows)
    merge_hot_counts(paths["hot_counts"], anchor_counts, cohabitation, memory_profile_id=memory_profile_id)
    after_hash = sha256_file(source)
    receipt = {
        "schema": "local_memory_file_intake_receipt@0",
        "created_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "source_path": str(source),
        "source_label": label,
        "source_id": source_id,
        "source_hash_before": before_hash,
        "source_hash_after": after_hash,
        "source_hash_unchanged": before_hash == after_hash,
        "chunk_count": len(address_rows),
        "anchor_count": sum(anchor_counts.values()),
        "unique_anchor_count": len(anchor_counts),
        "hot_counts_path": str(paths["hot_counts"]),
        "hot_address_index_path": str(paths["hot_address_index"]),
        "private_data_exported": False,
        "source_mutated": False,
    }
    receipt_path = paths["receipts"] / f"file_intake_receipt_{stamp()}_{sha256_text(str(source))[:8]}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    write_json(receipt_path, receipt)
    return receipt


def attach_source(
    path: str | Path,
    *,
    source_type: str,
    label: str,
    runtime_root: str | Path = "runtime",
    memory_profile_id: str = "default",
) -> dict[str, Any]:
    paths = runtime_paths(runtime_root, memory_profile_id)
    init_runtime(runtime_root, memory_profile_id=memory_profile_id)
    source_path = Path(path).expanduser().resolve()
    if source_type not in {"chat-binary", "file-root", "file"}:
        raise ValueError("source_type must be chat-binary, file-root, or file")
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if source_type == "file" and not source_path.is_file():
        raise ValueError("source_type=file requires a file path")
    if source_type == "file-root" and not source_path.is_dir():
        raise ValueError("source_type=file-root requires a directory path")
    if source_type == "chat-binary" and not source_path.is_file():
        raise ValueError("source_type=chat-binary requires a file path")

    source_hash = sha256_path(source_path)
    source_id = "SRC-" + sha256_text(f"{source_type}|{source_path}|{source_hash}")[:16]
    status = "attached_not_decoded" if source_type == "chat-binary" else "attached"
    record = {
        "schema": "local_memory_attached_source@0",
        "attached_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "source_id": source_id,
        "source_type": source_type,
        "label": label,
        "path": str(source_path),
        "path_kind": "directory" if source_path.is_dir() else "file",
        "size_bytes": path_size(source_path),
        "source_hash": source_hash,
        "status": status,
        "private": True,
        "indexed": False,
    }
    append_jsonl(paths["attached_sources"], [record])
    receipt = {
        "schema": "local_memory_attach_source_receipt@0",
        "created_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "source_id": source_id,
        "source_type": source_type,
        "label": label,
        "path": str(source_path),
        "source_hash": source_hash,
        "status": status,
        "private_data_exported": False,
        "source_mutated": False,
    }
    receipt_path = paths["receipts"] / f"attach_source_receipt_{stamp()}_{source_id}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    write_json(receipt_path, receipt)
    return receipt


def list_sources(runtime_root: str | Path = "runtime", *, memory_profile_id: str = "default") -> dict[str, Any]:
    paths = runtime_paths(runtime_root, memory_profile_id)
    rows = list(read_jsonl(paths["attached_sources"]))
    statuses = source_receipt_statuses(paths["receipts"])
    enriched_rows = []
    for row in rows:
        source_id = str(row.get("source_id") or "")
        status = statuses.get(source_id, {})
        enriched = dict(row)
        if status:
            enriched["indexed"] = bool(status.get("indexed", enriched.get("indexed", False)))
            enriched["latest_index_status"] = status.get("latest_index_status")
            enriched["latest_index_receipt"] = status.get("latest_index_receipt")
            enriched["latest_inspect_status"] = status.get("latest_inspect_status")
            enriched["latest_inspect_receipt"] = status.get("latest_inspect_receipt")
            enriched["sqlite_support_built"] = bool(status.get("sqlite_support_built", False))
            enriched["latest_sqlite_support_receipt"] = status.get("latest_sqlite_support_receipt")
        enriched_rows.append(enriched)
    return {
        "schema": "local_memory_attached_sources@0",
        "memory_profile_id": memory_profile_id,
        "source_count": len(enriched_rows),
        "sources": enriched_rows,
    }


def index_source(
    source_id: str,
    *,
    runtime_root: str | Path = "runtime",
    memory_profile_id: str = "default",
    hot: bool = False,
    chunk_lines: int = 12,
) -> dict[str, Any]:
    if not hot:
        raise ValueError("index-source v0 requires --hot")
    paths = runtime_paths(runtime_root, memory_profile_id)
    sources = list(read_jsonl(paths["attached_sources"]))
    source = next((row for row in reversed(sources) if row.get("source_id") == source_id), None)
    if not source:
        raise ValueError(f"unknown source_id: {source_id}")
    source_type = str(source.get("source_type") or "")
    source_path = Path(str(source.get("path") or "")).expanduser().resolve()
    before_hash = sha256_path(source_path)
    if before_hash != source.get("source_hash"):
        raise RuntimeError("source_hash_mismatch: attached source changed before indexing")
    if source_type == "chat-binary":
        receipt = {
            "schema": "local_memory_index_source_receipt@0",
            "created_at": utc_now(),
            "memory_profile_id": memory_profile_id,
            "source_id": source_id,
            "source_type": source_type,
            "status": "attached_not_decoded",
            "indexed": False,
            "reason": "chat-binary decoder is not implemented in v0",
            "source_hash_before": before_hash,
            "source_hash_after": before_hash,
            "source_hash_unchanged": True,
            "private_data_exported": False,
            "source_mutated": False,
        }
        receipt_path = paths["receipts"] / f"index_source_receipt_{stamp()}_{source_id}.json"
        write_json(receipt_path, receipt)
        receipt["receipt_path"] = str(receipt_path)
        write_json(receipt_path, receipt)
        return receipt
    if source_type == "file":
        file_paths = [source_path]
    elif source_type == "file-root":
        file_paths = list(iter_text_files(source_path))
    else:
        raise ValueError(f"unsupported source_type for indexing: {source_type}")

    total_chunks = 0
    total_anchors = 0
    indexed_files: list[dict[str, Any]] = []
    for file_path in file_paths:
        result = add_file(
            file_path,
            runtime_root=runtime_root,
            memory_profile_id=memory_profile_id,
            source_label=f"{source.get('label')}:{file_path.name}",
            chunk_lines=chunk_lines,
        )
        total_chunks += int(result.get("chunk_count", 0))
        total_anchors += int(result.get("anchor_count", 0))
        indexed_files.append({
            "path": str(file_path),
            "source_id": result.get("source_id"),
            "chunk_count": result.get("chunk_count"),
            "source_hash_unchanged": result.get("source_hash_unchanged"),
        })
    after_hash = sha256_path(source_path)
    receipt = {
        "schema": "local_memory_index_source_receipt@0",
        "created_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "source_id": source_id,
        "source_type": source_type,
        "status": "indexed_hot",
        "indexed": True,
        "file_count": len(file_paths),
        "chunk_count": total_chunks,
        "anchor_count": total_anchors,
        "indexed_files": indexed_files,
        "source_hash_before": before_hash,
        "source_hash_after": after_hash,
        "source_hash_unchanged": before_hash == after_hash,
        "private_data_exported": False,
        "source_mutated": False,
    }
    receipt_path = paths["receipts"] / f"index_source_receipt_{stamp()}_{source_id}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    write_json(receipt_path, receipt)
    return receipt


def inspect_binary(
    source_id: str,
    *,
    runtime_root: str | Path = "runtime",
    memory_profile_id: str = "default",
    sample_bytes: int = 64,
) -> dict[str, Any]:
    paths = runtime_paths(runtime_root, memory_profile_id)
    sources = list(read_jsonl(paths["attached_sources"]))
    source = next((row for row in reversed(sources) if row.get("source_id") == source_id), None)
    if not source:
        raise ValueError(f"unknown source_id: {source_id}")
    if source.get("source_type") != "chat-binary":
        raise ValueError("inspect-binary only accepts attached chat-binary sources")

    source_path = Path(str(source.get("path") or "")).expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source_path)

    sample_len = max(1, int(sample_bytes))
    before_hash = sha256_file(source_path)
    size = int(source_path.stat().st_size)
    first_bytes = read_binary_window(source_path, 0, sample_len)
    sample_offsets = sample_binary_offsets(size, sample_len)
    after_hash = sha256_file(source_path)
    receipt = {
        "schema": "local_memory_chat_binary_inspect_receipt@0",
        "created_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "source_id": source_id,
        "path": str(source_path),
        "source_type": "chat-binary",
        "size_bytes": size,
        "sha256": before_hash,
        "attached_source_hash": source.get("source_hash"),
        "attached_hash_matches_current": before_hash == source.get("source_hash"),
        "source_hash_after": after_hash,
        "source_hash_unchanged": before_hash == after_hash,
        "first_bytes_hex": first_bytes.hex(" "),
        "sample_bytes": sample_len,
        "sample_offsets": sample_offsets,
        "possible_format": guess_binary_format(first_bytes),
        "record_count_if_detectable": None,
        "decode_status": "not_decoded",
        "no_mutation": True,
        "source_mutated": False,
        "private_data_exported": False,
        "decoder_law": "Binary decoder must cite offsets before it claims meaning.",
    }
    receipt_path = paths["receipts"] / f"chat_binary_inspect_receipt_{stamp()}_{source_id}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    write_json(receipt_path, receipt)
    return receipt


def build_sqlite_support(
    source_id: str,
    *,
    runtime_root: str | Path = "runtime",
    memory_profile_id: str = "default",
    tables: list[str] | None = None,
    limit_per_table: int | None = None,
    allow_live_source: bool = False,
) -> dict[str, Any]:
    paths = runtime_paths(runtime_root, memory_profile_id)
    paths["support"].mkdir(parents=True, exist_ok=True)
    sources = list(read_jsonl(paths["attached_sources"]))
    source = next((row for row in reversed(sources) if row.get("source_id") == source_id), None)
    if not source:
        raise ValueError(f"unknown source_id: {source_id}")
    if source.get("source_type") != "chat-binary":
        raise ValueError("sqlite-support only accepts attached chat-binary sources")

    source_path = Path(str(source.get("path") or "")).expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source_path)
    first_bytes = read_binary_window(source_path, 0, 64)
    if guess_binary_format(first_bytes) != "sqlite":
        raise ValueError("sqlite-support requires a SQLite database source")

    before_hash = sha256_file(source_path)
    attached_hash = source.get("source_hash")
    attached_hash_matches_before = before_hash == attached_hash
    if attached_hash and not attached_hash_matches_before and not allow_live_source:
        raise RuntimeError("source_hash_mismatch: attached SQLite source changed before support conversion")

    binary_path = paths["support"] / f"sqlite_support_{source_id}.rows.bin"
    index_path = paths["support"] / f"sqlite_support_{source_id}.row_index.jsonl"
    table_stats: list[dict[str, Any]] = []
    index_rows: list[dict[str, Any]] = []
    row_count = 0
    binary_hash = hashlib.sha256()
    header = {
        "schema": "local_memory_sqlite_support_binary@0",
        "created_at": utc_now(),
        "source_id": source_id,
        "source_path": str(source_path),
        "source_hash": before_hash,
        "record_encoding": "uint32_le_length_prefixed_json",
    }

    con = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        available_tables = [
            str(row[0])
            for row in con.execute("select name from sqlite_master where type='table' order by name").fetchall()
            if not str(row[0]).startswith("sqlite_")
        ]
        selected_tables = [table for table in available_tables if tables is None or table in set(tables)]
        if tables is not None:
            missing = sorted(set(tables) - set(selected_tables))
            if missing:
                raise ValueError(f"unknown sqlite tables: {', '.join(missing)}")

        with binary_path.open("wb") as binary_handle:
            header_bytes = (json.dumps(header, ensure_ascii=True, sort_keys=True) + "\n").encode("utf-8")
            binary_handle.write(b"LMC-SQLITE-SUPPORT-0\n")
            binary_handle.write(struct.pack("<I", len(header_bytes)))
            binary_handle.write(header_bytes)
            binary_hash.update(b"LMC-SQLITE-SUPPORT-0\n")
            binary_hash.update(struct.pack("<I", len(header_bytes)))
            binary_hash.update(header_bytes)

            for table in selected_tables:
                columns = [str(col[1]) for col in con.execute(f"pragma table_info({quote_sql_identifier(table)})").fetchall()]
                count_query = f"select count(*) from {quote_sql_identifier(table)}"
                table_total = int(con.execute(count_query).fetchone()[0])
                query = f"select rowid, * from {quote_sql_identifier(table)} order by rowid"
                if limit_per_table is not None:
                    query += f" limit {max(0, int(limit_per_table))}"
                table_written = 0
                for row in con.execute(query):
                    sqlite_rowid = row[0]
                    values = {column: encode_sqlite_value(value) for column, value in zip(columns, row[1:])}
                    citation = "SQLCIT-" + sha256_text(f"{source_id}|{table}|{sqlite_rowid}")[:12]
                    payload = {
                        "schema": "local_memory_sqlite_support_row@0",
                        "source_id": source_id,
                        "source_path": str(source_path),
                        "source_hash": before_hash,
                        "table": table,
                        "sqlite_rowid": sqlite_rowid,
                        "citation": citation,
                        "values": values,
                    }
                    payload_bytes = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
                    offset = binary_handle.tell()
                    prefix = struct.pack("<I", len(payload_bytes))
                    binary_handle.write(prefix)
                    binary_handle.write(payload_bytes)
                    binary_hash.update(prefix)
                    binary_hash.update(payload_bytes)
                    row_hash = hashlib.sha256(payload_bytes).hexdigest()
                    index_rows.append({
                        "schema": "local_memory_sqlite_support_index@0",
                        "source_id": source_id,
                        "table": table,
                        "sqlite_rowid": sqlite_rowid,
                        "citation": citation,
                        "binary_path": str(binary_path),
                        "binary_offset": offset,
                        "record_length": len(prefix) + len(payload_bytes),
                        "payload_length": len(payload_bytes),
                        "row_hash": row_hash,
                    })
                    row_count += 1
                    table_written += 1
                table_stats.append({
                    "table": table,
                    "table_total_rows": table_total,
                    "rows_written": table_written,
                    "columns": columns,
                })
    finally:
        con.close()

    write_jsonl(index_path, index_rows)
    after_hash = sha256_file(source_path)
    receipt = {
        "schema": "local_memory_sqlite_support_receipt@0",
        "created_at": utc_now(),
        "memory_profile_id": memory_profile_id,
        "source_id": source_id,
        "source_path": str(source_path),
        "attached_source_hash": attached_hash,
        "source_hash_before": before_hash,
        "attached_hash_matches_before": attached_hash_matches_before,
        "source_hash_after": after_hash,
        "source_hash_unchanged": before_hash == after_hash,
        "binary_path": str(binary_path),
        "binary_sha256": binary_hash.hexdigest(),
        "index_path": str(index_path),
        "table_count": len(table_stats),
        "row_count": row_count,
        "tables": table_stats,
        "decode_status": "sqlite_rows_converted_to_support_binary",
        "source_mutated": False,
        "private_data_exported": False,
        "live_source_allowed": allow_live_source,
        "replay_note": "SQLite rows are supporting evidence. Turn-by-turn chat replay should use rollout/session JSONL where available.",
    }
    receipt_path = paths["receipts"] / f"sqlite_support_receipt_{stamp()}_{source_id}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    write_json(receipt_path, receipt)
    return receipt


def ask(
    question: str,
    *,
    runtime_root: str | Path = "runtime",
    memory_profile_id: str = "default",
    limit: int = 5,
) -> dict[str, Any]:
    paths = runtime_paths(runtime_root, memory_profile_id)
    address_rows = list(read_jsonl(paths["hot_address_index"]))
    if not address_rows:
        raise RuntimeError("memory_packet_empty: import demo or add memory before asking")
    hot_counts = read_json(paths["hot_counts"]) if paths["hot_counts"].exists() else {"anchors": {}, "cohabitation": {}}
    q_anchors = anchorize(question)
    scored = score_hot_memory(q_anchors, address_rows, hot_counts, limit=limit)
    missing = [anchor for anchor in q_anchors if not any(anchor in row.get("anchors", []) for row in address_rows)]
    packet = {
        "schema": "local_memory_packet@0",
        "created_at": utc_now(),
        "question": question,
        "memory_profile_id": memory_profile_id,
        "search_policy": {
            "hot_searched": True,
            "warm_searched": False,
            "cold_searched": False,
            "cold_search_reason": None,
        },
        "question_anchors": q_anchors,
        "evidence_items": [to_evidence_item(row) for row in scored],
        "missing_evidence": missing,
        "render_policy": "renderer_packet_only",
    }
    packet_path = paths["packets"] / f"memory_packet_{stamp()}_{sha256_text(question)[:8]}.json"
    write_json(packet_path, packet)
    receipt = {
        "schema": "local_memory_search_receipt@0",
        "created_at": utc_now(),
        "question_hash": sha256_text(question),
        "memory_packet_hash": sha256_file(packet_path),
        "memory_packet_path": str(packet_path),
        "hot_searched": True,
        "warm_searched": False,
        "cold_searched": False,
        "evidence_count": len(packet["evidence_items"]),
        "memory_items_used": [item["citation"] for item in packet["evidence_items"]],
        "private_data_exported": False,
    }
    receipt_path = paths["receipts"] / f"search_receipt_{stamp()}_{sha256_text(question)[:8]}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    write_json(receipt_path, receipt)
    return {"schema": "local_memory_ask_result@0", "packet": packet, "packet_path": str(packet_path), "receipt": receipt}


def score_hot_memory(
    q_anchors: list[str],
    address_rows: list[dict[str, Any]],
    hot_counts: dict[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    anchor_counts = hot_counts.get("anchors") if isinstance(hot_counts.get("anchors"), dict) else {}
    q_set = set(q_anchors)
    scored: list[dict[str, Any]] = []
    for row in address_rows:
        anchors = row.get("anchors") if isinstance(row.get("anchors"), list) else anchorize(str(row.get("snippet") or ""))
        overlap = q_set & set(str(anchor) for anchor in anchors)
        if not overlap:
            continue
        pressure = sum(float(anchor_counts.get(anchor, 0)) for anchor in overlap)
        score = len(overlap) * 10.0 + pressure
        scored.append({**row, "score": round(score, 4), "matched_anchors": sorted(overlap)})
    scored.sort(key=lambda row: (-float(row.get("score", 0.0)), str(row.get("timestamp") or ""), str(row.get("memory_id") or "")))
    return scored[: max(0, int(limit))]


def to_evidence_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "memory_id": row.get("memory_id"),
        "tier": row.get("tier", "hot"),
        "source_type": row.get("source_type"),
        "source_label": row.get("source_label"),
        "timestamp": row.get("timestamp"),
        "snippet": row.get("snippet"),
        "citation": row.get("citation"),
        "score": row.get("score", 0.0),
        "matched_anchors": row.get("matched_anchors", []),
        "address": {
            "source_id": row.get("source_id"),
            "chunk_id": row.get("chunk_id"),
            "line_start": row.get("line_start"),
            "line_end": row.get("line_end"),
            "char_start": row.get("char_start"),
            "char_end": row.get("char_end"),
        },
    }


def runtime_paths(runtime_root: str | Path, memory_profile_id: str) -> dict[str, Path]:
    root = Path(runtime_root).expanduser().resolve()
    profile = root / "profiles" / safe_id(memory_profile_id)
    sources = profile / "sources"
    hot = profile / "hot"
    packets = profile / "packets"
    receipts = profile / "receipts"
    support = profile / "support"
    return {
        "root": root,
        "profile": profile,
        "sources": sources,
        "hot": hot,
        "packets": packets,
        "receipts": receipts,
        "support": support,
        "source_manifest": sources / "source_manifest.jsonl",
        "hot_counts": hot / "hot_counts.json",
        "hot_address_index": hot / "hot_address_index.jsonl",
        "attached_sources": sources / "attached_sources.jsonl",
    }


def public_paths(paths: dict[str, Path]) -> dict[str, str]:
    return {key: str(value) for key, value in paths.items() if isinstance(value, Path)}


def anchorize(text: str) -> list[str]:
    anchors: list[str] = []
    seen: set[str] = set()
    for match in WORD_RE.finditer(str(text or "")):
        raw = normalize_anchor(match.group(0))
        for anchor in anchor_variants(raw):
            if anchor in STOP_ANCHORS or anchor in seen:
                continue
            seen.add(anchor)
            anchors.append(anchor)
    return anchors


def normalize_anchor(value: str) -> str:
    return str(value or "").strip("._-").casefold()


def anchor_variants(anchor: str) -> list[str]:
    variants = [anchor]
    if len(anchor) > 4 and anchor.endswith("s"):
        variants.append(anchor[:-1])
    if len(anchor) > 5 and anchor.endswith("ed"):
        variants.append(anchor[:-1])
    if len(anchor) > 6 and anchor.endswith("er"):
        variants.append(anchor[:-2])
    if anchor.endswith("renderer"):
        variants.append("render")
    return [variant for variant in variants if variant]


def update_counts(anchor_counts: Counter[str], cohabitation: Counter[str], anchors: list[str]) -> None:
    anchor_counts.update(anchors)
    for index, center in enumerate(anchors):
        for offset in (-2, -1, 1, 2):
            neighbor_index = index + offset
            if 0 <= neighbor_index < len(anchors):
                key = f"{center}|{anchors[neighbor_index]}|{offset:+d}"
                cohabitation[key] += 1


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def merge_hot_counts(
    hot_counts_path: Path,
    anchor_counts: Counter[str],
    cohabitation: Counter[str],
    *,
    memory_profile_id: str,
) -> None:
    existing = read_json(hot_counts_path) if hot_counts_path.exists() else {}
    anchors = Counter({str(key): int(value) for key, value in (existing.get("anchors") or {}).items()})
    relations = Counter({str(key): int(value) for key, value in (existing.get("cohabitation") or {}).items()})
    anchors.update(anchor_counts)
    relations.update(cohabitation)
    write_json(
        hot_counts_path,
        {
            "schema": "local_memory_hot_counts@0",
            "created_at": utc_now(),
            "memory_profile_id": memory_profile_id,
            "anchors": dict(sorted(anchors.items())),
            "cohabitation": dict(sorted(relations.items())),
        },
    )


def chunk_text_lines(text: str, *, chunk_lines: int) -> list[dict[str, Any]]:
    lines = str(text or "").splitlines()
    chunks: list[dict[str, Any]] = []
    char_cursor = 0
    line_offsets: list[int] = []
    for line in lines:
        line_offsets.append(char_cursor)
        char_cursor += len(line) + 1
    for start in range(0, len(lines), chunk_lines):
        end = min(len(lines), start + chunk_lines)
        chunk_text = "\n".join(lines[start:end]).strip()
        if not chunk_text:
            continue
        char_start = line_offsets[start] if start < len(line_offsets) else 0
        char_end = line_offsets[end - 1] + len(lines[end - 1]) if end - 1 < len(line_offsets) else char_start + len(chunk_text)
        chunks.append(
            {
                "line_start": start + 1,
                "line_end": end,
                "char_start": char_start,
                "char_end": char_end,
                "text": chunk_text,
            }
        )
    if not chunks and text:
        chunks.append({"line_start": 1, "line_end": 1, "char_start": 0, "char_end": len(text), "text": text})
    return chunks


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_receipt_statuses(receipts_path: Path) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    if not receipts_path.exists():
        return statuses
    for path in sorted(receipts_path.glob("*.json"), key=lambda item: item.stat().st_mtime):
        try:
            receipt = read_json(path)
        except Exception:
            continue
        source_id = str(receipt.get("source_id") or "")
        if not source_id:
            continue
        status = statuses.setdefault(source_id, {})
        schema = str(receipt.get("schema") or "")
        if schema == "local_memory_index_source_receipt@0":
            status["indexed"] = bool(receipt.get("indexed", False))
            status["latest_index_status"] = receipt.get("status")
            status["latest_index_receipt"] = str(path)
        elif schema == "local_memory_chat_binary_inspect_receipt@0":
            status["latest_inspect_status"] = receipt.get("decode_status")
            status["latest_inspect_receipt"] = str(path)
        elif schema == "local_memory_sqlite_support_receipt@0":
            status["sqlite_support_built"] = True
            status["latest_sqlite_support_receipt"] = str(path)
    return statuses


def quote_sql_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def encode_sqlite_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "type": "blob",
            "size": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
            "base64": b64encode(value).decode("ascii"),
        }
    return value


def safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("._")
    if not safe:
        raise ValueError("memory_profile_id is required")
    return safe


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)
    if path.is_dir():
        entries: list[str] = []
        for child in iter_text_files(path):
            rel = child.relative_to(path).as_posix()
            entries.append(f"{rel}:{sha256_file(child)}:{child.stat().st_size}")
        return sha256_text("\n".join(sorted(entries)))
    raise FileNotFoundError(path)


def path_size(path: Path) -> int:
    if path.is_file():
        return int(path.stat().st_size)
    if path.is_dir():
        return sum(int(child.stat().st_size) for child in iter_text_files(path))
    return 0


def read_binary_window(path: Path, offset: int, length: int) -> bytes:
    with path.open("rb") as handle:
        handle.seek(max(0, int(offset)))
        return handle.read(max(1, int(length)))


def sample_binary_offsets(size: int, sample_bytes: int) -> list[int]:
    if size <= 0:
        return []
    offsets = {0}
    if size > sample_bytes * 2:
        offsets.add(size // 2)
    if size > sample_bytes:
        offsets.add(max(0, size - sample_bytes))
    return sorted(offsets)


def guess_binary_format(first_bytes: bytes) -> str:
    if not first_bytes:
        return "empty"
    if first_bytes.startswith(b"SQLite format 3"):
        return "sqlite"
    if first_bytes.startswith(b"GGUF"):
        return "gguf"
    if first_bytes.startswith(b"PK\x03\x04"):
        return "zip"
    if first_bytes.startswith(b"\x1f\x8b"):
        return "gzip"
    stripped = first_bytes.lstrip()
    if stripped.startswith((b"{", b"[")):
        return "json_like"
    if all(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in first_bytes):
        return "plain_text_like"
    return "unknown"


def iter_text_files(root: Path) -> Iterable[Path]:
    suffixes = {".txt", ".md", ".markdown", ".jsonl", ".json", ".csv", ".log"}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.suffix.casefold() in suffixes:
            yield path
