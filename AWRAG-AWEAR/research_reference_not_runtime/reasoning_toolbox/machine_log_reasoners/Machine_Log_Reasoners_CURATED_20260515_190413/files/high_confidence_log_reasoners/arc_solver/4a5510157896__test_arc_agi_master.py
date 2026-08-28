"""
Run all operators on ARC-AGI-master dataset
Tests the original ARC-AGI dataset format (individual JSON files per task)
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import infer_rule_for_task, OPERATORS


def load_task_from_json(json_path):
    """Load a single task from JSON file"""
    with open(json_path) as f:
        return json.load(f)


def test_task(task_id, task_data):
    """Test all operators on a single task"""
    # Convert to operator format
    train_pairs = [
        (np.array(ex['input']), np.array(ex['output']))
        for ex in task_data['train']
    ]
    
    test_inputs = [np.array(ex['input']) for ex in task_data['test']]
    
    # Try to infer rule
    op, params = infer_rule_for_task(train_pairs)
    
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
    print("ARC-AGI-MASTER DATASET TEST - ALL 22 OPERATORS")
    print("=" * 80)
    
    print(f"\nOPERATORS IN PRIORITY ORDER:")
    for i, op in enumerate(OPERATORS, 1):
        print(f"  {i:2d}. {op.name}")
    
    # Paths to datasets
    train_dir = Path('ARC-AGI-master/data/training')
    eval_dir = Path('ARC-AGI-master/data/evaluation')
    
    # Get all task files
    train_files = sorted(train_dir.glob('*.json'))
    eval_files = sorted(eval_dir.glob('*.json'))
    
    print(f"\n{'=' * 80}")
    print(f"SCANNING TRAINING SET ({len(train_files)} tasks)")
    print(f"{'=' * 80}\n")
    
    train_results = []
    for json_file in train_files:
        task_id = json_file.stem
        task_data = load_task_from_json(json_file)
        result = test_task(task_id, task_data)
        if result:
            train_results.append(result)
            print(f"[OK] {task_id}: {result['operator']}")
    
    print(f"\n{'=' * 80}")
    print(f"SCANNING EVALUATION SET ({len(eval_files)} tasks)")
    print(f"{'=' * 80}\n")
    
    eval_results = []
    for json_file in eval_files:
        task_id = json_file.stem
        task_data = load_task_from_json(json_file)
        result = test_task(task_id, task_data)
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
    print(f"  Total tasks: {len(train_files)}")
    print(f"  Solved: {len(train_results)}")
    print(f"  Success rate: {100 * len(train_results) / len(train_files):.2f}%")
    
    print(f"\nEvaluation set:")
    print(f"  Total tasks: {len(eval_files)}")
    print(f"  Solved: {len(eval_results)}")
    print(f"  Success rate: {100 * len(eval_results) / len(eval_files):.2f}%")
    
    print(f"\nCOMBINED:")
    total_tasks = len(train_files) + len(eval_files)
    total_solved = len(train_results) + len(eval_results)
    print(f"  Total tasks: {total_tasks}")
    print(f"  Solved: {total_solved}")
    print(f"  Success rate: {100 * total_solved / total_tasks:.2f}%")
    
    print(f"\nOperators used: {len(operator_counts)}/{len(OPERATORS)}")
    
    print(f"\n{'=' * 80}")
    
    # Save detailed results (convert params to string for JSON serialization)
    results_file = Path('arc_agi_master_results.json')
    
    def make_json_serializable(obj):
        """Convert params to JSON-serializable format"""
        if isinstance(obj, dict):
            return {str(k): make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_json_serializable(item) for item in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        else:
            return obj
    
    with open(results_file, 'w') as f:
        json.dump({
            'training': [make_json_serializable(r) for r in train_results],
            'evaluation': [make_json_serializable(r) for r in eval_results],
            'summary': {
                'total_tasks': total_tasks,
                'total_solved': total_solved,
                'success_rate': total_solved / total_tasks,
                'operators_used': list(operator_counts.keys())
            }
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")


if __name__ == '__main__':
    main()
