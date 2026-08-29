"""
Analyze the EXACT row placement in output
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
    
    print(f"\nEXAMPLE {ex_num}:")
    print(f"Grid: {inp.shape}")
    midpoint = inp.shape[0] / 2
    print(f"Midpoint: {midpoint}")
    
    # Track each shape's movement
    colors = sorted(set(inp.flatten()) - {0})
    
    for color in colors:
        # Input shapes
        mask_in = (inp == color)
        labeled_in, num_in = ndimage.label(mask_in)
        
        # Output shapes
        mask_out = (out == color)
        labeled_out, num_out = ndimage.label(mask_out)
        
        print(f"\n  Color {color}:")
        
        for lid in range(1, num_in + 1):
            obj_mask = (labeled_in == lid)
            positions = np.argwhere(obj_mask)
            min_r_in, min_c_in = positions.min(axis=0)
            max_r_in, max_c_in = positions.max(axis=0)
            center_r_in = positions[:, 0].mean()
            
            hemisphere = "UPPER" if center_r_in < midpoint else "LOWER"
            
            print(f"    Input  #{lid}: rows {min_r_in}-{max_r_in}, cols {min_c_in}-{max_c_in}, center={center_r_in:.1f} [{hemisphere}]")
            
            # Find corresponding output shape (same columns)
            for lid_out in range(1, num_out + 1):
                obj_mask_out = (labeled_out == lid_out)
                pos_out = np.argwhere(obj_mask_out)
                min_r_out, min_c_out = pos_out.min(axis=0)
                max_r_out, max_c_out = pos_out.max(axis=0)
                
                # Match by column range
                if min_c_out == min_c_in and max_c_out == max_c_in:
                    row_shift = min_r_out - min_r_in
                    print(f"    Output #{lid_out}: rows {min_r_out}-{max_r_out}, cols {min_c_out}-{max_c_out} [SHIFT: {row_shift:+d}]")
                    break
