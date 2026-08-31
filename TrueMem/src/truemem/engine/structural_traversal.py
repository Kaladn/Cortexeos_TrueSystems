"""TrueMem Traversal Layer v1 above the frozen Authority Layer v1."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .structural_storage import read_structural_graph, verify_structural_graph
from .xpu_structural_graph import XpuStructuralGraph
from .pressure_contract import validate_pressure_points
from .query_pressure_plan import compile_query_pressure_plan


def _question_compile(question: str) -> dict[str, Any]:
    try:
        from truevision_intake.structural_binding import compile_question_structures
    except ModuleNotFoundError:
        root = Path(__file__).resolve().parents[4] / "TrueVisionIntake"
        if not root.is_dir():
            raise RuntimeError("TRUEVISION_STRUCTURAL_COMPILER_UNAVAILABLE")
        sys.path.insert(0, str(root))
        from truevision_intake.structural_binding import compile_question_structures
    return compile_question_structures(question)


def traverse_structural_evidence(
    paths: Any,
    question: str,
    *,
    selected_question_structure_keys: list[str] | None = None,
    admitted_start_block_ids: list[int] | None = None,
    required_structure_kinds: list[str] | None = None,
    maximum_hops: int = 6,
    loaded_graph: XpuStructuralGraph | None = None,
    decoded_graph: dict[str, list[dict[str, Any]]] | None = None,
    verified_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verification = verified_receipt or verify_structural_graph(paths)
    if verification["status"] != "PASS":
        return {"status": "STALE_PROVENANCE", "verification": verification, "operation_executed": False}
    overlay = _question_compile(question)
    verified_overlay_keys = {row["structure_key"] for row in overlay["structures"]}
    selected = list(selected_question_structure_keys or sorted(verified_overlay_keys))
    if any(key not in verified_overlay_keys for key in selected):
        return {"status": "INVALID_STRUCTURE_PATH", "operation_executed": False, "invented_structure_rejected": True}
    if admitted_start_block_ids is not None and not admitted_start_block_ids:
        return {
            "schema": "truemem_structural_traversal_receipt@2",
            "status": "NO_ADMITTED_START_EVIDENCE",
            "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
            "question_overlay_id": overlay["compilation_id"],
            "operation_executed": False, "model_used": False,
            "training_performed": False, "ranking_modified": False,
            "textual_answer_formed": False, "handoff_only": True,
        }
    stored = decoded_graph or read_structural_graph(paths.state / "structure_graph.awbin")
    admitted_blocks = {int(value) for value in (admitted_start_block_ids or [])}
    admitted_keys: set[str] = set()
    # Physical records intentionally retain symbols rather than duplicate keys.
    # Resolve admitted source-block structures through the dataset lexicon.
    lexicon = json.loads(paths.lexicon_path.read_text(encoding="utf-8"))
    symbol_to_key = {str(row["symbol"]): str(row["anchor"]) for row in lexicon["anchors"]}
    for row in stored["structures"]:
        if int(row["block_ordinal"]) in admitted_blocks:
            key = symbol_to_key.get(str(row["symbol"]))
            if key:
                admitted_keys.add(key)
    if admitted_blocks:
        selected = sorted(set(selected) & admitted_keys)
    else:
        selected = sorted(set(selected))
    graph = loaded_graph or XpuStructuralGraph(paths.root)
    walk = graph.walk(selected, maximum_hops=maximum_hops, start_block_ids=sorted(admitted_blocks))
    visited = set(walk.get("visited_occurrence_ids") or [])
    reached = [row for row in stored["structures"] if row["occurrence_id"] in visited]
    required = sorted(set(required_structure_kinds or []))
    found_kinds = sorted({str(row["kind"]) for row in reached})
    missing = sorted(set(required) - set(found_kinds))
    blocks = {}
    for line in paths.blocks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            blocks[int(row["block_ordinal"])] = row
    citations = []
    for block_id in walk.get("block_ids") or []:
        block = blocks[int(block_id)]
        citations.append({
            "block_ordinal": int(block_id),
            "citation_id": block["citation_id"],
            "file_path": block["file_path"],
            "line_start": block["line_start"],
            "line_end": block["line_end"],
            "text_hash": block["text_hash"],
        })
    status = "EVIDENCE_BURDEN_SATISFIED" if required and not missing else walk["status"]
    receipt = {
        "schema": "truemem_structural_traversal_receipt@2",
        "status": status,
        "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "question_overlay_id": overlay["compilation_id"],
        "selected_verified_structure_keys": selected,
        "admitted_start_block_ids": sorted(admitted_blocks),
        "required_structure_kinds": required,
        "found_structure_kinds": found_kinds,
        "missing_structure_kinds": missing,
        "evidence_burden_note": "structure kinds are diagnostic only; operation-specific identity/relation/value burdens are not inferred here",
        "gathered_occurrence_ids": sorted(visited),
        "coherent_path_receipts": walk.get("paths") or [],
        "walk": walk,
        "citations": citations,
        "operation_executed": False,
        "authority_layer_modified": False,
        "model_used": False,
        "training_performed": False,
        "ranking_modified": False,
        "textual_answer_formed": False,
        "handoff_only": True,
    }
    return receipt


def traverse_pressure_evidence(
    paths: Any,
    question: str,
    *,
    selected_question_structure_keys: list[str],
    admitted_start_block_ids: list[int],
    pressure_points: list[dict[str, Any]],
    maximum_rounds: int = 6,
    maximum_branches: int = 4096,
    loaded_graph: XpuStructuralGraph | None = None,
    decoded_graph: dict[str, list[dict[str, Any]]] | None = None,
    verified_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gather, discern, compile, and hand off exact evidence paths."""
    verification = verified_receipt or verify_structural_graph(paths)
    if verification["status"] != "PASS":
        return {"status": "STALE_PROVENANCE", "verification": verification, "operation_executed": False}
    overlay = _question_compile(question)
    overlay_keys = {row["structure_key"] for row in overlay["structures"]}
    selected = sorted(set(map(str, selected_question_structure_keys)))
    if not selected or any(value not in overlay_keys for value in selected):
        return {"status": "INVALID_STRUCTURE_PATH", "operation_executed": False, "invented_structure_rejected": True}
    if not admitted_start_block_ids:
        return {
            "schema": "truemem_pressure_evidence_workspace@1",
            "status": "NO_ADMITTED_START_EVIDENCE", "operation_executed": False,
            "textual_answer_formed": False, "handoff_only": True,
        }
    graph = loaded_graph or XpuStructuralGraph(paths.root)
    lexicon = json.loads(paths.lexicon_path.read_text(encoding="utf-8"))
    admitted_keys = {str(row["anchor"]) for row in lexicon["anchors"]}
    normalized = validate_pressure_points(
        pressure_points,
        verified_question_structure_keys=overlay_keys,
        admitted_keys=admitted_keys,
    )

    def symbol(key: str) -> int:
        raw = next(row["symbol"] for row in lexicon["anchors"] if str(row["anchor"]) == key)
        return int(str(raw)[2:], 16)

    tensor_specs = []
    for row in normalized:
        tensor_specs.append({
            **row,
            "ruling_symbols": [symbol(value) for value in row["ruling_structure_keys"]],
            "exact_symbols": [symbol(value) for value in row["exact_structure_keys"]],
            "relation_field_symbols": [symbol(value) for value in row["relation_field_anchor_keys"]],
            "context_symbols": [symbol(value) for value in row["context_anchor_keys"]],
            "mention_symbols": [symbol(value) for value in row["mention_structure_keys"]],
            "target_symbols": [symbol(value) for value in row["target_structure_keys"]],
            "transition_context_symbols": [symbol(value) for value in row["transition_context_anchor_keys"]],
        })
    walk = graph.walk_pressure(
        selected, tensor_specs, start_block_ids=sorted(set(map(int, admitted_start_block_ids))),
        maximum_rounds=maximum_rounds, maximum_branches=maximum_branches,
    )
    blocks = {}
    for line in paths.blocks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            blocks[int(row["block_ordinal"])] = row
    workspace_blocks = set()
    for branch in walk.get("branches") or []:
        for records in branch["pressure_evidence"].values():
            for record in records:
                if "block_ordinal" in record:
                    workspace_blocks.add(int(record["block_ordinal"]))
                for key in ("occurrence", "mention_occurrence", "subject_occurrence", "relation_occurrence", "object_occurrence"):
                    if key in record:
                        workspace_blocks.add(int(record[key]["block_ordinal"]))
        for record in branch["transition_evidence"]:
            workspace_blocks.add(int(record["mention_occurrence"]["block_ordinal"]))
            workspace_blocks.add(int(record["target_parent"]["block_ordinal"]))
    citations = [{
        "block_ordinal": block_id,
        "citation_id": blocks[block_id]["citation_id"],
        "file_path": blocks[block_id]["file_path"],
        "line_start": blocks[block_id]["line_start"],
        "line_end": blocks[block_id]["line_end"],
        "text_hash": blocks[block_id]["text_hash"],
    } for block_id in sorted(workspace_blocks)]
    workspace = {
        "schema": "truemem_pressure_evidence_workspace@1",
        "status": walk["status"],
        "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "question_overlay_id": overlay["compilation_id"],
        "selected_verified_structure_keys": selected,
        "admitted_start_block_ids": sorted(set(map(int, admitted_start_block_ids))),
        "pressure_points": normalized,
        "branches": walk.get("branches") or [],
        "rounds": walk.get("rounds") or [],
        "citations": citations,
        "device_receipt": {
            "device": walk.get("device"), "device_type": walk.get("device_type"),
            "adjacency": walk.get("adjacency"),
            "whole_array_hot_path_scans": walk.get("whole_array_hot_path_scans"),
            "cpu_relationship_math": walk.get("cpu_relationship_math"),
            "cpu_frontier_ranking": walk.get("cpu_frontier_ranking"),
            "silent_device_fallback": walk.get("silent_device_fallback"),
        },
        "gather_discern_compile_handoff": True,
        "textual_answer_formed": False, "handoff_only": True,
        "operation_executed": False, "authority_layer_modified": False,
        "model_used": False, "training_performed": False,
        "ranking_modified": False, "source_authority_modified": False,
        "operator_capability_created": False,
    }
    workspace["workspace_sha256_without_self"] = hashlib.sha256(
        (json.dumps(workspace, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()
    return workspace


def traverse_compiled_question_evidence(
    paths: Any,
    question: str,
    *,
    admitted_start_block_ids: list[int],
    maximum_rounds: int = 6,
    maximum_branches: int = 4096,
    loaded_graph: XpuStructuralGraph | None = None,
    decoded_graph: dict[str, list[dict[str, Any]]] | None = None,
    verified_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile and execute an oracle-free pressure request."""
    overlay = _question_compile(question)
    lexicon = json.loads(paths.lexicon_path.read_text(encoding="utf-8"))
    admitted_keys = {str(row["anchor"]) for row in lexicon["anchors"]}
    plan = compile_query_pressure_plan(
        question, question_overlay=overlay, admitted_keys=admitted_keys,
    )
    if plan["status"] != "READY":
        return {
            "schema": "truemem_pressure_evidence_workspace@1",
            "status": plan["status"], "query_plan": plan,
            "textual_answer_formed": False, "handoff_only": True,
            "operation_executed": False, "model_used": False,
            "training_performed": False, "ranking_modified": False,
        }
    result = traverse_pressure_evidence(
        paths, question,
        selected_question_structure_keys=plan["selected_question_structure_keys"],
        admitted_start_block_ids=admitted_start_block_ids,
        pressure_points=plan["pressure_points"],
        maximum_rounds=maximum_rounds, maximum_branches=maximum_branches,
        loaded_graph=loaded_graph, decoded_graph=decoded_graph,
        verified_receipt=verified_receipt,
    )
    result["query_plan"] = plan
    result["oracle_free_request"] = True
    return result
