"""
Full dataset sweep for CenterHaloExpansionOperator
Tests the operator on all training + evaluation tasks
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import CenterHaloExpansionOperator

def test_task(task_id, task_data, operator):
    """Test operator on a single task"""
    results = {
        'task_id': task_id,
        'train_examples': len(task_data['train']),
        'test_examples': len(task_data['test']),
        'train_matches': 0,
        'params': None,
        'status': 'fail'
    }
    
    # Try to learn from training examples
    params = None
    for example in task_data['train']:
        input_arr = np.array(example['input'])
        output_arr = np.array(example['output'])
        
        detected_params = operator.analyze(input_arr, output_arr)
        if detected_params:
            params = detected_params
            break
    
    if params is None:
        return results
    
    results['params'] = params
    
    # Test on all training examples
    for example in task_data['train']:
        input_arr = np.array(example['input'])
        output_arr = np.array(example['output'])
        
        generated = operator.apply(input_arr, params)
        if np.array_equal(generated, output_arr):
            results['train_matches'] += 1
    
    # If all training examples match, mark as success
    if results['train_matches'] == results['train_examples']:
        results['status'] = 'success'
    
    return results


def main():
    print("=" * 80)
    print("CENTER-HALO EXPANSION OPERATOR - FULL DATASET SWEEP")
    print("=" * 80)
    
    operator = CenterHaloExpansionOperator()
    
    # Load datasets
    train_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
    eval_path = Path('arc-prize-2024/arc-agi_evaluation_challenges.json')
    
    with open(train_path) as f:
        train_tasks = json.load(f)
    
    with open(eval_path) as f:
        eval_tasks = json.load(f)
    
    print(f"\nDatasets loaded:")
    print(f"  Training: {len(train_tasks)} tasks")
    print(f"  Evaluation: {len(eval_tasks)} tasks")
    
    # Test training set
    print("\n" + "=" * 80)
    print("SCANNING TRAINING SET")
    print("=" * 80)
    
    train_successes = []
    for task_id, task_data in sorted(train_tasks.items()):
        result = test_task(task_id, task_data, operator)
        if result['status'] == 'success':
            train_successes.append(result)
            print(f"✅ {task_id}: {result['train_matches']}/{result['train_examples']} matches")
            print(f"   Params: {result['params']}")
    
    # Test evaluation set
    print("\n" + "=" * 80)
    print("SCANNING EVALUATION SET")
    print("=" * 80)
    
    eval_successes = []
    for task_id, task_data in sorted(eval_tasks.items()):
        result = test_task(task_id, task_data, operator)
        if result['status'] == 'success':
            eval_successes.append(result)
            print(f"✅ {task_id}: {result['train_matches']}/{result['train_examples']} matches")
            print(f"   Params: {result['params']}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SWEEP SUMMARY")
    print("=" * 80)
    
    print(f"\nTraining set:")
    print(f"  Total tasks: {len(train_tasks)}")
    print(f"  Solved: {len(train_successes)}")
    print(f"  Success rate: {100 * len(train_successes) / len(train_tasks):.2f}%")
    
    if train_successes:
        print(f"\n  Solved tasks:")
        for result in train_successes:
            print(f"    - {result['task_id']}")
    
    print(f"\nEvaluation set:")
    print(f"  Total tasks: {len(eval_tasks)}")
    print(f"  Solved: {len(eval_successes)}")
    print(f"  Success rate: {100 * len(eval_successes) / len(eval_tasks):.2f}%")
    
    if eval_successes:
        print(f"\n  Solved tasks:")
        for result in eval_successes:
            print(f"    - {result['task_id']}")
    
    print(f"\n{'=' * 80}")
    print(f"TOTAL SOLVED: {len(train_successes) + len(eval_successes)} tasks")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    main()
