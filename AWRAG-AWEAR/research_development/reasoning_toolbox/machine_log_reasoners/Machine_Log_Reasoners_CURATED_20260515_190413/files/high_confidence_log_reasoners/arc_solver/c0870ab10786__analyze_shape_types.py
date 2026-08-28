"""
Analyze shapes by GEOMETRIC TYPE, not color
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from scipy import ndimage

def extract_shapes(grid):
    """Extract shapes with geometric analysis"""
    shapes = []
    colors = set(grid.flatten()) - {0}
    
    for color in colors:
        mask = (grid == color)
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            min_row, min_col = positions.min(axis=0)
            max_row, max_col = positions.max(axis=0)
            
            shape_grid = grid[min_row:max_row+1, min_col:max_col+1].copy()
            
            h = max_row - min_row + 1
            w = max_col - min_col + 1
            
            # Count filled cells
            filled = np.sum(shape_grid > 0)
            total = h * w
            
            shapes.append({
                'grid': shape_grid,
                'bbox': (min_row, min_col, max_row, max_col),
                'center_row': positions[:, 0].mean(),
                'center_col': positions[:, 1].mean(),
                'height': h,
                'width': w,
                'color': int(color),
                'filled': filled,
                'total': total,
                'positions': positions
            })
    
    return shapes

def classify_shape(shape):
    """Classify shape by geometric type"""
    h = shape['height']
    w = shape['width']
    filled = shape['filled']
    grid = shape['grid']
    
    # HOLLOW SQUARE: 3x3, filled=8 (hollow center)
    if h == 3 and w == 3 and filled == 8:
        return 'hollow_square'
    
    # THICK RING: 4x4, larger hollow structure
    if h == 4 and w == 4 and filled > 8:
        return 'thick_ring'
    
    # PLUS: cross shape
    # Check for plus pattern: center column and center row filled
    if h >= 3 and w >= 4:
        # Check if it's a plus: vertical + horizontal bars
        center_row = h // 2
        center_col = w // 2
        if np.sum(grid[center_row, :] > 0) >= 3 and np.sum(grid[:, center_col] > 0) >= 3:
            return 'plus'
    
    # Alternative plus: tall and thin with horizontal bar
    if h == 3 and w == 4 and filled >= 7:
        return 'plus'
    
    return 'unknown'

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']

for i, ex in enumerate(task['train'], 1):
    print(f"\n{'='*60}")
    print(f"EXAMPLE {i} - SHAPE TYPE ANALYSIS")
    print(f"{'='*60}")
    
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print("\nINPUT SHAPES:")
    input_shapes = extract_shapes(inp)
    for s in sorted(input_shapes, key=lambda x: x['center_row']):
        stype = classify_shape(s)
        print(f"  Color {s['color']}, {s['height']}x{s['width']}, filled={s['filled']}/{s['total']}")
        print(f"    rows {s['bbox'][0]:2d}-{s['bbox'][2]:2d}, cols {s['bbox'][1]:2d}-{s['bbox'][3]:2d}")
        print(f"    center=({s['center_row']:.1f}, {s['center_col']:.1f})")
        print(f"    TYPE: {stype}")
        print(f"    Grid:")
        for row in s['grid']:
            print(f"      {row}")
    
    print("\nOUTPUT SHAPES:")
    output_shapes = extract_shapes(out)
    
    # Group by type
    by_type = {}
    for s in output_shapes:
        stype = classify_shape(s)
        if stype not in by_type:
            by_type[stype] = []
        by_type[stype].append(s)
    
    for stype in ['hollow_square', 'thick_ring', 'plus', 'unknown']:
        if stype in by_type:
            print(f"\n  {stype.upper()}S:")
            for s in sorted(by_type[stype], key=lambda x: x['center_col']):
                print(f"    Color {s['color']}: rows {s['bbox'][0]:2d}-{s['bbox'][2]:2d}, cols {s['bbox'][1]:2d}-{s['bbox'][3]:2d}")
    
    # Check vertical bands
    print("\n  VERTICAL BAND ANALYSIS:")
    hollow_rows = [s['bbox'][0] for s in by_type.get('hollow_square', [])]
    ring_rows = [s['bbox'][0] for s in by_type.get('thick_ring', [])]
    plus_rows = [s['bbox'][0] for s in by_type.get('plus', [])]
    
    if hollow_rows:
        print(f"    Hollow squares: rows {min(hollow_rows)}-{max(hollow_rows)+2}")
    if ring_rows:
        print(f"    Thick rings: rows {min(ring_rows)}-{max(ring_rows)+3}")
    if plus_rows:
        print(f"    Plus shapes: rows {min(plus_rows)}-{max(plus_rows)+2}")
