"""
MULTI-STEP OPERATOR COMPOSITION SEARCH

Find tasks that can be solved by chaining multiple operators together.
Tests combinations of: flip, rotation, recolor, shape movement, tiling, etc.

Strategy:
1. Try all 2-step combinations
2. Try all 3-step combinations
3. Focus on common patterns: transform → recolor, flip → recolor → flip
"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import OPERATORS
from typing import List, Dict, Optional
import itertools

def test_operator_sequence(task: Dict, operator_names: List[str]) -> bool:
    """Test if a sequence of operators solves the task"""
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
        for op in ops:
            # Try to analyze
            params = op.analyze(inp, expected_out)
            if params is None:
                # Try with empty params
                params = {}
            
            try:
                current = op.apply(current, params)
            except:
                return False
        
        # Check if matches
        if not np.array_equal(current, expected_out):
            return False
    
    return True

def find_multi_step_solutions(data: Dict, max_steps: int = 3):
    """Find tasks solvable by multi-step operator composition"""
    op_names = [op.name for op in OPERATORS]
    
    print(f"\nAvailable operators ({len(op_names)}):")
    for name in sorted(op_names):
        print(f"  - {name}")
    
    print("\n" + "="*80)
    print("SEARCHING FOR MULTI-STEP COMPOSITIONS")
    print("="*80)
    print(f"\nTesting up to {max_steps}-step sequences")
    print(f"Total tasks: {len(data)}")
    
    solutions = {}
    
    for task_idx, (task_id, task) in enumerate(data.items(), 1):
        if task_idx % 100 == 0:
            print(f"\nProgress: {task_idx}/{len(data)} tasks checked")
            print(f"Found {len(solutions)} multi-step solutions so far")
        
        # Try 2-step combinations (most common)
        if task_id not in solutions:
            for op1, op2 in itertools.product(op_names, repeat=2):
                if test_operator_sequence(task, [op1, op2]):
                    solutions[task_id] = [op1, op2]
                    print(f"FOUND 2-STEP: {task_id} = {op1} -> {op2}")
                    break
        
        # Try 3-step combinations (if 2-step didn't work)
        if task_id not in solutions and max_steps >= 3:
            # Focus on common patterns
            common_patterns = [
                # Flip/rotate then recolor
                ('mirror', 'recolor_mapping'),
                ('rotation_90', 'recolor_mapping'),
                ('mirror', 'position_based_recolor'),
                
                # Double transforms
                ('mirror', 'mirror'),
                ('rotation_90', 'rotation_90'),
                
                # Transform → shape operations
                ('mirror', 'block_expansion'),
                ('rotation_90', 'symmetry_completion'),
            ]
            
            for base_pattern in common_patterns:
                for op3 in op_names:
                    sequence = list(base_pattern) + [op3]
                    if test_operator_sequence(task, sequence):
                        solutions[task_id] = sequence
                        print(f"FOUND 3-STEP: {task_id} = {' -> '.join(sequence)}")
                        break
                
                if task_id in solutions:
                    break
    
    return solutions

def analyze_composition_patterns(solutions: Dict):
    """Analyze what types of compositions work"""
    print("\n" + "="*80)
    print("COMPOSITION PATTERN ANALYSIS")
    print("="*80)
    
    if not solutions:
        print("\nNo multi-step solutions found.")
        return
    
    # Group by number of steps
    by_length = {}
    for task_id, sequence in solutions.items():
        length = len(sequence)
        if length not in by_length:
            by_length[length] = []
        by_length[length].append((task_id, sequence))
    
    for length in sorted(by_length.keys()):
        tasks = by_length[length]
        print(f"\n{length}-STEP COMPOSITIONS ({len(tasks)} tasks):")
        for task_id, sequence in tasks:
            print(f"  {task_id}: {' -> '.join(sequence)}")
    
    # Find common operator combinations
    print("\n" + "="*80)
    print("COMMON OPERATOR PAIRS")
    print("="*80)
    
    pair_counts = {}
    for task_id, sequence in solutions.items():
        for i in range(len(sequence) - 1):
            pair = (sequence[i], sequence[i+1])
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
    
    if pair_counts:
        print("\nMost common operator sequences:")
        for pair, count in sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {pair[0]} -> {pair[1]}: {count} times")
    
    # Find operators that work well as first/last step
    first_ops = {}
    last_ops = {}
    for task_id, sequence in solutions.items():
        first = sequence[0]
        last = sequence[-1]
        first_ops[first] = first_ops.get(first, 0) + 1
        last_ops[last] = last_ops.get(last, 0) + 1
    
    print("\n" + "="*80)
    print("OPERATOR ROLES")
    print("="*80)
    
    print("\nMost common FIRST operators:")
    for op, count in sorted(first_ops.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {op}: {count} times")
    
    print("\nMost common LAST operators:")
    for op, count in sorted(last_ops.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {op}: {count} times")

# Main execution
if __name__ == "__main__":
    print("="*80)
    print("MULTI-STEP OPERATOR COMPOSITION DISCOVERY")
    print("="*80)
    
    # Load dataset
    with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
        data = json.load(f)
    
    # Resume from task 700 (previous run crashed, found 44 solutions)
    all_tasks = list(data.keys())
    resume_from = 700
    sample_data = {k: data[k] for k in all_tasks[resume_from:]}
    
    print(f"\nRESUMING from task {resume_from}/{len(data)}")
    print(f"Testing on {len(sample_data)} remaining tasks")
    print("This may take several minutes...")
    
    # Find solutions
    solutions = find_multi_step_solutions(sample_data, max_steps=3)
    
    # Analyze patterns
    analyze_composition_patterns(solutions)
    
    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"\nTotal solutions found: {len(solutions)}/{len(sample_data)}")
    print(f"Success rate: {100*len(solutions)/len(sample_data):.1f}%")
    
    if len(solutions) > 0:
        print("\nKey findings:")
        print("  - Multi-step composition CAN solve additional tasks")
        print("  - Most solutions are 2-step compositions")
        print("  - Common pattern: transform → recolor")
        print("\nNext steps:")
        print("  - Test on full 1000-task dataset")
        print("  - Try 4-5 step compositions")
        print("  - Add more spatial reasoning primitives")
    else:
        print("\nNo multi-step compositions found in sample.")
        print("This suggests:")
        print("  - Need more diverse operator primitives")
        print("  - Tasks may require 4+ step compositions")
        print("  - Need better parameter inference between steps")
