"""
Deep dive into high-confidence eval tasks to understand actual patterns.
"""

import sys
sys.path.insert(0, '.')

import json
import numpy as np
from arc_organ.object_space import detect_objects

# Load data
with open('arc-prize-2024/arc-agi_evaluation_challenges.json') as f:
    eval_tasks = json.load(f)

with open('results/eval_anchor_point_matches.json') as f:
    matches = json.load(f)

high_conf = [tid for tid, info in matches['high_confidence']]

print('Deep Analysis: First 10 High-Confidence Eval Tasks')
print('='*70)

for i, task_id in enumerate(high_conf[:10], 1):
    task = eval_tasks[task_id]
    ex = task['train'][0]
    
    grid_in = np.array(ex['input'])
    grid_out = np.array(ex['output'])
    
    objs_in = detect_objects(grid_in)
    objs_out = detect_objects(grid_out)
    
    colors_in = sorted(set(grid_in.flatten()) - {0})
    colors_out = sorted(set(grid_out.flatten()) - {0})
    new_colors = set(colors_out) - set(colors_in)
    
    print(f'\n{i}. {task_id}')
    print(f'   Grid: {grid_in.shape} → {grid_out.shape}')
    print(f'   Objects: {len(objs_in)} → {len(objs_out)}')
    print(f'   Colors: {colors_in} → {colors_out}')
    if new_colors:
        print(f'   NEW colors: {sorted(new_colors)}')
    
    # Check if output is just input with color replacement
    if grid_in.shape == grid_out.shape:
        # Count how many pixels changed
        changed = np.sum(grid_in != grid_out)
        total_pixels = grid_in.size
        print(f'   Pixels changed: {changed}/{total_pixels} ({100*changed/total_pixels:.1f}%)')
        
        # Check for simple color replacement
        if len(colors_in) == 1 and len(colors_out) == 2 and len(new_colors) == 1:
            old_color = colors_in[0]
            new_color = list(new_colors)[0]
            
            # Check if some pixels of old_color became new_color
            old_pixels_in = np.sum(grid_in == old_color)
            old_pixels_out = np.sum(grid_out == old_color)
            new_pixels_out = np.sum(grid_out == new_color)
            
            if old_pixels_out + new_pixels_out == old_pixels_in:
                print(f'   PATTERN: Color {old_color} split into {old_color} + {new_color}')
                print(f'   ({old_pixels_out} pixels stay {old_color}, {new_pixels_out} become {new_color})')

print('\n' + '='*70)
print('Looking for common patterns...')
print('='*70)
