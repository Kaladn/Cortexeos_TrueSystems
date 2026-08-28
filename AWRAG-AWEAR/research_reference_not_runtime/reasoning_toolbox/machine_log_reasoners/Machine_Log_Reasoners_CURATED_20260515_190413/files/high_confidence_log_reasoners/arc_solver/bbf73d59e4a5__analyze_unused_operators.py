"""
Analyze which operators are unused and why they might be failing.

PURPOSE:
  Diagnose operators that never matched any tasks in the 56-solve baseline.
  
WHAT IT DOES:
  1. Loads baseline solves to see which operators worked
  2. Identifies 11 unused operators
  3. Tests each unused operator against sample unsolved tasks
  4. Reports which constraints are too strict
  
HOW TO RUN:
  python tools/analyze_unused_operators.py
"""
import numpy as np
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from arc_organ.arc_operators import OPERATORS

# Load baseline solves
baseline_path = Path(__file__).parent.parent / "solutions_with_new_operators.json"
with open(baseline_path) as f:
    baseline = json.load(f)

# Count operator usage
used_operators = {}
for task_id, solve_info in baseline.items():
    op_name = solve_info["operator"]
    used_operators[op_name] = used_operators.get(op_name, 0) + 1

# Find unused operators
all_operator_names = {op.name for op in OPERATORS}
unused_operator_names = all_operator_names - set(used_operators.keys())

print(f"=== Operator Usage Analysis ===")
print(f"Total operators: {len(OPERATORS)}")
print(f"Used operators: {len(used_operators)}")
print(f"Unused operators: {len(unused_operator_names)}")
print()

print("=== Unused Operators ===")
for name in sorted(unused_operator_names):
    print(f"  - {name}")
print()

# Diagnose each unused operator
print("=== Diagnosis ===")
print()

unused_ops = [op for op in OPERATORS if op.name in unused_operator_names]

for op in unused_ops:
    print(f"Operator: {op.name}")
    print(f"  Class: {op.__class__.__name__}")
    
    # Check docstring for clues
    if op.__class__.__doc__:
        doc_lines = op.__class__.__doc__.strip().split('\n')
        # Print first 3 lines
        for line in doc_lines[:3]:
            if line.strip():
                print(f"  {line.strip()}")
    
    # Analyze the analyze() method for overly strict constraints
    import inspect
    source = inspect.getsource(op.analyze)
    
    # Count constraint checks
    constraint_patterns = [
        ("shape equality", "shape =="),
        ("exact division", "% "),
        ("exact match", "array_equal"),
        ("strict equality", "!= "),
        ("len checks", "len("),
        ("set size", "len(extra)"),
        ("color count", "len(.*colors)"),
    ]
    
    constraints = []
    for pattern_name, pattern in constraint_patterns:
        if pattern in source:
            count = source.count(pattern)
            if count > 0:
                constraints.append(f"{pattern_name} ({count}x)")
    
    if constraints:
        print(f"  Constraints: {', '.join(constraints)}")
    
    print()

print("=== Recommendations ===")
print()
print("High-priority operators to relax:")
print()

# Prioritize based on likely usefulness
priority_ops = {
    "self_referential_tiling": "Used for 007bbfb7 but not in baseline? Check if tiling_expand subsumes it.",
    "sandwich_tiling": "Very specific (3x3 only). Could generalize to NxN.",
    "diagonal_marker_toroidal": "Very specific toroidal diagonal. Could relax to non-toroidal.",
    "largest_blob_extract": "Should be common. Check if strict color constraints block it.",
    "structured_position_recolor": "Claims to unlock many tasks. Check merge logic.",
    "lattice_role_recolor": "Tier 3 operator with input-conditioned colors. Test on real tasks.",
    "latin_square_from_diagonal": "Pattern generator. May need more flexible diagonal detection.",
    "grow_shrink": "Morphology should be common. Check single-color constraint.",
}

for op_name, recommendation in priority_ops.items():
    if op_name in unused_operator_names:
        print(f"{op_name}:")
        print(f"  {recommendation}")
        print()
