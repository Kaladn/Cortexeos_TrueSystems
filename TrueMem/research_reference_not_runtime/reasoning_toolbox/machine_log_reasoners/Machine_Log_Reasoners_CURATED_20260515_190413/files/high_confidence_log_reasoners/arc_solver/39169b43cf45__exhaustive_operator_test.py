"""
Exhaustive operator testing: run each operator individually against all tasks
to find all possible solves without early-exit optimization.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
import time
from arc_organ.arc_operators import OPERATORS

def test_operator_on_task(op, task_data):
    """Test a single operator on a task"""
    try:
        train_pairs = [
            (np.array(ex['input']), np.array(ex['output']))
            for ex in task_data['train']
        ]
        
        # Try analyze on all training examples
        params_list = []
        for inp, out in train_pairs:
            params = op.analyze(inp, out)
            if params is None:
                return None
            params_list.append(params)
        
        # Merge params (operator-specific logic)
        from arc_organ.arc_operators import merge_operator_params
        merged = merge_operator_params(op, params_list)
        if merged is None:
            return None
        
        # Validate: apply must work on all training examples
        for inp, exp_out in train_pairs:
            try:
                result = op.apply(inp, merged)
                if not np.array_equal(result, exp_out):
                    return None
            except:
                return None
        
        return merged
    except:
        return None

def main():
    start_time = time.time()
    
    # Load datasets
    load_start = time.time()
    with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
        train_data = json.load(f)
    
    with open('arc-prize-2025/arc-agi_evaluation_challenges.json', 'r') as f:
        eval_data = json.load(f)
    load_time = time.time() - load_start
    
    print("="*80)
    print("EXHAUSTIVE OPERATOR TESTING")
    print("="*80)
    print(f"Operators: {len(OPERATORS)}")
    print(f"Training tasks: {len(train_data)}")
    print(f"Evaluation tasks: {len(eval_data)}")
    print(f"Dataset load time: {load_time:.2f}s")
    print()
    
    # Results: operator_name -> list of task_ids
    results = {}
    operator_times = {}
    
    test_start = time.time()
    
    for op_idx, op in enumerate(OPERATORS, 1):
        op_start = time.time()
        print(f"[{op_idx}/{len(OPERATORS)}] Testing {op.name}...", end=" ", flush=True)
        
        solves = []
        
        # Test on training set
        for task_id, task in train_data.items():
            params = test_operator_on_task(op, task)
            if params is not None:
                solves.append(('train', task_id))
        
        # Test on evaluation set
        for task_id, task in eval_data.items():
            params = test_operator_on_task(op, task)
            if params is not None:
                solves.append(('eval', task_id))
        
        op_time = time.time() - op_start
        operator_times[op.name] = op_time
        
        if solves:
            results[op.name] = solves
            train_count = sum(1 for s in solves if s[0] == 'train')
            eval_count = sum(1 for s in solves if s[0] == 'eval')
            print(f"✓ {len(solves)} solves ({train_count} train, {eval_count} eval) [{op_time:.2f}s]")
        else:
            print(f"- No solves [{op_time:.2f}s]")
    
    test_time = time.time() - test_start
    
    print()
    print(f"Total testing time: {test_time:.2f}s")
    print()
    print("="*80)
    print("RESULTS BY OPERATOR")
    print("="*80)
    
    for op_name in sorted(results.keys()):
        solves = results[op_name]
        train_solves = [s[1] for s in solves if s[0] == 'train']
        eval_solves = [s[1] for s in solves if s[0] == 'eval']
        
        print(f"\n{op_name}:")
        print(f"  Training: {len(train_solves)} tasks")
        if train_solves:
            for tid in sorted(train_solves):
                print(f"    - {tid}")
        
        print(f"  Evaluation: {len(eval_solves)} tasks")
        if eval_solves:
            for tid in sorted(eval_solves):
                print(f"    - {tid}")
        
        print(f"  TOTAL: {len(solves)} tasks")
    
    print()
    print("="*80)
    print("OVERALL SUMMARY")
    print("="*80)
    
    all_train_solves = set()
    all_eval_solves = set()
    
    for solves in results.values():
        for dataset, task_id in solves:
            if dataset == 'train':
                all_train_solves.add(task_id)
            else:
                all_eval_solves.add(task_id)
    
    print(f"\nTraining set:")
    print(f"  Total tasks: {len(train_data)}")
    print(f"  Solved: {len(all_train_solves)}")
    print(f"  Success rate: {len(all_train_solves)/len(train_data)*100:.2f}%")
    
    print(f"\nEvaluation set:")
    print(f"  Total tasks: {len(eval_data)}")
    print(f"  Solved: {len(all_eval_solves)}")
    print(f"  Success rate: {len(all_eval_solves)/len(eval_data)*100:.2f}%")
    
    print(f"\nCOMBINED:")
    print(f"  Total tasks: {len(train_data) + len(eval_data)}")
    print(f"  Solved: {len(all_train_solves) + len(all_eval_solves)}")
    print(f"  Success rate: {(len(all_train_solves) + len(all_eval_solves))/(len(train_data) + len(eval_data))*100:.2f}%")
    
    print(f"\nOperators used: {len(results)}/{len(OPERATORS)}")
    
    total_time = time.time() - start_time
    print()
    print("="*80)
    print("TIMING SUMMARY")
    print("="*80)
    print(f"Dataset load: {load_time:.2f}s")
    print(f"Operator testing: {test_time:.2f}s")
    print(f"Total runtime: {total_time:.2f}s")
    print(f"Average per operator: {test_time/len(OPERATORS):.2f}s")
    print(f"Tasks processed: {len(train_data) + len(eval_data)}")
    print(f"Tasks per second: {(len(train_data) + len(eval_data))/test_time:.1f}")
    print()
    
    # Show slowest operators
    print("Slowest operators:")
    sorted_times = sorted(operator_times.items(), key=lambda x: x[1], reverse=True)
    for i, (op_name, op_time) in enumerate(sorted_times[:5], 1):
        pct = (op_time / test_time) * 100
        print(f"  {i}. {op_name}: {op_time:.2f}s ({pct:.1f}%)")
    print()

if __name__ == "__main__":
    main()
