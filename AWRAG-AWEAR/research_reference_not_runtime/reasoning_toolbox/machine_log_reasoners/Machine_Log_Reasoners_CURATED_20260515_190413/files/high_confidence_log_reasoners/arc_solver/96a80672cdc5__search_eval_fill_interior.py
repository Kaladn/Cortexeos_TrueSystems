"""
Search all evaluation tasks for fill-sealed-interiors pattern.
"""

import numpy as np
from scipy.ndimage import binary_fill_holes
import json

def fill_sealed_interiors(grid, boundary_color, fill_color):
    result = grid.copy()
    mask = (grid == boundary_color)
    filled_mask = binary_fill_holes(mask)
    interior_mask = filled_mask & ~mask
    result[interior_mask] = fill_color
    return result

# Load evaluation challenges
with open('arc-prize-2024/arc-agi_evaluation_challenges.json') as f:
    eval_tasks = json.load(f)

print('Searching ALL 100 evaluation tasks for fill-interior patterns...')
print('='*70)

matches = []
checked = 0

for task_id, task_data in eval_tasks.items():
    checked += 1
    if checked % 20 == 0:
        print(f'Checked {checked}/100 tasks...')
    
    if not task_data.get('train'):
        continue
    
    # Try all color combinations
    for boundary_color in range(1, 10):
        for fill_color in range(1, 10):
            if boundary_color == fill_color:
                continue
            
            correct = 0
            total = 0
            
            for ex in task_data['train']:
                grid_in = np.array(ex['input'])
                grid_out = np.array(ex['output'])
                
                if grid_in.shape != grid_out.shape:
                    continue
                
                try:
                    pred = fill_sealed_interiors(grid_in, boundary_color, fill_color)
                    if np.array_equal(pred, grid_out):
                        correct += 1
                    total += 1
                except:
                    continue
            
            if total > 0 and correct == total:
                matches.append({
                    'task_id': task_id,
                    'boundary_color': boundary_color,
                    'fill_color': fill_color,
                    'num_train': total
                })
                break
        
        if matches and matches[-1]['task_id'] == task_id:
            break

print(f'\nSearched all {checked} evaluation tasks')
print('='*70)

if matches:
    print(f'\nFOUND {len(matches)} EVALUATION TASK(S) WITH FILL-INTERIOR PATTERN:\n')
    
    for match in matches:
        print(f"Task: {match['task_id']}")
        print(f"  Boundary color: {match['boundary_color']}")
        print(f"  Fill color: {match['fill_color']}")
        print(f"  Training examples: {match['num_train']}")
        
        # Generate test prediction
        task = eval_tasks[match['task_id']]
        test_in = np.array(task['test'][0]['input'])
        test_out = fill_sealed_interiors(test_in, match['boundary_color'], match['fill_color'])
        
        print(f"  Test prediction shape: {test_out.shape}")
        print(f"  READY FOR SUBMISSION")
        print()
        
    # Save results
    with open('results/fill_interior_eval_matches.json', 'w') as f:
        json.dump(matches, f, indent=2)
    
    print(f"Results saved to: results/fill_interior_eval_matches.json")
else:
    print('\nNO MATCHES FOUND in evaluation set.')
    print('Fill-interior pattern appears to be training-only.')
