from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .anchors import STOP_ANCHORS, anchorize
from .base import safe_id, utc_now, with_protected_notice, write_json
from .querying import query


def build_citation_crosslinks(
    runtime_root: str | Path,
    left_dataset_id: str,
    right_dataset_id: str,
    question: str,
    *,
    top_k: int = 8,
    min_shared: int = 3,
) -> dict[str, Any]:
    """Build a cross-dataset citation sidecar from normal AWEAR query packets."""
    left = query(runtime_root, left_dataset_id, question, top_k=top_k)
    right = query(runtime_root, right_dataset_id, question, top_k=top_k)
    left_rows = crosslink_candidate_rows(left)
    right_rows = crosslink_candidate_rows(right)
    links: list[dict[str, Any]] = []

    for left_row in left_rows:
        left_anchors = crosslink_anchor_set(str(left_row.get("text") or ""))
        for right_row in right_rows:
            right_anchors = crosslink_anchor_set(str(right_row.get("text") or ""))
            shared = sorted(left_anchors & right_anchors)
            if len(shared) < min_shared:
                continue
            links.append({
                "schema": "awrag_citation_crosslink@1",
                "from_dataset": safe_id(left_dataset_id),
                "from_citation": left_row.get("citation"),
                "from_line_start": left_row.get("line_start"),
                "from_line_end": left_row.get("line_end"),
                "to_dataset": safe_id(right_dataset_id),
                "to_citation": right_row.get("citation"),
                "to_line_start": right_row.get("line_start"),
                "to_line_end": right_row.get("line_end"),
                "link_type": classify_crosslink(shared),
                "shared_anchors": shared[:30],
                "shared_anchor_count": len(shared),
                "confidence": crosslink_confidence(len(shared)),
                "created_from": "awrag_dataset_local_query_packets",
                "lifetime_allowed": False,
            })

    links.sort(key=lambda item: (-int(item["shared_anchor_count"]), str(item["from_citation"]), str(item["to_citation"])))
    run_id = f"{safe_id(left_dataset_id)}__{safe_id(right_dataset_id)}"
    out_dir = Path(runtime_root).expanduser().resolve() / "datasets" / "_crosslinks" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "citation_crosslinks.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for link in links:
            handle.write(json.dumps(with_protected_notice(link), ensure_ascii=True) + "\n")

    summary = with_protected_notice({
        "schema": "awrag_citation_crosslink_summary@1",
        "created_at": utc_now(),
        "left_dataset_id": safe_id(left_dataset_id),
        "right_dataset_id": safe_id(right_dataset_id),
        "question": question,
        "top_k": top_k,
        "min_shared": min_shared,
        "left_candidate_count": len(left_rows),
        "right_candidate_count": len(right_rows),
        "crosslink_count": len(links),
        "crosslink_path": str(path),
        "top_crosslinks": links[:10],
        "left_output_path": left.get("output_path"),
        "right_output_path": right.get("output_path"),
        "lifetime_allowed": False,
    })
    write_json(out_dir / "citation_crosslink_summary.json", summary)
    return summary

def crosslink_candidate_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    packet = result.get("answer_packet") or {}
    rows = list(packet.get("locations") or [])
    rows.extend(packet.get("rejected_locations") or [])
    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        citation = str(row.get("citation") or "")
        if citation and citation not in deduped:
            deduped[citation] = row
    return list(deduped.values())

def classify_crosslink(shared: list[str]) -> str:
    shared_set = set(shared)
    if {"citation", "linking"} & shared_set and {"graph", "network", "cross"} & shared_set:
        return "same_requirement"
    if {"file", "path", "commit"} & shared_set:
        return "implementation_followup"
    if {"contradiction", "conflict", "conflicting"} & shared_set:
        return "contradiction"
    return "same_evidence_field"

def crosslink_confidence(shared_count: int) -> str:
    if shared_count >= 8:
        return "strong"
    if shared_count >= 5:
        return "partial"
    return "weak"

def crosslink_anchor_set(text: str) -> set[str]:
    cleaned = evidence_text_only(text)
    blocked = STOP_ANCHORS | {
        "chat", "created", "conversation", "doctrine", "export", "false", "id",
        "message", "scope", "source", "speaker", "text", "truth", "turn",
        "user", "assistant", "model", "system", "because", "would", "could",
        "should", "there", "these", "those", "this", "that", "with", "from",
    }
    out: set[str] = set()
    for anchor in anchorize(cleaned):
        if anchor in blocked:
            continue
        if len(anchor) < 3:
            continue
        if anchor.isdigit():
            continue
        out.add(anchor)
    return out

def evidence_text_only(text: str) -> str:
    lines: list[str] = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## CHAT_TURN_"):
            continue
        if re.match(r"^CHAT_[A-Z0-9_]+:", stripped):
            continue
        lines.append(line)
    return "\n".join(lines)

