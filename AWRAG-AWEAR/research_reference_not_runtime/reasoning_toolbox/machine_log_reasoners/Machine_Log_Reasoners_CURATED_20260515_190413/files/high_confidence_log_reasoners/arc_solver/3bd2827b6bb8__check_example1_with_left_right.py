import numpy as np
import json
from scipy import ndimage

with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

ex = data['ac2e8ecf']['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])
H, W = inp.shape
h_mid = W / 2.0

print(f"Example 1: {H}x{W}, h_midpoint={h_mid}")
print("=" * 80)

for color in range(1, 10):
    mask = (inp == color)
    if not mask.any():
        continue
    
    labeled, num = ndimage.label(mask)
    print(f"\nColor {color}: {num} shape(s)")
    
    for shape_id in range(1, num + 1):
        shape_mask = (labeled == shape_id)
        rows, cols = np.where(shape_mask)
        
        center_row = rows.mean()
        center_col = cols.mean()
        min_row, max_row = rows.min(), rows.max()
        min_col, max_col = cols.min(), cols.max()
        
        is_left = center_col < h_mid
        predicted = "UP" if is_left else "DOWN"
        
        print(f"  Shape {shape_id}: center=({center_row:.1f}, {center_col:.1f})")
        print(f"    Input rows: {min_row}-{max_row}, cols: {min_col}-{max_col}")
        print(f"    LEFT={is_left}, predict={predicted}")
        
        # Find in output
        out_mask = (out == color)
        if out_mask.any():
            out_labeled, out_num = ndimage.label(out_mask)
            # Try to match by size
            for out_id in range(1, out_num + 1):
                out_shape = (out_labeled == out_id)
                if out_shape.sum() == shape_mask.sum():
                    out_rows, out_cols = np.where(out_shape)
                    out_min_row, out_max_row = out_rows.min(), out_rows.max()
                    actual_dir = "UP" if out_min_row < min_row else "DOWN" if out_min_row > min_row else "SAME"
                    match = "✓" if actual_dir == predicted else "✗"
                    print(f"    Actual rows: {out_min_row}-{out_max_row}, direction={actual_dir} {match}")
                    break
