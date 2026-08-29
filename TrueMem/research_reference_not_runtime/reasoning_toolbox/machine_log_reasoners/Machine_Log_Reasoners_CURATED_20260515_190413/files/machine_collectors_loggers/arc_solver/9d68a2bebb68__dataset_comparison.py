"""
Dataset Comparison Tool

Compare tasks between different ARC dataset formats (2024 vs 2025, Kaggle vs ARC-AGI-master)
to verify they contain identical puzzle data.

This tool helped discover the 2024/2025 dataset mismatch that caused
the apparent 34-task regression (56 → 22 solves).

Usage:
    python tools/dataset_comparison.py --dataset1 arc-prize-2024 --dataset2 arc-prize-2025
    python tools/dataset_comparison.py --sample 10  # Compare 10 random tasks
"""
import json
import numpy as np
import random
import argparse
from pathlib import Path

def load_dataset(path: Path):
    """Load ARC dataset from directory."""
    train_path = path / 'arc-agi_training_challenges.json'
    eval_path = path / 'arc-agi_evaluation_challenges.json'
    
    dataset = {}
    if train_path.exists():
        with open(train_path, 'r') as f:
            dataset.update(json.load(f))
    if eval_path.exists():
        with open(eval_path, 'r') as f:
            dataset.update(json.load(f))
    
    return dataset

def grids_equal(grid1, grid2):
    """Check if two grids are exactly equal."""
    return np.array_equal(np.array(grid1), np.array(grid2))

def compare_tasks(task_id, task1, task2):
    """Deep comparison of task data."""
    print(f"\nTask: {task_id}")
    print("-" * 60)
    
    # Compare training examples
    if len(task1['train']) != len(task2['train']):
        print(f"  ✗ Training count mismatch: {len(task1['train'])} vs {len(task2['train'])}")
        return False
    
    all_match = True
    for i, (ex1, ex2) in enumerate(zip(task1['train'], task2['train'])):
        inp_match = grids_equal(ex1['input'], ex2['input'])
        out_match = grids_equal(ex1['output'], ex2['output'])
        
        if not (inp_match and out_match):
            print(f"  ✗ Training example {i+1} mismatch")
            all_match = False
    
    # Compare test examples
    if len(task1['test']) != len(task2['test']):
        print(f"  ✗ Test count mismatch: {len(task1['test'])} vs {len(task2['test'])}")
        return False
    
    for i, (test1, test2) in enumerate(zip(task1['test'], task2['test'])):
        inp_match = grids_equal(test1['input'], test2['input'])
        
        # Check outputs if they exist
        if 'output' in test1 and 'output' in test2:
            out_match = grids_equal(test1['output'], test2['output'])
            if not (inp_match and out_match):
                print(f"  ✗ Test example {i+1} mismatch")
                all_match = False
        elif not inp_match:
            print(f"  ✗ Test example {i+1} input mismatch")
            all_match = False
    
    if all_match:
        print(f"  ✓ Identical")
    
    return all_match

def main():
    parser = argparse.ArgumentParser(description='Compare ARC datasets')
    parser.add_argument('--dataset1', type=str, default='arc-prize-2024',
                       help='First dataset directory')
    parser.add_argument('--dataset2', type=str, default='arc-prize-2025',
                       help='Second dataset directory')
    parser.add_argument('--sample', type=int, default=None,
                       help='Number of random tasks to compare (default: all shared)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for sampling')
    
    args = parser.parse_args()
    
    # Load datasets
    script_dir = Path(__file__).parent.parent
    dataset1 = load_dataset(script_dir / args.dataset1)
    dataset2 = load_dataset(script_dir / args.dataset2)
    
    print("="*70)
    print("DATASET COMPARISON")
    print("="*70)
    print(f"Dataset 1: {args.dataset1} ({len(dataset1)} tasks)")
    print(f"Dataset 2: {args.dataset2} ({len(dataset2)} tasks)")
    print()
    
    # Find shared tasks
    shared_tasks = set(dataset1.keys()) & set(dataset2.keys())
    only_in_1 = set(dataset1.keys()) - set(dataset2.keys())
    only_in_2 = set(dataset2.keys()) - set(dataset1.keys())
    
    print(f"Shared tasks: {len(shared_tasks)}")
    print(f"Only in {args.dataset1}: {len(only_in_1)}")
    print(f"Only in {args.dataset2}: {len(only_in_2)}")
    
    if only_in_1:
        print(f"\nTasks only in {args.dataset1}:")
        for tid in sorted(list(only_in_1)[:10]):
            print(f"  {tid}")
        if len(only_in_1) > 10:
            print(f"  ... and {len(only_in_1) - 10} more")
    
    if only_in_2:
        print(f"\nTasks only in {args.dataset2}:")
        for tid in sorted(list(only_in_2)[:10]):
            print(f"  {tid}")
        if len(only_in_2) > 10:
            print(f"  ... and {len(only_in_2) - 10} more")
    
    # Sample tasks to compare
    if args.sample and args.sample < len(shared_tasks):
        random.seed(args.seed)
        test_tasks = random.sample(sorted(shared_tasks), args.sample)
    else:
        test_tasks = sorted(shared_tasks)
    
    print(f"\nComparing {len(test_tasks)} tasks...")
    print("="*70)
    
    # Compare tasks
    matches = 0
    mismatches = 0
    
    for task_id in test_tasks:
        if compare_tasks(task_id, dataset1[task_id], dataset2[task_id]):
            matches += 1
        else:
            mismatches += 1
    
    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Identical: {matches}/{len(test_tasks)}")
    print(f"Mismatches: {mismatches}/{len(test_tasks)}")
    
    if mismatches == 0 and len(only_in_1) == 0 and len(only_in_2) == 0:
        print("\n✓ Datasets are IDENTICAL")
    elif mismatches == 0:
        print("\n⚠ Datasets have different task sets but shared tasks are identical")
    else:
        print("\n✗ Datasets have content differences")

if __name__ == "__main__":
    main()
