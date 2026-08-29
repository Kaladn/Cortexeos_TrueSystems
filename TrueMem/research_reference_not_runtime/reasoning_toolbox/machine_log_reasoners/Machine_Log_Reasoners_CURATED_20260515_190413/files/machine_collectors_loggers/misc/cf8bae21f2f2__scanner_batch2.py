"""
Contract Extraction Scanner - Batch 2
Scans Python files for function/method definitions and their documentation.
Outputs CSV with pairing status.
"""

import ast
import csv
import os
import sys


# Configuration
TARGET_DIR = r"F:\Desktop 812025"
OUTPUT_FILE = r"F:\contract_extraction\scan_batch_2.csv"
BASE_PATH = "F:\\"  # relative paths will be relative to /f/

SKIP_DIRS = {
    "__pycache__", ".venv", "site-packages", ".git", ".mypy_cache",
    "node_modules", ".tox", ".eggs", "dist", "build"
}

CSV_HEADER = [
    "file_path", "symbol_name", "function_detected", "definition_detected",
    "function_type", "definition_type", "definition_source",
    "line_start", "line_end", "status"
]


def should_skip_dir(dirname):
    """Check if directory should be skipped."""
    return dirname in SKIP_DIRS


def get_relative_path(abs_path):
    """Convert absolute path to relative path from /f/."""
    # Normalize to forward slashes for CSV consistency
    rel = os.path.relpath(abs_path, BASE_PATH)
    return rel.replace("\\", "/")


def collect_py_files(root_dir):
    """Walk directory tree collecting .py files, skipping excluded dirs."""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out skip directories in-place (prevents os.walk from descending)
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for fname in filenames:
            if fname.endswith(".py"):
                py_files.append(os.path.join(dirpath, fname))
    return sorted(py_files)


def get_function_type(node, parent_class=None):
    """Determine the function type based on context and decorators."""
    decorators = [d for d in node.decorator_list] if node.decorator_list else []
    decorator_names = []
    for d in decorators:
        if isinstance(d, ast.Name):
            decorator_names.append(d.id)
        elif isinstance(d, ast.Attribute):
            decorator_names.append(d.attr)
        elif isinstance(d, ast.Call):
            if isinstance(d.func, ast.Name):
                decorator_names.append(d.func.id)
            elif isinstance(d.func, ast.Attribute):
                decorator_names.append(d.func.attr)

    if isinstance(node, ast.AsyncFunctionDef):
        return "python_async"

    if parent_class is not None:
        if "staticmethod" in decorator_names:
            return "python_staticmethod"
        if "classmethod" in decorator_names:
            return "python_classmethod"
        if "property" in decorator_names:
            return "python_property"
        return "python_method"

    return "python_function"


