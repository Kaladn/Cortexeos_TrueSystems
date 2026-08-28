import numpy as np
import json
from scipy import ndimage

with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']

print("=" * 80)
print("ANALYZING SWAP PATTERN - Do shapes swap positions?")
print("=" * 80)

for ex_idx, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    H, W = inp.shape
    h_mid = W / 2.0
    v_mid = H / 2.0
    
    print(f"\n{'='*80}")
    print(f"Example {ex_idx}: {H}x{W} grid, H-midpoint={h_mid}, V-midpoint={v_mid}")
    print(f"{'='*80}")
    
    # Extract shapes from input
    for color in range(1, 10):
        mask = (inp == color)
        if not mask.any():
            continue
        
        labeled, num = ndimage.label(mask)
        for shape_id in range(1, num + 1):
            shape_mask = (labeled == shape_id)
            rows, cols = np.where(shape_mask)
            
            if len(rows) == 0:
                continue
            
            in_min_row, in_max_row = rows.min(), rows.max()
            in_min_col, in_max_col = cols.min(), cols.max()
            in_center_row = rows.mean()
            in_center_col = cols.mean()
            
            # Find this shape in output
            out_shape_mask = (out == color)
            if not out_shape_mask.any():
                print(f"  Color {color}: NOT FOUND IN OUTPUT!")
                continue
            
            out_labeled, out_num = ndimage.label(out_shape_mask)
            
            # Find which output shape matches best by size
            best_match = None
            best_overlap = 0
            
            for out_id in range(1, out_num + 1):
                out_mask = (out_labeled == out_id)
                if out_mask.sum() == shape_mask.sum():
                    best_match = out_id
                    break
            
            if best_match is None and out_num > 0:
                best_match = 1
            
            if best_match:
                out_mask = (out_labeled == best_match)
                out_rows, out_cols = np.where(out_mask)
                out_min_row, out_max_row = out_rows.min(), out_rows.max()
                out_min_col, out_max_col = out_cols.min(), out_cols.max()
                out_center_row = out_rows.mean()
                out_center_col = out_cols.mean()
                
                # Analyze the transformation
                row_shift = out_center_row - in_center_row
                col_shift = out_center_col - in_center_col
                
                in_left = "LEFT" if in_center_col < h_mid else "RIGHT"
                in_upper = "UPPER" if in_center_row < v_mid else "LOWER"
                out_left = "LEFT" if out_center_col < h_mid else "RIGHT"
                out_upper = "UPPER" if out_center_row < v_mid else "LOWER"
                
                vertical_move = "UP" if row_shift < 0 else "DOWN" if row_shift > 0 else "SAME"
                horizontal_move = "LEFT" if col_shift < 0 else "RIGHT" if col_shift > 0 else "SAME"
                
                print(f"\n  Color {color} @ cols {in_min_col}-{in_max_col}:")
                print(f"    INPUT:  rows {in_min_row:2d}-{in_max_row:2d}, center=({in_center_row:.1f}, {in_center_col:.1f}) [{in_left}, {in_upper}]")
                print(f"    OUTPUT: rows {out_min_row:2d}-{out_max_row:2d}, center=({out_center_row:.1f}, {out_center_col:.1f}) [{out_left}, {out_upper}]")
                print(f"    MOVEMENT: {vertical_move:>5s} {row_shift:+.1f} rows, {horizontal_move:>5s} {col_shift:+.1f} cols")
                
                # Check for swap pattern
                if in_left != out_left:
                    print(f"    >>> HORIZONTAL SWAP: {in_left} → {out_left}")
                if in_upper != out_upper:
                    print(f"    >>> VERTICAL SWAP: {in_upper} → {out_upper}")

print("\n" + "=" * 80)
print("PATTERN SUMMARY")
print("=" * 80)
