"""
Build and test operators for the 104 high-confidence evaluation tasks.

Strategy: Create specialized operators based on anchor point measurements.
"""

import sys
sys.path.insert(0, '.')

import json
import numpy as np
from scipy.ndimage import binary_fill_holes
from collections import defaultdict
from arc_organ.object_space import detect_objects


def fill_interior_operator(grid_in, boundary_color, fill_color):
    """Fill sealed interiors with new color."""
    result = grid_in.copy()
    mask = (grid_in == boundary_color)
    filled_mask = binary_fill_holes(mask)
    interior_mask = filled_mask & ~mask
    result[interior_mask] = fill_color
    return result


def test_operator_on_task(task_data, operator_func, params):
    """Test an operator with given parameters on a task."""
    correct = 0
    total = 0
    
    for ex in task_data['train']:
        grid_in = np.array(ex['input'])
        grid_out = np.array(ex['output'])
        
        try:
            prediction = operator_func(grid_in, **params)
            if np.array_equal(prediction, grid_out):
                correct += 1
        except:
            pass
        
        total += 1
    
    return correct, total


def find_fill_interior_params(task_data):
    """Try to find fill-interior parameters that work."""
    ex = task_data['train'][0]
    grid_in = np.array(ex['input'])
    grid_out = np.array(ex['output'])
    
    # Get colors that appear
    colors_in = set(grid_in.flatten()) - {0}
    colors_out = set(grid_out.flatten()) - {0}
    new_colors = colors_out - colors_in
    
    if not new_colors:
        return None
    
    # Try each combination
    for boundary_color in colors_in:
        for fill_color in new_colors:
            params = {'boundary_color': boundary_color, 'fill_color': fill_color}
            correct, total = test_operator_on_task(task_data, fill_interior_operator, params)
            
            if correct == total:
                return params
    
    return None


def scan_and_solve_eval_tasks():
    """Scan 104 high-confidence tasks and build solutions."""
    
    # Load evaluation tasks
    with open('arc-prize-2024/arc-agi_evaluation_challenges.json') as f:
        eval_tasks = json.load(f)
    
    # Load high-confidence matches
    with open('results/eval_anchor_point_matches.json') as f:
        matches = json.load(f)
    
    high_conf_tasks = [tid for tid, info in matches['high_confidence']]
    
    print('Building operators for 104 high-confidence evaluation tasks...')
    print('='*70)
    
    solutions = {}
    operator_stats = defaultdict(int)
    
    # Try fill-interior operator
    print('\nTesting Fill-Interior Operator...')
    fill_interior_solves = []
    
    for task_id in high_conf_tasks[:50]:  # Test first 50
        task_data = eval_tasks[task_id]
        params = find_fill_interior_params(task_data)
        
        if params:
            # Validate on all training examples
            correct, total = test_operator_on_task(task_data, fill_interior_operator, params)
            
            if correct == total:
                # Generate test prediction
                test_in = np.array(task_data['test'][0]['input'])
                test_out = fill_interior_operator(test_in, **params)
                
                solutions[task_id] = {
                    'operator': 'fill_interior',
                    'params': params,
                    'prediction': test_out.tolist(),
                    'train_accuracy': f'{correct}/{total}'
                }
                
                fill_interior_solves.append(task_id)
                operator_stats['fill_interior'] += 1
                
                print(f'  ✓ {task_id}: boundary={params["boundary_color"]}, fill={params["fill_color"]}')
    
    print(f'\nFill-Interior: {len(fill_interior_solves)} solves')
    
    # Summary
    print('\n' + '='*70)
    print('OPERATOR RESULTS')
    print('='*70)
    
    total_solved = sum(operator_stats.values())
    print(f'\nTotal solved: {total_solved}/{len(high_conf_tasks[:50])} tested')
    
    for operator, count in operator_stats.items():
        print(f'  {operator}: {count} tasks')
    
    if solutions:
        print(f'\nSolved tasks:')
        for task_id in sorted(solutions.keys()):
            sol = solutions[task_id]
            print(f'  {task_id}: {sol["operator"]} ({sol["train_accuracy"]})')
    
    # Save solutions
    with open('results/operator_solutions_eval.json', 'w') as f:
        json.dump(solutions, f, indent=2)
    
    print(f'\n✓ Solutions saved to: results/operator_solutions_eval.json')
    print(f'\nNext: Expand to more operator types for remaining {len(high_conf_tasks)-total_solved} tasks')
    
    return solutions


if __name__ == "__main__":
    scan_and_solve_eval_tasks()
