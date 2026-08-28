"""
Run all operators on full ARC dataset
Tests all 22 operators (including CenterHaloExpansionOperator) on both training and evaluation sets
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import infer_rule_for_task, OPERATORS

def test_task(task_id, task_data):
    """Test all operators on a single task"""
    try:
        # Convert to operator format
        train_pairs = [
            (np.array(ex['input']), np.array(ex['output']))
            for ex in task_data['train']
        ]
        
        test_inputs = [np.array(ex['input']) for ex in task_data['test']]
        
        # Try to infer rule
        op, params = infer_rule_for_task(train_pairs)
    except Exception as e:
        # Skip tasks that cause errors in operators
        return None
    
    if op is None:
        return None
    
    # Verify on all training examples
    all_train_match = True
    for inp, exp_out in train_pairs:
        try:
            generated = op.apply(inp, params)
            if not np.array_equal(generated, exp_out):
                all_train_match = False
                break
        except:
            all_train_match = False
            break
    
    if not all_train_match:
        return None
    
    return {
        'task_id': task_id,
        'operator': op.name,
        'params': params,
        'train_count': len(train_pairs),
        'test_count': len(test_inputs)
    }


def main():
    print("=" * 80)
    print("FULL OPERATOR SYSTEM TEST - ALL 22 OPERATORS")
    print("=" * 80)
    
    print(f"\nOPERATORS IN PRIORITY ORDER:")
    for i, op in enumerate(OPERATORS, 1):
        print(f"  {i:2d}. {op.name}")
    
    # Load datasets (2025)
    train_path = Path('arc-prize-2025/arc-agi_training_challenges.json')
    eval_path = Path('arc-prize-2025/arc-agi_evaluation_challenges.json')
    
    with open(train_path) as f:
        train_tasks = json.load(f)
    
    with open(eval_path) as f:
        eval_tasks = json.load(f)
    
    print(f"\n{'=' * 80}")
    print(f"SCANNING TRAINING SET ({len(train_tasks)} tasks)")
    print(f"{'=' * 80}\n")
    
    train_results = []
    for task_id in sorted(train_tasks.keys()):
        result = test_task(task_id, train_tasks[task_id])
        if result:
            train_results.append(result)
            print(f"[OK] {task_id}: {result['operator']}")
    
    print(f"\n{'=' * 80}")
    print(f"SCANNING EVALUATION SET ({len(eval_tasks)} tasks)")
    print(f"{'=' * 80}\n")
    
    eval_results = []
    for task_id in sorted(eval_tasks.keys()):
        result = test_task(task_id, eval_tasks[task_id])
        if result:
            eval_results.append(result)
            print(f"[OK] {task_id}: {result['operator']}")
    
    # Summary by operator
    print(f"\n{'=' * 80}")
    print("RESULTS BY OPERATOR")
    print(f"{'=' * 80}\n")
    
    # Count by operator
    operator_counts = {}
    all_results = train_results + eval_results
    
    for result in all_results:
        op_name = result['operator']
        if op_name not in operator_counts:
            operator_counts[op_name] = {'train': [], 'eval': []}
        
        if result in train_results:
            operator_counts[op_name]['train'].append(result['task_id'])
        else:
            operator_counts[op_name]['eval'].append(result['task_id'])
    
    for op_name in sorted(operator_counts.keys()):
        counts = operator_counts[op_name]
        train_count = len(counts['train'])
        eval_count = len(counts['eval'])
        total = train_count + eval_count
        
        print(f"{op_name}:")
        print(f"  Training: {train_count} tasks")
        if counts['train']:
            for task_id in counts['train'][:5]:  # Show first 5
                print(f"    - {task_id}")
            if train_count > 5:
                print(f"    ... and {train_count - 5} more")
        
        print(f"  Evaluation: {eval_count} tasks")
        if counts['eval']:
            for task_id in counts['eval'][:5]:
                print(f"    - {task_id}")
            if eval_count > 5:
                print(f"    ... and {eval_count - 5} more")
        
        print(f"  TOTAL: {total} tasks\n")
    
    # Overall summary
    print(f"{'=' * 80}")
    print("OVERALL SUMMARY")
    print(f"{'=' * 80}\n")
    
    print(f"Training set:")
    print(f"  Total tasks: {len(train_tasks)}")
    print(f"  Solved: {len(train_results)}")
    print(f"  Success rate: {100 * len(train_results) / len(train_tasks):.2f}%")
    
    print(f"\nEvaluation set:")
    print(f"  Total tasks: {len(eval_tasks)}")
    print(f"  Solved: {len(eval_results)}")
    print(f"  Success rate: {100 * len(eval_results) / len(eval_tasks):.2f}%")
    
    print(f"\nCOMBINED:")
    print(f"  Total tasks: {len(train_tasks) + len(eval_tasks)}")
    print(f"  Solved: {len(train_results) + len(eval_results)}")
    print(f"  Success rate: {100 * (len(train_results) + len(eval_results)) / (len(train_tasks) + len(eval_tasks)):.2f}%")
    
    print(f"\nOperators used: {len(operator_counts)}/{len(OPERATORS)}")
    
    print(f"\n{'=' * 80}")


if __name__ == '__main__':
    main()
