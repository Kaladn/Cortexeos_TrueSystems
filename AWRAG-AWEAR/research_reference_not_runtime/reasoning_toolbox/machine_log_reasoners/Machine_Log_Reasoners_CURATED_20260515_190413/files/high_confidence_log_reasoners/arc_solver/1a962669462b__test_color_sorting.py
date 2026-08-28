"""
Test COLOR SORTING hypothesis
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from scipy import ndimage

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']

for ex_num, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\n{'='*70}")
    print(f"EXAMPLE {ex_num} - COLOR SORTING ANALYSIS")
    print(f"{'='*70}")
    
    # Get all colors and their shapes
    input_colors = {}
    output_colors = {}
    
    for color in sorted(set(inp.flatten()) - {0}):
        mask = (inp == color)
        labeled, num = ndimage.label(mask)
        input_colors[color] = num
        
    for color in sorted(set(out.flatten()) - {0}):
        mask = (out == color)
        labeled, num = ndimage.label(mask)
        output_colors[color] = num
    
    print(f"\nCOLOR INVENTORY:")
    print(f"  Input colors:  {dict(input_colors)} (color: count)")
    print(f"  Output colors: {dict(output_colors)} (color: count)")
    print(f"  Match: {input_colors == output_colors}")
    
    # For each color, show WHERE its shapes end up
    print(f"\nCOLOR PLACEMENT IN OUTPUT:")
    
    for color in sorted(output_colors.keys()):
        mask = (out == color)
        labeled, num = ndimage.label(mask)
        
        print(f"\n  Color {color} ({num} shapes):")
        
        for lid in range(1, num + 1):
            obj_mask = (labeled == lid)
            positions = np.argwhere(obj_mask)
            min_r, min_c = positions.min(axis=0)
            max_r, max_c = positions.max(axis=0)
            
            # Classify position
            H = out.shape[0]
            third = H / 3
            
            if min_r < third:
                vert_zone = "TOP"
            elif min_r < 2 * third:
                vert_zone = "MID"
            else:
                vert_zone = "BOT"
            
            W = out.shape[1]
            third_w = W / 3
            
            if min_c < third_w:
                horiz_zone = "LEFT"
            elif min_c < 2 * third_w:
                horiz_zone = "CENTER"
            else:
                horiz_zone = "RIGHT"
            
            print(f"    Shape #{lid}: rows {min_r:2d}-{max_r:2d}, cols {min_c:2d}-{max_c:2d} → {vert_zone}-{horiz_zone}")
    
    # Check if colors with 2 shapes split top/bottom
    print(f"\nCOLOR SPLIT PATTERN:")
    for color in sorted(output_colors.keys()):
        if output_colors[color] == 2:
            mask = (out == color)
            labeled, num = ndimage.label(mask)
            
            positions_1 = np.argwhere(labeled == 1)
            positions_2 = np.argwhere(labeled == 2)
            
            row_1 = positions_1[:, 0].mean()
            row_2 = positions_2[:, 0].mean()
            
            if row_1 < row_2:
                print(f"  Color {color}: Shape 1 TOP, Shape 2 BOTTOM ✓")
            else:
                print(f"  Color {color}: Shape 1 BOTTOM, Shape 2 TOP ✓")
