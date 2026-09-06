from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from .base import safe_id, utc_now, with_protected_notice
from .evidence_need import AnchorGroup, EvidenceNeed
from .storage import dataset_paths, index_readiness, read_block_anchor_rows, read_blocks, read_symbol_to_anchor


def query_evidence_need(
    runtime_root: str | Path,
    dataset_id: str,
    evidence_need: EvidenceNeed,
) -> dict[str, Any]:
    """Return exact occurrences and 6-1-6 clouds without ranking or answering."""

    if not isinstance(evidence_need, EvidenceNeed):
        raise TypeError("STRUCTURED_EVIDENCE_NEED_REQUIRED; raw questions cannot enter retrieval")
    paths = dataset_paths(runtime_root, dataset_id)
    readiness = index_readiness(runtime_root, dataset_id)
    if not readiness["query_allowed"]:
        reason = ", ".join(readiness.get("reasons") or ["index_not_ready"])
        raise RuntimeError(f"INDEX_NOT_READY: query_allowed=false; {reason}")

    blocks = read_blocks(paths)
    symbol_to_anchor = read_symbol_to_anchor(paths)
    tokens_by_block: dict[int, dict[int, str]] = defaultdict(dict)
    occurrences: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for symbol, block_ordinal, position in read_block_anchor_rows(paths):
        anchor = symbol_to_anchor["0x" + symbol.hex().upper()]
        tokens_by_block[block_ordinal][position] = anchor
        occurrences[anchor].append((block_ordinal, position))

    group_blocks = {group.field: _blocks_for_group(group, occurrences) for group in evidence_need.groups()}
    required_groups = evidence_need.required_groups()
    full_blocks = set.intersection(*(set(group_blocks[group.field]) for group in required_groups))
    non_subject_groups = tuple(group for group in required_groups if group.field != evidence_need.subject.field)
    target_blocks = set.intersection(*(_blocks_for_group(group, occurrences) for group in non_subject_groups))

    subject_occurrences = []
    subject_cloud_anchors: set[str] = set()
    for anchor in evidence_need.subject.anchors:
        for block_ordinal, position in occurrences.get(anchor, []):
            local = _cloud(tokens_by_block[block_ordinal], position)
            subject_cloud_anchors.update(str(row["anchor"]) for row in local)
            subject_occurrences.append(_location(blocks[block_ordinal], block_ordinal, anchor, position, local))

    proof_locations = [_block_location(blocks[ordinal], ordinal) for ordinal in sorted(full_blocks)]
    partial_locations = []
    for ordinal in sorted(target_blocks - full_blocks):
        block_anchors = set(tokens_by_block[ordinal].values())
        partial_locations.append({
            **_block_location(blocks[ordinal], ordinal),
            "missing_fields": [evidence_need.subject.field],
            "shared_subject_cloud_anchors": sorted(subject_cloud_anchors & block_anchors),
        })

    return with_protected_notice({
        "schema": "truemem_evidence_need_result@1",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "evidence_need": evidence_need.to_dict(),
        "method": {
            "subject_lookup": "all exact admitted anchor occurrences",
            "occurrence_cloud": "signed -6..-1 and +1..+6",
            "proof_selection": "set intersection of required anchor groups",
            "ranking": "none",
            "top_k": "not accepted",
            "answer_generation": False,
        },
        "group_block_counts": {field: len(values) for field, values in group_blocks.items()},
        "subject_occurrences": subject_occurrences,
        "proof_locations": proof_locations,
        "partial_target_locations": partial_locations,
        "evidence_status": "COMPLETE_EVIDENCE" if proof_locations else (
            "PARTIAL_EVIDENCE" if partial_locations or subject_occurrences else "NO_EVIDENCE"
        ),
        "proof_boundary": "Only proof_locations satisfy every required field in one witnessed source block.",
        "model_used": "none",
    })


def query_evidence_need_mapping(
    runtime_root: str | Path,
    dataset_id: str,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    return query_evidence_need(runtime_root, dataset_id, EvidenceNeed.from_mapping(value))


def _blocks_for_group(group: AnchorGroup, occurrences: Mapping[str, list[tuple[int, int]]]) -> set[int]:
    return {block for anchor in group.anchors for block, _ in occurrences.get(anchor, [])}


def _cloud(tokens: Mapping[int, str], position: int) -> list[dict[str, Any]]:
    return [
        {"offset": candidate - position, "position": candidate, "anchor": tokens[candidate]}
        for candidate in range(position - 6, position + 7)
        if candidate != position and candidate in tokens
    ]


def _location(block: Mapping[str, Any], ordinal: int, anchor: str, position: int,
              cloud: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        **_block_location(block, ordinal),
        "anchor": anchor,
        "position": position,
        "cloud": cloud,
    }


def _block_location(block: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    return {
        "block_ordinal": ordinal,
        "block_id": block.get("block_id"),
        "file_path": block.get("file_path"),
        "line_start": block.get("line_start"),
        "line_end": block.get("line_end"),
        "citation_id": block.get("citation_id"),
        "citation": block.get("marker"),
        "text": block.get("text"),
        "text_hash": block.get("text_hash"),
    }
