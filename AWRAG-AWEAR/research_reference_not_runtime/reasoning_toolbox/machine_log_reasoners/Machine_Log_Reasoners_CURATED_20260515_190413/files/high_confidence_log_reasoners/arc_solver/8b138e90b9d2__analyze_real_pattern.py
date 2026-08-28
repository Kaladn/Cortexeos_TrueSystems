"""
Analyze the test case to understand the REAL rule (not hardcoded for training)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from scipy import ndimage

def analyze_shape_movement(inp, out):
    """Analyze what actually happens to shapes"""
    print(f"Grid: {inp.shape} → {out.shape}")
    
    # Extract shapes from input
    input_shapes = []
    colors = set(inp.flatten()) - {0}
    
    for color in colors:
        mask = (inp == color)
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            min_r, min_c = positions.min(axis=0)
            max_r, max_c = positions.max(axis=0)
            
            input_shapes.append({
                'color': color,
                'input_rows': (min_r, max_r),
                'input_cols': (min_c, max_c),
                'center_row': positions[:, 0].mean(),
                'center_col': positions[:, 1].mean()
            })
    
    # Extract shapes from output
    output_shapes = []
    for color in colors:
        mask = (out == color)
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            min_r, min_c = positions.min(axis=0)
            max_r, max_c = positions.max(axis=0)
            
            output_shapes.append({
                'color': color,
                'output_rows': (min_r, max_r),
                'output_cols': (min_c, max_c),
                'center_row': positions[:, 0].mean(),
                'center_col': positions[:, 1].mean()
            })
    
    # Match shapes by color and analyze movement
    print("\nSHAPE MOVEMENTS:")
    for inp_shape in sorted(input_shapes, key=lambda s: (s['color'], s['center_row'])):
        # Find matching output shape by color
        matches = [s for s in output_shapes if s['color'] == inp_shape['color']]
        
        # Find closest by column position
        if matches:
            out_shape = min(matches, key=lambda s: abs(s['center_col'] - inp_shape['center_col']))
            
            in_r_min, in_r_max = inp_shape['input_rows']
            out_r_min, out_r_max = out_shape['output_rows']
            in_c_min, in_c_max = inp_shape['input_cols']
            out_c_min, out_c_max = out_shape['output_cols']
            
            row_shift = out_r_min - in_r_min
            col_shift = out_c_min - in_c_min
            
            H = inp.shape[0]
            input_hemisphere = "UPPER" if inp_shape['center_row'] < H/2 else "LOWER"
            output_hemisphere = "UPPER" if out_shape['center_row'] < H/2 else "LOWER"
            
            print(f"  Color {inp_shape['color']}")
            print(f"    Input:  rows {in_r_min:2d}-{in_r_max:2d}, cols {in_c_min:2d}-{in_c_max:2d} ({input_hemisphere})")
            print(f"    Output: rows {out_r_min:2d}-{out_r_max:2d}, cols {out_c_min:2d}-{out_c_max:2d} ({output_hemisphere})")
            print(f"    Shift: rows {row_shift:+3d}, cols {col_shift:+3d}")
            print(f"    Movement: {input_hemisphere} → {output_hemisphere}")

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

with open('arc-prize-2025/arc-agi_training_solutions.json', 'r') as f:
    solutions = json.load(f)

task = data['ac2e8ecf']

print("TRAINING EXAMPLES:")
print("="*80)
for i, ex in enumerate(task['train'], 1):
    print(f"\nExample {i}:")
    analyze_shape_movement(np.array(ex['input']), np.array(ex['output']))

print("\n\nTEST CASE:")
print("="*80)
test_input = np.array(task['test'][0]['input'])
expected_output = np.array(solutions['ac2e8ecf'][0])
analyze_shape_movement(test_input, expected_output)
