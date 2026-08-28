"""Deterministic moving-window answer prediction over native AWRAG counts."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
from typing import Any, Iterable


@dataclass(frozen=True)
class Relation:
    center: str
    neighbor: str
    offset: int
    count: int


def predict_anchor_path(
    relations: Iterable[Relation | tuple[str, str, int, int]],
    *,
    resolved_history: list[str],
    max_new_anchors: int = 24,
    top_k: int = 6,
    beam_width: int = 6,
) -> dict[str, Any]:
    """Predict next anchors while retaining alternatives for backtracking."""
    if not resolved_history:
        raise ValueError("resolved_history must contain a current anchor")
    if int(top_k) != 6:
        raise ValueError("AWRAG prediction TopK is fixed at six")
    if max_new_anchors < 0 or beam_width < 1:
        raise ValueError("invalid prediction bounds")

    rows = [_relation(row) for row in relations]
    counts = {(row.center, row.neighbor, row.offset): row.count for row in rows}
    next_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        if row.offset == 1 and row.count > 0:
            next_counts[row.center][row.neighbor] += row.count

    beam = [{"path": list(resolved_history), "new": [], "score": 0.0, "steps": []}]
    completed: list[dict[str, Any]] = []
    for output_position in range(max_new_anchors):
        expanded: list[dict[str, Any]] = []
        for branch in beam:
            current = branch["path"][-1]
            candidates = _candidate_field(current, next_counts, counts, branch["path"])
            if not candidates:
                completed.append({**branch, "stop_reason": "no_observed_plus_one_continuation"})
                continue
            for candidate in candidates:
                expanded.append({
                    "path": [*branch["path"], candidate["anchor"]],
                    "new": [*branch["new"], candidate["anchor"]],
                    "score": branch["score"] + candidate["path_score"],
                    "steps": [*branch["steps"], {
                        "output_position": output_position,
                        "current_anchor": current,
                        "candidate_field": candidates,
                        "selected_anchor": candidate["anchor"],
                        "selected_rank": candidate["rank"],
                        "rear_relationships": candidate["rear_relationships"],
                    }],
                })
        if not expanded:
            break
        expanded.sort(key=lambda row: (-float(row["score"]), tuple(row["new"])))
        beam = expanded[:beam_width]

    completed.extend({**row, "stop_reason": "max_new_anchors"} for row in beam)
    completed.sort(key=lambda row: (-len(row["new"]), -float(row["score"]), tuple(row["new"])))
    chosen = completed[0]
    return {
        "schema": "awear_anchor_prediction_walk@1",
        "method": "moving_6_1_6_topk_prediction",
        "top_k": 6,
        "beam_width": int(beam_width),
        "resolved_history": list(resolved_history),
        "generated_anchors": chosen["new"],
        "complete_path": chosen["path"],
        "chosen_ranks": [step["selected_rank"] for step in chosen["steps"]],
        "path_score": round(float(chosen["score"]), 9),
        "steps": chosen["steps"],
        "stop_reason": chosen["stop_reason"],
        "backtracking": {
            "enabled": True,
            "mechanism": "bounded_deterministic_beam",
            "alternatives_retained_per_step": int(beam_width),
            "rank_one_forced": False,
        },
        "authority": {
            "candidate_source": "native_relation_counts_offset_plus_one",
            "rear_validation_source": "native_signed_6_1_6_relation_counts",
            "random_sampling": False,
        },
    }


def deeper_wider_relationship_search(
    relations: Iterable[Relation | tuple[str, str, int, int]],
    *,
    first_answer: dict[str, Any],
    depth: int = 3,
    width: int = 12,
) -> dict[str, Any]:
    """Expand relationships only after receiving the first-answer receipt."""
    if first_answer.get("schema") != "awear_anchor_prediction_walk@1":
        raise ValueError("deeper/wider requires the first prediction-walk answer")
    if depth < 1 or width < 1:
        raise ValueError("invalid deeper/wider bounds")
    adjacency: dict[str, Counter[tuple[str, int]]] = defaultdict(Counter)
    for row in (_relation(value) for value in relations):
        if row.offset and -6 <= row.offset <= 6 and row.count > 0:
            adjacency[row.center][(row.neighbor, row.offset)] += row.count

    seeds = list(dict.fromkeys(str(anchor) for anchor in first_answer.get("complete_path") or []))
    visited = set(seeds)
    frontier = seeds
    layers = []
    for layer in range(1, depth + 1):
        candidates: Counter[tuple[str, int, str]] = Counter()
        for center in frontier:
            for (neighbor, offset), count in adjacency.get(center, {}).items():
                if neighbor not in visited:
                    candidates[(neighbor, offset, center)] += count
        ranked = sorted(candidates.items(), key=lambda item: (-item[1], item[0][1], item[0][0], item[0][2]))[:width]
        relationships = [
            {"anchor": key[0], "offset": key[1], "from_anchor": key[2], "native_relation_count": count}
            for key, count in ranked
        ]
        layers.append({"depth": layer, "relationships": relationships})
        frontier = [row["anchor"] for row in relationships]
        visited.update(frontier)
        if not frontier:
            break
    return {
        "schema": "awear_deeper_wider_relationship_search@1",
        "choice_timing": "only_after_first_answer_returned",
        "first_answer_path": first_answer.get("complete_path"),
        "depth": int(depth),
        "width": int(width),
        "layers": layers,
        "authority": "same_native_awrag_relation_counts",
        "first_answer_mutated": False,
    }


def citation_coordinates_for_path(path: list[str], *, blocks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve a predicted path to exact block and sentence ordinals."""
    wanted = set(path)
    out = []
    for block in blocks:
        sentence_hits = []
        for sentence in block.get("sentences") or []:
            anchors = set(str(value) for value in sentence.get("anchors") or [])
            matched = list(dict.fromkeys(anchor for anchor in path if anchor in anchors))
            if matched:
                sentence_hits.append({
                    "sentence_ordinal": int(sentence["sentence_ordinal"]),
                    "matched_anchors": matched,
                    "text": sentence["text"],
                })
        covered = set(anchor for row in sentence_hits for anchor in row["matched_anchors"])
        if sentence_hits and covered & wanted:
            out.append({
                "citation": block.get("marker"),
                "citation_id": block.get("citation_id"),
                "block_ordinal": int(block["block_ordinal"]),
                "sentence_ordinals": [row["sentence_ordinal"] for row in sentence_hits],
                "sentences": sentence_hits,
                "file_path": block.get("file_path"),
                "line_start": block.get("line_start"),
                "line_end": block.get("line_end"),
                "path_anchor_coverage": len(covered & wanted),
            })
    out.sort(key=lambda row: (-row["path_anchor_coverage"], row["block_ordinal"]))
    return out


