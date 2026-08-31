"""Compact sectioned storage for TrueVision-compiled structural records."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

MAGIC = b"TVSB2\x00"
HEADER = struct.Struct(">6sII")
LENGTH = struct.Struct(">I")


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_structural_graph(paths: Any, compilations: list[dict[str, Any]], symbol_map: dict[str, str]) -> dict[str, Any]:
    structures = []
    relations = []
    parent_objects = []
    for compilation in sorted(compilations, key=lambda row: int(row["block_ordinal"])):
        parent_objects.append({
            "parent_object_id": compilation["parent_object_id"],
            "block_ordinal": int(compilation["block_ordinal"]),
            "source_identity": compilation["source_identity"],
            "native_identity_byte_start": int(compilation["native_identity_byte_start"]),
            "native_identity_byte_end": int(compilation["native_identity_byte_end"]),
        })
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
                "semantic_subtype": row.get("semantic_subtype"),
                "status": row["status"],
                "occurrence_id": row["occurrence_id"],
                "parent_object_id": row["parent_object_id"],
                "inside_native_identity_region": bool(row["inside_native_identity_region"]),
                "exact_text_sha256": row["exact_text_sha256"],
                "child_symbols": [symbol_map[child["anchor"]] for child in row["children"]],
                "punctuation_count_bearing": False,
            })
        for row in compilation["relations"]:
            relations.append({
                "subject_symbol": symbol_map[row["subject_structure_key"]],
                "relation_symbol": symbol_map[row["relation_structure_key"]],
                "object_symbol": symbol_map[row["object_structure_key"]],
                "subject_occurrence_id": row["subject_occurrence_id"],
                "relation_occurrence_id": row["relation_occurrence_id"],
                "object_occurrence_id": row["object_occurrence_id"],
                "parent_object_id": row["parent_object_id"],
                "block_ordinal": int(row["block_ordinal"]),
                "sentence_ordinal": int(row["sentence_ordinal"]),
                "byte_start": int(row["byte_start"]),
                "byte_end": int(row["byte_end"]),
                "direction": row["direction"],
                "status": row["status"],
                "subject_binding_kind": row.get("subject_binding_kind", "EXACT_OCCURRENCE"),
                "explicit_alias": bool(row.get("explicit_alias", False)),
                "relation_id": row["relation_id"],
            })
    structures.sort(key=lambda row: (row["symbol"], row["block_ordinal"], row["byte_start"], row["occurrence_id"]))
    relations.sort(key=lambda row: (row["subject_symbol"], row["relation_symbol"], row["object_symbol"], row["block_ordinal"], row["relation_id"]))
    parent_objects.sort(key=lambda row: (row["block_ordinal"], row["parent_object_id"]))
    native_parents: dict[str, set[str]] = {}
    for row in structures:
        if row["inside_native_identity_region"] and row["kind"] in {"NAMED_STRUCTURE", "NATIVE_IDENTITY_REGION"}:
            native_parents.setdefault(row["symbol"], set()).add(row["parent_object_id"])
    reference_bindings = []
    for row in structures:
        if row["inside_native_identity_region"] or row["kind"] != "NAMED_STRUCTURE":
            continue
        candidates = sorted(native_parents.get(row["symbol"], set()))
        if not candidates:
            status = "NO_PARENT_IDENTITY"
        elif len(candidates) == 1:
            status = "VERIFIED_EXACT_PARENT_IDENTITY"
        else:
            status = "AMBIGUOUS_PARENT_IDENTITY"
        binding_basis = {
            "mention_occurrence_id": row["occurrence_id"],
            "candidate_parent_object_ids": candidates,
            "binding_kind": "EXACT_COMPLETE_STRUCTURE",
            "binding_status": status,
            "source_parent_object_id": row["parent_object_id"],
            "block_ordinal": row["block_ordinal"],
        }
        reference_bindings.append({**binding_basis, "binding_id": hashlib.sha256(_canonical(binding_basis)).hexdigest()})
    reference_bindings.sort(key=lambda row: (row["mention_occurrence_id"], row["binding_id"]))
    artifact = paths.state / "structure_graph.awbin"
    envelope = {
        "schema": "truemem_structural_graph@2",
        "structures": structures,
        "relations": relations,
        "parent_objects": parent_objects,
        "reference_bindings": reference_bindings,
    }
    envelope_raw = _canonical(envelope)
    payload = bytearray(HEADER.pack(MAGIC, 1, 0))
    payload.extend(LENGTH.pack(len(envelope_raw)))
    payload.extend(envelope_raw)
    artifact.write_bytes(bytes(payload))
    base_size = sum(path.stat().st_size for path in (paths.anchor_counts_path, paths.relation_counts_path, paths.block_anchor_path, paths.blocks_path, paths.lexicon_path) if path.exists())
    manifest = {
        "schema": "truemem_structural_graph_manifest@2",
        "compiler_authority": "TrueVision.DocuFilm",
        "artifact": str(artifact),
        "artifact_bytes": len(payload),
        "artifact_sha256": hashlib.sha256(payload).hexdigest(),
        "structure_records": len(structures),
        "relation_records": len(relations),
        "parent_object_records": len(parent_objects),
        "reference_binding_records": len(reference_bindings),
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
    if structure_count != 1 or relation_count != 0:
        raise ValueError("INVALID_STRUCTURAL_GRAPH_V2_ENVELOPE")
    cursor = HEADER.size
    records = []
    for _ in range(structure_count + relation_count):
        size = LENGTH.unpack(raw[cursor:cursor + LENGTH.size])[0]
        cursor += LENGTH.size
        records.append(json.loads(raw[cursor:cursor + size]))
        cursor += size
    if cursor != len(raw):
        raise ValueError("INVALID_STRUCTURAL_GRAPH_TRAILING_BYTES")
    envelope = records[0]
    if envelope.get("schema") != "truemem_structural_graph@2":
        raise ValueError("INVALID_STRUCTURAL_GRAPH_SCHEMA")
    return envelope


def verify_structural_graph(paths: Any) -> dict[str, Any]:
    graph_path = paths.state / "structure_graph.awbin"
    manifest_path = paths.state / "structure_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = graph_path.read_bytes()
    graph = read_structural_graph(graph_path)
    blocks = {}
    for line in paths.blocks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            blocks[int(row["block_ordinal"])] = row
    lexicon = json.loads(paths.lexicon_path.read_text(encoding="utf-8"))
    symbols = {str(row["symbol"]) for row in lexicon["anchors"]}
    failures = []
    for row in graph["structures"]:
        block = blocks.get(int(row["block_ordinal"]))
        if block is None:
            failures.append("MISSING_BLOCK")
            continue
        source = str(block["text"]).encode("utf-8")
        exact = source[int(row["byte_start"]):int(row["byte_end"])]
        if hashlib.sha256(exact).hexdigest() != row["exact_text_sha256"]:
            failures.append("SOURCE_SPAN_HASH_MISMATCH")
        if row["symbol"] not in symbols or any(value not in symbols for value in row["child_symbols"]):
            failures.append("UNRESOLVED_SYMBOL")
    occurrence_rows = {row["occurrence_id"]: row for row in graph["structures"]}
    structure_symbols = {row["symbol"] for row in graph["structures"]}
    for row in graph["relations"]:
        if any(row[key] not in structure_symbols for key in ("subject_symbol", "relation_symbol", "object_symbol")):
            failures.append("UNRESOLVED_RELATION_ENDPOINT")
        endpoint_ids = (row["subject_occurrence_id"], row["relation_occurrence_id"], row["object_occurrence_id"])
        if any(value not in occurrence_rows for value in endpoint_ids):
            failures.append("UNRESOLVED_RELATION_OCCURRENCE")
            continue
        endpoints = [occurrence_rows[value] for value in endpoint_ids]
        if any(int(value["block_ordinal"]) != int(row["block_ordinal"]) for value in endpoints):
            failures.append("RELATION_OCCURRENCE_CONTEXT_MISMATCH")
        if endpoints[0]["symbol"] != row["subject_symbol"] or endpoints[1]["symbol"] != row["relation_symbol"] or endpoints[2]["symbol"] != row["object_symbol"]:
            failures.append("RELATION_OCCURRENCE_SYMBOL_MISMATCH")
    parent_ids = {row["parent_object_id"] for row in graph["parent_objects"]}
    for row in graph["reference_bindings"]:
        if row["mention_occurrence_id"] not in occurrence_rows:
            failures.append("UNRESOLVED_REFERENCE_MENTION")
        if any(value not in parent_ids for value in row["candidate_parent_object_ids"]):
            failures.append("UNRESOLVED_REFERENCE_PARENT")
    if hashlib.sha256(raw).hexdigest() != manifest["artifact_sha256"]:
        failures.append("ARTIFACT_HASH_MISMATCH")
    return {
        "schema": "truemem_structural_graph_verification@2",
        "status": "PASS" if not failures else "FAIL",
        "structure_records": len(graph["structures"]),
        "relation_records": len(graph["relations"]),
        "parent_object_records": len(graph["parent_objects"]),
        "reference_binding_records": len(graph["reference_bindings"]),
        "failures": sorted(set(failures)),
        "all_source_spans_reconstructed": "SOURCE_SPAN_HASH_MISMATCH" not in failures,
        "all_symbols_resolved": not any("UNRESOLVED" in value for value in failures),
        "all_relation_occurrences_reconstructed": not any(value.startswith("RELATION_OCCURRENCE") or value == "UNRESOLVED_RELATION_OCCURRENCE" for value in failures),
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
    }
