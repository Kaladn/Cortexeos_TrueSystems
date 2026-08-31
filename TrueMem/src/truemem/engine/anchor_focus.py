"""Lexicon-first question focus over the unchanged admitted anchor map."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .anchors import anchor_kind, anchorize
from .storage import DatasetPaths, read_anchor_to_symbol, read_block_anchor_rows, read_blocks

GROUP_END_MARKS = frozenset({
    "boundary:sentence:period", "boundary:sentence:question", "boundary:sentence:exclamation",
})
PARENT_FORMAT_PREFIXES = frozenset({"boundary:heading-or-reference:hash"})


def build_anchor_focus(
    paths: DatasetPaths, question: str, *,
    block_anchor_rows: list[tuple[bytes, int, int]] | None = None,
    blocks: dict[int, dict[str, Any]] | None = None,
    prepared_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Receipt every query anchor; search content anchors independently first."""
    anchors = anchorize(question)
    index = prepared_index or prepare_anchor_focus_index(
        paths, block_anchor_rows=block_anchor_rows, blocks=blocks,
    )
    lexicon_hex = index["lexicon_hex"]
    lexicon = index["lexicon"]
    postings = index["postings"]
    case_index: dict[str, list[str]] = defaultdict(list)
    for admitted_anchor in lexicon:
        case_index[admitted_anchor.casefold()].append(admitted_anchor)

    recognized = []
    solo = []
    for ordinal, anchor in enumerate(anchors):
        exact = anchor in lexicon
        resolved_anchors = [anchor] if exact else sorted(case_index.get(anchor.casefold(), []))
        kind = anchor_kind(anchor)
        row = {
            "ordinal": ordinal, "anchor": anchor, "anchor_kind": kind,
            "recognized": bool(resolved_anchors),
            "recognition": "exact" if exact else ("verified_case_variant" if resolved_anchors else "absent"),
            "resolved_admitted_anchors": resolved_anchors,
            "symbols": [lexicon_hex[value] for value in resolved_anchors],
            # Relation/glue/boundary anchors shape groups; they do not spend an
            # independent corpus-wide focus search.
            "standalone_focus_eligible": kind == "content",
        }
        recognized.append(row)
        if kind == "content":
            for admitted_anchor in resolved_anchors:
                symbol = lexicon[admitted_anchor]
                anchor_blocks = postings.get(symbol, {})
                solo.append({
                    **row, "query_anchor": anchor, "anchor": admitted_anchor,
                    "symbol": lexicon_hex[admitted_anchor],
                    "posting_count": sum(len(values) for values in anchor_blocks.values()),
                    "block_count": len(anchor_blocks),
                    "block_ordinals": sorted(anchor_blocks),
                })

    groups = _groups(anchors, lexicon, postings, index["title_index"])
    occurrence_areas = _occurrence_focus_areas(solo)
    seeds = sorted({
        block for group in groups
        for block in (group["parent_identity_block_ordinals"] or group["exact_sequence_block_ordinals"])
    } | {int(area["block_ordinal"]) for area in occurrence_areas})
    return {
        "schema": "truemem_lexicon_anchor_focus@1",
        "question": question,
        "question_anchors": recognized,
        "standalone_searches": solo,
        "focus_groups": groups,
        "occurrence_focus_areas": occurrence_areas,
        "seed_block_ordinals": seeds,
        "laws": {
            "admitted_map_changed": False,
            "every_question_anchor_receipted": True,
            "low_consequence_anchors_suppressed_only_as_standalone_focus": True,
            "glue_preserved_inside_exact_structure": True,
            "punctuation_preserved_as_symbolic_boundary": True,
            "case_preserved_and_variants_explicit": True,
            "ranking_performed": False,
            "model_used": False,
        },
    }


