"""
Analyze ac2e8ecf task - determine the rule for EACH example independently
"""
import numpy as np
import json
from scipy import ndimage

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']

def analyze_example(inp, out, ex_num):
    print(f"\n{'='*70}")
    print(f"EXAMPLE {ex_num} RULE DISCOVERY")
    print(f"{'='*70}")
    
    H, W = inp.shape
    h_mid = H / 2.0
    v_mid = W / 2.0
    
    print(f"Grid: {H}x{W}, H-midpoint={h_mid}, V-midpoint={v_mid}")
    
    # Track each shape's movement
    colors = sorted(set(inp.flatten()) - {0})
    
    for color in colors:
        in_mask = (inp == color)
        labeled_in, num_in = ndimage.label(in_mask)
        
        out_mask = (out == color)
        labeled_out, num_out = ndimage.label(out_mask)
        
        if num_in != num_out:
            continue
        
        for i in range(1, num_in + 1):
            shape_mask = (labeled_in == i)
            in_pos = np.argwhere(shape_mask)
            in_rows = in_pos[:, 0]
            in_cols = in_pos[:, 1]
            in_center_row = in_rows.mean()
            in_center_col = in_cols.mean()
            in_min_col, in_max_col = in_cols.min(), in_cols.max()
            in_min_row, in_max_row = in_rows.min(), in_rows.max()
            
            # Find matching output shape
            for j in range(1, num_out + 1):
                out_shape_mask = (labeled_out == j)
                out_pos = np.argwhere(out_shape_mask)
                out_cols = out_pos[:, 1]
                out_center_col = out_cols.mean()
                
                # Match by column (columns should be preserved)
                if abs(out_center_col - in_center_col) < 0.5:
                    out_rows = out_pos[:, 0]
                    out_center_row = out_rows.mean()
                    out_min_row = out_rows.min()
                    
                    row_shift = out_min_row - in_min_row
                    col_shift = out_cols.mean() - in_cols.mean()
                    
                    # Analyze position relative to midpoints
                    left_cells = np.sum(in_cols < v_mid)
                    right_cells = np.sum(in_cols >= v_mid)
                    upper_cells = np.sum(in_rows < h_mid)
                    lower_cells = np.sum(in_rows >= h_mid)
                    
                    direction = "UP" if out_min_row < in_min_row else "DOWN" if out_min_row > in_min_row else "SAME"
                    
                    print(f"\nColor {color} shape @ col {in_center_col:.1f}:")
                    print(f"  Input:  rows {in_min_row}-{in_max_row}, cols {in_min_col}-{in_max_col}")
                    print(f"  Output: rows {out_min_row}-{out_rows.max()}")
                    print(f"  Shift: rows {row_shift:+d}, cols {col_shift:+.1f}")
                    print(f"  Position: {left_cells} left, {right_cells} right | {upper_cells} upper, {lower_cells} lower")
                    print(f"  Movement: {direction}")
                    
                    break
    
    print()

# Analyze each example
for i, ex in enumerate(task['train'], 1):
    analyze_example(np.array(ex['input']), np.array(ex['output']), i)

print(f"\n{'='*70}")
print("PATTERN SUMMARY")
print(f"{'='*70}")
print("Looking for consistent rule across all examples...")
print("Hypothesis: Left-side shapes go UP, right-side shapes go DOWN")
print("Columns are PRESERVED (no horizontal movement)")
print("Rows change based on left/right position")
