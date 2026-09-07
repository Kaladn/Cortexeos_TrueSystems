"""Extract parser-observed function method lessons without inventing intent or results."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np


def _strings(values: list[str]) -> tuple[np.ndarray, np.ndarray]:
    encoded = [value.encode("utf-8") for value in values]
    offsets = np.zeros(len(values) + 1, dtype=np.uint64)
    for index, value in enumerate(encoded):
        offsets[index + 1] = offsets[index] + len(value)
    return np.frombuffer(b"".join(encoded), dtype=np.uint8).copy(), offsets


def _name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _scope_nodes(root: ast.AST) -> Iterable[ast.AST]:
    stack = list(reversed(list(ast.iter_child_nodes(root))))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield node
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _mistake(node: ast.FunctionDef | ast.AsyncFunctionDef, text: str) -> dict[str, Any]:
    defaults = [*node.args.defaults, *(value for value in node.args.kw_defaults if value is not None)]
    for value in defaults:
        if isinstance(value, (ast.List, ast.Dict, ast.Set, ast.Call)):
            return {
                "rule_id": "evaluated_default_state_v1",
                "candidate": "A mutable or constructed default can be shared or evaluated earlier than the caller expects.",
                "trigger_surface": ast.get_source_segment(text, value),
                "line": value.lineno,
                "what_not_to_do": "Do not use mutable or stateful constructed defaults unless shared evaluation is the explicit contract.",
            }
    for child in _scope_nodes(node):
        if isinstance(child, ast.ExceptHandler) and child.type is None:
            return {
                "rule_id": "bare_except_v1", "candidate": "A bare exception handler can hide termination and unrelated failures.",
                "trigger_surface": "except:", "line": child.lineno,
                "what_not_to_do": "Do not catch every exception class when the function can name the failures it handles.",
            }
        if isinstance(child, ast.Call) and _name(child.func) in {"subprocess.run", "subprocess.call", "subprocess.Popen"}:
            for keyword_node in child.keywords:
                if keyword_node.arg == "shell" and isinstance(keyword_node.value, ast.Constant) and keyword_node.value.value is True:
                    return {
                        "rule_id": "subprocess_shell_true_v1", "candidate": "Shell interpretation can turn data into command syntax.",
                        "trigger_surface": ast.get_source_segment(text, child), "line": child.lineno,
                        "what_not_to_do": "Do not pass untrusted or composed text through shell=True.",
                    }
    return {
        "rule_id": "no_rule_backed_candidate_v1",
        "candidate": None,
        "trigger_surface": None,
        "line": None,
        "what_not_to_do": "No corpus-independent mistake rule fired; do not invent one from the function name.",
    }


def build_function_method_curriculum(*, source_root: Path, catalog_csv: Path, output_path: Path) -> dict[str, Any]:
    with catalog_csv.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["language"] == "Python" and row["parse_status"] == "PYTHON_AST_PARSED"]
    by_hash: dict[str, list[str]] = {}
    for row in rows:
        by_hash.setdefault(row["source_sha256"], []).append(row["source_relative_path"])

    sources = []
    methods = []
    reasons = []
    results = []
    mistakes = []
    source_hashes = []
    line_start = []
    line_end = []
    for source_hash, paths in sorted(by_hash.items()):
        raw = (source_root / sorted(paths)[0]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source_hash:
            raise ValueError("function curriculum source hash mismatch")
        text = raw.decode("utf-8")
        tree = ast.parse(text, filename=sorted(paths)[0], type_comments=True)
        functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        functions.sort(key=lambda node: (node.lineno, node.col_offset, node.name))
        for node in functions:
            scoped = list(_scope_nodes(node))
            returns = [child for child in scoped if isinstance(child, (ast.Return, ast.Yield, ast.YieldFrom))]
            raises = [child for child in scoped if isinstance(child, ast.Raise)]
            calls = [child for child in scoped if isinstance(child, ast.Call)]
            method = {
                "kind": type(node).__name__,
                "name": node.name,
                "parameters": [value.arg for value in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]],
                "ordered_calls": [{"surface": _name(value.func), "line": value.lineno} for value in calls],
                "control_flow": {
                    kind: sum(isinstance(value, node_type) for value in scoped)
                    for kind, node_type in (("if", ast.If), ("for", (ast.For, ast.AsyncFor)), ("while", ast.While), ("try", ast.Try), ("with", (ast.With, ast.AsyncWith)))
                },
            }
            docstring = ast.get_docstring(node, clean=False)
            reason = {
                "value": docstring,
                "authority": "explicit_function_docstring" if docstring is not None else "unavailable_not_invented",
            }
            result = {
                "return_and_yield_surfaces": [ast.get_source_segment(text, value) for value in returns],
                "raise_surfaces": [ast.get_source_segment(text, value) for value in raises],
                "runtime_result_observed": False,
            }
            sources.append(ast.get_source_segment(text, node) or "")
            methods.append(json.dumps(method, sort_keys=True, separators=(",", ":")))
            reasons.append(json.dumps(reason, sort_keys=True, separators=(",", ":")))
            results.append(json.dumps(result, sort_keys=True, separators=(",", ":")))
            mistakes.append(json.dumps(_mistake(node, text), sort_keys=True, separators=(",", ":")))
            source_hashes.append(bytes.fromhex(source_hash))
            line_start.append(node.lineno)
            line_end.append(node.end_lineno or node.lineno)

    arrays: dict[str, np.ndarray] = {
        "source_sha256": np.frombuffer(b"".join(source_hashes), dtype=np.uint8).reshape((-1, 32)),
        "line_start": np.asarray(line_start, dtype=np.uint32),
        "line_end": np.asarray(line_end, dtype=np.uint32),
    }
    for name, values in (("accepted_source", sources), ("method", methods), ("reason", reasons), ("result", results), ("most_likely_mistake", mistakes)):
        arrays[f"{name}_utf8"], arrays[f"{name}_offsets"] = _strings(values)
    np.savez_compressed(output_path, **arrays)
    return {
        "function_example_count": len(sources),
        "parser_accepted_source_groups": len(by_hash),
        "reason_from_docstring_count": sum('"explicit_function_docstring"' in value for value in reasons),
        "rule_backed_mistake_candidate_count": sum('"no_rule_backed_candidate_v1"' not in value for value in mistakes),
        "lesson_order": ["accepted_source", "method", "reason", "result", "most_likely_mistake", "how_it_is_done", "what_not_to_do"],
        "how_it_is_done": "accepted_source exact AST span",
        "runtime_results_observed": False,
    }
