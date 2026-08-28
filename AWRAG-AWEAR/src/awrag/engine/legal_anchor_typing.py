from __future__ import annotations

import re
from typing import Any

from .anchors import anchorize

AUTHORITY_MARKERS = {"section", "statute", "rule", "s", "§"}
DEFINITION_MARKERS = {"means", "includes", "defined"}
EXCEPTION_MARKERS = {"unless", "except", "provided"}
MANDATORY_MARKERS = {"must", "shall", "required", "requires"}
DISCRETION_MARKERS = {"may", "can", "discretion"}


def classify_anchor_occurrences(text: str, *, window: int = 6) -> list[dict[str, Any]]:
    tokens = _tokenize_with_shape(text)
    rows: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        anchor = _clean_anchor(str(token["text"]))
        if not anchor:
            continue
        left = [_clean_anchor(str(row["text"])) for row in tokens[max(0, index - window) : index]]
        right = [_clean_anchor(str(row["text"])) for row in tokens[index + 1 : index + 1 + window]]
        features = {
            "marker_anchor_type": _marker_anchor_type(anchor),
            "has_section_marker": anchor in AUTHORITY_MARKERS or _contains(left + right, AUTHORITY_MARKERS),
            "has_case_marker": _near_case_marker(tokens, index, window),
            "has_definition_marker": anchor in DEFINITION_MARKERS or _contains(left + right, DEFINITION_MARKERS),
            "has_exception_marker": anchor in EXCEPTION_MARKERS or _contains(left + right, EXCEPTION_MARKERS),
            "has_mandatory_marker": anchor in MANDATORY_MARKERS or _contains(left + right, MANDATORY_MARKERS),
            "has_discretion_marker": anchor in DISCRETION_MARKERS or _contains(left + right, DISCRETION_MARKERS),
            "punctuation_shape": token["punctuation_shape"],
            "heading_shape": token["heading_shape"],
        }
        anchor_type, proof_need = _type_from_features(features)
        rows.append(
            {
                "anchor": anchor,
                "anchor_type": anchor_type,
                "symbol": f"{anchor}[{anchor_type}]",
                "features": features,
                "proof_need": proof_need,
            }
        )
    return rows


def typed_anchor_summary(text: str) -> dict[str, Any]:
    rows = classify_anchor_occurrences(text)
    return {
        "schema": "awear_typed_anchor_summary@1",
        "all_anchors": anchorize(text),
        "typed_anchors": rows,
        "proof_needs": sorted({str(row["proof_need"]) for row in rows}),
    }


def _type_from_features(features: dict[str, Any]) -> tuple[str, str]:
    marker_type = features.get("marker_anchor_type")
    if marker_type == "definition_anchor":
        return "definition_anchor", "definition_controls_meaning"
    if marker_type == "exception_anchor":
        return "exception_anchor", "check_if_exception_applies"
    if marker_type == "duty_anchor":
        return "duty_anchor", "prove_required_condition"
    if marker_type == "discretion_anchor":
        return "discretion_anchor", "prove_allowed_not_required"
    if marker_type == "authority_anchor":
        return "authority_anchor", "cite_statute_or_section"
    if features["has_definition_marker"]:
        return "definition_anchor", "definition_controls_meaning"
    if features["has_exception_marker"]:
        return "exception_anchor", "check_if_exception_applies"
    if features["has_mandatory_marker"]:
        return "duty_anchor", "prove_required_condition"
    if features["has_discretion_marker"]:
        return "discretion_anchor", "prove_allowed_not_required"
    if features["has_section_marker"]:
        return "authority_anchor", "cite_statute_or_section"
    if features["has_case_marker"]:
        return "case_authority_anchor", "cite_case_relationship"
    return "plain_language_anchor", "ordinary_context_check"


def _tokenize_with_shape(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in re.finditer(r"\S+", text):
        raw = match.group(0)
        rows.append(
            {
                "text": raw,
                "punctuation_shape": "".join(ch for ch in raw if not ch.isalnum()),
                "heading_shape": raw.isupper() and len(raw) > 1,
            }
        )
    return rows


def _clean_anchor(token: str) -> str:
    cleaned = re.sub(r"(^[^\w§]+|[^\w§]+$)", "", token.casefold())
    if not cleaned:
        return ""
    if cleaned == "§":
        return cleaned
    if any(ch.isalnum() for ch in cleaned):
        return cleaned
    return ""


def _contains(values: list[str], markers: set[str]) -> bool:
    return any(value in markers for value in values if value)


def _marker_anchor_type(anchor: str) -> str | None:
    if anchor in DEFINITION_MARKERS:
        return "definition_anchor"
    if anchor in EXCEPTION_MARKERS:
        return "exception_anchor"
    if anchor in MANDATORY_MARKERS:
        return "duty_anchor"
    if anchor in DISCRETION_MARKERS:
        return "discretion_anchor"
    if anchor in AUTHORITY_MARKERS:
        return "authority_anchor"
    return None


def _near_case_marker(tokens: list[dict[str, Any]], index: int, window: int) -> bool:
    start = max(0, index - window)
    end = min(len(tokens), index + window + 1)
    nearby = " ".join(str(row["text"]) for row in tokens[start:end]).casefold()
    return bool(re.search(r"\bv\.|\bvs\.", nearby))
