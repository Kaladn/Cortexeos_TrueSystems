"""
Multi-Step Operator Composition Finder

Search for tasks that can be solved by chaining multiple operators together.
This is RESEARCH CODE for discovering new composition opportunities.

CRITICAL FIX: Original version had bug on line 36 - used original input instead
of intermediate result when analyzing second operator. This version is FIXED.

Usage:
    python research/composition_finder.py --max-steps 3 --sample 100
    python research/composition_finder.py --resume-from 700

Strategy:
1. Try all 2-step combinations
2. Try all 3-step combinations (if enabled)
3. Focus on common patterns: transform → recolor, flip → recolor → flip
"""
import json
import numpy as np
import argparse
from typing import List, Dict, Optional
import itertools
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cod_616.arc_organ.arc_operators import OPERATORS

def test_operator_sequence(task: Dict, operator_names: List[str], verbose=False) -> bool:
    """
    Test if a sequence of operators solves the task.
    
    FIXED: Now correctly uses intermediate results when analyzing next operator.
    """
    op_dict = {op.name: op for op in OPERATORS}
    
    # Get operators
    ops = []
    for name in operator_names:
        if name not in op_dict:
            return False
        ops.append(op_dict[name])
    
    # Test on all training examples
    for example in task['train']:
        inp = np.array(example['input'])
        expected_out = np.array(example['output'])
        
        # Apply sequence
        current = inp.copy()
        for i, op in enumerate(ops):
            # CRITICAL FIX: Use current state for analysis, not original input
            # Old buggy version: params = op.analyze(inp, expected_out)
            # New correct version: params = op.analyze(current, expected_out)
            params = op.analyze(current, expected_out)
            
            if params is None:
                # Try with empty params as fallback
                params = {}
            
            try:
                current = op.apply(current, params)
                
                if verbose and i == 0:
                    print(f"    Step {i+1} ({op.name}): {inp.shape} -> {current.shape}")
            except Exception as e:
                if verbose:
                    print(f"    Failed at step {i+1} ({op.name}): {e}")
                return False
        
        # Check if matches expected output
        if not np.array_equal(current, expected_out):
            return False
    
    return True

def find_multi_step_solutions(data: Dict, max_steps: int = 3, verbose=False):
    """Find tasks solvable by multi-step operator composition."""
    op_names = [op.name for op in OPERATORS]
    
    if verbose:
        print(f"\nAvailable operators ({len(op_names)}):")
        for name in sorted(op_names):
            print(f"  - {name}")
    
    print("\n" + "="*80)
    print("MULTI-STEP COMPOSITION SEARCH")
    print("="*80)
    print(f"Max steps: {max_steps}")
    print(f"Total tasks: {len(data)}")
    print()
    
    solutions = {}
    
    for task_idx, (task_id, task) in enumerate(data.items(), 1):
        if task_idx % 100 == 0:
            print(f"Progress: {task_idx}/{len(data)} tasks | Found: {len(solutions)} solutions")
        
        # Try 2-step combinations first
        if task_id not in solutions:
            for op1, op2 in itertools.product(op_names, repeat=2):
                if test_operator_sequence(task, [op1, op2], verbose=verbose):
                    solutions[task_id] = [op1, op2]
                    print(f"✓ 2-STEP: {task_id} = {op1} -> {op2}")
                    break
        
        # Try 3-step combinations (if enabled and 2-step didn't work)
        if task_id not in solutions and max_steps >= 3:
            # Focus on promising patterns
            common_first_ops = ['mirror', 'rotation_90', 'crop_to_content']
            common_last_ops = ['recolor_mapping', 'position_based_recolor', 'pattern_completion']
            
            for op1 in common_first_ops:
                for op2 in op_names:
                    for op3 in common_last_ops:
                        sequence = [op1, op2, op3]
                        if test_operator_sequence(task, sequence, verbose=verbose):
                            solutions[task_id] = sequence
                            print(f"✓ 3-STEP: {task_id} = {' -> '.join(sequence)}")
                            break
                    if task_id in solutions:
                        break
                if task_id in solutions:
                    break
    
    return solutions

def analyze_patterns(solutions: Dict):
    """Analyze composition patterns."""
    print("\n" + "="*80)
    print("PATTERN ANALYSIS")
    print("="*80)
    
    if not solutions:
        print("\nNo multi-step solutions found.")
        return
    
    # Group by length
    by_length = {}
    for task_id, sequence in solutions.items():
        length = len(sequence)
        if length not in by_length:
            by_length[length] = []
        by_length[length].append((task_id, sequence))
    
    for length in sorted(by_length.keys()):
        tasks = by_length[length]
        print(f"\n{length}-STEP COMPOSITIONS: {len(tasks)} tasks")
        for task_id, sequence in tasks[:10]:
            print(f"  {task_id}: {' -> '.join(sequence)}")
        if len(tasks) > 10:
            print(f"  ... and {len(tasks) - 10} more")
    
    # Find common pairs
    pair_counts = {}
    for task_id, sequence in solutions.items():
        for i in range(len(sequence) - 1):
            pair = (sequence[i], sequence[i+1])
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
    
    if pair_counts:
        print("\nMost common operator pairs:")
        for pair, count in sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {pair[0]} -> {pair[1]}: {count}x")

def main():
    parser = argparse.ArgumentParser(description='Find multi-step operator compositions')
    parser.add_argument('--max-steps', type=int, default=2,
                       help='Maximum composition length')
    parser.add_argument('--sample', type=int, default=None,
                       help='Test on random sample of N tasks')
    parser.add_argument('--resume-from', type=int, default=0,
                       help='Resume from task index N')
    parser.add_argument('--verbose', action='store_true',
                       help='Print detailed debugging info')
    parser.add_argument('--output', type=str, default=None,
                       help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # Load dataset
    script_dir = Path(__file__).parent.parent
    data_path = script_dir / 'arc-prize-2025' / 'arc-agi_training_challenges.json'
    
    with open(data_path) as f:
        data = json.load(f)
    
    # Sample or resume
    all_tasks = list(data.keys())
    if args.resume_from > 0:
        print(f"Resuming from task {args.resume_from}/{len(data)}")
        sample_tasks = all_tasks[args.resume_from:]
    elif args.sample:
        import random
        random.seed(42)
        sample_tasks = random.sample(all_tasks, min(args.sample, len(all_tasks)))
    else:
        sample_tasks = all_tasks
    
    sample_data = {k: data[k] for k in sample_tasks}
    
    # Find compositions
    solutions = find_multi_step_solutions(sample_data, max_steps=args.max_steps, verbose=args.verbose)
    
    # Analyze patterns
    analyze_patterns(solutions)
    
    # Save results
    if args.output and solutions:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(solutions, f, indent=2)
        print(f"\n✓ Results saved to {output_path}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Solutions found: {len(solutions)}/{len(sample_data)}")
    print(f"Success rate: {100*len(solutions)/len(sample_data):.1f}%")
    
    if len(solutions) > 0:
        print("\n✓ Multi-step compositions CAN solve additional tasks")
        print("  Next: Integrate into ProductionSolver CompositionLayer")
    else:
        print("\n⚠ No compositions found - may need:")
        print("  - More diverse operator primitives")
        print("  - Longer composition chains (try --max-steps 4)")
        print("  - Better parameter inference")

if __name__ == "__main__":
    main()