def has_docstring(node):
    """Check if a function/class node has a docstring."""
    if (node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
        val = node.body[0].value
        if isinstance(val, ast.Constant):
            return isinstance(val.value, str)
        # ast.Str for older Python
        return True
    return False


def check_inline_comment(lines, def_line_num):
    """Check if there's a comment line immediately above the def line."""
    # def_line_num is 1-based from ast
    idx = def_line_num - 2  # convert to 0-based index of line above
    if idx < 0:
        return False
    # Walk upward through consecutive comment lines
    while idx >= 0:
        stripped = lines[idx].strip()
        if stripped.startswith("#"):
            return True
        elif stripped == "" or stripped.startswith("@"):
            # Skip blank lines and decorators, keep looking
            idx -= 1
            continue
        else:
            break
    return False


def get_end_line(node):
    """Get end line number of a node."""
    if hasattr(node, "end_lineno") and node.end_lineno is not None:
        return node.end_lineno
    # Fallback: use the last line we can find in the body
    max_line = node.lineno
    for child in ast.walk(node):
        if hasattr(child, "lineno") and child.lineno is not None:
            max_line = max(max_line, child.lineno)
        if hasattr(child, "end_lineno") and child.end_lineno is not None:
            max_line = max(max_line, child.end_lineno)
    return max_line


def extract_functions(tree, lines):
    """Extract all function/method definitions from an AST tree."""
    results = []

    def visit_node(node, parent_class=None):
        if isinstance(node, ast.ClassDef):
            # Process methods inside the class
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbol_name = f"{node.name}.{child.name}"
                    func_type = get_function_type(child, parent_class=node.name)
                    docstring = has_docstring(child)
                    inline = check_inline_comment(lines, child.lineno)
                    line_start = child.lineno
                    line_end = get_end_line(child)

                    if docstring:
                        def_detected = "yes"
                        def_type = "docstring"
                        def_source = "docstring"
                    elif inline:
                        def_detected = "yes"
                        def_type = "inline_comment"
                        def_source = "inline_comment"
                    else:
                        def_detected = "no"
                        def_type = "none"
                        def_source = "none"

                    status = "PAIRED" if def_detected == "yes" else "FUNCTION_ONLY"

                    results.append({
                        "symbol_name": symbol_name,
                        "function_detected": "yes",
                        "definition_detected": def_detected,
                        "function_type": func_type,
                        "definition_type": def_type,
                        "definition_source": def_source,
                        "line_start": line_start,
                        "line_end": line_end,
                        "status": status,
                    })
                elif isinstance(child, ast.ClassDef):
                    # Nested class
                    visit_node(child, parent_class=node.name)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if parent_class is None:
                symbol_name = node.name
                func_type = get_function_type(node, parent_class=None)
                docstring = has_docstring(node)
                inline = check_inline_comment(lines, node.lineno)
                line_start = node.lineno
                line_end = get_end_line(node)

                if docstring:
                    def_detected = "yes"
                    def_type = "docstring"
                    def_source = "docstring"
                elif inline:
                    def_detected = "yes"
                    def_type = "inline_comment"
                    def_source = "inline_comment"
                else:
                    def_detected = "no"
                    def_type = "none"
                    def_source = "none"

                status = "PAIRED" if def_detected == "yes" else "FUNCTION_ONLY"

                results.append({
                    "symbol_name": symbol_name,
                    "function_detected": "yes",
                    "definition_detected": def_detected,
                    "function_type": func_type,
                    "definition_type": def_type,
                    "definition_source": def_source,
                    "line_start": line_start,
                    "line_end": line_end,
                    "status": status,
                })

    # Process top-level nodes
    for node in ast.iter_child_nodes(tree):
        visit_node(node)

    return results


def scan_file(filepath):
    """Parse a single Python file and extract function definitions."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
            lines = source.splitlines()
    except Exception as e:
        print(f"  [WARN] Could not read {filepath}: {e}", file=sys.stderr)
        return []

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        print(f"  [WARN] Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [WARN] Parse error in {filepath}: {e}", file=sys.stderr)
        return []

    return extract_functions(tree, lines)


def main():
    print(f"Scanning: {TARGET_DIR}")
    print(f"Output:   {OUTPUT_FILE}")

    # Collect files
    py_files = collect_py_files(TARGET_DIR)
    print(f"Found {len(py_files)} Python files (after filtering)")

    # Process all files
    all_rows = []
    files_processed = 0
    files_skipped = 0
    total_functions = 0

    for filepath in py_files:
        rel_path = get_relative_path(filepath)
        results = scan_file(filepath)

        if results is None:
            files_skipped += 1
            continue

        files_processed += 1
        total_functions += len(results)

        for r in results:
            all_rows.append({
                "file_path": rel_path,
                **r
            })

    # Write CSV
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADER)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    # Summary
    paired = sum(1 for r in all_rows if r["status"] == "PAIRED")
    func_only = sum(1 for r in all_rows if r["status"] == "FUNCTION_ONLY")

    print(f"\n--- Scan Complete ---")
    print(f"Files processed:  {files_processed}")
    print(f"Files skipped:    {files_skipped}")
    print(f"Functions found:  {total_functions}")
    print(f"  PAIRED:         {paired}")
    print(f"  FUNCTION_ONLY:  {func_only}")
    print(f"CSV written to:   {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

# TO RUN: Open a terminal and execute:
#   python "F:\contract_extraction\scanner_batch2.py"
# Output will be written to: F:\contract_extraction\scan_batch_2.csv
