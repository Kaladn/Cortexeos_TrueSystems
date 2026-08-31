"""Lexicon-first question focus over the unchanged admitted anchor map."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .anchors import anchor_kind, anchorize
from .storage import DatasetPaths, read_anchor_to_symbol, read_block_anchor_rows, read_blocks

GROUP_END_MARKS = frozenset({
    "boundary:sentence:period", "boundary:sentence:question", "boundary:sentence:exclamation",
})


def build_anchor_focus(
    paths: DatasetPaths, question: str, *,
    block_anchor_rows: list[tuple[bytes, int, int]] | None = None,
    blocks: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Receipt every query anchor; search content anchors independently first."""
    anchors = anchorize(question)
    lexicon_hex = read_anchor_to_symbol(paths)
    lexicon = {anchor: bytes.fromhex(symbol[2:]) for anchor, symbol in lexicon_hex.items()}
    postings: dict[bytes, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    rows = block_anchor_rows if block_anchor_rows is not None else read_block_anchor_rows(paths)
    for symbol, block_id, position in rows:
        postings[symbol][block_id].append(position)

    recognized = []
    solo = []
    for ordinal, anchor in enumerate(anchors):
        symbol = lexicon.get(anchor)
        kind = anchor_kind(anchor)
        row = {
            "ordinal": ordinal, "anchor": anchor, "anchor_kind": kind,
            "recognized": symbol is not None,
            "symbol": lexicon_hex.get(anchor),
            # Relation/glue/boundary anchors shape groups; they do not spend an
            # independent corpus-wide focus search.
            "standalone_focus_eligible": kind == "content",
        }
        recognized.append(row)
        if kind == "content" and symbol is not None:
            anchor_blocks = postings.get(symbol, {})
            solo.append({
                **row,
                "posting_count": sum(len(values) for values in anchor_blocks.values()),
                "block_count": len(anchor_blocks),
                "block_ordinals": sorted(anchor_blocks),
            })

    groups = _groups(anchors, lexicon, postings, blocks if blocks is not None else read_blocks(paths))
    # Solo posting inventories prove where each anchor exists.  They do not
    # authorize a corpus-wide broadcast.  Exact grouped occurrences alone seed
    # the existing evidence-gathering/traversal stage.
    seeds = sorted({
        block for group in groups
        for block in (group["parent_identity_block_ordinals"] or group["exact_sequence_block_ordinals"])
    })
    return {
        "schema": "truemem_lexicon_anchor_focus@1",
        "question": question,
        "question_anchors": recognized,
        "standalone_searches": solo,
        "focus_groups": groups,
        "seed_block_ordinals": seeds,
        "laws": {
            "admitted_map_changed": False,
            "every_question_anchor_receipted": True,
            "low_consequence_anchors_suppressed_only_as_standalone_focus": True,
            "glue_preserved_inside_exact_structure": True,
            "punctuation_preserved_as_symbolic_boundary": True,
            "ranking_performed": False,
            "model_used": False,
        },
    }


def _groups(anchors: list[str], lexicon: dict[str, bytes], postings: dict[bytes, dict[int, list[int]]], blocks: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Find maximal exact parent identities without benchmark/query templates."""
    title_index: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for block, payload in blocks.items():
        lines = str(payload.get("text", "")).splitlines()
        title = anchorize(lines[0]) if lines else []
        _begin, title_end = _trim(title, 0, len(title))
        if title_end:
            title_index[tuple(title[:title_end])].append(block)

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
    while begin < end and anchors[end - 1] in GROUP_END_MARKS:
        end -= 1
    return begin, end
