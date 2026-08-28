"""
Analyze EACH example independently - don't assume patterns carry over
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from scipy import ndimage

def classify_shape(grid):
    """Classify by pattern"""
    h, w = grid.shape
    filled = np.sum(grid > 0)
    
    if h == 3 and w == 3 and filled == 5:
        return 'PLUS_3x3'
    if h == 3 and w == 3 and filled == 8:
        return 'HOLLOW_3x3'
    if h == 4 and w == 4 and filled == 12:
        return 'RING_4x4'
    if h == 3 and w == 4 and filled >= 10:
        return 'FILLED_3x4'
    if h == 4 and w == 3 and filled >= 10:
        return 'FILLED_4x3'
    if h == 3 and w == 4 and filled <= 6:
        return 'CROSS_3x4'
    if h == 4 and w == 4 and filled == 7:
        return 'CROSS_4x4'
    if h >= 4 and filled >= 6:
        return f'CROSS_{h}x{w}'
    
    return f'UNKNOWN_{h}x{w}_f{filled}'

def analyze_example(ex_num, inp, out):
    print(f"\n{'='*80}")
    print(f"EXAMPLE {ex_num} - INDEPENDENT ANALYSIS")
    print(f"{'='*80}")
    print(f"Grid size: {inp.shape} → {out.shape}")
    
    # Extract input shapes
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
            
            grid = inp[min_r:max_r+1, min_c:max_c+1].copy()
            stype = classify_shape(grid)
            
            input_shapes.append({
                'color': color,
                'type': stype,
                'input_bbox': (min_r, min_c, max_r, max_c),
                'center_col': positions[:, 1].mean()
            })
    
    # Extract output shapes
    output_shapes = []
    for color in colors:
        mask = (out == color)
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            min_r, min_c = positions.min(axis=0)
            max_r, max_c = positions.max(axis=0)
            
            grid = out[min_r:max_r+1, min_c:max_c+1].copy()
            stype = classify_shape(grid)
            
            output_shapes.append({
                'color': color,
                'type': stype,
                'output_bbox': (min_r, min_c, max_r, max_c),
                'center_col': positions[:, 1].mean()
            })
    
    # Match shapes by color and type
    print(f"\nSHAPE TRANSFORMATIONS:")
    for inp_shape in sorted(input_shapes, key=lambda s: (s['type'], s['color'])):
        # Find matching output shape
        matches = [s for s in output_shapes 
                   if s['color'] == inp_shape['color'] and s['type'] == inp_shape['type']]
        
        if matches:
            out_shape = matches[0]
            in_r0, in_c0, in_r1, in_c1 = inp_shape['input_bbox']
            out_r0, out_c0, out_r1, out_c1 = out_shape['output_bbox']
            
            print(f"  {inp_shape['type']:15s} Color {inp_shape['color']}")
            print(f"    Input:  rows {in_r0:2d}-{in_r1:2d}, cols {in_c0:2d}-{in_c1:2d}")
            print(f"    Output: rows {out_r0:2d}-{out_r1:2d}, cols {out_c0:2d}-{out_c1:2d}")
            print(f"    Column preserved: {in_c0 == out_c0}")
    
    # Analyze output layout
    print(f"\nOUTPUT LAYOUT BY TYPE:")
    by_type = {}
    for s in output_shapes:
        if s['type'] not in by_type:
            by_type[s['type']] = []
        by_type[s['type']].append(s)
    
    for stype in sorted(by_type.keys()):
        rows = [s['output_bbox'][0] for s in by_type[stype]]
        print(f"  {stype:15s}: row range {min(rows):2d} - {max(rows)+2:2d}")

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']

for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    analyze_example(i, inp, out)
