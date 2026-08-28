"""Metadata-only glyph extender for TrueVision SC Edition.

This translates AnchorWorks visual-glyph discipline into SecureCore telemetry.
It does not reconstruct text, store raw pixels, run OCR, or grant truth
authority. It only summarizes known/unknown mark-pattern pressure for Forge and
fusion.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any


def normalize_trim_pattern(rows: list[str]) -> tuple[str, ...]:
    cleaned = [str(row) for row in rows if "1" in str(row)]
    if not cleaned:
        return tuple()
    left = min(row.index("1") for row in cleaned)
    right = max(row.rindex("1") for row in cleaned)
    return tuple(row[left : right + 1] for row in cleaned)


def pattern_hash(pattern: tuple[str, ...]) -> str:
    return sha256("\n".join(pattern).encode("utf-8")).hexdigest()


def build_glyph_extender_summary(
    approved_patterns: list[dict[str, Any]],
    components: list[dict[str, Any]],
) -> dict[str, Any]:
    approved_hashes = _approved_hashes(approved_patterns)
    known_hashes: list[str] = []
    unknown_hashes: list[str] = []
    anomalies: list[dict[str, Any]] = []
    normalized_components = []

    for component in components:
        pattern = normalize_trim_pattern(list(component.get("pattern") or []))
        digest = pattern_hash(pattern)
        bounds = tuple(int(value) for value in component.get("bounds") or (0, 0, 0, 0))
        row = {
            "component_id": str(component.get("component_id", "")),
            "bounds": bounds,
            "pattern_hash": digest,
            "known": digest in approved_hashes,
        }
        normalized_components.append(row)
        if row["known"]:
            known_hashes.append(digest)
        else:
            unknown_hashes.append(digest)
            anomalies.append(
                {
                    "kind": "visual_unknown_glyph",
                    "component_id": row["component_id"],
                    "blocking": True,
                }
            )

    anomalies.extend(_overlap_anomalies(normalized_components))

    return {
        "schema_version": 1,
        "kind": "truevision_sc_glyph_extender_summary",
        "enabled": True,
        "known_pattern_count": len(known_hashes),
        "unknown_pattern_count": len(unknown_hashes),
        "component_count": len(normalized_components),
        "blocking_anomaly_count": sum(1 for row in anomalies if row.get("blocking")),
        "known_pattern_hashes": sorted(set(known_hashes)),
        "unknown_pattern_hashes": sorted(set(unknown_hashes)),
        "anomaly_kinds": sorted({str(row.get("kind", "")) for row in anomalies if row.get("kind")}),
        "text_reconstruction_allowed": False,
        "raw_content_stored": False,
        "fact_authority": False,
    }


def _approved_hashes(records: list[dict[str, Any]]) -> set[str]:
    hashes: set[str] = set()
    for record in records:
        if record.get("promotion_status") != "approved":
            continue
        pattern = normalize_trim_pattern(list(record.get("trim_pattern") or []))
        if pattern:
            hashes.add(pattern_hash(pattern))
    return hashes


def _overlap_anomalies(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for index, left in enumerate(components):
        for right in components[index + 1 :]:
            if _overlaps(left["bounds"], right["bounds"]):
                anomalies.append(
                    {
                        "kind": "component_overlap",
                        "component_id": left["component_id"],
                        "other_component_id": right["component_id"],
                        "blocking": True,
                    }
                )
    return anomalies


def _overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1
