"""
Verification script to measure operator fixes impact.

PURPOSE:
  Run full dataset evaluation with patched operators.
  Compare against baseline (56 solves).
  
EXPECTED RESULTS:
  Baseline: 56/1000 (5.6%)
  After patches: 80-100+ solves (8-10%)
  
HOW TO RUN:
  python tools/verify_operators_after_patches.py
"""
import json
import time
from pathlib import Path
import sys
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import operators
from arc_organ.arc_operators import OPERATORS, infer_rule_for_task

BASE_DIR = Path(__file__).parent.parent
DATA_2025 = BASE_DIR / "arc-prize-2025" / "arc-agi_training_challenges.json"
BASELINE_SOLUTIONS = BASE_DIR / "solutions_with_new_operators.json"
NEW_SOLUTIONS = BASE_DIR / "results" / "solutions_after_operator_patches.json"


def solve_task(task_id, task_data, operators):
    """
    Use proper infer_rule_for_task logic - matches baseline solver exactly.
    Returns: (operator_name, params) if solved, else (None, None)
    """
    # Convert to format expected by infer_rule_for_task
    train_pairs = [
        (np.array(pair["input"]), np.array(pair["output"]))
        for pair in task_data["train"]
    ]
    
    # Use REAL solver that handles multi-example param inference correctly
    op, params = infer_rule_for_task(train_pairs)
    
    if op is None or params is None:
        return None, None
    
    return op.name, params


def main():
    print("="*70)
    print("OPERATOR PATCH VERIFICATION")
    print("="*70)
    print()
    
    print("Loading 2025 training challenges...")
    with open(DATA_2025, "r", encoding="utf-8") as f:
        challenges = json.load(f)
    
    print(f"Loaded {len(challenges)} tasks")
    print()
    
    print("Loading baseline solutions...")
    with open(BASELINE_SOLUTIONS, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    
    print(f"Baseline solves: {len(baseline)}/1000 ({len(baseline)/10:.1f}%)")
    print()
    
    print(f"Testing with {len(OPERATORS)} operators (including patched ones)...")
    print()
    
    solves = {}
    operator_stats = {}
    new_solves = []
    
    total = len(challenges)
    t0 = time.time()
    
    for i, (task_id, task_def) in enumerate(challenges.items(), 1):
        operator_name, params = solve_task(task_id, task_def, OPERATORS)
        
        if operator_name is not None:
            solves[task_id] = {
                "operator": operator_name,
                "params": str(params)[:100]  # Truncate for readability
            }
            
            # Track operator usage
            operator_stats[operator_name] = operator_stats.get(operator_name, 0) + 1
            
            # Track if this is a new solve
            if task_id not in baseline:
                new_solves.append((task_id, operator_name))
        
        if i % 100 == 0:
            elapsed = time.time() - t0
            print(f"[{i}/{total}] solved={len(solves)} new={len(new_solves)} time={elapsed:.1f}s")
    
    elapsed = time.time() - t0
    
    print()
    print("="*70)
    print("RESULTS")
    print("="*70)
    print()
    print(f"Total tasks:     {total}")
    print(f"Baseline solves: {len(baseline)}")
    print(f"New solves:      {len(solves)}")
    print(f"**GAIN:          +{len(solves) - len(baseline)} solves**")
    print(f"Coverage:        {len(solves) / total * 100:.2f}%")
    print(f"Time:            {elapsed:.1f}s ({elapsed/total:.3f}s per task)")
    print()
    
    # Show operator usage stats
    print("Operator usage (sorted by count):")
    for op_name, count in sorted(operator_stats.items(), key=lambda x: -x[1]):
        is_new = op_name in ['lattice_role_recolor', 'largest_blob_extract', 'latin_square_from_diagonal']
        marker = " ✨ PATCHED" if is_new else ""
        print(f"  {count:3d} × {op_name}{marker}")
    print()
    
    # Show new solves
    if new_solves:
        print(f"NEW SOLVES ({len(new_solves)} tasks unlocked by patches):")
        for task_id, op_name in new_solves[:20]:
            print(f"  ✓ {task_id} (via {op_name})")
        if len(new_solves) > 20:
            print(f"  ... and {len(new_solves) - 20} more")
        print()
    
    # Save results
    NEW_SOLUTIONS.parent.mkdir(exist_ok=True)
    with open(NEW_SOLUTIONS, "w", encoding="utf-8") as f:
        json.dump(solves, f, indent=2)
    
    print(f"Solutions saved to: {NEW_SOLUTIONS}")
    print()
    
    # Verdict
    gain = len(solves) - len(baseline)
    if gain >= 20:
        print("🔥 MASSIVE GAIN! Operators are unlocking new pattern families!")
    elif gain >= 10:
        print("✓ SOLID GAIN! Patches are working.")
    elif gain >= 5:
        print("~ MODERATE GAIN. Some patterns unlocked.")
    elif gain > 0:
        print("↑ SMALL GAIN. Patterns are rare but patches help.")
    else:
        print("× NO GAIN. Operators need deeper fixes or patterns genuinely don't exist.")


if __name__ == "__main__":
    main()