def _candidate_field(
    current: str,
    next_counts: dict[str, Counter[str]],
    counts: dict[tuple[str, str, int], int],
    history: list[str],
) -> list[dict[str, Any]]:
    ranked = sorted(next_counts.get(current, {}).items(), key=lambda item: (-item[1], item[0]))[:6]
    total = sum(count for _anchor, count in ranked)
    field = []
    for rank, (anchor, count) in enumerate(ranked, start=1):
        rear = []
        stability = 0.0
        for distance, previous in enumerate(reversed(history[-6:]), start=1):
            forward = int(counts.get((previous, anchor, distance), 0))
            reverse = int(counts.get((anchor, previous, -distance), 0))
            stable = min(forward, reverse) if forward and reverse else max(forward, reverse)
            rear.append({
                "previous_anchor": previous,
                "signed_offset": distance,
                "forward_count": forward,
                "reverse_count": reverse,
                "stable_count": stable,
            })
            stability += math.log1p(stable) / distance
        field.append({
            "anchor": anchor,
            "rank": rank,
            "native_plus_one_count": int(count),
            "deterministic_probability": round(count / max(1, total), 9),
            "rear_relationships": rear,
            "path_score": round(math.log1p(count) + stability, 9),
        })
    return field


def _relation(row: Relation | tuple[str, str, int, int]) -> Relation:
    return row if isinstance(row, Relation) else Relation(str(row[0]), str(row[1]), int(row[2]), int(row[3]))
