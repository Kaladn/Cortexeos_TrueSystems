"""Lossless optional single-file publication for a completed TrueMem intake."""

from __future__ import annotations

import hashlib
import io
import json
import mmap
import os
import struct
import zlib
from pathlib import Path
from typing import Any, BinaryIO, Iterable

from .base import DatasetPaths
from .chat import parse_chat_datetime
from .storage import ANCHOR_RECORD, RELATION_RECORD, block_anchor_record
from .structural_storage import read_structural_graph


MAGIC = b"TMNAT001"
PREFIX = struct.Struct("<8sI")
ANCHOR = struct.Struct(">6sQIQQQQQB")
RELATION = struct.Struct(">6sbI")
OCCURRENCE = struct.Struct(">II")
DOCUMENT = struct.Struct(">QIQQ32s")
KIND = {"content": 1, "relation": 2, "glue": 3, "boundary": 4, "object": 5}


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _records(path: Path, record: struct.Struct) -> Iterable[tuple]:
    with path.open("rb") as handle:
        while chunk := handle.read(record.size):
            if len(chunk) != record.size:
                raise ValueError(f"truncated native record source: {path}")
            yield record.unpack(chunk)


def _write_value(handle: BinaryIO, value: object) -> None:
    if value is None:
        handle.write(b"n")
    elif value is False:
        handle.write(b"f")
    elif value is True:
        handle.write(b"t")
    elif isinstance(value, int):
        handle.write(b"i" + struct.pack(">q", value))
    elif isinstance(value, float):
        handle.write(b"d" + struct.pack(">d", value))
    elif isinstance(value, str):
        raw = value.encode()
        handle.write(b"s" + struct.pack(">I", len(raw)) + raw)
    elif isinstance(value, list):
        handle.write(b"l" + struct.pack(">I", len(value)))
        for item in value:
            _write_value(handle, item)
    elif isinstance(value, dict):
        handle.write(b"m" + struct.pack(">I", len(value)))
        for key in sorted(value):
            _write_value(handle, str(key))
            _write_value(handle, value[key])
    else:
        raise TypeError(f"unsupported native value: {type(value).__name__}")


def _encoded(value: object) -> bytes:
    raw = io.BytesIO()
    _write_value(raw, value)
    return zlib.compress(raw.getvalue(), level=9)


