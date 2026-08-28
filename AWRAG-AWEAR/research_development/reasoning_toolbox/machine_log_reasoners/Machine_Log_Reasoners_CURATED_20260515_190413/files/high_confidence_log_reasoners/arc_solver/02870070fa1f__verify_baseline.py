"""
Baseline Regression Detector

Verifies that the production solver maintains 56/56 baseline solves.
Run this before every commit to ensure no regressions.

Usage:
    python tools/verify_baseline.py

Expected output:
    ✓ Solved: 56/56
    ✓ BASELINE VERIFIED - No regressions
"""
import json
import numpy as np
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers import BaselineSolver

def verify_baseline():
    """Test baseline solver against known 56 solutions."""
    
    # Load baseline solutions (ground truth)
    baseline_path = Path(__file__).parent.parent / 'solutions_with_new_operators.json'
    with open(baseline_path, 'r') as f:
        baseline = json.load(f)

    # Load datasets
    data_dir = Path(__file__).parent.parent / 'arc-prize-2025'
    with open(data_dir / 'arc-agi_training_challenges.json', 'r') as f:
        train_tasks = json.load(f)
    with open(data_dir / 'arc-agi_evaluation_challenges.json', 'r') as f:
        eval_tasks = json.load(f)

    all_tasks = {**train_tasks, **eval_tasks}

    print("="*70)
    print("BASELINE REGRESSION CHECK")
    print("="*70)
    print(f"Expected: {len(baseline)} baseline tasks")
    print()

    # Initialize solver
    from cod_616.arc_organ.arc_operators import OPERATORS
    solver = BaselineSolver(OPERATORS)

    solved = 0
    failed = []

    for task_id in baseline.keys():
        if task_id not in all_tasks:
            print(f"⚠ MISSING: {task_id} not in dataset")
            failed.append((task_id, "missing_from_dataset"))
            continue
        
        task = all_tasks[task_id]
        
        # Test solver
        result = solver.solve(task)
        
        if result is not None:
            # Validate result
            valid = True
            for example in task['train']:
                test_input = np.array(example['input'])
                expected = np.array(example['output'])
                
                test_output = result['operator'].apply(test_input, result['config'])
                if not np.array_equal(test_output, expected):
                    valid = False
                    break
            
            if valid:
                solved += 1
            else:
                print(f"✗ FAIL: {task_id} - {result['operator'].name} invalid")
                failed.append((task_id, "invalid_solution"))
        else:
            print(f"✗ FAIL: {task_id} - baseline says {baseline[task_id]['operator']}")
            failed.append((task_id, "not_found"))

    print()
    print("="*70)
    print(f"✓ Solved: {solved}/{len(baseline)}")
    print(f"✗ Failed: {len(failed)}")
    print("="*70)

    if failed:
        print("\nFailed tasks:")
        for task_id, reason in failed[:10]:
            print(f"  {task_id}: {reason}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")

    # Final verdict
    print()
    if solved == len(baseline):
        print("✓ BASELINE VERIFIED - No regressions")
        return 0
    else:
        print(f"✗ REGRESSION DETECTED - Lost {len(baseline) - solved} solves")
        return 1

if __name__ == "__main__":
    sys.exit(verify_baseline())
