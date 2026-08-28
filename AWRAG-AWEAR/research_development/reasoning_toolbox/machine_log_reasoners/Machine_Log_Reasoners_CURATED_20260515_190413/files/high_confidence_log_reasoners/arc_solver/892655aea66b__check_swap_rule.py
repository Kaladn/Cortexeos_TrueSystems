import numpy as np
import json
from scipy import ndimage

with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']

for ex_idx, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    H, W = inp.shape
    h_mid = W / 2.0
    v_mid = H / 2.0
    
    print(f"\n{'='*80}")
    print(f"Example {ex_idx}: {H}x{W} grid")
    print(f"{'='*80}")
    
    # Group shapes by color
    for color in range(1, 10):
        mask = (inp == color)
        if not mask.any():
            continue
        
        labeled, num = ndimage.label(mask)
        if num == 0:
            continue
        
        print(f"\nColor {color}: {num} shape(s)")
        
        # Extract all shapes of this color
        shapes = []
        for shape_id in range(1, num + 1):
            shape_mask = (labeled == shape_id)
            rows, cols = np.where(shape_mask)
            
            center_row = rows.mean()
            center_col = cols.mean()
            min_row, max_row = rows.min(), rows.max()
            
            is_left = center_col < h_mid
            is_upper = center_row < v_mid
            
            shapes.append({
                'id': shape_id,
                'center_row': center_row,
                'center_col': center_col,
                'min_row': min_row,
                'max_row': max_row,
                'is_left': is_left,
                'is_upper': is_upper
            })
        
        # Check if they're in opposite vertical hemispheres
        if num == 2:
            s1, s2 = shapes
            opposite_vert = s1['is_upper'] != s2['is_upper']
            print(f"  Two shapes: opposite vertical hemispheres = {opposite_vert}")
            
            if opposite_vert:
                print(f"    Shape 1: row {s1['min_row']}-{s1['max_row']}, {'UPPER' if s1['is_upper'] else 'LOWER'}")
                print(f"    Shape 2: row {s2['min_row']}-{s2['max_row']}, {'UPPER' if s2['is_upper'] else 'LOWER'}")
                print(f"    >>> SWAP EXPECTED")
            else:
                print(f"    Both {'UPPER' if s1['is_upper'] else 'LOWER'}")
                print(f"    >>> NO SWAP, apply LEFT→UP, RIGHT→DOWN")
        else:
            for s in shapes:
                side = "LEFT" if s['is_left'] else "RIGHT"
                vert = "UPPER" if s['is_upper'] else "LOWER"
                predicted = "UP" if s['is_left'] else "DOWN"
                print(f"    Shape {s['id']}: {side}, {vert} → predict {predicted}")
