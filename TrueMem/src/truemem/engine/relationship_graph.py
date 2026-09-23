"""Deterministic relationship measurements derived from signed 6-1-6 counts."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
from typing import Any, Iterable


SIGNED_LANES = (*range(-6, 0), *range(1, 7))


@dataclass(frozen=True)
class RelationshipCount:
    center: str
    neighbor: str
    offset: int
    count: int


class RelationshipGraph:
    """A read-only measurement view over admitted anchor and relation counts."""

    def __init__(
        self,
        relations: Iterable[RelationshipCount | tuple[str, str, int, int]],
        *,
        anchor_frequencies: dict[str, int] | Counter[str] | None = None,
    ) -> None:
        self.counts: Counter[tuple[str, str, int]] = Counter()
        self.lane_totals: Counter[tuple[str, int]] = Counter()
        self.outgoing: dict[str, set[str]] = defaultdict(set)
        for value in relations:
            row = value if isinstance(value, RelationshipCount) else RelationshipCount(
                str(value[0]), str(value[1]), int(value[2]), int(value[3])
            )
            if row.offset not in SIGNED_LANES or row.count <= 0:
                continue
            key = (row.center, row.neighbor, row.offset)
            self.counts[key] += int(row.count)
            self.lane_totals[(row.center, row.offset)] += int(row.count)
            self.outgoing[row.center].add(row.neighbor)

        self.anchor_frequencies = Counter({
            str(anchor): int(count)
            for anchor, count in (anchor_frequencies or {}).items()
            if int(count) > 0
        })
        if not self.anchor_frequencies:
            # This fallback is explicit and used only when callers did not supply
            # the authoritative anchor-count file.
            for (_center, neighbor, _offset), count in self.counts.items():
                self.anchor_frequencies[neighbor] = max(self.anchor_frequencies[neighbor], int(count))
        self.total_anchor_occurrences = sum(self.anchor_frequencies.values())

    def lane(self, center: str, neighbor: str, offset: int) -> dict[str, Any]:
        count = int(self.counts.get((center, neighbor, int(offset)), 0))
        lane_total = int(self.lane_totals.get((center, int(offset)), 0))
        neighbor_frequency = int(self.anchor_frequencies.get(neighbor, 0))
        conditional = count / lane_total if lane_total else 0.0
        background = neighbor_frequency / self.total_anchor_occurrences if self.total_anchor_occurrences else 0.0
        lift = conditional / background if conditional and background else 0.0
        log_lift = math.log(lift) if lift > 0 else None
        return {
            "signed_distance": int(offset),
            "count": count,
            "lane_total": lane_total,
            "conditional_probability": _round(conditional),
            "background_probability": _round(background),
            "lift": _round(lift),
            "log_lift": _round(log_lift) if log_lift is not None else None,
            "support_confidence": _round(math.log1p(count)),
        }

    def edge(self, center: str, neighbor: str) -> dict[str, Any]:
        lanes = [self.lane(center, neighbor, offset) for offset in SIGNED_LANES]
        return {
            "schema": "truemem_relationship_edge@1",
            "center_anchor": center,
            "neighbor_anchor": neighbor,
            "lanes": lanes,
            "signed_lane_counts": [int(row["count"]) for row in lanes],
            "measurements_collapsed": False,
        }

    def lane_profile(self, center: str, neighbor: str) -> tuple[int, ...]:
        """Return all signed lane counts as a vector; never collapse them."""

        return tuple(int(self.counts.get((center, neighbor, offset), 0)) for offset in SIGNED_LANES)

    def lane_selection_profile(self, center: str, neighbor: str) -> tuple[int, ...]:
        """Order the complete cloud with forward lanes first for continuation."""

        return tuple(int(self.counts.get((center, neighbor, offset), 0)) for offset in (*range(1, 7), *range(-6, 0)))

    def path_measurements(self, path: list[str]) -> dict[str, Any]:
        edges = [self.edge(left, right) for left, right in zip(path, path[1:])]
        conditional_values: list[float] = []
        lift_values: list[float] = []
        for edge in edges:
            observed_lanes = [row for row in edge["lanes"] if int(row["count"]) > 0]
            conditional_values.append(max((float(row["conditional_probability"]) for row in observed_lanes), default=0.0))
            lift_values.append(max((float(row["lift"]) for row in observed_lanes), default=0.0))
        return {
            "path": list(path),
            "edge_count": len(edges),
            "edges": edges,
            "conditional_bottleneck": _minimum(conditional_values),
            "conditional_geometric_mean": _geometric_mean(conditional_values),
            "lift_bottleneck": _minimum(lift_values),
            "lift_geometric_mean": _geometric_mean(lift_values),
            "signed_lane_profiles": [edge["signed_lane_counts"] for edge in edges],
            "measurements_collapsed": False,
        }

    def strongest_paths(
        self,
        starts: Iterable[str],
        target: str,
        *,
        max_depth: int = 3,
        max_paths: int = 6,
    ) -> list[dict[str, Any]]:
        paths: list[list[str]] = []
        frontier = [[start] for start in dict.fromkeys(str(value) for value in starts) if start]
        for _depth in range(max(0, int(max_depth))):
            expanded: list[list[str]] = []
            for path in frontier:
                current = path[-1]
                neighbors = sorted(
                    self.outgoing.get(current, set()),
                    key=lambda value: (tuple(-count for count in self.lane_selection_profile(current, value)), value),
                )[:12]
                for neighbor in neighbors:
                    if neighbor in path:
                        continue
                    candidate = [*path, neighbor]
                    if neighbor == target:
                        paths.append(candidate)
                    else:
                        expanded.append(candidate)
            frontier = expanded
            if not frontier:
                break
        measured = [self.path_measurements(path) for path in paths]
        measured.sort(key=_path_order_key)
        return measured[:max_paths]


def _path_order_key(row: dict[str, Any]) -> tuple[Any, ...]:
    # Deterministic lexicographic comparison; no weighted scalar is invented.
    return (
        -float(row["conditional_bottleneck"]),
        -float(row["lift_bottleneck"]),
        tuple(tuple(-count for count in profile) for profile in row["signed_lane_profiles"]),
        int(row["edge_count"]),
        tuple(row["path"]),
    )


def _minimum(values: list[float]) -> float:
    return _round(min(values)) if values else 0.0


def _geometric_mean(values: list[float]) -> float:
    if not values or any(value <= 0 for value in values):
        return 0.0
    return _round(math.exp(sum(math.log(value) for value in values) / len(values)))


def _round(value: float) -> float:
    return round(float(value), 12)
