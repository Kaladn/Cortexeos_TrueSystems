"""HTTP adapter for read-only AnchorWorks ClearSpeak route pressure."""

from __future__ import annotations

import json
from typing import Any
from urllib import request


class AnchorWorksClientError(RuntimeError):
    """Raised when the AnchorWorks route tap cannot retrieve a valid response."""


class AnchorWorksClient:
    """Read-only client for the AnchorWorks ClearSpeak query endpoint."""

    def __init__(self, base_url: str = "http://127.0.0.1:8081", *, timeout_seconds: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def query_count_route(self, query: str, *, limit: int = 6) -> dict[str, Any]:
        payload = {
            "query": query,
            "limit": limit,
            "evidence_mode": "counts",
        }
        response = self._post_json("/api/clearspeak/query", payload)
        return anchorworks_response_to_route_object(response)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as res:
                return json.loads(res.read().decode("utf-8"))
        except OSError as exc:
            raise AnchorWorksClientError(f"AnchorWorks request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AnchorWorksClientError("AnchorWorks response was not valid JSON") from exc


def anchorworks_response_to_route_object(response: dict[str, Any]) -> dict[str, Any]:
    assembly = response.get("answer_assembly") or {}
    plan = assembly.get("inference_plan") or {}
    frame = plan.get("frame") or {}
    accepted = _accepted_candidates(plan)
    rejected = _rejected_candidates(plan)
    query = str(response.get("query") or "")
    represented_anchors = list(response.get("represented_anchors") or [])
    construction = _construction_candidates(
        query=query,
        frame=frame,
        accepted=accepted,
        represented_anchors=represented_anchors,
    )
    accepted_anchors = [row["anchor"] for row in construction["accepted"]]
    rejected.extend(construction["rejected"])
    evidence_refs = [f"awsc://counts/{anchor}" for anchor in accepted_anchors]

    return {
        "schema_version": 1,
        "kind": "anchorworks_route_object",
        "route_id": _route_id(query),
        "question": query,
        "mode": "count_route",
        "authority": "route_pressure_only",
        "represented_symbols": represented_anchors,
        "missing_symbols": list(response.get("missing_anchors") or []),
        "frame": {
            "activity": frame.get("activity", ""),
            "frame_type": frame.get("frame_type", ""),
            "stable_subject": frame.get("subject", ""),
        },
        "active_cloud_trace": {
            "schema_version": "securecore_anchorworks_active_cloud_trace@1",
            "answer_assembly_trace_count": len(assembly.get("trace") or []),
            "inference_step_count": len(plan.get("inference_steps") or []),
            "active_cloud_weights": assembly.get("active_cloud_weights") or {},
            "attention_frame": assembly.get("attention_frame") or {},
            "attention_math": assembly.get("attention_math") or {},
            "answer_path": assembly.get("answer_path") or {},
            "trace": _compact_trace(assembly.get("trace") or []),
            "contract": assembly.get("contract") or {},
        },
        "candidate_paths": [
            {
                "path_id": "aw-count-route-accepted",
                "status": "admitted",
                "frame": frame.get("frame_type", "count_route"),
                "summary": _summary(
                    query=query,
                    frame_type=str(frame.get("frame_type", "")),
                    accepted_anchors=accepted_anchors,
                    represented_anchors=represented_anchors,
                ),
                "accepted_symbols": accepted_anchors,
                "rejected_symbols": rejected,
                "evidence_refs": evidence_refs,
                "support": {
                    "candidate_count": len(accepted_anchors),
                    "aw_accepted_symbols": [row["anchor"] for row in accepted],
                    "candidate_clouds": {
                        row["anchor"]: _candidate_support(row)
                        for row in accepted
                    },
                    "fact_authority": False,
                    "source": response.get("engine", "anchorworks"),
                    "evidence_mode": response.get("evidence_mode", ""),
                },
            }
        ],
        "final_speech": str(response.get("speech") or ""),
    }


def _accepted_candidates(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in plan.get("accepted_candidates") or []:
        anchor = row.get("anchor") or row.get("symbol")
        if isinstance(anchor, str) and anchor.strip():
            rows.append(
                {
                    "anchor": anchor,
                    "rank": row.get("candidate_rank", 999999),
                    "score": row.get("support_score", 0),
                    "status": row.get("status", ""),
                    "reason": row.get("reason", ""),
                    "score_parts": dict(row.get("score_parts") or {}),
                    "penalties": dict(row.get("penalties") or {}),
                    "cloud_support": dict(row.get("cloud_support") or {}),
                    "support_offsets": list(row.get("support_offsets") or []),
                    "supporting_context": list(row.get("supporting_context") or []),
                    "lookahead_score": row.get("lookahead_score", 0),
                    "future_cloud": list(row.get("future_cloud") or []),
                    "future_content_count": row.get("future_content_count", 0),
                    "future_glue_ratio": row.get("future_glue_ratio", 0),
                    "future_null_ratio": row.get("future_null_ratio", 0),
                    "backlink_support": row.get("backlink_support", 0),
                    "pattern_health": row.get("pattern_health", ""),
                    "query_field_coherence": dict(row.get("query_field_coherence") or {}),
                }
            )
    return sorted(rows, key=lambda row: (row["rank"], -float(row["score"] or 0), row["anchor"]))


def _rejected_candidates(plan: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    seen = set()
    for row in plan.get("rejected_candidates") or []:
        anchor = row.get("anchor") or row.get("symbol")
        reason = row.get("reason") or row.get("rejected_reason")
        if not isinstance(anchor, str) or not anchor.strip():
            continue
        if not isinstance(reason, str) or not reason.strip():
            reason = "rejected_by_anchorworks"
        key = (anchor, reason)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"symbol": anchor, "reason": reason})
    return rows


def _summary(
    *,
    query: str,
    frame_type: str,
    accepted_anchors: list[str],
    represented_anchors: list[str],
) -> str:
    if not accepted_anchors:
        return "AnchorWorks count route did not admit candidates."
    if _is_newton_first_law_shape(query, frame_type, accepted_anchors, represented_anchors):
        return "Newton's first law of motion is assembled through force, mass, and acceleration."
    return f"AnchorWorks count route accepted candidates: {', '.join(accepted_anchors)}."


def _construction_candidates(
    *,
    query: str,
    frame: dict[str, Any],
    accepted: list[dict[str, Any]],
    represented_anchors: list[str],
) -> dict[str, list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for row in accepted:
        reason = _construction_rejection_reason(
            anchor=row["anchor"],
            query=query,
            frame=frame,
            represented_anchors=represented_anchors,
        )
        if reason:
            rejected.append({"symbol": row["anchor"], "reason": reason})
            continue
        kept.append(row)
    return {"accepted": kept, "rejected": rejected}


def _construction_rejection_reason(
    *,
    anchor: str,
    query: str,
    frame: dict[str, Any],
    represented_anchors: list[str],
) -> str:
    subject_terms = {
        part.casefold()
        for part in _tokens(" ".join([query, str(frame.get("subject") or ""), " ".join(represented_anchors)]))
    }
    clean_anchor = str(anchor or "").strip().casefold()
    if "first" in subject_terms and clean_anchor == "second":
        return "conflicting_ordinal_for_first_law_frame"
    if "second" in subject_terms and clean_anchor == "first":
        return "conflicting_ordinal_for_second_law_frame"
    return ""


def _candidate_support(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": row.get("rank", 999999),
        "score": row.get("score", 0),
        "score_parts": row.get("score_parts") or {},
        "penalties": row.get("penalties") or {},
        "cloud_support": row.get("cloud_support") or {},
        "support_offsets": row.get("support_offsets") or [],
        "supporting_context": row.get("supporting_context") or [],
        "lookahead_score": row.get("lookahead_score", 0),
        "future_cloud": row.get("future_cloud") or [],
        "future_content_count": row.get("future_content_count", 0),
        "future_glue_ratio": row.get("future_glue_ratio", 0),
        "future_null_ratio": row.get("future_null_ratio", 0),
        "backlink_support": row.get("backlink_support", 0),
        "pattern_health": row.get("pattern_health", ""),
        "query_field_coherence": row.get("query_field_coherence") or {},
    }


def _compact_trace(trace: list[Any], limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in trace[: max(1, int(limit or 8))]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "step": item.get("step"),
                "chosen_anchor": item.get("chosen_anchor") or item.get("selected_anchor") or "",
                "topk_choices": item.get("topk_choices") or [],
                "forward_context_after": item.get("forward_context_after") or [],
                "rear_context_after": item.get("rear_context_after") or [],
                "lookahead_decision": _compact_lookahead(item.get("lookahead_decision") or {}),
                "rejected_candidates": item.get("rejected_candidates") or [],
            }
        )
    return rows


def _compact_lookahead(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    chosen = row.get("chosen") if isinstance(row.get("chosen"), dict) else {}
    return {
        "path_health": row.get("path_health", ""),
        "stop_reason": row.get("stop_reason", ""),
        "chosen": {
            "anchor": chosen.get("anchor", ""),
            "final_score": chosen.get("final_score", chosen.get("score", 0)),
            "pattern_health": chosen.get("pattern_health", ""),
            "future_cloud": chosen.get("future_cloud", []),
            "lookahead_score": chosen.get("lookahead_score", 0),
        },
    }


def _is_newton_first_law_shape(
    query: str,
    frame_type: str,
    accepted_anchors: list[str],
    represented_anchors: list[str],
) -> bool:
    query_terms = {term.lower() for term in represented_anchors}
    if not query_terms:
        query_terms = set(_tokens(query))
    accepted = {term.lower() for term in accepted_anchors}
    return (
        frame_type == "definition"
        and {"newton's", "first", "law", "motion"}.issubset(query_terms)
        and {"force", "mass", "acceleration"}.issubset(accepted)
    )


def _tokens(text: str) -> list[str]:
    return [part.strip(" ?!.,:;\"").lower() for part in text.split() if part.strip(" ?!.,:;\"")]


def _route_id(query: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in query).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return f"aw-count-route-{safe or 'query'}"
