#!/usr/bin/env python3
"""
Phase C: Contract Inference Engine

Reads categorized CSVs, reads actual source code for each function,
infers structured contracts using AST analysis + heuristics.

Usage:
    python phase_c_infer.py <category_name> [<category_name2> ...]
    python phase_c_infer.py engines
    python phase_c_infer.py retrievers validators transformers storage extractors
    python phase_c_infer.py controllers agents workers pipelines services

Reads from:  F:\contract_extraction\categories\{category}.csv
Writes to:   F:\contract_extraction\contracts\{category}_contracts.csv
"""

import ast
import csv
import os
import re
import sys
import hashlib
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple, Any

BASE_DIR = r"F:\contract_extraction"
CAT_DIR = os.path.join(BASE_DIR, "categories")
OUT_DIR = os.path.join(BASE_DIR, "contracts")
SOURCE_ROOT = "F:\\"

os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================================
# SOURCE CODE CACHE — read each file only once
# ============================================================================

_file_cache: Dict[str, Optional[str]] = {}
_ast_cache: Dict[str, Optional[ast.Module]] = {}

def read_source(file_path: str) -> Optional[str]:
    """Read source file, cached."""
    if file_path not in _file_cache:
        full_path = os.path.join(SOURCE_ROOT, file_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                _file_cache[file_path] = f.read()
        except (OSError, IOError):
            _file_cache[file_path] = None
    return _file_cache[file_path]

def parse_ast(file_path: str) -> Optional[ast.Module]:
    """Parse AST for file, cached."""
    if file_path not in _ast_cache:
        source = read_source(file_path)
        if source:
            try:
                _ast_cache[file_path] = ast.parse(source)
            except SyntaxError:
                _ast_cache[file_path] = None
        else:
            _ast_cache[file_path] = None
    return _ast_cache[file_path]

def get_source_lines(file_path: str, start: int, end: int) -> str:
    """Get source lines for a function."""
    source = read_source(file_path)
    if not source:
        return ""
    lines = source.splitlines()
    s = max(0, start - 1)
    e = min(len(lines), end)
    return "\n".join(lines[s:e])


# ============================================================================
# AST-BASED CONTRACT INFERENCE
# ============================================================================

def find_function_node(file_path: str, symbol_name: str, line_start: int) -> Optional[ast.FunctionDef]:
    """Find the AST node for a function by name and approximate line."""
    tree = parse_ast(file_path)
    if not tree:
        return None

    # Handle Class.method format
    parts = symbol_name.split(".")
    target_name = parts[-1] if parts else symbol_name

    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == target_name:
                candidates.append(node)

    if not candidates:
        return None

    # Pick the one closest to line_start
    try:
        ls = int(line_start)
    except (ValueError, TypeError):
        ls = 0

    best = min(candidates, key=lambda n: abs(getattr(n, 'lineno', 0) - ls))
    return best


def infer_input_shape(node: ast.FunctionDef) -> str:
    """Infer input shape from function signature."""
    if not node:
        return "UNKNOWN"

    args = node.args
    parts = []

    # Regular args
    all_args = args.args + args.posonlyargs
    defaults_offset = len(all_args) - len(args.defaults)

    for i, arg in enumerate(all_args):
        if arg.arg == "self" or arg.arg == "cls":
            continue
        name = arg.arg
        ann = ""
        if arg.annotation:
            ann = ast.unparse(arg.annotation)
        has_default = i >= defaults_offset
        if ann:
            parts.append(f"{name}:{ann}{'?' if has_default else ''}")
        else:
            parts.append(f"{name}{'?' if has_default else ''}")

    # *args
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")

    # **kwargs
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")

    # Keyword-only args
    for i, arg in enumerate(args.kwonlyargs):
        name = arg.arg
        ann = ""
        if arg.annotation:
            ann = ast.unparse(arg.annotation)
        if ann:
            parts.append(f"{name}:{ann}")
        else:
            parts.append(name)

    return "|".join(parts) if parts else "none"


def infer_output_shape(node: ast.FunctionDef, source_lines: str) -> str:
    """Infer output shape from return annotation or return statements."""
    if not node:
        return "UNKNOWN"

    # Check return annotation
    if node.returns:
        return ast.unparse(node.returns)

    # Scan return statements
    return_values = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            if child.value is None:
                return_values.add("None")
            elif isinstance(child.value, ast.Constant):
                return_values.add(type(child.value.value).__name__)
            elif isinstance(child.value, ast.Dict):
                return_values.add("dict")
            elif isinstance(child.value, ast.List):
                return_values.add("list")
            elif isinstance(child.value, ast.Tuple):
                return_values.add("tuple")
            elif isinstance(child.value, ast.Call):
                if isinstance(child.value.func, ast.Name):
                    return_values.add(child.value.func.id)
                elif isinstance(child.value.func, ast.Attribute):
                    return_values.add(child.value.func.attr)
                else:
                    return_values.add("call_result")
            elif isinstance(child.value, ast.Name):
                return_values.add(child.value.id)
            elif isinstance(child.value, ast.BoolOp):
                return_values.add("bool")
            elif isinstance(child.value, ast.Compare):
                return_values.add("bool")
            else:
                return_values.add("inferred")

    if not return_values:
        # Check if it's a generator
        for child in ast.walk(node):
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return "generator"
        return "None"

    return "|".join(sorted(return_values))


def infer_side_effects(node: ast.FunctionDef, source_lines: str) -> str:
    """Detect side effects from code patterns."""
    if not node:
        return "UNKNOWN"

    effects = set()
    src = source_lines.lower()

    # File I/O
    if any(p in src for p in ["open(", "write(", "writelines(", "f.write", "pathlib", "os.remove",
                               "os.rename", "shutil.", "os.makedirs", "os.mkdir"]):
        effects.add("disk")

    # Network
    if any(p in src for p in ["requests.", "urllib", "http", "socket.", "aiohttp",
                               "fetch(", "curl", "grpc", "websocket"]):
        effects.add("network")

    # Database
    if any(p in src for p in ["cursor.", "execute(", "commit(", "rollback(", "session.",
                               "db.", "database", "sqlite", "postgres", "mongo", "redis"]):
        effects.add("db")

    # Subprocess
    if any(p in src for p in ["subprocess.", "os.system(", "popen(", "exec(", "eval("]):
        effects.add("subprocess")

    # State mutation
    if any(p in src for p in ["self.", "cls."]):
        # Check for assignments to self
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                        if target.value.id in ("self", "cls"):
                            effects.add("mutation")
                            break

    # Logging
    if any(p in src for p in ["logging.", "logger.", "log.", "print("]):
        effects.add("logging")

    return "|".join(sorted(effects)) if effects else "none"


def infer_dependencies(node: ast.FunctionDef, source_lines: str, file_path: str) -> str:
    """Infer dependencies from imports and references."""
    if not node:
        return "UNKNOWN"

    deps = set()

    # Check file-level imports
    tree = parse_ast(file_path)
    if tree:
        for n in ast.iter_child_nodes(tree):
            if isinstance(n, ast.Import):
                for alias in n.names:
                    deps.add(alias.name.split(".")[0])
            elif isinstance(n, ast.ImportFrom):
                if n.module and not n.module.startswith("__"):
                    deps.add(n.module.split(".")[0])

    # Filter out stdlib
    stdlib = {"os", "sys", "re", "json", "csv", "time", "datetime", "math",
              "collections", "itertools", "functools", "typing", "pathlib",
              "hashlib", "struct", "zlib", "io", "copy", "abc", "enum",
              "dataclasses", "logging", "traceback", "unittest", "tempfile",
              "shutil", "threading", "multiprocessing", "asyncio", "uuid",
              "random", "string", "textwrap", "inspect", "contextlib",
              "warnings", "operator", "bisect", "heapq", "pickle", "base64",
              "configparser", "argparse", "subprocess", "signal", "socket",
              "http", "urllib", "ssl", "email", "html", "xml", "pprint",
              "importlib", "types", "weakref", "array", "queue", "glob"}
    deps -= stdlib

    return "|".join(sorted(deps)[:10]) if deps else "none"


def infer_failure_modes(node: ast.FunctionDef, source_lines: str) -> str:
    """Infer failure modes from exception handling and return patterns."""
    if not node:
        return "UNKNOWN"

    modes = set()

    for child in ast.walk(node):
        # Explicit raises
        if isinstance(child, ast.Raise):
            if child.exc:
                if isinstance(child.exc, ast.Call) and isinstance(child.exc.func, ast.Name):
                    modes.add(f"raises_{child.exc.func.id}")
                elif isinstance(child.exc, ast.Name):
                    modes.add(f"raises_{child.exc.id}")
                else:
                    modes.add("raises_exception")
            else:
                modes.add("re_raises")

        # Return None patterns
        if isinstance(child, ast.Return):
            if child.value is None:
                modes.add("returns_none")
            elif isinstance(child.value, ast.Constant) and child.value.value is None:
                modes.add("returns_none")
            elif isinstance(child.value, ast.List) and len(child.value.elts) == 0:
                modes.add("returns_empty_list")
            elif isinstance(child.value, ast.Dict) and len(child.value.keys) == 0:
                modes.add("returns_empty_dict")

    # Check for try/except
    for child in ast.walk(node):
        if isinstance(child, ast.Try):
            modes.add("has_try_except")

    return "|".join(sorted(modes)) if modes else "unknown"


def infer_statefulness(node: ast.FunctionDef, source_lines: str) -> str:
    """Determine if function is stateful or stateless."""
    if not node:
        return "UNKNOWN"

    # Check for self/cls access
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
            if child.value.id in ("self", "cls"):
                return "STATEFUL"

    # Check for global/nonlocal
    for child in ast.walk(node):
        if isinstance(child, (ast.Global, ast.Nonlocal)):
            return "STATEFUL"

    return "STATELESS"


def infer_sync_mode(node: ast.FunctionDef, function_type: str) -> str:
    """Determine sync/async mode."""
    if not node:
        return "UNKNOWN"

    if isinstance(node, ast.AsyncFunctionDef):
        return "ASYNC"

    if function_type and "async" in function_type.lower():
        return "ASYNC"

    return "SYNC"


def infer_assumptions_in(node: ast.FunctionDef, docstring: str, source_lines: str) -> str:
    """Infer input assumptions."""
    if not node:
        return "UNKNOWN"

    assumptions = []

    # From type annotations
    for arg in node.args.args:
        if arg.arg in ("self", "cls"):
            continue
        if arg.annotation:
            ann = ast.unparse(arg.annotation)
            assumptions.append(f"{arg.arg} must be {ann}")

    # From docstring patterns
    if docstring:
        doc_lower = docstring.lower()
        if "must be" in doc_lower or "required" in doc_lower:
            assumptions.append("has_explicit_requirements")
        if "non-null" in doc_lower or "not none" in doc_lower or "cannot be none" in doc_lower:
            assumptions.append("non_null_inputs")
        if "normalized" in doc_lower or "lowercase" in doc_lower:
            assumptions.append("expects_normalized_input")
        if "valid" in doc_lower:
            assumptions.append("expects_valid_input")
        if "authenticated" in doc_lower:
            assumptions.append("requires_auth_context")

    # From assertions in code
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            assumptions.append("has_assertions")
            break

    return "|".join(assumptions[:5]) if assumptions else "implicit"


def infer_assumptions_out(node: ast.FunctionDef, docstring: str) -> str:
    """Infer output assumptions."""
    if not node:
        return "UNKNOWN"

    assumptions = []

    # Return type annotation
    if node.returns:
        ann = ast.unparse(node.returns)
        assumptions.append(f"returns_{ann}")

    # Docstring clues
    if docstring:
        doc_lower = docstring.lower()
        if "returns" in doc_lower:
            assumptions.append("documented_return")
        if "never none" in doc_lower or "always returns" in doc_lower:
            assumptions.append("guaranteed_non_null")
        if "sorted" in doc_lower:
            assumptions.append("sorted_output")
        if "validated" in doc_lower:
            assumptions.append("validated_output")

    return "|".join(assumptions[:5]) if assumptions else "implicit"


def get_docstring_text(node: ast.FunctionDef) -> str:
    """Extract docstring from AST node."""
    if not node or not node.body:
        return ""
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return first.value.value.strip()
    return ""


def compute_trust_level(confidence: str, contract_completeness: int) -> str:
    """Compute trust level based on confidence and contract completeness."""
    if confidence == "HIGH" and contract_completeness >= 4:
        return "HIGH"
    elif confidence in ("HIGH", "MEDIUM") and contract_completeness >= 2:
        return "MEDIUM"
    return "LOW"


def determine_contract_status(input_shape, output_shape, side_effects, assumptions_in) -> str:
    """Determine overall contract status."""
    unknowns = sum(1 for v in [input_shape, output_shape, side_effects, assumptions_in]
                   if v in ("UNKNOWN", ""))
    if unknowns == 0:
        return "READY"
    elif unknowns <= 1:
        return "PARTIAL"
    elif unknowns <= 2:
        return "UNKNOWN"
    return "BLOCKED"


def determine_promotion(contract_status: str, trust_level: str) -> str:
    """Determine promotion readiness."""
    if contract_status == "READY" and trust_level in ("HIGH", "MEDIUM"):
        return "YES"
    elif contract_status in ("READY", "PARTIAL") and trust_level in ("HIGH", "MEDIUM", "LOW"):
        return "REVIEW"
    return "NO"


# ============================================================================
# MAIN CONTRACT INFERENCE
# ============================================================================

def infer_contract(row: dict) -> dict:
    """Infer contract for a single row. Returns the row with new columns added."""
    file_path = row.get("file_path", "")
    symbol_name = row.get("symbol_name", "")
    line_start = row.get("line_start", "0")
    line_end = row.get("line_end", "0")
    function_type = row.get("function_type", "")
    confidence = row.get("category_confidence", "LOW")

    # Find the AST node
    node = find_function_node(file_path, symbol_name, line_start)

    # Get source lines
    try:
        src_lines = get_source_lines(file_path, int(line_start), int(line_end))
    except (ValueError, TypeError):
        src_lines = ""

    # Get docstring
    docstring = get_docstring_text(node) if node else ""

    # Infer all contract fields
    input_shape = infer_input_shape(node)
    output_shape = infer_output_shape(node, src_lines)
    assumptions_in = infer_assumptions_in(node, docstring, src_lines)
    assumptions_out = infer_assumptions_out(node, docstring)
    side_effects = infer_side_effects(node, src_lines)
    dependencies = infer_dependencies(node, src_lines, file_path)
    failure_modes = infer_failure_modes(node, src_lines)
    statefulness = infer_statefulness(node, src_lines)
    sync_mode = infer_sync_mode(node, function_type)

    # Compute completeness score (how many fields are non-UNKNOWN)
    completeness = sum(1 for v in [input_shape, output_shape, side_effects, assumptions_in, statefulness]
                       if v not in ("UNKNOWN", ""))

    trust_level = compute_trust_level(confidence, completeness)
    contract_status = determine_contract_status(input_shape, output_shape, side_effects, assumptions_in)
    promotion_ready = determine_promotion(contract_status, trust_level)

    # Build reason
    reasons = []
    if node:
        reasons.append("ast_parsed")
    else:
        reasons.append("no_ast_node")
    if docstring:
        reasons.append("has_docstring")
    if node and node.returns:
        reasons.append("has_return_annotation")
    reasons.append(f"completeness={completeness}/5")

    # Add new columns
    row["contract_status"] = contract_status
    row["input_shape"] = input_shape
    row["output_shape"] = output_shape
    row["assumptions_in"] = assumptions_in
    row["assumptions_out"] = assumptions_out
    row["side_effects"] = side_effects
    row["dependencies"] = dependencies
    row["failure_modes"] = failure_modes
    row["statefulness"] = statefulness
    row["sync_mode"] = sync_mode
    row["trust_level"] = trust_level
    row["promotion_ready"] = promotion_ready
    row["contract_reason"] = "|".join(reasons)

    return row


def process_category(category_name: str) -> dict:
    """Process a single category file. Returns stats dict."""
    input_file = os.path.join(CAT_DIR, f"{category_name}.csv")
    output_file = os.path.join(OUT_DIR, f"{category_name}_contracts.csv")

    if not os.path.exists(input_file):
        print(f"  SKIP: {input_file} not found")
        return {"category": category_name, "total": 0, "error": "file not found"}

    # Read input
    rows = []
    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        input_fields = reader.fieldnames[:]
        for row in reader:
            rows.append(row)

    if not rows:
        print(f"  SKIP: {category_name} is empty")
        return {"category": category_name, "total": 0}

    # Define output fields
    new_fields = [
        "contract_status", "input_shape", "output_shape",
        "assumptions_in", "assumptions_out", "side_effects",
        "dependencies", "failure_modes", "statefulness",
        "sync_mode", "trust_level", "promotion_ready", "contract_reason"
    ]
    output_fields = input_fields + new_fields

    # Process each row
    print(f"  Processing {category_name}: {len(rows)} rows...")
    processed = []
    for i, row in enumerate(rows):
        enriched = infer_contract(row)
        processed.append(enriched)
        if (i + 1) % 500 == 0:
            print(f"    ...{i+1}/{len(rows)}")

    # Write output
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(processed)

    # Compute stats
    stats = {
        "category": category_name,
        "total_rows": len(processed),
        "ready_count": sum(1 for r in processed if r["contract_status"] == "READY"),
        "partial_count": sum(1 for r in processed if r["contract_status"] == "PARTIAL"),
        "unknown_count": sum(1 for r in processed if r["contract_status"] == "UNKNOWN"),
        "blocked_count": sum(1 for r in processed if r["contract_status"] == "BLOCKED"),
        "promotion_yes_count": sum(1 for r in processed if r["promotion_ready"] == "YES"),
        "promotion_review_count": sum(1 for r in processed if r["promotion_ready"] == "REVIEW"),
        "promotion_no_count": sum(1 for r in processed if r["promotion_ready"] == "NO"),
        "high_trust_count": sum(1 for r in processed if r["trust_level"] == "HIGH"),
        "medium_trust_count": sum(1 for r in processed if r["trust_level"] == "MEDIUM"),
        "low_trust_count": sum(1 for r in processed if r["trust_level"] == "LOW"),
        "output_file": f"contracts/{category_name}_contracts.csv",
    }

    # Side effect distribution
    se_counter = Counter()
    for r in processed:
        for se in r.get("side_effects", "").split("|"):
            if se.strip():
                se_counter[se.strip()] += 1
    stats["side_effects_dist"] = dict(se_counter.most_common(5))

    print(f"  Done: {stats['ready_count']} READY, {stats['promotion_yes_count']} YES, "
          f"{stats['promotion_review_count']} REVIEW, {stats['promotion_no_count']} NO")

    # Clear caches periodically to manage memory
    _file_cache.clear()
    _ast_cache.clear()

    return stats


def main():
    categories = sys.argv[1:]
    if not categories:
        print("Usage: python phase_c_infer.py <category1> [category2] ...")
        sys.exit(1)

    print("=" * 60)
    print("Phase C: Contract Inference Agent")
    print("=" * 60)
    print(f"Categories to process: {categories}")
    print()

    all_stats = []
    total_rows = 0
    total_ready = 0
    total_yes = 0
    total_review = 0
    total_no = 0
    global_se = Counter()

    for cat in categories:
        stats = process_category(cat)
        all_stats.append(stats)
        total_rows += stats.get("total_rows", 0)
        total_ready += stats.get("ready_count", 0)
        total_yes += stats.get("promotion_yes_count", 0)
        total_review += stats.get("promotion_review_count", 0)
        total_no += stats.get("promotion_no_count", 0)
        for se, cnt in stats.get("side_effects_dist", {}).items():
            global_se[se] += cnt
        print()

    # Write contract_index.csv
    index_file = os.path.join(OUT_DIR, "contract_index.csv")
    index_fields = [
        "category", "total_rows", "ready_count", "partial_count",
        "unknown_count", "blocked_count", "promotion_yes_count",
        "promotion_review_count", "promotion_no_count",
        "high_trust_count", "medium_trust_count", "low_trust_count",
        "output_file"
    ]

    with open(index_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=index_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_stats)

    # Final summary
    print("=" * 60)
    print("PHASE C FINAL SUMMARY")
    print("=" * 60)
    print(f"Total rows processed:       {total_rows}")
    print(f"Total READY contracts:      {total_ready}")
    print(f"Total REVIEW promotions:    {total_review}")
    print(f"Total YES promotions:       {total_yes}")
    print(f"Total NO promotions:        {total_no}")
    print()
    print("Counts by category:")
    for s in sorted(all_stats, key=lambda x: -x.get("total_rows", 0)):
        cat = s["category"]
        t = s.get("total_rows", 0)
        r = s.get("ready_count", 0)
        y = s.get("promotion_yes_count", 0)
        print(f"  {cat:25s}  total={t:>5}  ready={r:>5}  promo_yes={y:>5}")

    print()
    print("Top 10 categories by promotion_ready=YES:")
    for s in sorted(all_stats, key=lambda x: -x.get("promotion_yes_count", 0))[:10]:
        print(f"  {s['category']:25s}  {s.get('promotion_yes_count', 0):>5} YES")

    print()
    print("Top side_effect patterns:")
    for se, cnt in global_se.most_common(10):
        print(f"  {se:20s}  {cnt:>5}")

    unknown_heavy = sum(1 for s in all_stats
                        for _ in range(s.get("unknown_count", 0) + s.get("blocked_count", 0)))
    print(f"\nTotal UNKNOWN+BLOCKED rows needing inspection: {unknown_heavy}")
    print()
    print("Phase C complete.")


if __name__ == "__main__":
    main()
