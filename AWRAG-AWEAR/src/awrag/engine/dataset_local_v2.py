"""Versioned dataset-local four-byte AWEAR symbol format.

This module is intentionally additive.  The older ``awrag_dataset_6b@1``
readers and artifacts remain untouched legacy authority.  Values in this
format have meaning only inside the dataset identified by the manifest.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from typing import Iterable

FORMAT_SCHEMA = "awear_dataset_local_u32@1"
MANIFEST_SCHEMA = "awear_dataset_manifest@2"
LEXICON_SCHEMA = "awear_dataset_lexicon@2"
COUNT_BACKEND = "awear_dataset_local_u32_counts@1"
SYMBOL_SYSTEM = "awear_dataset_local_sequential_u32@1"
SYMBOL_BYTES = 4
SYMBOL_MIN = 1
SYMBOL_MAX = (1 << 32) - 1
LEGACY_FORMATS = ("awrag_dataset_6b@1", "workspace_monotonic_integer_6b", "deterministic_anchor_hash_6b")

ANCHOR_RECORD = struct.Struct(">4sQ")
RELATION_RECORD = struct.Struct(">4s4shI")
BLOCK_ANCHOR_RECORD = struct.Struct(">4sIH")


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def symbol_hex(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or not SYMBOL_MIN <= value <= SYMBOL_MAX:
        raise ValueError("DATASET_LOCAL_U32_SYMBOL_OUT_OF_RANGE")
    return "0x" + value.to_bytes(SYMBOL_BYTES, "big").hex().upper()


def symbol_raw(value: int) -> bytes:
    return bytes.fromhex(symbol_hex(value)[2:])


def allocate_dataset_local_symbols(anchors: Counter[str]) -> dict:
    """Assign stable local IDs from one dataset's sorted frozen lexicon."""
    ordered = sorted(str(anchor) for anchor in anchors)
    if len(ordered) > SYMBOL_MAX:
        raise OverflowError("DATASET_LOCAL_U32_NAMESPACE_EXHAUSTED")
    mapping = {anchor: index for index, anchor in enumerate(ordered, start=SYMBOL_MIN)}
    body = {
        "schema": LEXICON_SCHEMA,
        "format": FORMAT_SCHEMA,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "symbol_scope": "dataset_local",
        "symbol_assignment": "sorted_frozen_lexicon_sequential_u32",
        "legacy_symbol_compatibility": "NONE_VALUES_MUST_NOT_BE_COMPARED",
        "anchors": [
            {"anchor": anchor, "local_symbol": mapping[anchor], "symbol": symbol_hex(mapping[anchor]), "observations": int(anchors[anchor])}
            for anchor in ordered
        ],
    }
    return {"mapping": mapping, "lexicon": body, "lexicon_identity": sha256_bytes(canonical_bytes(body))}


def encode_counts(
    mapping: dict[str, int],
    anchors: Counter[str],
    relations: Counter[tuple[str, str, int]],
    block_anchors: Iterable[tuple[str, int, int]],
) -> dict[str, bytes]:
    anchor_bytes = bytearray()
    for anchor, observations in sorted(anchors.items()):
        anchor_bytes.extend(ANCHOR_RECORD.pack(symbol_raw(mapping[anchor]), int(observations)))
    relation_bytes = bytearray()
    for (center, neighbor, offset), observations in sorted(relations.items()):
        if offset == 0 or not -6 <= int(offset) <= 6:
            raise ValueError("INVALID_SIGNED_6_1_6_OFFSET")
        relation_bytes.extend(RELATION_RECORD.pack(symbol_raw(mapping[center]), symbol_raw(mapping[neighbor]), int(offset), int(observations)))
    posting_bytes = bytearray()
    ordered = sorted(block_anchors, key=lambda row: (mapping[row[0]], int(row[1]), int(row[2])))
    for anchor, block_ordinal, position in ordered:
        posting_bytes.extend(BLOCK_ANCHOR_RECORD.pack(symbol_raw(mapping[anchor]), int(block_ordinal), int(position)))
    return {"anchor_counts.awbin": bytes(anchor_bytes), "relation_counts.awbin": bytes(relation_bytes), "block_anchor_postings.awbin": bytes(posting_bytes)}


