"""
Rapid operator validation - 1 hour to prove usefulness or delete.

PURPOSE:
  Test all 11 unused operators against full dataset.
  Any operator with 0 solves gets marked for deletion.
  
WHAT IT DOES:
  1. Test each unused operator against 1000 training tasks
  2. Count new solves (not in baseline)
  3. Report time spent per operator
  4. Generate deletion list
  
HOW TO RUN:
  python tools/rapid_operator_validation.py
"""
import numpy as np
import json
from pathlib import Path
import sys
import time
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from arc_organ.arc_operators import (
    GrowShrinkOperator, 
    SandwichTilingOperator,
    LatticeRoleRecolorOperator,
    StructuredRecolorOperator,
    LatinSquareFromDiagonalOperator,
    LargestBlobExtractOperator,
    SelfReferentialTilingOperator,
    DiagonalMarkerOperator,
)

# Try to import new operators
try:
    from arc_organ.operators.checkerboard_tiling_alternating import CheckerboardTilingAlternatingOperator
    from arc_organ.operators.symmetry_from_fragment import SymmetryFromFragmentOperator
    from arc_organ.operators.pattern_completion_prototype import PatternCompletionPrototypeOperator
    HAS_NEW_OPS = True
except ImportError:
    HAS_NEW_OPS = False
    print("Warning: Could not import new operators from arc_organ/operators/")

def load_dataset():
    """Load 2025 training dataset."""
    dataset_path = Path(__file__).parent.parent / "arc-prize-2025" / "arc-agi_training_challenges.json"
    with open(dataset_path) as f:
        return json.load(f)

def load_baseline_solves():
    """Load tasks already solved by baseline."""
    baseline_path = Path(__file__).parent.parent / "solutions_with_new_operators.json"
    with open(baseline_path) as f:
        return set(json.load(f).keys())

def test_operator_on_task(operator, task_data) -> bool:
    """Test if operator solves a task."""
    train_pairs = task_data["train"]
    
    # Try analyze on first example
    try:
        first_input = np.array(train_pairs[0]["input"])
        first_output = np.array(train_pairs[0]["output"])
        
        params = operator.analyze(first_input, first_output)
        if params is None:
            return False
    except Exception:
        return False
    
    # Verify on all training examples
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

def test_operator(name: str, operator, dataset: Dict, baseline_solves: set) -> Tuple[int, List[str], float]:
    """Test operator on full dataset. Returns (new_solves, task_ids, time_taken)."""
    start = time.time()
    new_solves = []
    
    for task_id, task_data in dataset.items():
        if task_id in baseline_solves:
            continue  # Skip already solved
        
        if test_operator_on_task(operator, task_data):
            new_solves.append(task_id)
    
    elapsed = time.time() - start
    return len(new_solves), new_solves, elapsed

def main():
    print("="*60)
    print("RAPID OPERATOR VALIDATION - 1 HOUR DEADLINE")
    print("="*60)
    print()
    
    print("Loading dataset...")
    dataset = load_dataset()
    baseline_solves = load_baseline_solves()
    
    print(f"Dataset: {len(dataset)} tasks")
    print(f"Baseline solves: {len(baseline_solves)} tasks")
    print(f"Unsolved: {len(dataset) - len(baseline_solves)} tasks")
    print()
    
    operators_to_test = [
        ("grow_shrink", GrowShrinkOperator()),
        ("sandwich_tiling", SandwichTilingOperator()),
        ("lattice_role_recolor", LatticeRoleRecolorOperator()),
        ("structured_position_recolor", StructuredRecolorOperator()),
        ("latin_square_from_diagonal", LatinSquareFromDiagonalOperator()),
        ("largest_blob_extract", LargestBlobExtractOperator()),
        ("self_referential_tiling", SelfReferentialTilingOperator()),
        ("diagonal_marker_toroidal", DiagonalMarkerOperator()),
    ]
    
    if HAS_NEW_OPS:
        operators_to_test.extend([
            ("checkerboard_tiling_alternating", CheckerboardTilingAlternatingOperator()),
            ("symmetry_from_fragment", SymmetryFromFragmentOperator()),
            ("pattern_completion_prototype", PatternCompletionPrototypeOperator()),
        ])
    
    results = []
    total_start = time.time()
    
    for op_name, operator in operators_to_test:
        print(f"Testing {op_name}...", end=" ", flush=True)
        
        count, task_ids, elapsed = test_operator(op_name, operator, dataset, baseline_solves)
        
        print(f"{count} new solves ({elapsed:.1f}s)")
        
        if count > 0:
            for task_id in task_ids[:5]:  # Show first 5
                print(f"  ✓ {task_id}")
            if count > 5:
                print(f"  ... and {count - 5} more")
        
        results.append({
            "operator": op_name,
            "new_solves": count,
            "task_ids": task_ids,
            "time": elapsed,
            "verdict": "KEEP" if count > 0 else "DELETE"
        })
    
    total_elapsed = time.time() - total_start
    
    print()
    print("="*60)
    print("RESULTS")
    print("="*60)
    print()
    
    keepers = [r for r in results if r["verdict"] == "KEEP"]
    deleters = [r for r in results if r["verdict"] == "DELETE"]
    
    print(f"KEEP ({len(keepers)} operators):")
    for r in keepers:
        print(f"  ✓ {r['operator']:30s} - {r['new_solves']} new solves")
    print()
    
    print(f"DELETE ({len(deleters)} operators):")
    for r in deleters:
        print(f"  ✗ {r['operator']:30s} - 0 solves, {r['time']:.1f}s wasted")
    print()
    
    print(f"Total new solves: {sum(r['new_solves'] for r in results)}")
    print(f"Total time: {total_elapsed:.1f}s")
    print()
    
    # Save results
    output_path = Path(__file__).parent.parent / "results" / "operator_validation_results.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {output_path}")
    
    # Generate deletion command
    if deleters:
        print()
        print("="*60)
        print("DELETION PLAN")
        print("="*60)
        print()
        print("Remove these operator classes from arc_operators.py:")
        for r in deleters:
            class_name = "".join(word.capitalize() for word in r['operator'].split('_')) + "Operator"
            print(f"  - {class_name}")
        print()
        print("Remove these from OPERATORS list:")
        for r in deleters:
            class_name = "".join(word.capitalize() for word in r['operator'].split('_')) + "Operator"
            print(f"  - {class_name}(),")

if __name__ == "__main__":
    main()
