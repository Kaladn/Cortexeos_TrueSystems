"""Read-only TrueCore workers for the first repository-graph investigation set."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

TRUECORE_ROOT = Path(__file__).resolve().parents[2]
TRUESYSTEMS_ROOT = Path(__file__).resolve().parents[3]
TRUEMACHINE_SRC = TRUESYSTEMS_ROOT / "TrueMachine" / "src"
for import_root in (TRUECORE_ROOT, TRUEMACHINE_SRC):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from truecore.live_agents.worker_result import build_result
from truemachine.repository_views import run_view


def _execute(worker_id: str, view: str, map_dir: str, limit: int = 5000) -> dict[str, Any]:
    packet = run_view(map_dir, view, limit)
    grade = packet["result_grade"]
    if grade == "NOT_IMPLEMENTED":
        status = "NOT_IMPLEMENTED"
        continuation = "STOP_NOT_IMPLEMENTED"
        reason = "REQUIRED_GRAPH_AUTHORITY_NOT_IMPLEMENTED"
    else:
        status = "PARTIAL"
        continuation = "STOP_PARTIAL"
        reason = "STATIC_INVESTIGATION_CANDIDATES_RETURNED" if packet["locations"] else "NO_CANDIDATES_IN_INCOMPLETE_STATIC_VIEW"
    receipt = packet.pop("receipt_sha256")
    return build_result(
        worker_id=worker_id,
        operation=view,
        status=status,
        result={
            "snapshot_id": packet["snapshot_id"],
            "method": packet["method"],
            "result_grade": grade,
            "channels": packet["channels"],
            "returned": packet["returned"],
            "total_matches": packet["total_matches"],
            "truncated": packet["truncated"],
        },
        locations=packet["locations"],
        relationships=packet["relationships"],
        unresolved=packet["unresolved"],
        artifacts=[{"kind": "TRUEMACHINE_REPOSITORY_MAP", "path": str(Path(map_dir).expanduser().resolve())}],
        receipts=[{
            "receipt_type": "truemachine.repository_view@1",
            "snapshot_id": packet["snapshot_id"],
            "method": view,
            "receipt_sha256": receipt,
        }],
        continuation=continuation,
        reason_code=reason,
    )


def locate_external_entrypoints(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_external_entrypoints", "external_entrypoint_candidates", map_dir, limit)


def locate_filesystem_writers(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_filesystem_writers", "filesystem_writer_candidates", map_dir, limit)


def locate_process_execution(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_process_execution", "process_execution_candidates", map_dir, limit)


def locate_direct_truemem_references(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_direct_truemem_references", "direct_truemem_references", map_dir, limit)


def locate_truecore_bypass_candidates(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_truecore_bypass", "truecore_bypass_candidates", map_dir, limit)


def locate_agent_registration_surfaces(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_agent_registration", "agent_registration_candidates", map_dir, limit)


def locate_security_config_writers(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_security_config_writers", "security_config_writer_candidates", map_dir, limit)


def locate_canonical_evidence_writers(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_canonical_evidence_writers", "canonical_evidence_writer_candidates", map_dir, limit)


def locate_untested_privileged_sinks(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_untested_privileged_sinks", "untested_privileged_sink_candidates", map_dir, limit)


def locate_unresolved_privileged_reachability(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_unresolved_privileged_reachability", "unresolved_privileged_reachability_candidates", map_dir, limit)


def locate_detached_subgraphs(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_detached_subgraphs", "detached_subgraph_candidates", map_dir, limit)


def locate_no_incoming_dependencies(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_no_incoming_dependencies", "no_incoming_dependency_candidates", map_dir, limit)


def locate_documentation_claims_without_code(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_documentation_without_code", "documentation_claim_without_code_candidates", map_dir, limit)


def locate_code_without_documentation(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_code_without_documentation", "code_without_documentation_candidates", map_dir, limit)


def locate_duplicate_implementations(map_dir: str, limit: int = 5000) -> dict[str, Any]:
    return _execute("repo_duplicate_implementations", "duplicate_implementation_candidates", map_dir, limit)
