"""
Targeted operators for the 104 high-confidence evaluation tasks.

Based on detailed pattern analysis.
"""

import sys
sys.path.insert(0, '.')

import json
import numpy as np
from scipy.ndimage import binary_fill_holes, label
from collections import Counter


def fill_interior_preserve_existing(grid_in, boundary_color, fill_color):
    """
    Fill interior of boundary with new color, but preserve any existing non-zero pixels.
    
    Example: Boundary is color 2, interior has some 2s and some 0s.
    Fill only the 0s with fill_color, keep interior 2s unchanged.
    """
    result = grid_in.copy()
    
    # Find boundary mask
    mask = (grid_in == boundary_color)
    
    # Fill holes to find interior
    filled = binary_fill_holes(mask)
    
    # Interior = filled AND NOT boundary
    interior = filled & ~mask
    
    # Fill only the background (0) pixels in interior
    fill_mask = interior & (grid_in == 0)
    result[fill_mask] = fill_color
    
    return result


def test_fill_preserve_on_task(task_data):
    """Find parameters for fill-preserve operator."""
    ex = task_data['train'][0]
    grid_in = np.array(ex['input'])
    grid_out = np.array(ex['output'])
    
    if grid_in.shape != grid_out.shape:
        return None
    
    # Find what changed
    changed_mask = (grid_in != grid_out)
    if not changed_mask.any():
        return None
    
    # Get colors (convert to int to avoid numpy int64 issues)
    colors_in = set(int(x) for x in grid_in.flatten() if x != 0)
    colors_out = set(int(x) for x in grid_out.flatten() if x != 0)
    new_colors = colors_out - colors_in
    
    if not new_colors:
        return None
    
    # Try each boundary color with each new fill color
    for boundary_color in colors_in:
        for fill_color in new_colors:
            try:
                pred = fill_interior_preserve_existing(grid_in, boundary_color, fill_color)
            except:
                continue
            
            if np.array_equal(pred, grid_out):
                # Validate on ALL training examples
                all_match = True
                for ex in task_data['train']:
                    g_in = np.array(ex['input'])
                    g_out = np.array(ex['output'])
                    
                    if g_in.shape != g_out.shape:
                        all_match = False
                        break
                    
                    p = fill_interior_preserve_existing(g_in, boundary_color, fill_color)
                    if not np.array_equal(p, g_out):
                        all_match = False
                        break
                
                if all_match:
                    return {'boundary_color': int(boundary_color), 'fill_color': int(fill_color)}
    
    return None


def solve_104_eval_tasks():
    """Build solutions for 104 high-confidence evaluation tasks."""
    
    # Load data
    with open('arc-prize-2025/arc-agi_evaluation_challenges.json') as f:
        eval_tasks = json.load(f)
    
    with open('results/eval_anchor_point_matches.json') as f:
        matches = json.load(f)
    
    high_conf = [tid for tid, info in matches['high_confidence']]
    
    print('Building Operators for 104 High-Confidence Evaluation Tasks')
    print('='*70)
    
    solutions = {}
    
    print('\nTesting: Fill Interior (Preserve Existing)')
    fill_preserve_count = 0
    
    for task_id in high_conf:
        task_data = eval_tasks[task_id]
        params = test_fill_preserve_on_task(task_data)
        
        if params:
            # Generate test prediction
            test_in = np.array(task_data['test'][0]['input'])
            test_out = fill_interior_preserve_existing(
                test_in, 
                params['boundary_color'], 
                params['fill_color']
            )
            
            solutions[task_id] = {
                'operator': 'fill_interior_preserve',
                'params': params,
                'prediction': test_out.tolist()
            }
            
            fill_preserve_count += 1
            bc = params['boundary_color']
            fc = params['fill_color']
            print(f'  ✓ {task_id}: boundary={bc}, fill={fc}')
    
    print(f'\nFill-Interior-Preserve: {fill_preserve_count} solves')
    
    # Summary
    print('\n' + '='*70)
    print(f'TOTAL SOLVED: {len(solutions)}/104 tasks')
    print('='*70)
    
    if solutions:
        # Save solutions
        with open('results/operator_eval_solutions.json', 'w') as f:
            json.dump(solutions, f, indent=2)
        
        print(f'\n✓ Solutions saved to: results/operator_eval_solutions.json')
        print(f'\nSolved tasks ({len(solutions)}):')
        for task_id in sorted(solutions.keys())[:20]:
            sol = solutions[task_id]
            op = sol['operator']
            params = sol['params']
            print(f'  {task_id}: {op} {params}')
        
        if len(solutions) > 20:
            print(f'  ... and {len(solutions)-20} more')
    
    return solutions


if __name__ == "__main__":
    solve_104_eval_tasks()
