"""
Contract Extraction Scanner - Phase A
Scans Python files for function/method definitions and their documentation.
Outputs CSV with function detection and definition pairing status.

USAGE:
    python F:\\contract_extraction\\scanner.py

OUTPUT:
    F:\\contract_extraction\\scan_batch_1.csv

This script uses Python's ast module for reliable parsing.
It excludes __pycache__, .venv, site-packages, .git, node_modules directories.
Files that fail to parse (syntax errors) are silently skipped.
"""

import ast
import csv
import os
import sys
import traceback

TARGET_DIR = r"F:\From removable drive"
OUTPUT_CSV = r"F:\contract_extraction\scan_batch_1.csv"
BASE_PATH = "F:\\"

EXCLUDE_DIRS = {"__pycache__", ".venv", "venv", "site-packages", ".git", "node_modules", ".tox", "env"}

CSV_HEADER = [
    "file_path", "symbol_name", "function_detected", "definition_detected",
    "function_type", "definition_type", "definition_source",
    "line_start", "line_end", "status"
]


def get_relative_path(abs_path):
    """Get path relative to F:/"""
    # Normalize to forward slashes
    abs_path = abs_path.replace("\\", "/")
    base = BASE_PATH.replace("\\", "/")
    if abs_path.startswith(base):
        return abs_path[len(base):]
    return abs_path


def should_exclude(dirpath):
    """Check if directory should be excluded."""
    parts = dirpath.replace("\\", "/").split("/")
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def get_function_type(node, parent_class=None):
    """Determine the function type based on context and decorators."""
    if isinstance(node, ast.AsyncFunctionDef):
        return "python_async"

    if parent_class is None:
        return "python_function"

    # Check decorators
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            if dec.id == "staticmethod":
                return "python_staticmethod"
            elif dec.id == "classmethod":
                return "python_classmethod"
            elif dec.id == "property":
                return "python_property"
        elif isinstance(dec, ast.Attribute):
            # e.g. @something.setter
            if dec.attr in ("setter", "getter", "deleter"):
                return "python_property"

    return "python_method"


def has_docstring(node):
    """Check if a function/class node has a docstring."""
    if (node.body and
        isinstance(node.body[0], ast.Expr) and
        isinstance(node.body[0].value, (ast.Constant, ast.Str))):
        val = node.body[0].value
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            return True
        if isinstance(val, ast.Str):  # Python 3.7 compat
            return True
    return False


def check_inline_comment(lines, def_line_no):
    """Check if there's an inline comment above the def line."""
    # def_line_no is 1-based
    idx = def_line_no - 2  # line above the def (0-based)
    if idx < 0:
        return False
    # Check up to 3 lines above for comments
    for i in range(idx, max(idx - 3, -1), -1):
        line = lines[i].strip()
        if line.startswith("#"):
            return True
        elif line == "" or line.startswith("@"):
            continue  # skip blanks and decorators
        else:
            break
    return False


def extract_functions_from_file(filepath):
    """Parse a Python file and extract all function/method definitions."""
    results = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
            lines = source.splitlines()
    except Exception:
        return results

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return results
    except Exception:
        return results

    rel_path = get_relative_path(filepath)

    def visit_node(node, parent_class=None):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                # Process methods inside the class
                for item in ast.iter_child_nodes(child):
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        process_funcdef(item, parent_class=child.name)
                    elif isinstance(item, ast.ClassDef):
                        # Nested class
                        visit_node(item, parent_class=child.name)

            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                process_funcdef(child, parent_class=parent_class)

    def process_funcdef(node, parent_class=None):
        if parent_class:
            symbol_name = f"{parent_class}.{node.name}"
        else:
            symbol_name = node.name

        func_type = get_function_type(node, parent_class)

        # Determine end line
        end_line = getattr(node, "end_lineno", node.lineno)
        if end_line is None:
            # Fallback: estimate from body
            end_line = node.lineno
            for child in ast.walk(node):
                cl = getattr(child, "lineno", 0)
                if cl and cl > end_line:
                    end_line = cl

        # Check for docstring
        docstring = has_docstring(node)

        # Check for inline comment above
        inline_comment = check_inline_comment(lines, node.lineno)

        # Determine definition info
        if docstring:
            definition_detected = "yes"
            definition_type = "docstring"
            definition_source = "docstring"
        elif inline_comment:
            definition_detected = "yes"
            definition_type = "inline_comment"
            definition_source = "inline_comment"
        else:
            definition_detected = "no"
            definition_type = "none"
            definition_source = "none"

        # Determine status
        if definition_detected == "yes":
            status = "PAIRED"
        else:
            status = "FUNCTION_ONLY"

        results.append({
            "file_path": rel_path,
            "symbol_name": symbol_name,
            "function_detected": "yes",
            "definition_detected": definition_detected,
            "function_type": func_type,
            "definition_type": definition_type,
            "definition_source": definition_source,
            "line_start": node.lineno,
            "line_end": end_line,
            "status": status,
        })

        # Process nested functions
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nested_name = f"{symbol_name}.{child.name}" if parent_class else child.name
                # Just recurse with no parent class (nested func, not method)
                process_funcdef(child, parent_class=None)
            elif isinstance(child, ast.ClassDef):
                visit_node(child, parent_class=child.name)

    visit_node(tree)
    return results


def collect_py_files(target_dir):
    """Walk directory tree and collect .py files, excluding specified dirs."""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(target_dir):
        # Filter out excluded directories in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for fname in filenames:
            if fname.endswith(".py"):
                py_files.append(os.path.join(dirpath, fname))
    return py_files


def main():
    print(f"Scanning: {TARGET_DIR}")
    py_files = collect_py_files(TARGET_DIR)
    print(f"Found {len(py_files)} Python files")

    all_results = []
    files_parsed = 0
    files_failed = 0

    for filepath in py_files:
        try:
            results = extract_functions_from_file(filepath)
            all_results.extend(results)
            files_parsed += 1
        except Exception as e:
            files_failed += 1

    # Write CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
        writer.writeheader()
        for row in all_results:
            writer.writerow(row)

    print(f"\nResults:")
    print(f"  Files scanned: {files_parsed}")
    print(f"  Files failed:  {files_failed}")
    print(f"  Functions found: {len(all_results)}")
    print(f"  Output: {OUTPUT_CSV}")

    # Summary stats
    paired = sum(1 for r in all_results if r["status"] == "PAIRED")
    func_only = sum(1 for r in all_results if r["status"] == "FUNCTION_ONLY")
    print(f"\n  PAIRED (has definition): {paired}")
    print(f"  FUNCTION_ONLY (no definition): {func_only}")

    # Type breakdown
    types = {}
    for r in all_results:
        t = r["function_type"]
        types[t] = types.get(t, 0) + 1
    print(f"\n  Function type breakdown:")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")


if __name__ == "__main__":
    main()
