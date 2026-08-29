"""
Verify exact shape classification and band placement
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from scipy import ndimage

def classify_by_pattern(grid):
    """Classify by exact filled pattern"""
    h, w = grid.shape
    filled_cells = np.sum(grid > 0)
    
    # PLUS: 5-cell cross (0X0 / XXX / 0X0)
    if h == 3 and w == 3 and filled_cells == 5:
        pattern = (grid > 0).astype(int)
        plus_pattern = np.array([[0,1,0], [1,1,1], [0,1,0]])
        if np.array_equal(pattern, plus_pattern):
            return 'PLUS'
    
    # HOLLOW_SQUARE: 8-cell hollow (XXX / X0X / XXX)
    if h == 3 and w == 3 and filled_cells == 8:
        pattern = (grid > 0).astype(int)
        hollow_pattern = np.array([[1,1,1], [1,0,1], [1,1,1]])
        if np.array_equal(pattern, hollow_pattern):
            return 'HOLLOW_SQUARE'
    
    # THICK_RING: 4x4 hollow
    if h == 4 and w == 4 and filled_cells == 12:
        pattern = (grid > 0).astype(int)
        ring_pattern = np.array([[1,1,1,1], [1,0,0,1], [1,0,0,1], [1,1,1,1]])
        if np.array_equal(pattern, ring_pattern):
            return 'THICK_RING'
    
    # WIDE_PLUS: 3x4 cross with 6 cells
    if h == 3 and w == 4 and filled_cells == 6:
        return 'WIDE_PLUS'
    
    # TALL_PLUS: 4x3 or 4x4 cross shapes
    if (h == 4 or h == 3) and filled_cells >= 6:
        # Check for cross pattern
        return 'TALL_PLUS'
    
    # WIDE_RING: 3x4 with 10 cells
    if h == 3 and w == 4 and filled_cells == 10:
        return 'WIDE_RING'
    
    return f'UNKNOWN_{h}x{w}_f{filled_cells}'

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']
ex = task['train'][0]

inp = np.array(ex['input'])
out = np.array(ex['output'])

print("INPUT vs OUTPUT SHAPE MAPPING:")
print("="*80)

# Extract all shapes from input
input_shapes = []
colors = set(inp.flatten()) - {0}
for color in colors:
    mask = (inp == color)
    labeled, num_features = ndimage.label(mask)
    
    for label_id in range(1, num_features + 1):
        obj_mask = (labeled == label_id)
        positions = np.argwhere(obj_mask)
        
        min_row, min_col = positions.min(axis=0)
        max_row, max_col = positions.max(axis=0)
        
        shape_grid = inp[min_row:max_row+1, min_col:max_col+1].copy()
        
        stype = classify_by_pattern(shape_grid)
        
        input_shapes.append({
            'color': color,
            'type': stype,
            'grid': shape_grid,
            'input_bbox': (min_row, min_col, max_row, max_col),
            'center_col': positions[:, 1].mean()
        })

# Extract all shapes from output
output_shapes = []
for color in colors:
    mask = (out == color)
    labeled, num_features = ndimage.label(mask)
    
    for label_id in range(1, num_features + 1):
        obj_mask = (labeled == label_id)
        positions = np.argwhere(obj_mask)
        
        min_row, min_col = positions.min(axis=0)
        max_row, max_col = positions.max(axis=0)
        
        shape_grid = out[min_row:max_row+1, min_col:max_col+1].copy()
        
        stype = classify_by_pattern(shape_grid)
        
        output_shapes.append({
            'color': color,
            'type': stype,
            'grid': shape_grid,
            'output_bbox': (min_row, min_col, max_row, max_col),
            'center_col': positions[:, 1].mean()
        })

# Match shapes by grid pattern
print("\nINPUT SHAPES:")
for s in sorted(input_shapes, key=lambda x: (x['input_bbox'][0], x['input_bbox'][1])):
    print(f"  Color {s['color']}: {s['type']}")
    print(f"    Input rows {s['input_bbox'][0]:2d}-{s['input_bbox'][2]:2d}, cols {s['input_bbox'][1]:2d}-{s['input_bbox'][3]:2d}")
    for row in s['grid']:
        print(f"      {row}")

print("\nOUTPUT SHAPES (grouped by type):")
by_type = {}
for s in output_shapes:
    if s['type'] not in by_type:
        by_type[s['type']] = []
    by_type[s['type']].append(s)

for stype in sorted(by_type.keys()):
    print(f"\n  {stype}:")
    for s in sorted(by_type[stype], key=lambda x: x['output_bbox'][1]):  # Sort by column
        print(f"    Color {s['color']}: rows {s['output_bbox'][0]:2d}-{s['output_bbox'][2]:2d}, cols {s['output_bbox'][1]:2d}-{s['output_bbox'][3]:2d}")

print("\n" + "="*80)
print("BAND ASSIGNMENTS:")
for stype in sorted(by_type.keys()):
    rows = [s['output_bbox'][0] for s in by_type[stype]]
    print(f"  {stype}: rows {min(rows)}-{max(rows)+2}")
