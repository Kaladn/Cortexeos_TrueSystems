"""
CSV Builder - Processes grep output files to build scan_batch_1.csv
Run this if scanner.py cannot be executed directly.
Uses pre-collected grep data from the contract extraction scan.
"""

import re
import csv
import os

# Input files (grep output already collected)
DEFS_FILE = None  # Will use inline data
CONTEXT_FILE = None  # Will use inline data
OUTPUT_CSV = r"F:\contract_extraction\scan_batch_1.csv"

# Regex to parse grep output lines
# Format: F:\From removable drive\path\file.py:linenum:    def funcname(...)
DEF_PATTERN = re.compile(
    r'^F:\\From removable drive\\(.+\.py):(\d+):\s*(async\s+)?def\s+(\w+)'
)

# For context lines (next line after def)
CONTEXT_NEXT_PATTERN = re.compile(
    r'^F:\\From removable drive\\(.+\.py)-(\d+)-\s*("""|\'\'\')'
)

BASE_PREFIX = "From removable drive/"

EXCLUDE_PATTERNS = ['.venv', 'site-packages', '__pycache__', '.git']


def should_exclude(path):
    for pat in EXCLUDE_PATTERNS:
        if pat in path:
            return True
    return False


def parse_def_line(line):
    """Parse a grep output line for def information."""
    m = DEF_PATTERN.match(line.strip())
    if not m:
        return None
    filepath = m.group(1).replace("\\", "/")
    line_num = int(m.group(2))
    is_async = bool(m.group(3))
    func_name = m.group(4)
    return {
        'filepath': filepath,
        'line_num': line_num,
        'is_async': is_async,
        'func_name': func_name,
        'raw': line.strip()
    }


def detect_method_context(raw_line):
    """Check if the def is indented (likely a method)."""
    # Look at the content after filepath:linenum:
    parts = raw_line.split(':', 2)
    if len(parts) >= 3:
        code = parts[2]
        stripped = code.lstrip()
        indent = len(code) - len(stripped)
        return indent >= 4  # Methods are typically indented 4+ spaces
    return False


def main():
    """Process grep data and build CSV."""
    # Read the defs file
    defs_path = input("Path to defs grep output file: ").strip()
    context_path = input("Path to context grep output file (or skip): ").strip()

    # Build docstring lookup from context file
    docstring_set = set()  # (filepath, linenum) tuples that have docstrings
    if context_path and os.path.exists(context_path):
        with open(context_path, 'r', encoding='utf-8', errors='replace') as f:
            prev_def = None
            for line in f:
                line = line.rstrip('\n')
                if line == '--':
                    prev_def = None
                    continue
                # Check if this is a def line
                m = DEF_PATTERN.match(line)
                if m:
                    prev_def = (m.group(1).replace("\\", "/"), int(m.group(2)))
                    continue
                # Check if this is a context line with docstring
                if prev_def and ('"""' in line or "'''" in line):
                    docstring_set.add(prev_def)
                prev_def = None

    print(f"Loaded {len(docstring_set)} docstring entries")

    # Process defs file
    results = []
    with open(defs_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            parsed = parse_def_line(line)
            if not parsed:
                continue
            if should_exclude(parsed['filepath']):
                continue

            fp = parsed['filepath']
            is_method = detect_method_context(line)

            # Determine function type
            if parsed['is_async']:
                func_type = 'python_async'
            elif is_method:
                func_type = 'python_method'
            else:
                func_type = 'python_function'

            # Check docstring
            key = (fp, parsed['line_num'])
            has_doc = key in docstring_set

            # Build CSV row
            rel_path = BASE_PREFIX + fp
            results.append({
                'file_path': rel_path,
                'symbol_name': parsed['func_name'],
                'function_detected': 'yes',
                'definition_detected': 'yes' if has_doc else 'no',
                'function_type': func_type,
                'definition_type': 'docstring' if has_doc else 'none',
                'definition_source': 'docstring' if has_doc else 'none',
                'line_start': parsed['line_num'],
                'line_end': parsed['line_num'],  # Approximate - would need AST for exact
                'status': 'PAIRED' if has_doc else 'FUNCTION_ONLY',
            })

    # Write CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    header = [
        'file_path', 'symbol_name', 'function_detected', 'definition_detected',
        'function_type', 'definition_type', 'definition_source',
        'line_start', 'line_end', 'status'
    ]
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    # Stats
    paired = sum(1 for r in results if r['status'] == 'PAIRED')
    func_only = sum(1 for r in results if r['status'] == 'FUNCTION_ONLY')
    print(f"\nResults written to: {OUTPUT_CSV}")
    print(f"  Total functions: {len(results)}")
    print(f"  PAIRED: {paired}")
    print(f"  FUNCTION_ONLY: {func_only}")


if __name__ == '__main__':
    main()