def _temporal_graph(
    dataset_id: str,
    blocks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Build explicit chat-turn nodes and conversation-local order edges."""

    conversations: dict[str, dict[tuple[int, str], list[dict[str, Any]]]] = {}
    for block in blocks:
        metadata = block.get("chat_metadata") or {}
        conversation_id = str(metadata.get("conversation_id") or "").strip()
        turn_index = metadata.get("turn_index")
        if not conversation_id or not isinstance(turn_index, int):
            continue
        message_id = str(metadata.get("message_id") or "").strip()
        turn_key = (turn_index, message_id)
        conversations.setdefault(conversation_id, {}).setdefault(turn_key, []).append(block)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    ambiguous_turn_count = 0
    for conversation_id in sorted(conversations):
        turn_groups = conversations[conversation_id]
        index_counts: dict[int, int] = {}
        for turn_index, _message_id in turn_groups:
            index_counts[turn_index] = index_counts.get(turn_index, 0) + 1
        ambiguous_turn_count += sum(count for count in index_counts.values() if count > 1)
        turns: list[dict[str, Any]] = []
        for (turn_index, message_id), turn_blocks in sorted(turn_groups.items()):
            if index_counts[turn_index] != 1:
                continue
            ordered_blocks = sorted(turn_blocks, key=lambda row: int(row["block_ordinal"]))
            metadata = ordered_blocks[0]["chat_metadata"]
            identity = {
                "dataset_id": dataset_id,
                "conversation_id": conversation_id,
                "message_id": message_id or None,
                "turn_index": turn_index,
            }
            node = {
                "schema": "truemem_temporal_node@1",
                "node_type": "CHAT_TURN",
                "node_id": hashlib.sha256(_canonical(identity)).hexdigest(),
                **identity,
                "block_ordinals": [int(row["block_ordinal"]) for row in ordered_blocks],
                "block_ids": [str(row["block_id"]) for row in ordered_blocks],
                "created_at": metadata.get("created_at"),
                "speaker": metadata.get("speaker"),
                "provenance": "explicit_chat_conversation_and_turn_index",
                "inferred_semantics": False,
            }
            nodes.append(node)
            turns.append(node)
        for source, target in zip(turns, turns[1:]):
            if int(target["turn_index"]) <= int(source["turn_index"]):
                continue
            source_time = parse_chat_datetime(str(source.get("created_at") or ""))
            target_time = parse_chat_datetime(str(target.get("created_at") or ""))
            delta_ms = None
            if source_time and target_time:
                delta_ms = int((target_time - source_time).total_seconds() * 1000)
            edges.append({
                "schema": "truemem_temporal_edge@1",
                "relation": "NEXT_TURN",
                "coordinate_domain": "TEMPORAL",
                "provenance": "explicit_chat_conversation_and_turn_index",
                "conversation_id": conversation_id,
                "source_node_id": source["node_id"],
                "target_node_id": target["node_id"],
                "source_message_id": source["message_id"],
                "target_message_id": target["message_id"],
                "source_turn_index": int(source["turn_index"]),
                "target_turn_index": int(target["turn_index"]),
                "delta_ms": delta_ms,
                "inferred_semantics": False,
            })
    return nodes, edges, ambiguous_turn_count


def _ranges(rows: Iterable[tuple]) -> tuple[bytes, dict[bytes, tuple[int, int]], int]:
    output = bytearray()
    ranges: dict[bytes, tuple[int, int]] = {}
    current = None
    start = count = total = 0
    for row in rows:
        key = row[0]
        if key != current:
            if current is not None:
                if current in ranges:
                    raise ValueError("native records are not grouped by symbol")
                ranges[current] = (start, count)
            current, start, count = key, total, 0
        if len(row) == 3:
            _symbol, block, position = row
            output.extend(OCCURRENCE.pack(int(block), int(position)))
        else:
            _center, target, lane, observations = row
            output.extend(RELATION.pack(target, int(lane), int(observations)))
        count += 1
        total += 1
    if current is not None:
        ranges[current] = (start, count)
    return bytes(output), ranges, total


def publish_native_dataset(paths: DatasetPaths, source_files: list[Path], output_path: Path) -> dict[str, Any]:
    """Publish one verified copy; split artifacts remain the runtime authority."""

    lexicon = json.loads(paths.lexicon_path.read_text(encoding="utf-8"))
    anchor_rows = lexicon.get("anchors") or []
    counts = {symbol: count for symbol, count in _records(paths.anchor_counts_path, ANCHOR_RECORD)}
    occurrences, occurrence_ranges, occurrence_count = _ranges(_records(paths.block_anchor_path, block_anchor_record(paths)))
    relations, relation_ranges, relation_count = _ranges(_records(paths.relation_counts_path, RELATION_RECORD))

    strings = bytearray()
    string_ranges: dict[str, tuple[int, int]] = {}

    def add_string(value: str) -> tuple[int, int]:
        if value not in string_ranges:
            raw = value.encode()
            string_ranges[value] = (len(strings), len(raw))
            strings.extend(raw)
        return string_ranges[value]

    anchors = bytearray()
    for row in sorted(anchor_rows, key=lambda item: bytes.fromhex(str(item["symbol"])[2:])):
        symbol = bytes.fromhex(str(row["symbol"])[2:])
        offset, length = add_string(str(row["anchor"]))
        occurrence_start, occurrence_total = occurrence_ranges.get(symbol, (0, 0))
        relation_start, relation_total = relation_ranges.get(symbol, (0, 0))
        observed = int(counts.get(symbol, 0))
        if observed != int(row["observations"]):
            raise ValueError(f"anchor count mismatch: {row['anchor']}")
        anchors.extend(ANCHOR.pack(
            symbol, offset, length, observed, occurrence_start, occurrence_total,
            relation_start, relation_total, KIND.get(str(row.get("anchor_kind")), 6),
        ))

    source_files = sorted({Path(path).resolve() for path in source_files}, key=str)
    documents = bytearray()
    source_bytes = bytearray()
    for path in source_files:
        payload = path.read_bytes()
        name_offset, name_length = add_string(str(path))
        documents.extend(DOCUMENT.pack(
            name_offset, name_length, len(source_bytes), len(payload), hashlib.sha256(payload).digest()
        ))
        source_bytes.extend(payload)

    state = paths.state
    blocks = _rows(paths.blocks_path)
    temporal_nodes, temporal_edges, ambiguous_turn_count = _temporal_graph(paths.root.name, blocks)
    represented_inputs = {
        "dataset_manifest": paths.manifest_path,
        "dataset_lexicon": paths.lexicon_path,
        "anchor_counts": paths.anchor_counts_path,
        "block_anchor_postings": paths.block_anchor_path,
        "relation_counts": paths.relation_counts_path,
        "blocks": paths.blocks_path,
        "citations": paths.citations / "citations.jsonl",
        "coordinates": paths.coordinates / "coordinate_index.jsonl",
        "chat_metadata": paths.chat_metadata_path,
        "structure_graph": state / "structure_graph.awbin",
        "structure_manifest": state / "structure_manifest.json",
    }
    represented_inputs.update({f"source/{index:06d}": path for index, path in enumerate(source_files)})
    represented_legacy_bytes = sum(path.stat().st_size for path in represented_inputs.values())
    sections = {
        "strings": bytes(strings),
        "anchors": bytes(anchors),
        "occurrences": occurrences,
        "relations": relations,
        "documents": bytes(documents),
        "source_bytes": bytes(source_bytes),
        "metadata": _encoded({
            "dataset_manifest": json.loads(paths.manifest_path.read_text(encoding="utf-8")),
            "structure_manifest": json.loads((state / "structure_manifest.json").read_text(encoding="utf-8")),
            "publication_law": "verified copy only; split artifacts remain active runtime authority",
        }),
        "blocks": _encoded(blocks),
        "citations": _encoded(_rows(paths.citations / "citations.jsonl")),
        "coordinates": _encoded(_rows(paths.coordinates / "coordinate_index.jsonl")),
        "chat_metadata": _encoded(_rows(paths.chat_metadata_path)),
        "temporal_nodes": _encoded(temporal_nodes),
        "temporal_edges": _encoded(temporal_edges),
        "structure_graph": _encoded(read_structural_graph(state / "structure_graph.awbin")),
    }
    ordered = list(sections)
    offset = 0
    section_index = {}
    for name in ordered:
        payload = sections[name]
        section_index[name] = {
            "relative_offset": offset,
            "byte_length": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        offset += len(payload)
    header = {
        "schema": "truemem_native_dataset_container@1",
        "status": "EXPERIMENTAL_NONPRODUCTION",
        "dataset_id": paths.root.name,
        "intake_authority": "TrueVision.DocuFilm",
        "runtime_authority_format": "split",
        "native_query_backend_active": False,
        "source_authority_replaced": False,
        "anchor_count": len(anchor_rows),
        "occurrence_count": occurrence_count,
        "relation_record_count": relation_count,
        "temporal_node_count": len(temporal_nodes),
        "temporal_edge_count": len(temporal_edges),
        "ambiguous_temporal_turn_count": ambiguous_turn_count,
        "temporal_edge_relation": "NEXT_TURN",
        "temporal_edge_authority": "explicit metadata only; no cross-conversation or semantic inference",
        "source_document_count": len(source_files),
        "source_bytes": len(source_bytes),
        "record_bytes": {
            "anchor": ANCHOR.size, "occurrence": OCCURRENCE.size,
            "relation": RELATION.size, "document": DOCUMENT.size,
        },
        "represented_input_sha256": {name: _sha256(path) for name, path in represented_inputs.items()},
        "represented_legacy_bytes": represented_legacy_bytes,
        "sections": section_index,
    }
    header_raw = _canonical(header)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("wb") as output:
            output.write(PREFIX.pack(MAGIC, len(header_raw)))
            output.write(header_raw)
            for name in ordered:
                output.write(sections[name])
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    verification = verify_native_dataset(output_path)
    native_bytes = output_path.stat().st_size
    return {
        "schema": "truemem_native_publication_receipt@1",
        "status": "completed",
        "verification_status": "verified_success",
        "path": str(output_path),
        "bytes": native_bytes,
        "sha256": _sha256(output_path),
        "runtime_authority_format": "split",
        "native_query_backend_active": False,
        "source_authority_replaced": False,
        "verified_source_documents": verification["verified_source_documents"],
        "temporal_node_count": len(temporal_nodes),
        "temporal_edge_count": len(temporal_edges),
        "ambiguous_temporal_turn_count": ambiguous_turn_count,
        "section_count": len(section_index),
        "represented_legacy_bytes": represented_legacy_bytes,
        "reduction_bytes": represented_legacy_bytes - native_bytes,
        "reduction_percent": (represented_legacy_bytes - native_bytes) / represented_legacy_bytes * 100,
    }


def verify_native_dataset(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
        magic, header_length = PREFIX.unpack_from(mapped)
        if magic != MAGIC:
            raise ValueError("invalid TrueMem native container magic")
        payload_start = PREFIX.size + header_length
        header = json.loads(mapped[PREFIX.size:payload_start])
        if header.get("schema") != "truemem_native_dataset_container@1":
            raise ValueError("unsupported TrueMem native container schema")
        expected_offset = 0
        for name, row in sorted(header["sections"].items(), key=lambda item: int(item[1]["relative_offset"])):
            if int(row["relative_offset"]) != expected_offset:
                raise ValueError(f"non-contiguous native section: {name}")
            start = payload_start + expected_offset
            end = start + int(row["byte_length"])
            if hashlib.sha256(mapped[start:end]).hexdigest() != row["sha256"]:
                raise ValueError(f"native section integrity failure: {name}")
            expected_offset += int(row["byte_length"])
        if payload_start + expected_offset != len(mapped):
            raise ValueError("native container trailing or missing bytes")
        documents_row = header["sections"]["documents"]
        sources_row = header["sections"]["source_bytes"]
        documents_start = payload_start + int(documents_row["relative_offset"])
        sources_start = payload_start + int(sources_row["relative_offset"])
        for index in range(int(header["source_document_count"])):
            values = DOCUMENT.unpack_from(mapped, documents_start + index * DOCUMENT.size)
            _name_offset, _name_length, offset, length, expected_digest = values
            source = mapped[sources_start + offset:sources_start + offset + length]
            if hashlib.sha256(source).digest() != expected_digest:
                raise ValueError("native source reconstruction failure")
    return {
        "schema": "truemem_native_dataset_verification@1",
        "status": "PASS",
        "verification_status": "verified_success",
        "verified_source_documents": int(header["source_document_count"]),
    }
