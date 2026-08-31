"""Compact sectioned storage for TrueVision-compiled structural records."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

MAGIC = b"TVSB1\x00"
HEADER = struct.Struct(">6sII")
LENGTH = struct.Struct(">I")


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_structural_graph(paths: Any, compilations: list[dict[str, Any]], symbol_map: dict[str, str]) -> dict[str, Any]:
    structures = []
    relations = []
    for compilation in sorted(compilations, key=lambda row: int(row["block_ordinal"])):
        for row in compilation["structures"]:
            structures.append({
                "symbol": symbol_map[row["structure_key"]],
                "block_ordinal": int(row["block_ordinal"]),
                "sentence_ordinal": int(row["sentence_ordinal"]),
                "anchor_start": int(row["anchor_start"]),
                "anchor_count": int(row["anchor_count"]),
                "byte_start": int(row["byte_start"]),
                "byte_end": int(row["byte_end"]),
                "kind": row["kind"],
                "status": row["status"],
                "occurrence_id": row["occurrence_id"],
                "exact_text_sha256": row["exact_text_sha256"],
                "child_symbols": [symbol_map[child["anchor"]] for child in row["children"]],
                "punctuation_count_bearing": False,
            })
        for row in compilation["relations"]:
            relations.append({
                "subject_symbol": symbol_map[row["subject_structure_key"]],
                "relation_symbol": symbol_map[row["relation_structure_key"]],
                "object_symbol": symbol_map[row["object_structure_key"]],
                "block_ordinal": int(row["block_ordinal"]),
                "sentence_ordinal": int(row["sentence_ordinal"]),
                "byte_start": int(row["byte_start"]),
                "byte_end": int(row["byte_end"]),
                "direction": row["direction"],
                "status": row["status"],
                "relation_id": row["relation_id"],
            })
    structures.sort(key=lambda row: (row["symbol"], row["block_ordinal"], row["byte_start"], row["occurrence_id"]))
    relations.sort(key=lambda row: (row["subject_symbol"], row["relation_symbol"], row["object_symbol"], row["block_ordinal"], row["relation_id"]))
    artifact = paths.state / "structure_graph.awbin"
    payload = bytearray(HEADER.pack(MAGIC, len(structures), len(relations)))
    for row in structures + relations:
        raw = _canonical(row)
        payload.extend(LENGTH.pack(len(raw)))
        payload.extend(raw)
    artifact.write_bytes(bytes(payload))
    base_size = sum(path.stat().st_size for path in (paths.anchor_counts_path, paths.relation_counts_path, paths.block_anchor_path, paths.blocks_path, paths.lexicon_path) if path.exists())
    manifest = {
        "schema": "truemem_structural_graph_manifest@1",
        "compiler_authority": "TrueVision.DocuFilm",
        "artifact": str(artifact),
        "artifact_bytes": len(payload),
        "artifact_sha256": hashlib.sha256(payload).hexdigest(),
        "structure_records": len(structures),
        "relation_records": len(relations),
        "source_text_duplicated": False,
        "punctuation_count_bearing": False,
        "base_artifact_bytes": base_size,
        "expansion_ratio": (len(payload) / base_size) if base_size else None,
    }
    (paths.state / "structure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


def read_structural_graph(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    raw = Path(path).read_bytes()
    magic, structure_count, relation_count = HEADER.unpack(raw[:HEADER.size])
    if magic != MAGIC:
        raise ValueError("INVALID_STRUCTURAL_GRAPH_MAGIC")
    cursor = HEADER.size
    records = []
    for _ in range(structure_count + relation_count):
        size = LENGTH.unpack(raw[cursor:cursor + LENGTH.size])[0]
        cursor += LENGTH.size
        records.append(json.loads(raw[cursor:cursor + size]))
        cursor += size
    if cursor != len(raw):
        raise ValueError("INVALID_STRUCTURAL_GRAPH_TRAILING_BYTES")
    return {"structures": records[:structure_count], "relations": records[structure_count:]}
