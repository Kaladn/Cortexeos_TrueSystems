"""Build exact, provenance-bound operational training records from source.

The records are training material, not runtime evidence. No discovered symbol
is promoted to an operation or agent, and no discovered call is executed.
"""

from __future__ import annotations

import ast
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing
import os
import resource
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "truesystems_code_intake@1"
COMPONENT_ROOTS = (
    ("TrueVisionIntake", "TrueVisionIntake"), ("TrueMem", "TrueMem"),
    ("TrueMachine", "TrueMachine"), ("TrueVision", "TrueVision"),
    ("TrueAudio", "TrueAudio"), ("TrueSpeech", "TrueSpeech"),
    ("TrueCore", "TrueCore"), ("LocalMemoryChat", "LocalMemoryChat"),
    ("ChatChain", "clearbox-chat-chain"), ("ControlAPI", "control-api"),
)
TEXT_SUFFIXES = {".py", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".md", ".txt", ".service"}
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache", "node_modules", "target"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    payload = b"".join(_canonical(row) + b"\n" for row in rows)
    path.write_bytes(payload)
    return {"path": path.name, "sha256": _digest(payload), "bytes": len(payload), "records": payload.count(b"\n")}


def _git_commit(root: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and not (set(relative.parts) & SKIP_DIRS):
            yield path


def _name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _name(node.func)
    return ""


class _Behavior(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.raises: list[dict[str, Any]] = []
        self.state_reads: set[str] = set()
        self.state_writes: set[str] = set()
        self.assertions: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append({"name": _name(node.func), "line": node.lineno})
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        self.raises.append({"exception": _name(node.exc) if node.exc else "reraised", "line": node.lineno})
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        name = _name(node)
        (self.state_writes if isinstance(node.ctx, ast.Store) else self.state_reads).add(name)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.assertions.append({"expression": ast.unparse(node.test), "line": node.lineno})
        self.generic_visit(node)


def _arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, str | None]]:
    values = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    return [{"name": item.arg, "annotation": ast.unparse(item.annotation) if item.annotation else None} for item in values]


def _unit(component: str, relative: str, source_hash: str, text: str, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, qualified: str, parent: str | None) -> dict[str, Any]:
    behavior = _Behavior(); behavior.visit(node)
    is_class = isinstance(node, ast.ClassDef)
    payload = {
        "schema": f"{SCHEMA}:code_unit", "source_system": component,
        "repository_relative_file": relative, "source_sha256": source_hash,
        "symbol": qualified, "symbol_type": "class" if is_class else ("method" if parent else "function"),
        "line_start": node.lineno, "line_end": node.end_lineno, "parent_symbol": parent,
        "source_payload": ast.get_source_segment(text, node),
        "docstring": ast.get_docstring(node, clean=False),
        "decorators": [ast.unparse(item) for item in node.decorator_list],
        "inputs": [] if is_class else _arguments(node),
        "output_annotation": None if is_class or node.returns is None else ast.unparse(node.returns),
        "calls": behavior.calls, "raises": behavior.raises,
        "state_read": sorted(behavior.state_reads), "state_written": sorted(behavior.state_writes),
        "assertions": behavior.assertions,
        "classification": {
            "test_evidence": "/tests/" in f"/{relative}" or Path(relative).name.startswith("test_"),
            "candidate_from_source": not is_class, "callable_verified": False, "agent": False,
        },
    }
    payload["record_id"] = _digest(_canonical(payload))
    return payload