def _occurrence_focus_areas(solo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose exact focus blocks without weighted ranking or semantic guesses."""
    memberships: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for search in solo:
        for block in search["block_ordinals"]:
            memberships[int(block)].append(search)
    out = []
    for block in sorted(memberships):
        members = memberships[block]
        distinct = sorted({str(row["anchor"]) for row in members})
        unique = sorted({str(row["anchor"]) for row in members if int(row["block_count"]) == 1})
        reasons = []
        if len(distinct) >= 2:
            reasons.append("multiple_independent_anchor_intersection")
        if unique:
            reasons.append("dataset_unique_anchor_occurrence")
        if reasons:
            out.append({"block_ordinal": block, "matched_anchors": distinct, "dataset_unique_anchors": unique, "reasons": reasons})
    return out


def prepare_anchor_focus_index(
    paths: DatasetPaths, *,
    block_anchor_rows: list[tuple[bytes, int, int]] | None = None,
    blocks: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prepare immutable reusable lexicon/posting/title structures."""
    lexicon_hex = read_anchor_to_symbol(paths)
    lexicon = {anchor: bytes.fromhex(symbol[2:]) for anchor, symbol in lexicon_hex.items()}
    postings: dict[bytes, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    rows = block_anchor_rows if block_anchor_rows is not None else read_block_anchor_rows(paths)
    for symbol, block_id, position in rows:
        postings[symbol][block_id].append(position)
    admitted_blocks = blocks if blocks is not None else read_blocks(paths)
    title_index: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for block, payload in admitted_blocks.items():
        lines = str(payload.get("text", "")).splitlines()
        title = anchorize(lines[0]) if lines else []
        title_begin, title_end = _trim(title, 0, len(title))
        if title_begin < title_end:
            title_index[tuple(title[title_begin:title_end])].append(block)
    return {"lexicon_hex": lexicon_hex, "lexicon": lexicon, "postings": postings, "title_index": title_index}


def _groups(anchors: list[str], lexicon: dict[str, bytes], postings: dict[bytes, dict[int, list[int]]], title_index: dict[tuple[str, ...], list[int]]) -> list[dict[str, Any]]:
    """Find maximal exact parent identities without question-specific templates."""
    candidates = []
    for begin in range(len(anchors)):
        for end in range(begin + 1, len(anchors) + 1):
            values = tuple(anchors[begin:end])
            matched = title_index.get(values)
            if matched:
                candidates.append((begin, end, values, sorted(matched)))
    candidates.sort(key=lambda row: (-(row[1] - row[0]), row[0], row[1], row[2]))

    occupied: set[int] = set()
    selected = []
    for begin, end, values, parent_identity in candidates:
        if any(position in occupied for position in range(begin, end)):
            continue
        occupied.update(range(begin, end))
        selected.append((begin, end, values, parent_identity))

    out = []
    for begin, end, values_tuple, parent_identity in sorted(selected):
        values = list(values_tuple)
        exact = _exact_blocks(values, lexicon, postings)
        out.append({
            "group_id": f"focus-{begin}-{end}-exact-parent-identity", "kind": "exact-parent-identity",
            "start_ordinal": begin, "end_ordinal_exclusive": end,
            "anchors": values,
            "recognized": all(value in lexicon for value in values),
            "exact_sequence_block_ordinals": exact,
            "parent_identity_block_ordinals": parent_identity,
        })
    return out


def _exact_blocks(values: list[str], lexicon: dict[str, bytes], postings: dict[bytes, dict[int, list[int]]]) -> list[int]:
    symbols = [lexicon.get(value) for value in values]
    if not values or any(symbol is None for symbol in symbols):
        return []
    candidates = set(postings[symbols[0]])
    for symbol in symbols[1:]:
        candidates &= set(postings[symbol])
    return [block for block in sorted(candidates) if _consecutive(block, symbols, postings)]


def _consecutive(block: int, symbols: list[bytes], postings: dict[bytes, dict[int, list[int]]]) -> bool:
    positions = [set(postings[symbol][block]) for symbol in symbols]
    return any(all(start + offset in positions[offset] for offset in range(len(symbols))) for start in positions[0])


def _trim(anchors: list[str], begin: int, end: int) -> tuple[int, int]:
    while begin < end and anchors[begin] in PARENT_FORMAT_PREFIXES:
        begin += 1
    while begin < end and anchors[end - 1] in GROUP_END_MARKS:
        end -= 1
    return begin, end