def iter_anchor_records(raw: bytes):
    if len(raw) % ANCHOR_RECORD.size:
        raise ValueError("INVALID_U32_ANCHOR_COUNT_BYTES")
    for offset in range(0, len(raw), ANCHOR_RECORD.size):
        symbol, count = ANCHOR_RECORD.unpack(raw[offset:offset + ANCHOR_RECORD.size])
        yield int.from_bytes(symbol, "big"), int(count)


def iter_relation_records(raw: bytes):
    if len(raw) % RELATION_RECORD.size:
        raise ValueError("INVALID_U32_RELATION_COUNT_BYTES")
    for offset in range(0, len(raw), RELATION_RECORD.size):
        center, neighbor, signed_offset, count = RELATION_RECORD.unpack(raw[offset:offset + RELATION_RECORD.size])
        yield int.from_bytes(center, "big"), int.from_bytes(neighbor, "big"), int(signed_offset), int(count)


def validate_resolution(lexicon: dict, artifacts: dict[str, bytes]) -> dict:
    symbol_to_anchor = {int(row["local_symbol"]): row["anchor"] for row in lexicon["anchors"]}
    unresolved = []
    anchor_rows = list(iter_anchor_records(artifacts["anchor_counts.awbin"]))
    relation_rows = list(iter_relation_records(artifacts["relation_counts.awbin"]))
    for symbol, _count in anchor_rows:
        if symbol not in symbol_to_anchor:
            unresolved.append(symbol)
    for center, neighbor, _offset, _count in relation_rows:
        if center not in symbol_to_anchor:
            unresolved.append(center)
        if neighbor not in symbol_to_anchor:
            unresolved.append(neighbor)
    return {
        "schema": "awear_dataset_local_u32_validation@1",
        "status": "PASS" if not unresolved else "FAIL",
        "symbol_bytes": SYMBOL_BYTES,
        "anchor_records": len(anchor_rows),
        "relation_records": len(relation_rows),
        "unresolved_symbols": sorted(set(unresolved)),
        "legacy_values_compared": False,
    }


def write_frozen_dataset(root: str | Path, dataset_id: str, anchors: Counter[str], relations: Counter, block_anchors: list, source_identity: dict) -> dict:
    target = Path(root).resolve()
    target.mkdir(parents=True, exist_ok=False)
    allocation = allocate_dataset_local_symbols(anchors)
    artifacts = encode_counts(allocation["mapping"], anchors, relations, block_anchors)
    lexicon = {**allocation["lexicon"], "dataset_id": dataset_id, "dataset_identity_pending_manifest": True}
    (target / "dataset_lexicon.json").write_bytes(canonical_bytes(lexicon))
    for name, raw in artifacts.items():
        (target / name).write_bytes(raw)
    validation = validate_resolution(lexicon, artifacts)
    manifest_body = {
        "schema": MANIFEST_SCHEMA,
        "dataset_id": dataset_id,
        "format": FORMAT_SCHEMA,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "symbol_scope": "dataset_local",
        "symbol_transferable": False,
        "symbol_assignment": "sorted_frozen_lexicon_sequential_u32",
        "count_backend": COUNT_BACKEND,
        "signed_location_offsets": [-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6],
        "source_authority": source_identity,
        "legacy_formats_preserved": list(LEGACY_FORMATS),
        "artifacts": {name: {"bytes": len(raw), "sha256": sha256_bytes(raw)} for name, raw in sorted(artifacts.items())},
        "lexicon_sha256": sha256_bytes((target / "dataset_lexicon.json").read_bytes()),
        "validation": validation,
    }
    manifest = {**manifest_body, "dataset_identity": sha256_bytes(canonical_bytes(manifest_body))}
    (target / "dataset_manifest.json").write_bytes(canonical_bytes(manifest))
    return manifest
