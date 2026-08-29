"""Facts-only report shaping for TrueCore package calls."""

from __future__ import annotations

import hashlib
import json

from truecore.time import utc_now


class TextFactsReportError(ValueError):
    """Raised when a facts report would violate the Central Writer boundary."""


def build_text_facts_report(
    *,
    title: str,
    facts: list[str],
    evidence_refs: list[str],
    warnings: list[str],
) -> dict:
    if not isinstance(title, str) or not title.strip():
        raise TextFactsReportError("title must be a non-empty string")
    _string_list("facts", facts)
    _string_list("evidence_refs", evidence_refs)
    _string_list("warnings", warnings)
    if facts and not evidence_refs:
        raise TextFactsReportError("facts require evidence refs")
    payload = {
        "schema_version": 1,
        "kind": "truecore_text_facts_report",
        "title": title,
        "created_at_utc": utc_now(),
        "facts": list(facts),
        "evidence_refs": list(evidence_refs),
        "warnings": list(warnings),
        "action_authorized": False,
        "model_authority": False,
        "inference_authority": False,
    }
    payload["report_hash"] = hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def _string_list(name: str, values: list[str]) -> None:
    if not isinstance(values, list) or not all(isinstance(item, str) and item.strip() for item in values):
        raise TextFactsReportError(f"{name} must be a list of non-empty strings")
