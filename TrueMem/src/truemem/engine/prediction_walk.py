"""Deterministic moving-window prediction over measured 6-1-6 relationships."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from .anchors import anchor_kind
from .relationship_graph import RelationshipCount, RelationshipGraph


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
    query_anchors: list[str] | None = None,
    anchor_frequencies: dict[str, int] | Counter[str] | None = None,
    max_new_anchors: int = 24,
    top_k: int = 6,
    beam_width: int = 6,
    cloud_depth: int = 3,
    allowed_anchors: set[str] | None = None,
) -> dict[str, Any]:
    if not resolved_history:
        raise ValueError("resolved_history must contain a current anchor")
    if int(top_k) not in {3, 6}:
        raise ValueError("TrueMem prediction TopK must be three or six")
    if max_new_anchors < 0 or beam_width < 1 or cloud_depth < 1:
        raise ValueError("invalid prediction bounds")

    rows = [_relation(row) for row in relations]
    graph = RelationshipGraph(
        [RelationshipCount(row.center, row.neighbor, row.offset, row.count) for row in rows],
        anchor_frequencies=anchor_frequencies,
    )
    next_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        if row.offset == 1 and row.count > 0:
            next_counts[row.center][row.neighbor] += row.count

    query_demand = list(dict.fromkeys(str(value) for value in (query_anchors or resolved_history) if value))
    beam = [{"path": list(resolved_history), "new": [], "steps": [], "branch_events": []}]
    completed: list[dict[str, Any]] = []
    pruned: list[dict[str, Any]] = []
    for output_position in range(max_new_anchors):
        expanded: list[dict[str, Any]] = []
        for branch in beam:
            current = branch["path"][-1]
            candidates = _candidate_field(
                current,
                next_counts,
                graph,
                branch["path"],
                query_demand,
                cloud_depth,
                top_k=int(top_k),
                allowed_anchors=allowed_anchors,
            )
            if not candidates:
                completed.append({**branch, "stop_reason": "evidence_dead_end"})
                continue
            for candidate in candidates:
                expanded.append({
                    "path": [*branch["path"], candidate["anchor"]],
                    "new": [*branch["new"], candidate["anchor"]],
                    "steps": [*branch["steps"], {
                        "output_position": output_position,
                        "current_anchor": current,
                        "candidate_field": candidates,
                        "selected_anchor": candidate["anchor"],
                        "selected_rank": candidate["rank"],
                        "candidate_vector": candidate["candidate_vector"],
                        "relationship_evidence": candidate["relationship_evidence"],
                    }],
                    "branch_events": [*branch["branch_events"], {
                        "output_position": output_position,
                        "candidate": candidate["anchor"],
                        "warnings": _branch_warning_reasons(candidate),
                    }],
                })
        if not expanded:
            break
        expanded.sort(key=_branch_order_key)
        for rejected in expanded[beam_width:]:
            pruned.append({
                "path": rejected["path"],
                "at_output_position": output_position,
                "reason": "support_collapse_against_sibling_branch",
                "candidate_vector": rejected["steps"][-1]["candidate_vector"],
            })
        beam = expanded[:beam_width]

    completed.extend({**row, "stop_reason": "max_new_anchors"} for row in beam)
    completed.sort(key=_completed_order_key)
    chosen = completed[0]
    return {
        "schema": "truemem_anchor_prediction_walk@2",
        "method": "moving_6_1_6_relationship_vector_prediction",
        "selection_method": "deterministic_lexicographic_vector_no_weighted_score",
        "top_k": int(top_k),
        "beam_width": int(beam_width),
        "resolved_history": list(resolved_history),
        "query_demand_anchors": query_demand,
        "generated_anchors": chosen["new"],
        "complete_path": chosen["path"],
        "chosen_ranks": [step["selected_rank"] for step in chosen["steps"]],
        "steps": chosen["steps"],
        "branch_events": chosen["branch_events"],
        "stop_reason": chosen["stop_reason"],
        "path_measurements": graph.path_measurements(chosen["path"]),
        "backtracking": {
            "enabled": True,
            "mechanism": "bounded_deterministic_branch_restore",
            "alternatives_retained_per_step": int(beam_width),
            "rank_one_forced": False,
            "pruned_branch_count": len(pruned),
            "pruned_branches": pruned,
            "reproducible": True,
        },
        "authority": {
            "candidate_source": "native_relation_counts_offset_plus_one",
            "relationship_source": "native_signed_6_1_6_relation_counts",
            "anchor_frequency_source": "native_dataset_anchor_counts" if anchor_frequencies else "relation_count_fallback",
            "measurements_collapsed": False,
            "random_sampling": False,
            "candidate_workspace_filter": "explicit_allowed_anchor_set" if allowed_anchors is not None else "none",
        },
    }


def deeper_wider_relationship_search(
    relations: Iterable[Relation | tuple[str, str, int, int]],
    *,
    first_answer: dict[str, Any],
    anchor_frequencies: dict[str, int] | Counter[str] | None = None,
    depth: int = 3,
    width: int = 12,
) -> dict[str, Any]:
    if first_answer.get("schema") not in {"truemem_anchor_prediction_walk@1", "truemem_anchor_prediction_walk@2"}:
        raise ValueError("deeper/wider requires the first prediction-walk answer")
    if depth < 1 or width < 1:
        raise ValueError("invalid deeper/wider bounds")
    rows = [_relation(value) for value in relations]
    graph = RelationshipGraph(
        [RelationshipCount(row.center, row.neighbor, row.offset, row.count) for row in rows],
        anchor_frequencies=anchor_frequencies,
    )
    adjacency: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.offset and -6 <= row.offset <= 6 and row.count > 0:
            adjacency[row.center].add(row.neighbor)

    seeds = list(dict.fromkeys(str(anchor) for anchor in first_answer.get("complete_path") or []))
    visited = set(seeds)
    frontier = seeds
    layers = []
    trails: list[dict[str, Any]] = []
    for layer in range(1, depth + 1):
        relationships: list[dict[str, Any]] = []
        for center in sorted(frontier):
            ranked = sorted(adjacency.get(center, set()), key=lambda neighbor: (-graph.pair_totals[(center, neighbor)], neighbor))
            for neighbor in ranked:
                if neighbor in visited:
                    continue
                relationships.append({"anchor": neighbor, "from_anchor": center, "relationship": graph.edge(center, neighbor)})
        relationships.sort(key=_relationship_order_key)
        relationships = relationships[:width]
        layers.append({"depth": layer, "relationships": relationships})
        trails.extend(graph.path_measurements([row["from_anchor"], row["anchor"]]) for row in relationships)
        frontier = [row["anchor"] for row in relationships]
        visited.update(frontier)
        if not frontier:
            break
    return {
        "schema": "truemem_deeper_wider_relationship_search@2",
        "choice_timing": "only_after_first_answer_returned",
        "first_answer_path": first_answer.get("complete_path"),
        "depth": int(depth),
        "width": int(width),
        "layers": layers,
        "trail_measurements": trails,
        "selection_method": "deterministic_lexicographic_vector_no_weighted_score",
        "authority": "same_native_truemem_relation_and_anchor_counts",
        "measurements_collapsed": False,
        "first_answer_mutated": False,
    }


def citation_coordinates_for_path(path: list[str], *, blocks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = set(path)
    out = []
    for block in blocks:
        sentence_hits = []
        for sentence in block.get("sentences") or []:
            anchors = set(str(value) for value in sentence.get("anchors") or [])
            matched = list(dict.fromkeys(anchor for anchor in path if anchor in anchors))
            if matched:
                sentence_hits.append({"sentence_ordinal": int(sentence["sentence_ordinal"]), "matched_anchors": matched, "text": sentence["text"]})
        covered = set(anchor for row in sentence_hits for anchor in row["matched_anchors"])
        if sentence_hits and covered & wanted:
            out.append({
                "citation": block.get("marker"),
                "citation_id": block.get("citation_id"),
                "source": block.get("file_path"),
                "block_ordinal": int(block["block_ordinal"]),
                "sentence_ordinals": [row["sentence_ordinal"] for row in sentence_hits],
                "sentences": sentence_hits,
                "file_path": block.get("file_path"),
                "line_start": block.get("line_start"),
                "line_end": block.get("line_end"),
                "path_anchor_coverage": len(covered & wanted),
                "path_anchor_coverage_ratio": round(len(covered & wanted) / max(1, len(wanted)), 12),
            })
    out.sort(key=lambda row: (-row["path_anchor_coverage"], -row["path_anchor_coverage_ratio"], row["block_ordinal"]))
    return out


def _candidate_field(
    current: str,
    next_counts: dict[str, Counter[str]],
    graph: RelationshipGraph,
    history: list[str],
    query_demand: list[str],
    cloud_depth: int,
    *,
    top_k: int,
    allowed_anchors: set[str] | None,
) -> list[dict[str, Any]]:
    ranked = sorted(
        (
            item for item in next_counts.get(current, {}).items()
            if allowed_anchors is None or item[0] in allowed_anchors
        ),
        key=lambda item: (-item[1], item[0]),
    )[:top_k]
    total = sum(count for _anchor, count in ranked)
    field = []
    for rank, (anchor, count) in enumerate(ranked, start=1):
        local_lane = graph.lane(current, anchor, 1)
        local_edge = graph.edge(current, anchor)
        backside = [
            {
                "previous_anchor": previous,
                "expected_signed_distance": distance,
                "lane": graph.lane(previous, anchor, distance),
                "edge": graph.edge(previous, anchor),
            }
            for distance, previous in enumerate(reversed(history[-6:]), start=1)
        ]
        cloud_paths = graph.strongest_paths(query_demand, anchor, max_depth=cloud_depth, max_paths=top_k)
        forward = [
            {"anchor": future, "lane": graph.lane(anchor, future, 1), "edge": graph.edge(anchor, future)}
            for future, _future_count in sorted(
                (
                    item for item in next_counts.get(anchor, {}).items()
                    if allowed_anchors is None or item[0] in allowed_anchors
                ),
                key=lambda item: (-item[1], item[0]),
            )[:top_k]
        ]
        vector = {
            "Local": local_lane,
            "Back": {
                "expected_lane_support": sum(int(row["lane"]["count"]) for row in backside),
                "conditional_bottleneck": min((float(row["lane"]["conditional_probability"]) for row in backside), default=0.0),
                "relationships": backside,
            },
            "Cloud": {"supported_path_count": len(cloud_paths), "paths": cloud_paths},
            "Forward": {"candidate_count": len(forward), "candidates": forward},
            "Support": local_lane["support_confidence"],
            "Lift": local_lane["lift"],
            "DistanceStability": local_edge["distance_stability"],
            "Direction": local_edge["direction_consistency"],
        }
        field.append({
            "anchor": anchor,
            "anchor_kind": anchor_kind(anchor),
            "rank": rank,
            "native_plus_one_count": int(count),
            "deterministic_probability": round(count / max(1, total), 12),
            "candidate_vector": vector,
            "relationship_evidence": {"local_edge": local_edge, "backside": backside, "cloud_paths": cloud_paths, "lookahead": forward},
            "measurements_collapsed": False,
        })
    return field


def _candidate_order_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    vector = candidate["candidate_vector"]
    local = vector["Local"]
    return (
        -int(vector["Cloud"]["supported_path_count"] > 0),
        -int(vector["Forward"]["candidate_count"] > 0),
        -int(vector["Back"]["expected_lane_support"]),
        -int(local["count"]),
        -float(local["conditional_probability"]),
        -float(local["lift"]),
        -float(vector["DistanceStability"]),
        -float(vector["Direction"]),
        int(candidate["rank"]),
        candidate["anchor"],
    )


def _selected_candidate(step: dict[str, Any]) -> dict[str, Any]:
    return next(row for row in step["candidate_field"] if row["anchor"] == step["selected_anchor"])


def _branch_order_key(branch: dict[str, Any]) -> tuple[Any, ...]:
    return (*_candidate_order_key(_selected_candidate(branch["steps"][-1])), tuple(branch["new"]))


def _completed_order_key(branch: dict[str, Any]) -> tuple[Any, ...]:
    return (-len(branch["new"]), *_candidate_order_key(_selected_candidate(branch["steps"][-1])), tuple(branch["new"])) if branch["steps"] else (0, tuple(branch["new"]))


def _relationship_order_key(row: dict[str, Any]) -> tuple[Any, ...]:
    edge = row["relationship"]
    best_lane = max(edge["lanes"], key=lambda lane: (lane["count"], -abs(lane["signed_distance"])))
    return (-int(edge["total_support"]), -float(best_lane["conditional_probability"]), -float(best_lane["lift"]), -float(edge["distance_stability"]), row["from_anchor"], row["anchor"])


def _branch_warning_reasons(candidate: dict[str, Any]) -> list[str]:
    vector = candidate["candidate_vector"]
    reasons = []
    if int(vector["Local"]["count"]) <= 1:
        reasons.append("unsupported_jump_tiny_support")
    if int(vector["Forward"]["candidate_count"]) == 0:
        reasons.append("evidence_dead_end_ahead")
    if int(vector["Cloud"]["supported_path_count"]) == 0:
        reasons.append("cloud_divergence_no_query_trail")
    if float(vector["Direction"]) < -0.5:
        reasons.append("relationship_contradiction_reverse_dominant")
    return reasons


def _relation(row: Relation | tuple[str, str, int, int]) -> Relation:
    return row if isinstance(row, Relation) else Relation(str(row[0]), str(row[1]), int(row[2]), int(row[3]))
