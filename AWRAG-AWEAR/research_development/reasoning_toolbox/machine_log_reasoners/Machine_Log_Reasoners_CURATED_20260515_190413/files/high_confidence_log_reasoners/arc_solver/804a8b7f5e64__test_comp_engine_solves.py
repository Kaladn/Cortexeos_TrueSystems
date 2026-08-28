"""
Test COMP-ENGINE Phase 1 on specific tasks to verify it can produce solutions.
"""

import json
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from arc_organ.comp_engine import CompEngine


def test_a416b8f3():
    """Test COMP-ENGINE on a416b8f3 (horizontal replicate with potential masking)."""
    print("="*70)
    print("TEST: a416b8f3 (Horizontal Replicate)")
    print("="*70)
    
    with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
        challenges = json.load(f)
    
    with open('arc-prize-2024/arc-agi_training_solutions.json', 'r') as f:
        solutions = json.load(f)
    
    task = challenges['a416b8f3']
    expected_output = solutions['a416b8f3']
    
    engine = CompEngine()
    
    # Extract training pairs
    train_pairs = []
    for example in task['train']:
        inp = np.array(example['input'])
        out = np.array(example['output'])
        train_pairs.append((inp, out))
    
    print(f"\nTraining examples: {len(train_pairs)}")
    
    # Analyze pattern
    hypothesis = engine.analyze_training_examples(train_pairs)
    
    if hypothesis is None:
        print("✗ No pattern detected")
        print("\nNote: a416b8f3 is horizontal_replicate (not masked tiling)")
        return False
    
    print(f"\n✓ Pattern detected:")
    print(f"  Mask type: {hypothesis.mask_type}")
    print(f"  Tile factor: {hypothesis.tile_factor}")
    
    # Apply to test input
    test_input = np.array(task['test'][0]['input'])
    prediction = engine.apply_masked_tiling(test_input, hypothesis)
    
    expected = np.array(expected_output[0])
    
    match = np.array_equal(prediction, expected)
    
    print(f"\nTest prediction matches expected: {match}")
    
    if match:
        print("\n✓ a416b8f3 SOLVED by COMP-ENGINE")
        return True
    else:
        print("\n✗ Prediction doesn't match")
        print(f"\nExpected shape: {expected.shape}")
        print(f"Predicted shape: {prediction.shape}")
        return False


def search_for_masked_tiling_tasks():
    """Search training set for tasks that COMP-ENGINE can solve."""
    print("\n" + "="*70)
    print("SEARCH: Finding Masked Tiling Tasks")
    print("="*70)
    
    with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
        challenges = json.load(f)
    
    with open('arc-prize-2024/arc-agi_training_solutions.json', 'r') as f:
        solutions = json.load(f)
    
    engine = CompEngine()
    solved_tasks = []
    
    for task_id, task in list(challenges.items())[:200]:  # Test first 200
        if not task['train'] or not task['test']:
            continue
        
        # Extract training pairs
        train_pairs = []
        for example in task['train']:
            inp = np.array(example['input'])
            out = np.array(example['output'])
            train_pairs.append((inp, out))
        
        # Try to detect pattern
        hypothesis = engine.analyze_training_examples(train_pairs)
        
        if hypothesis is None:
            continue
        
        # Test on test input
        test_input = np.array(task['test'][0]['input'])
        prediction = engine.apply_masked_tiling(test_input, hypothesis)
        
        expected = np.array(solutions[task_id][0])
        
        if np.array_equal(prediction, expected):
            solved_tasks.append((task_id, hypothesis))
            print(f"\n✓ SOLVED: {task_id}")
            print(f"  Mask type: {hypothesis.mask_type}")
            print(f"  Tile factor: {hypothesis.tile_factor}")
    
    print(f"\n{'='*70}")
    print(f"RESULTS: COMP-ENGINE solved {len(solved_tasks)}/200 tasks")
    print(f"{'='*70}")
    
    return solved_tasks


if __name__ == "__main__":
    print("\n" + "="*80)
    print(" COMP-ENGINE PHASE 1: TASK SOLVING TEST")
    print("="*80)
    
    # Test specific task
    test_a416b8f3()
    
    # Search for solvable tasks
    solved = search_for_masked_tiling_tasks()
    
    print("\n" + "="*80)
    print(f" SUMMARY: Found {len(solved)} tasks solvable by COMP-ENGINE")
    print("="*80)
