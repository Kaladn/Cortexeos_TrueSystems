"""
Test fixed operators against dataset to find new solves.

PURPOSE:
  Verify that relaxed operator constraints find additional task solves.
  
WHAT IT TESTS:
  - grow_shrink (now supports multi-color)
  - sandwich_tiling (now supports 2x2, 3x3, 4x4, 5x5)
  
HOW TO RUN:
  python tools/test_fixed_operators.py
"""
import numpy as np
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from arc_organ.arc_operators import GrowShrinkOperator, SandwichTilingOperator

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

def test_operator(operator, task_data):
    """Test if operator solves a task."""
    train_pairs = task_data["train"]
    
    # Try analyze on first example
    first_input = np.array(train_pairs[0]["input"])
    first_output = np.array(train_pairs[0]["output"])
    
    params = operator.analyze(first_input, first_output)
    if params is None:
        return False
    
    # Verify on all training examples
    for pair in train_pairs:
        inp = np.array(pair["input"])
        expected_out = np.array(pair["output"])
        
        try:
            predicted = operator.apply(inp, params)
            if not np.array_equal(predicted, expected_out):
                return False
        except Exception as e:
            return False
    
    return True

def main():
    print("Loading dataset...")
    dataset = load_dataset()
    baseline_solves = load_baseline_solves()
    
    print(f"Dataset: {len(dataset)} tasks")
    print(f"Baseline solves: {len(baseline_solves)} tasks")
    print()
    
    operators_to_test = [
        ("grow_shrink", GrowShrinkOperator()),
        ("sandwich_tiling", SandwichTilingOperator()),
    ]
    
    for op_name, operator in operators_to_test:
        print(f"Testing {op_name}...")
        new_solves = []
        reconfirmed_solves = []
        
        for task_id, task_data in dataset.items():
            if test_operator(operator, task_data):
                if task_id in baseline_solves:
                    reconfirmed_solves.append(task_id)
                else:
                    new_solves.append(task_id)
        
        print(f"  New solves: {len(new_solves)}")
        if new_solves:
            for task_id in new_solves[:10]:  # Show first 10
                print(f"    - {task_id}")
            if len(new_solves) > 10:
                print(f"    ... and {len(new_solves) - 10} more")
        
        print(f"  Reconfirmed: {len(reconfirmed_solves)}")
        print()
    
    print("Done!")

if __name__ == "__main__":
    main()
