"""
Test top 3 fixed operators for new solves.

PURPOSE:
  Verify fixes to lattice_role_recolor, largest_blob_extract, latin_square_from_diagonal
  
EXPECTED GAIN:
  +25-45 solves from these 3 operators
  
HOW TO RUN:
  python tools/test_top3_fixes.py
"""
import numpy as np
import json
from pathlib import Path
import sys
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from arc_organ.arc_operators import (
    LatticeRoleRecolorOperator,
    LargestBlobExtractOperator,
    LatinSquareFromDiagonalOperator,
)

def load_dataset():
    dataset_path = Path(__file__).parent.parent / "arc-prize-2025" / "arc-agi_training_challenges.json"
    with open(dataset_path) as f:
        return json.load(f)

def load_baseline_solves():
    baseline_path = Path(__file__).parent.parent / "solutions_with_new_operators.json"
    with open(baseline_path) as f:
        return set(json.load(f).keys())

def test_operator_on_task(operator, task_data) -> bool:
    train_pairs = task_data["train"]
    
    try:
        first_input = np.array(train_pairs[0]["input"])
        first_output = np.array(train_pairs[0]["output"])
        
        params = operator.analyze(first_input, first_output)
        if params is None:
            return False
    except Exception:
        return False
    
    for pair in train_pairs:
        try:
            inp = np.array(pair["input"])
            expected_out = np.array(pair["output"])
            
            predicted = operator.apply(inp, params)
            if not np.array_equal(predicted, expected_out):
                return False
        except Exception:
            return False
    
    return True

def main():
    print("Testing top 3 fixed operators...")
    print()
    
    dataset = load_dataset()
    baseline_solves = load_baseline_solves()
    
    print(f"Dataset: {len(dataset)} tasks")
    print(f"Baseline: {len(baseline_solves)} solves")
    print()
    
    operators = [
        ("lattice_role_recolor", LatticeRoleRecolorOperator()),
        ("largest_blob_extract", LargestBlobExtractOperator()),
        ("latin_square_from_diagonal", LatinSquareFromDiagonalOperator()),
    ]
    
    total_new = 0
    all_new_solves = []
    
    for op_name, operator in operators:
        print(f"Testing {op_name}...", end=" ", flush=True)
        start = time.time()
        
        new_solves = []
        for task_id, task_data in dataset.items():
            if task_id in baseline_solves:
                continue
            
            if test_operator_on_task(operator, task_data):
                new_solves.append(task_id)
        
        elapsed = time.time() - start
        print(f"{len(new_solves)} new ({elapsed:.1f}s)")
        
        if new_solves:
            for task_id in new_solves[:10]:
                print(f"  ✓ {task_id}")
            if len(new_solves) > 10:
                print(f"  ... and {len(new_solves) - 10} more")
        
        total_new += len(new_solves)
        all_new_solves.extend([(op_name, task_id) for task_id in new_solves])
    
    print()
    print(f"TOTAL NEW SOLVES: {total_new}")
    print(f"Baseline: 56 → New total: {56 + total_new}")
    print()
    
    if total_new > 0:
        print("SUCCESS! Operators are now unlocking new tasks.")
    else:
        print("No new solves - operators still need work or patterns are genuinely rare.")

if __name__ == "__main__":
    main()
