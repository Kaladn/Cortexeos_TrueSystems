"""
Check example 2 specifically - where do 4-row shapes go?
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
    
    # PLUS: 3x3 with 5 cells (0X0 / XXX / 0X0)
    if h == 3 and w == 3 and filled_cells == 5:
        pattern = (grid > 0).astype(int)
        plus_pattern = np.array([[0,1,0], [1,1,1], [0,1,0]])
        if np.array_equal(pattern, plus_pattern):
            return 'PLUS'
    
    # HOLLOW_SQUARE: 3x3 with 8 cells (XXX / X0X / XXX)
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
    
    # Tall/wide crosses
    if h == 4 and w == 4 and filled_cells == 7:
        return 'TALL_CROSS'
    
    if h == 4 and w == 3 and filled_cells == 10:
        return 'TALL_RING'
    
    return f'UNKNOWN_{h}x{w}_f{filled_cells}'

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']
ex = task['train'][1]  # EXAMPLE 2

inp = np.array(ex['input'])
out = np.array(ex['output'])

print("EXAMPLE 2 - INPUT SHAPES:")
print("="*80)

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
        
        print(f"\nColor {color}: {stype}")
        print(f"  Input  rows {min_row:2d}-{max_row:2d}, cols {min_col:2d}-{max_col:2d}")
        for row in shape_grid:
            print(f"    {row}")

print("\n\nEXAMPLE 2 - OUTPUT SHAPES:")
print("="*80)

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
        
        print(f"\nColor {color}: {stype}")
        print(f"  Output rows {min_row:2d}-{max_row:2d}, cols {min_col:2d}-{max_col:2d}")
        for row in shape_grid:
            print(f"    {row}")
