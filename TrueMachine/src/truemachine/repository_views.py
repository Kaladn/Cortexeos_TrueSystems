"""Named, source-grounded investigation views over a TrueMachine repository map."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from .repository_map import canonical, iter_jsonl


SCHEMA = "truemachine.repository_view@1"
VIEW_NAMES = (
    "external_entrypoint_candidates",
    "filesystem_writer_candidates",
    "process_execution_candidates",
    "direct_truemem_references",
    "truecore_bypass_candidates",
    "agent_registration_candidates",
    "security_config_writer_candidates",
    "canonical_evidence_writer_candidates",
    "untested_privileged_sink_candidates",
    "unresolved_privileged_reachability_candidates",
    "detached_subgraph_candidates",
    "no_incoming_dependency_candidates",
    "documentation_claim_without_code_candidates",
    "code_without_documentation_candidates",
    "duplicate_implementation_candidates",
)

NOT_IMPLEMENTED = {
    "truecore_bypass_candidates": (
        "EXPECTED_ROUTE_POLICY",
        "SECURITY_ROLE_ASSIGNMENTS",
        "CONTROL_OR_DATA_FLOW",
    ),
    "security_config_writer_candidates": (
        "SECURITY_CONFIGURATION_OBJECT_REGISTRY",
        "DATA_FLOW",
    ),
    "canonical_evidence_writer_candidates": (
        "CANONICAL_EVIDENCE_OBJECT_REGISTRY",
        "DATA_FLOW",
    ),
    "untested_privileged_sink_candidates": (
        "PRIVILEGED_SINK_REGISTRY",
        "TEST_TARGET_RELATIONSHIPS",
    ),
    "unresolved_privileged_reachability_candidates": (
        "PRIVILEGED_SINK_REGISTRY",
        "CONTROL_OR_DATA_FLOW",
    ),
    "documentation_claim_without_code_candidates": (
        "DOCUMENTATION_CLAIM_RELATIONSHIPS",
        "SEMANTIC_CLAIM_TO_CODE_BINDINGS",
    ),
    "code_without_documentation_candidates": (
        "DOCUMENTATION_CLAIM_RELATIONSHIPS",
        "CODE_CAPABILITY_CLASSIFICATION",
    ),
}

FILESYSTEM_WRITE_SURFACES = frozenset({
    "Path.write_bytes", "Path.write_text", "write_bytes", "write_text",
    "os.replace", "os.rename", "os.remove", "os.unlink", "os.chmod", "os.chown",
    "shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree", "shutil.move",
    "unlink", "rename", "chmod", "chown",
})
FILESYSTEM_WRITE_TAILS = frozenset({
    "chmod", "chown", "rename", "unlink", "write_bytes", "write_text",
})
PROCESS_EXECUTION_SURFACES = frozenset({
    "subprocess.call", "subprocess.check_call", "subprocess.check_output",
    "subprocess.Popen", "subprocess.run", "os.execv", "os.execve", "os.execvp",
    "os.execvpe", "os.posix_spawn", "os.posix_spawnp", "os.spawnl", "os.spawnle",
    "os.spawnlp", "os.spawnlpe", "os.spawnv", "os.spawnve", "os.spawnvp",
    "os.spawnvpe", "os.system", "pty.spawn",
})
REGISTRATION_SURFACE_TAILS = frozenset({
    "add_agent", "add_route", "add_tool", "register", "register_agent",
    "register_blueprint", "register_capability", "register_tool", "route",
    "subscribe",
})
ENTRYPOINT_NAMES = frozenset({"main", "cli", "app", "application"})


def _source_scope(path: str) -> str:
    """Classify only from exact repository path; this is not reachability proof."""
    parts = tuple(Path(path).parts)
    if "research_reference_not_runtime" in parts:
        return "RESEARCH_REFERENCE_NOT_RUNTIME"
    if "tests" in parts or Path(path).name.startswith("test_"):
        return "TEST"
    if "scripts" in parts:
        return "SCRIPT"
    if "docs" in parts or Path(path).suffix.casefold() in {".md", ".rst"}:
        return "DOCUMENTATION"
    runtime_prefixes = (
        "TrueCore/truecore/",
        "TrueMachine/src/truemachine/",
        "TrueMem/src/truemem/",
        "TrueVision/truevision_runtime/",
        "TrueAudio/trueaudio_runtime/",
        "LocalMemoryChat/src/local_memory_chat/",
    )
    if path.startswith(runtime_prefixes):
        return "RUNTIME_SOURCE"
    return "PROJECT_SOURCE"


def _manifest(map_dir: Path) -> dict[str, Any]:
    manifest = json.loads((map_dir / "manifest.json").read_bytes())
    if manifest.get("persistent_symbols") is not False:
        raise ValueError("repository view requires a symbol-free map")
    contract = manifest.get("n_n_n_contract", {})
    if contract.get("meaning") != "ownership-source_order-dependency":
        raise ValueError("repository view requires the qualified N-N-N contract")
    return manifest


def _bounded(rows: Iterable[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], int, bool]:
    selected = []
    total = 0
    for row in rows:
        total += 1
        if len(selected) < limit:
            selected.append(row)
    return selected, total, total > limit


def _call_candidates(map_dir: Path, predicate: Callable[[str], bool], grade: str, rule: str, limit: int):
    def rows():
        for site in iter_jsonl(map_dir / "call_and_import_sites.jsonl"):
            if site.get("schema") != "truesystems_call_site@1":
                continue
            surface = site.get("callee_surface") or ""
            if predicate(surface):
                yield {
                    "location_type": "CALL_SITE",
                    "path": site["path"],
                    "file_id": site["file_id"],
                    "caller_node_id": site["caller_node_id"],
                    "callee_surface": surface,
                    "line": site["line"],
                    "column": site["column"],
                    "byte_start": site["byte_start"],
                    "byte_end": site["byte_end"],
                    "result_grade": grade,
                    "classification_rule": rule,
                    "source_scope": _source_scope(site["path"]),
                }
    return _bounded(rows(), limit)


def _external_entrypoints(map_dir: Path, limit: int):
    def rows():
        for node in iter_jsonl(map_dir / "code_objects.jsonl"):
            path = node["path"]
            by_filename = path.endswith("/__main__.py") or path == "__main__.py"
            by_name = node.get("kind") in {"function", "async_function"} and node.get("name") in ENTRYPOINT_NAMES
            if by_filename or by_name:
                yield {**node, "source_scope": _source_scope(path), "result_grade": "STATIC_CANDIDATE",
                       "classification_rule": "EXACT_ENTRYPOINT_NAME_OR_DUNDER_MAIN_PATH"}
    return _bounded(rows(), limit)


def _direct_truemem(map_dir: Path, limit: int):
    def rows():
        for site in iter_jsonl(map_dir / "call_and_import_sites.jsonl"):
            if site.get("schema") == "truesystems_import_site@1":
                surface = ".".join(filter(None, (site.get("module"), site.get("name"))))
            elif site.get("schema") == "truesystems_call_site@1":
                surface = site.get("callee_surface") or ""
            else:
                continue
            is_direct = (
                site.get("schema") == "truesystems_import_site@1" and "truemem" in surface.casefold()
            ) or (
                site.get("schema") == "truesystems_call_site@1"
                and surface.casefold().split(".", 1)[0] == "truemem"
            )
            if is_direct:
                yield {**site, "exact_surface": surface, "source_scope": _source_scope(site["path"]),
                       "result_grade": "WITNESSED_STATIC",
                       "classification_rule": "EXACT_SURFACE_CONTAINS_TRUEMEM"}
    return _bounded(rows(), limit)


def _registration(map_dir: Path, limit: int):
    return _call_candidates(
        map_dir,
        lambda surface: surface.split(".")[-1].casefold() in REGISTRATION_SURFACE_TAILS,
        "STATIC_CANDIDATE",
        "EXACT_CALL_TAIL_IN_REGISTRATION_SURFACE_REGISTRY",
        limit,
    )


def _node_and_incoming(map_dir: Path):
    nodes = {}
    for node in iter_jsonl(map_dir / "code_objects.jsonl"):
        nodes[node["node_id"]] = node
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in iter_jsonl(map_dir / "resolved_dependency_relationships.jsonl"):
        target = edge.get("target_node_id")
        if target:
            incoming[target].append(edge)
    return nodes, incoming


def _detached(map_dir: Path, limit: int):
    nodes, incoming = _node_and_incoming(map_dir)
    paths_with_external_incoming = set()
    for target, edges in incoming.items():
        target_path = nodes[target]["path"]
        for edge in edges:
            source = nodes.get(edge["source_node_id"])
            if source and source["path"] != target_path:
                paths_with_external_incoming.add(target_path)
    rows = ({**node, "source_scope": _source_scope(node["path"]), "result_grade": "STATIC_CANDIDATE",
             "classification_rule": "MODULE_HAS_NO_UNIQUELY_RESOLVED_CROSS_FILE_CALL_IN_CURRENT_MAP"}
            for node in nodes.values()
            if node.get("kind") == "module" and node["path"] not in paths_with_external_incoming)
    return _bounded(rows, limit)


def _no_incoming(map_dir: Path, limit: int):
    nodes, incoming = _node_and_incoming(map_dir)
    rows = ({**node, "source_scope": _source_scope(node["path"]), "result_grade": "STATIC_CANDIDATE",
             "classification_rule": "NO_UNIQUELY_RESOLVED_INCOMING_CALL_IN_CURRENT_MAP"}
            for node_id, node in nodes.items()
            if node.get("kind") in {"class", "function", "async_function"} and node_id not in incoming)
    return _bounded(rows, limit)


def _duplicates(map_dir: Path, limit: int):
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in iter_jsonl(map_dir / "code_objects.jsonl"):
        if node.get("kind") not in {"class", "function", "async_function"}:
            continue
        by_hash[node["exact_span_sha256"]].append(node)
        by_name[node["name"]].append(node)
    def rows():
        for digest_value, members in sorted(by_hash.items()):
            if len(members) > 1:
                yield {"location_type": "EXACT_DUPLICATE_GROUP", "exact_span_sha256": digest_value,
                       "members": [{**member, "source_scope": _source_scope(member["path"])} for member in members],
                       "source_scopes": sorted({_source_scope(member["path"]) for member in members}),
                       "result_grade": "WITNESSED_STATIC",
                       "classification_rule": "IDENTICAL_EXACT_SOURCE_SPAN_SHA256"}
        for name, members in sorted(by_name.items()):
            if len(members) > 1 and len({item["exact_span_sha256"] for item in members}) > 1:
                yield {"location_type": "SAME_NAME_GROUP", "exact_name": name, "members": members,
                       "source_scopes": sorted({_source_scope(member["path"]) for member in members}),
                       "result_grade": "STATIC_CANDIDATE",
                       "classification_rule": "SAME_EXACT_DECLARED_NAME_DIFFERENT_SOURCE_HASH"}
    return _bounded(rows(), limit)


def run_view(map_dir: str | Path, view: str, limit: int = 5000) -> dict[str, Any]:
    root = Path(map_dir).expanduser().resolve()
    manifest = _manifest(root)
    if view not in VIEW_NAMES:
        raise ValueError(f"unknown repository view: {view}")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100_000:
        raise ValueError("limit must be an integer from 1 through 100000")
    if view in NOT_IMPLEMENTED:
        locations: list[dict[str, Any]] = []
        total = 0
        truncated = False
        grade = "NOT_IMPLEMENTED"
        unresolved = [{"required_relationship": item, "state": "NOT_IMPLEMENTED"} for item in NOT_IMPLEMENTED[view]]
    elif view == "external_entrypoint_candidates":
        locations, total, truncated = _external_entrypoints(root, limit); grade = "STATIC_CANDIDATE"; unresolved = []
    elif view == "filesystem_writer_candidates":
        locations, total, truncated = _call_candidates(root, lambda value: value in FILESYSTEM_WRITE_SURFACES or value.split(".")[-1] in FILESYSTEM_WRITE_TAILS,
            "STATIC_CANDIDATE", "EXACT_CALL_SURFACE_IN_FILESYSTEM_WRITE_REGISTRY", limit); grade = "STATIC_CANDIDATE"; unresolved = []
    elif view == "process_execution_candidates":
        locations, total, truncated = _call_candidates(root, lambda value: value in PROCESS_EXECUTION_SURFACES,
            "STATIC_CANDIDATE", "EXACT_CALL_SURFACE_IN_PROCESS_EXECUTION_REGISTRY", limit); grade = "STATIC_CANDIDATE"; unresolved = []
    elif view == "direct_truemem_references":
        locations, total, truncated = _direct_truemem(root, limit); grade = "WITNESSED_STATIC"; unresolved = []
    elif view == "agent_registration_candidates":
        locations, total, truncated = _registration(root, limit); grade = "STATIC_CANDIDATE"; unresolved = []
    elif view == "detached_subgraph_candidates":
        locations, total, truncated = _detached(root, limit); grade = "STATIC_CANDIDATE"; unresolved = []
    elif view == "no_incoming_dependency_candidates":
        locations, total, truncated = _no_incoming(root, limit); grade = "STATIC_CANDIDATE"; unresolved = []
    elif view == "duplicate_implementation_candidates":
        locations, total, truncated = _duplicates(root, limit); grade = "MIXED_WITNESSED_AND_CANDIDATE"; unresolved = []
    else:
        raise AssertionError("view registry and dispatcher differ")
    relationships = []
    for location in locations:
        source_id = location.get("caller_node_id") or location.get("scope_node_id")
        target_surface = location.get("callee_surface") or location.get("exact_surface")
        if source_id and target_surface:
            relationships.append({
                "relation": "STATIC_SURFACE_MATCH",
                "source_node_id": source_id,
                "target_surface": target_surface,
                "resolution": "WITNESSED_STATIC",
                "result_grade": location["result_grade"],
                "classification_rule": location["classification_rule"],
                "witness": {key: location[key] for key in ("path", "file_id", "line", "column", "byte_start", "byte_end") if key in location},
            })
    packet = {
        "schema": SCHEMA,
        "snapshot_id": manifest["snapshot_id"],
        "method": view,
        "result_grade": grade,
        "locations": locations,
        "relationships": relationships,
        "channels": {
            "ownership": "AVAILABLE_IN_MAP",
            "source_order": "AVAILABLE_IN_MAP",
            "dependency": "AVAILABLE_WITH_EXPLICIT_RESOLUTION_STATES",
            "control_flow": manifest["n_n_n_contract"]["control_flow_status"],
            "data_flow": manifest["n_n_n_contract"]["data_flow_status"],
            "tests": "NOT_IMPLEMENTED",
            "documentation_claims": "NOT_IMPLEMENTED",
            "security_roles": "NOT_IMPLEMENTED",
        },
        "unresolved": unresolved,
        "returned": len(locations),
        "total_matches": total,
        "truncated": truncated,
        "answer": None,
    }
    packet["receipt_sha256"] = hashlib.sha256(canonical(packet)).hexdigest()
    return packet
