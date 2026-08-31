"""TrueMem Traversal Layer v1 above the frozen Authority Layer v1."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .structural_storage import read_structural_graph, verify_structural_graph
from .xpu_structural_graph import XpuStructuralGraph


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
    required_structure_kinds: list[str] | None = None,
    maximum_hops: int = 6,
) -> dict[str, Any]:
    verification = verify_structural_graph(paths)
    if verification["status"] != "PASS":
        return {"status": "STALE_PROVENANCE", "verification": verification, "operation_executed": False}
    overlay = _question_compile(question)
    verified_overlay_keys = {row["structure_key"] for row in overlay["structures"]}
    selected = list(selected_question_structure_keys or sorted(verified_overlay_keys))
    if any(key not in verified_overlay_keys for key in selected):
        return {"status": "INVALID_STRUCTURE_PATH", "operation_executed": False, "invented_structure_rejected": True}
    graph = XpuStructuralGraph(paths.root)
    walk = graph.walk(selected, maximum_hops=maximum_hops)
    stored = read_structural_graph(paths.state / "structure_graph.awbin")
    visited = set(walk.get("visited_symbols") or [])
    reached = [row for row in stored["structures"] if int(row["symbol"][2:], 16) in visited]
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
        "schema": "truemem_structural_traversal_receipt@1",
        "status": status,
        "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "question_overlay_id": overlay["compilation_id"],
        "selected_verified_structure_keys": selected,
        "required_structure_kinds": required,
        "found_structure_kinds": found_kinds,
        "missing_structure_kinds": missing,
        "walk": walk,
        "citations": citations,
        "operation_executed": False,
        "authority_layer_modified": False,
        "model_used": False,
        "training_performed": False,
        "ranking_modified": False,
    }
    return receipt