def _python_units(component: str, relative: str, source_hash: str, text: str) -> tuple[list[dict], list[dict]]:
    tree = ast.parse(text, filename=relative)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend({"module": name.name, "line": node.lineno} for name in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append({"module": node.module or "", "names": [name.name for name in node.names], "line": node.lineno})
    units: list[dict] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            units.append(_unit(component, relative, source_hash, text, node, node.name, None))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    units.append(_unit(component, relative, source_hash, text, child, f"{node.name}.{child.name}", node.name))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            units.append(_unit(component, relative, source_hash, text, node, node.name, None))
    return units, imports


def _analyze_file(task: tuple[str, str, bytes, str | None]) -> tuple[dict | None, list[dict], list[dict]]:
    component, relative, raw, repository_commit = task
    digest = _digest(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, [], [{"path": relative, "failure": "invalid_utf8"}]
    imports: list[dict] = []; file_units: list[dict] = []; failures: list[dict] = []
    if Path(relative).suffix.lower() == ".py":
        try: file_units, imports = _python_units(component, relative, digest, text)
        except SyntaxError as error: failures.append({"path": relative, "failure": "syntax_error", "line": error.lineno})
    file_record = {"schema": f"{SCHEMA}:source_file", "source_system": component, "repository_commit": repository_commit, "repository_relative_file": relative, "source_sha256": digest, "byte_size": len(raw), "role": _role(relative), "imports": imports, "exact_payload": text}
    return file_record, file_units, failures


_EDGE_INDEX: dict[str, list[str]] = {}


def _edge_task(task: tuple[str, dict]) -> list[dict]:
    component, row = task
    edges = []
    for ordinal, call in enumerate(row["calls"]):
        targets = _EDGE_INDEX.get(call["name"].split(".")[-1], [])
        edge = {"schema": f"{SCHEMA}:call_edge", "source_system": component, "caller_record_id": row["record_id"], "caller": row["symbol"], "callee_observed": call["name"], "call_line": call["line"], "call_ordinal": ordinal, "resolution": "unique_component_symbol" if len(targets) == 1 else ("ambiguous_component_symbol" if targets else "external_or_dynamic"), "candidate_target_record_ids": targets}
        edge["record_id"] = _digest(_canonical(edge)); edges.append(edge)
    return edges


def _role(relative: str) -> str:
    parts = set(Path(relative).parts); name = Path(relative).name.lower(); suffix = Path(relative).suffix.lower()
    if "tests" in parts or name.startswith("test_"): return "test"
    if "research_reference_not_runtime" in parts or "external_research" in parts: return "research_reference"
    if "schemas" in parts or "schema" in name: return "schema"
    if "docs" in parts or suffix == ".md": return "documentation"
    if suffix in {".json", ".jsonl", ".toml", ".yaml", ".yml", ".service"}: return "configuration_or_manifest"
    return "source"


def _component_records(component: str, root: Path, repository_commit: str | None, workers: int) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    files: list[dict] = []; units: list[dict] = []; failures: list[dict] = []
    tasks = [(component, path.relative_to(root).as_posix(), path.read_bytes(), repository_commit) for path in _files(root)]
    if workers == 1:
        analyzed = map(_analyze_file, tasks)
    else:
        executor = ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("fork"))
        analyzed = executor.map(_analyze_file, tasks, chunksize=max(1, min(16, len(tasks) // max(1, workers * 4))))
    try:
        for file_record, file_units, file_failures in analyzed:
            if file_record is not None: files.append(file_record)
            units.extend(file_units); failures.extend(file_failures)
    finally:
        if workers != 1: executor.shutdown()

    by_short: dict[str, list[str]] = {}
    for row in units: by_short.setdefault(row["symbol"].split(".")[-1], []).append(row["record_id"])
    global _EDGE_INDEX
    _EDGE_INDEX = by_short
    edge_tasks = [(component, row) for row in units]
    if workers == 1:
        edge_groups = map(_edge_task, edge_tasks)
    else:
        context = multiprocessing.get_context("fork")
        pool = context.Pool(processes=workers)
        edge_groups = pool.imap(_edge_task, edge_tasks, chunksize=max(1, min(64, len(edge_tasks) // max(1, workers * 8))))
    try: edges = [edge for group in edge_groups for edge in group]
    finally:
        if workers != 1: pool.close(); pool.join()

    trajectories: list[dict] = []
    for row in units:
        is_cli = any(call["name"].endswith(("add_argument", "add_parser")) for call in row["calls"])
        if not (row["classification"]["test_evidence"] or is_cli): continue
        trajectories.append({
            "schema": "truesystems_operator_training_example@1", "example_id": f"partial-{row['record_id']}",
            "source_system": component, "trajectory_source": "test" if row["classification"]["test_evidence"] else "cli_definition",
            "user_request": "Resolve intent against this source-backed operational trajectory.",
            "available_operations": [call["name"] for call in row["calls"]],
            "expected_operation": {"component": component, "operation": row["symbol"], "arguments": {}, "status": "PARTIAL_REQUIRES_RUNTIME_VERIFICATION"},
            "component_result": {"status": "NOT_EXECUTED_TRAINING_PARTIAL", "source_record_id": row["record_id"]},
            "field_authority": {"authoritative": ["component_result.source_record_id"], "derived": ["available_operations", "expected_operation"], "presentation_only": ["user_request"]},
            "continuation": {"allowed": True, "reason": "Verify runtime callable and actual receipt.", "operation": "VERIFY_CALLABLE_CONTRACT"},
            "expected_operator_response": {"claims": [], "citations": [f"{row['repository_relative_file']}:{row['line_start']}"], "limitations": ["Source-derived partial trajectory; no operation was executed."], "preserved_receipt_fields": [], "follow_up": "Execute only through the component-owned boundary."},
            "forbidden_transformations": ["case_folding", "unicode_normalization", "stop_word_removal", "invented_result", "catalog_row_to_agent_promotion"],
            "unsupported_claim_conditions": ["No execution receipt exists.", "Static calls do not prove runtime order."],
            "ordered_observed_calls": row["calls"], "assertions": row["assertions"], "raises": row["raises"],
        })
    trajectories.extend({"schema": f"{SCHEMA}:failure", "source_system": component, **row} for row in failures)
    return files, units, edges, trajectories


def build_training_corpus(systems_root: Path, output_root: Path, workers: int = 24) -> dict[str, Any]:
    systems_root = systems_root.resolve(); output_root = output_root.resolve()
    if workers < 1: raise ValueError("workers must be at least 1")
    if output_root.exists(): raise FileExistsError(f"output root already exists: {output_root}")
    output_root.mkdir(parents=True); summaries = []; commit = _git_commit(systems_root)
    wall_start = time.perf_counter(); cpu_start = resource.getrusage(resource.RUSAGE_SELF); child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    for component, relative in COMPONENT_ROOTS:
        root = systems_root / relative
        if not root.is_dir(): raise FileNotFoundError(f"missing component root: {root}")
        destination = output_root / component; destination.mkdir()
        files, units, edges, trajectories = _component_records(component, root, commit, workers)
        artifacts = [
            _jsonl(destination / "level-1-code-literacy.jsonl", sorted([*files, *units], key=_canonical)),
            _jsonl(destination / "level-2-operational-relationships.jsonl", sorted(edges, key=lambda row: row["record_id"])),
            _jsonl(destination / "level-3-operator-trajectories.partial.jsonl", sorted(trajectories, key=_canonical)),
        ]
        summaries.append({"component": component, "source_files": len(files), "code_units": len(units), "call_edges": len(edges), "partial_trajectories_and_failures": len(trajectories), "artifacts": artifacts})
    wall = time.perf_counter() - wall_start; self_usage = resource.getrusage(resource.RUSAGE_SELF); child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_seconds = (self_usage.ru_utime + self_usage.ru_stime - cpu_start.ru_utime - cpu_start.ru_stime) + (child_usage.ru_utime + child_usage.ru_stime - child_start.ru_utime - child_start.ru_stime)
    records = sum(item["source_files"] + item["code_units"] + item["call_edges"] + item["partial_trajectories_and_failures"] for item in summaries)
    performance = {"workers": workers, "logical_cpus": os.cpu_count(), "elapsed_wall_seconds": wall, "aggregate_cpu_seconds": cpu_seconds, "effective_cpu_cores": cpu_seconds / wall if wall else 0.0, "machine_cpu_utilization_percent": (cpu_seconds / wall / (os.cpu_count() or 1) * 100.0) if wall else 0.0, "records_per_second": records / wall if wall else 0.0, "maximum_resident_kib": max(self_usage.ru_maxrss, child_usage.ru_maxrss)}
    manifest = {"schema": SCHEMA, "classification": "PARTIAL_NOT_ADMITTED_NOT_TRAINED", "repository_commit": commit, "component_separation": True, "source_text_normalization": "none", "record_shape_normalization": SCHEMA, "docufilm_admission_performed": False, "model_training_performed": False, "components": summaries}
    (output_root / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
    (output_root / "performance-receipt.json").write_bytes(_canonical({"schema": f"{SCHEMA}:performance_receipt", **performance}) + b"\n")
    return manifest
