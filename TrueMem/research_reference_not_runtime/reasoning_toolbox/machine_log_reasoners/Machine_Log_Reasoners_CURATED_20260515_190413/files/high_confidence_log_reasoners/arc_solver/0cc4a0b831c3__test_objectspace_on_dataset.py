"""
Test ObjectSpace + Transform Library on full ARC training dataset.

Evaluates which tasks can be solved with the new Euclidean geometry pipeline.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from collections import defaultdict
from arc_organ.object_space import detect_objects, build_object_space
from arc_organ.transform_library import infer_transform, apply_transform_to_grid, TRANSFORM_LIBRARY


def load_training_tasks():
    """Load all training tasks."""
    path = 'arc-prize-2024/arc-agi_training_challenges.json'
    with open(path, 'r') as f:
        return json.load(f)


def evaluate_task(task_id: str, task_data: dict) -> dict:
    """
    Evaluate a single task with ObjectSpace + Transform Library.
    
    Returns:
        dict with keys: solved, transform, train_accuracy, test_predictions
    """
    result = {
        'task_id': task_id,
        'solved': False,
        'transform': None,
        'train_accuracy': 0.0,
        'test_predictions': [],
        'error': None
    }
    
    try:
        train_examples = task_data['train']
        test_examples = task_data['test']
        
        if not train_examples or not test_examples:
            result['error'] = "No train/test examples"
            return result
        
        # Try to infer transform from first training example
        grid_in = np.array(train_examples[0]['input'])
        grid_out = np.array(train_examples[0]['output'])
        
        objects_in = detect_objects(grid_in)
        objects_out = detect_objects(grid_out)
        
        if not objects_in or not objects_out:
            result['error'] = "No objects detected"
            return result
        
        os_in = build_object_space(objects_in, *grid_in.shape)
        os_out = build_object_space(objects_out, *grid_out.shape)
        
        transform = infer_transform(os_in, os_out)
        
        if not transform:
            result['error'] = "No transform matched"
            return result
        
        result['transform'] = transform.name
        
        # Validate on all training examples
        correct_train = 0
        for ex in train_examples:
            grid_in = np.array(ex['input'])
            grid_out = np.array(ex['output'])
            
            prediction = apply_transform_to_grid(grid_in, transform)
            
            if np.array_equal(prediction, grid_out):
                correct_train += 1
        
        result['train_accuracy'] = correct_train / len(train_examples)
        
        # If all training examples match, try test examples
        if result['train_accuracy'] == 1.0:
            for ex in test_examples:
                grid_in = np.array(ex['input'])
                prediction = apply_transform_to_grid(grid_in, transform)
                result['test_predictions'].append(prediction.tolist())
            
            result['solved'] = True
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def run_dataset_evaluation():
    """Run evaluation on full training dataset."""
    print("\n" + "="*80)
    print(" OBJECTSPACE + TRANSFORM LIBRARY: FULL DATASET EVALUATION")
    print("="*80)
    
    tasks = load_training_tasks()
    print(f"\nLoaded {len(tasks)} training tasks")
    
    results = []
    solved_tasks = []
    transform_counts = defaultdict(int)
    error_counts = defaultdict(int)
    
    print("\nEvaluating tasks...")
    for i, (task_id, task_data) in enumerate(tasks.items()):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(tasks)} tasks...")
        
        result = evaluate_task(task_id, task_data)
        results.append(result)
        
        if result['solved']:
            solved_tasks.append(task_id)
            transform_counts[result['transform']] += 1
        elif result['error']:
            error_counts[result['error']] += 1
    
    # Summary
    print("\n" + "="*80)
    print(" RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n✓ Solved: {len(solved_tasks)}/{len(tasks)} tasks ({100*len(solved_tasks)/len(tasks):.1f}%)")
    
    if solved_tasks:
        print("\nSolved tasks:")
        for task_id in sorted(solved_tasks):
            result = next(r for r in results if r['task_id'] == task_id)
            print(f"  {task_id}: {result['transform']}")
    
    if transform_counts:
        print("\nTransforms used:")
        for transform, count in sorted(transform_counts.items(), key=lambda x: -x[1]):
            print(f"  {transform}: {count} task(s)")
    
    print("\nCommon errors:")
    for error, count in sorted(error_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {error}: {count} task(s)")
    
    # Save results
    output_file = 'results/objectspace_evaluation_results.json'
    Path('results').mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'total_tasks': len(tasks),
            'solved_tasks': solved_tasks,
            'solve_count': len(solved_tasks),
            'solve_rate': len(solved_tasks) / len(tasks),
            'transform_counts': dict(transform_counts),
            'error_counts': dict(error_counts),
            'detailed_results': results
        }, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    
    print("\n" + "="*80)
    print(f" OBJECTSPACE BASELINE: {len(solved_tasks)} SOLVES")
    print("="*80)
    
    return results, solved_tasks


if __name__ == "__main__":
    run_dataset_evaluation()
