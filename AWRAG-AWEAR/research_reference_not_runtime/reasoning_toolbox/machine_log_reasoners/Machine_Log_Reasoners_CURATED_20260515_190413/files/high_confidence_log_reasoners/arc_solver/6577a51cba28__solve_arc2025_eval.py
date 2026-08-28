"""
Complete solution pipeline for arc-prize-2025 evaluation set.

1. Scan with anchor point measurements
2. Build operators for high-confidence matches  
3. Generate test predictions
"""

import sys
sys.path.insert(0, '.')

import json
import numpy as np
from scipy.ndimage import binary_fill_holes
from arc_organ.transform_matcher import find_close_matches

def fill_interior_preserve_existing(grid_in, boundary_color, fill_color):
    """Fill sealed interior with new color, preserving existing non-zero pixels."""
    result = grid_in.copy()
    mask = (grid_in == boundary_color)
    filled = binary_fill_holes(mask)
    interior = filled & ~mask
    fill_mask = interior & (grid_in == 0)
    result[fill_mask] = fill_color
    return result

def find_fill_params(task_data):
    """Find fill-interior parameters that work for all training examples."""
    ex = task_data['train'][0]
    grid_in = np.array(ex['input'])
    grid_out = np.array(ex['output'])
    
    if grid_in.shape != grid_out.shape:
        return None
    
    colors_in = set(int(x) for x in grid_in.flatten() if x != 0)
    colors_out = set(int(x) for x in grid_out.flatten() if x != 0)
    new_colors = colors_out - colors_in
    
    if not new_colors:
        return None
    
    # Try all combinations
    for bc in colors_in:
        for fc in new_colors:
            # Test on ALL training examples
            all_match = True
            for ex in task_data['train']:
                g_in = np.array(ex['input'])
                g_out = np.array(ex['output'])
                
                if g_in.shape != g_out.shape:
                    all_match = False
                    break
                
                try:
                    pred = fill_interior_preserve_existing(g_in, bc, fc)
                    if not np.array_equal(pred, g_out):
                        all_match = False
                        break
                except:
                    all_match = False
                    break
            
            if all_match:
                return {'boundary_color': int(bc), 'fill_color': int(fc)}
    
    return None

print('='*70)
print(' ARC-PRIZE-2025 EVALUATION: OPERATOR PIPELINE')
print('='*70)

# Load 2025 evaluation data
with open('arc-prize-2025/arc-agi_evaluation_challenges.json') as f:
    eval_tasks = json.load(f)

print(f'\nLoaded {len(eval_tasks)} evaluation tasks from arc-prize-2025')

# Step 1: Scan for high-confidence anchor point matches
print('\nStep 1: Scanning with anchor point measurements...')
high_confidence = []
checked = 0

for task_id, task_data in eval_tasks.items():
    checked += 1
    if checked % 50 == 0:
        print(f'  Checked {checked} tasks...')
    
    if not task_data.get('train'):
        continue
    
    ex = task_data['train'][0]
    grid_in = np.array(ex['input'])
    grid_out = np.array(ex['output'])
    
    if grid_in.shape != grid_out.shape:
        continue
    
    try:
        matches = find_close_matches(grid_in, grid_out, min_confidence=0.7)
        if matches:
            high_confidence.append((task_id, matches[0]))
    except:
        continue

print(f'\nFound {len(high_confidence)} high-confidence tasks')

# Step 2: Apply fill-interior operator
print('\nStep 2: Testing fill-interior-preserve operator...')
solutions = {}

for task_id, match_info in high_confidence:
    task_data = eval_tasks[task_id]
    params = find_fill_params(task_data)
    
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
        
        bc = params['boundary_color']
        fc = params['fill_color']
        print(f'  ✓ {task_id}: boundary={bc}, fill={fc}')

print(f'\nFill-interior-preserve: {len(solutions)} solves')

# Summary
print('\n' + '='*70)
print(f' RESULTS: {len(solutions)}/{len(high_confidence)} high-confidence tasks solved')
print('='*70)

if solutions:
    # Save solutions
    with open('results/arc2025_operator_solutions.json', 'w') as f:
        json.dump(solutions, f, indent=2)
    
    print(f'\n✓ Solutions saved to: results/arc2025_operator_solutions.json')
    print(f'\nSolved tasks ({len(solutions)}):')
    for task_id in sorted(solutions.keys())[:10]:
        sol = solutions[task_id]
        print(f'  {task_id}: {sol["operator"]} {sol["params"]}')
    
    if len(solutions) > 10:
        print(f'  ... and {len(solutions)-10} more')
else:
    print('\nNo solutions found yet. Need to implement more operator types.')
    print(f'\nHigh-confidence tasks ({len(high_confidence)}) are ready for manual operator development.')
