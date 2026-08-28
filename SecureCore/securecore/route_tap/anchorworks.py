"""AnchorWorks route-pressure adapter for SecureCore.

AnchorWorks final speech is not authority here. This module accepts only
structured route objects and converts admitted, evidence-backed candidate paths
into Central Writer-ready sentence plans.
"""

from __future__ import annotations

from typing import Any

from securecore.central.contracts import build_model_writer_report_request


class RouteTapError(ValueError):
    """Raised when an external route object violates SecureCore boundaries."""


def validate_anchorworks_route_object(route: dict[str, Any]) -> dict[str, Any]:
    _require(route, "schema_version", 1)
    _require(route, "kind", "anchorworks_route_object")
    _require(route, "authority", "route_pressure_only")
    for field in ("route_id", "question", "mode"):
        _require_nonempty_string(route, field)
    _require_string_list(route, "represented_symbols")
    _require_list(route, "candidate_paths")
    for candidate in route["candidate_paths"]:
        _validate_candidate(candidate)
    return dict(route)


def build_sentence_plan(route: dict[str, Any]) -> dict[str, Any]:
    validated = validate_anchorworks_route_object(route)
    admitted = [
        candidate
        for candidate in validated["candidate_paths"]
        if candidate.get("status") == "admitted"
    ]
    if not admitted:
        raise RouteTapError("at least one admitted candidate path is required")

    sentences: list[str] = []
    evidence_refs: list[str] = []
    rejected_notes: list[str] = []
    source_refs: list[str] = [f"anchorworks_route:{validated['route_id']}"]

    for candidate in admitted:
        refs = candidate["evidence_refs"]
        if not refs:
            raise RouteTapError("admitted candidate path must include evidence_refs")
        sentences.append(candidate["summary"])
        evidence_refs.extend(refs)
        for rejected in candidate.get("rejected_symbols", []):
            rejected_notes.append(f"{rejected['symbol']}: {rejected['reason']}")

    return {
        "schema_version": 1,
        "kind": "securecore_sentence_plan",
        "source": "anchorworks_route_tap",
        "source_route_id": validated["route_id"],
        "question": validated["question"],
        "sentences": sentences,
        "evidence_refs": _dedupe(evidence_refs),
        "source_refs": source_refs,
        "rejected_candidate_notes": rejected_notes,
        "fact_authority": False,
        "enforcement_authorized": False,
    }


def build_writer_request_from_sentence_plan(
    plan: dict[str, Any],
    *,
    request_id: str,
    requested_by_model: str,
    severity: str,
) -> dict[str, Any]:
    _require(plan, "schema_version", 1)
    _require(plan, "kind", "securecore_sentence_plan")
    _require(plan, "fact_authority", False)
    _require(plan, "enforcement_authorized", False)
    _require_string_list(plan, "sentences")
    _require_string_list(plan, "evidence_refs")
    _require_string_list(plan, "source_refs")
    return build_model_writer_report_request(
        request_id=request_id,
        requested_by_model=requested_by_model,
        condition="chain_recipe_report_step",
        summary=f"AnchorWorks route tap: {plan['question']}",
        severity=severity,
        facts=plan["sentences"],
        evidence_refs=plan["evidence_refs"],
        reader_bundle_refs=plan["source_refs"],
        language_task="format_facts",
    )


def _validate_candidate(candidate: dict[str, Any]) -> None:
    for field in ("path_id", "status", "frame", "summary"):
        _require_nonempty_string(candidate, field)
    if candidate["status"] not in {"admitted", "rejected", "pending"}:
        raise RouteTapError("candidate status must be admitted, rejected, or pending")
    _require_string_list(candidate, "accepted_symbols", allow_empty=True)
    _require_string_list(candidate, "evidence_refs", allow_empty=True)
    _require_list(candidate, "rejected_symbols")
    for row in candidate["rejected_symbols"]:
        _require_nonempty_string(row, "symbol")
        _require_nonempty_string(row, "reason")
    support = candidate.get("support")
    if not isinstance(support, dict):
        raise RouteTapError("candidate support must be an object")


def _require(row: dict[str, Any], field: str, expected: Any) -> None:
    if row.get(field) != expected:
        raise RouteTapError(f"{field} must be {expected!r}")


def _require_nonempty_string(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise RouteTapError(f"{field} must be a non-empty string")


def _require_list(row: dict[str, Any], field: str) -> None:
    if not isinstance(row.get(field), list):
        raise RouteTapError(f"{field} must be a list")


def _require_string_list(row: dict[str, Any], field: str, *, allow_empty: bool = False) -> None:
    _require_list(row, field)
    if not allow_empty and not row[field]:
        raise RouteTapError(f"{field} must not be empty")
    if not all(isinstance(item, str) and item.strip() for item in row[field]):
        raise RouteTapError(f"{field} must contain only non-empty strings")


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
