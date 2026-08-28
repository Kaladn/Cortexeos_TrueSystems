"""Phase A contract extraction scanner - Batch 3.

Scans all .py files under /f/New folder/ (excluding __pycache__, .venv,
site-packages, .git), extracts every function/method definition, checks for
docstrings and inline comments, and writes results to scan_batch_3.csv.
"""
from __future__ import annotations

import ast
import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TARGET_DIR = Path(r"F:\New folder")
OUTPUT_CSV = Path(r"F:\contract_extraction\scan_batch_3.csv")
BASE_PREFIX = Path(r"F:")  # relative paths start after F:\

SKIP_DIRS = {"__pycache__", ".venv", "venv", "site-packages", ".git"}

CSV_HEADER = [
    "file_path",
    "symbol_name",
    "function_detected",
    "definition_detected",
    "function_type",
    "definition_type",
    "definition_source",
    "line_start",
    "line_end",
    "status",
]


def should_skip(path: Path) -> bool:
    """Return True if any component of *path* is in SKIP_DIRS."""
    parts = set(path.parts)
    return bool(parts & SKIP_DIRS)


def collect_py_files(root: Path) -> List[Path]:
    """Walk *root* and return all .py files not under excluded directories."""
    result: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories in-place so os.walk skips them.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if fname.endswith(".py"):
                result.append(Path(dirpath) / fname)
    return sorted(result)


def relative_path(filepath: Path) -> str:
    """Return a path relative to F:\\ using forward slashes."""
    try:
        rel = filepath.relative_to(BASE_PREFIX)
    except ValueError:
        rel = filepath
    return str(rel).replace("\\", "/")


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check whether the first statement of a function body is a docstring."""
    if not node.body:
        return False
    first = node.body[0]
    if isinstance(first, ast.Expr):
        value = first.value
        # Python 3.8+ uses ast.Constant
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return True
        # Older Python fallback
        if isinstance(value, ast.Str):  # type: ignore[attr-defined]
            return True
    return False


def _has_inline_comment(lines: List[str], def_lineno: int) -> bool:
    """Check the line(s) immediately above a def for a comment."""
    idx = def_lineno - 2  # lines is 0-indexed, lineno is 1-indexed
    while idx >= 0:
        stripped = lines[idx].strip()
        if stripped.startswith("#"):
            return True
        if stripped == "" or stripped.startswith("@"):
            # Skip blank lines and decorators, keep looking
            idx -= 1
            continue
        break
    return False


def _decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
    """Return the simple names of decorators on a function node."""
    names: List[str] = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            names.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            names.append(dec.attr)
        elif isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Name):
                names.append(func.id)
            elif isinstance(func, ast.Attribute):
                names.append(func.attr)
    return names


def classify_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    parent_class: Optional[str],
    is_async: bool,
) -> str:
    """Return the function_type string."""
    decorators = _decorator_names(node)
    if is_async:
        return "python_async"
    if "property" in decorators:
        return "python_property"
    if "staticmethod" in decorators:
        return "python_staticmethod"
    if "classmethod" in decorators:
        return "python_classmethod"
    if parent_class is not None:
        return "python_method"
    return "python_function"


def _end_lineno(node: ast.AST) -> int:
    """Best-effort end line number."""
    return getattr(node, "end_lineno", None) or getattr(node, "lineno", 0)


def extract_functions(
    tree: ast.Module,
    lines: List[str],
) -> List[Dict[str, Any]]:
    """Extract all function/method definitions from an AST."""
    results: List[Dict[str, Any]] = []

    def visit(node: ast.AST, parent_class: Optional[str] = None) -> None:
        if isinstance(node, ast.ClassDef):
            for child in ast.iter_child_nodes(node):
                visit(child, parent_class=node.name)
            return

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            symbol = f"{parent_class}.{node.name}" if parent_class else node.name
            func_type = classify_function(node, parent_class, is_async)

            has_doc = _has_docstring(node)
            has_comment = _has_inline_comment(lines, node.lineno)

            if has_doc:
                def_detected = "yes"
                def_type = "docstring"
                def_source = "docstring"
            elif has_comment:
                def_detected = "yes"
                def_type = "inline_comment"
                def_source = "inline_comment"
            else:
                def_detected = "no"
                def_type = "none"
                def_source = "none"

            if def_detected == "yes":
                status = "PAIRED"
            else:
                status = "FUNCTION_ONLY"

            results.append({
                "symbol_name": symbol,
                "function_detected": "yes",
                "definition_detected": def_detected,
                "function_type": func_type,
                "definition_type": def_type,
                "definition_source": def_source,
                "line_start": node.lineno,
                "line_end": _end_lineno(node),
                "status": status,
            })

            # Recurse into nested functions / classes
            for child in ast.iter_child_nodes(node):
                visit(child, parent_class=parent_class)
            return

        # Recurse for module-level or other containers
        for child in ast.iter_child_nodes(node):
            visit(child, parent_class=parent_class)

    visit(tree)
    return results


def scan_file(filepath: Path) -> List[Dict[str, Any]]:
    """Parse a single .py file and return extracted rows."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    lines = source.splitlines()
    rel = relative_path(filepath)
    rows = extract_functions(tree, lines)
    for row in rows:
        row["file_path"] = rel
    return rows


def main() -> None:
    py_files = collect_py_files(TARGET_DIR)
    print(f"Found {len(py_files)} Python files to scan.")

    all_rows: List[Dict[str, Any]] = []
    files_parsed = 0
    files_failed = 0

    for filepath in py_files:
        rows = scan_file(filepath)
        if rows is not None:
            all_rows.extend(rows)
            files_parsed += 1
        else:
            files_failed += 1

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADER)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"Scan complete: {files_parsed} files parsed, {files_failed} failed.")
    print(f"Extracted {len(all_rows)} function/method definitions.")
    print(f"Output written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
