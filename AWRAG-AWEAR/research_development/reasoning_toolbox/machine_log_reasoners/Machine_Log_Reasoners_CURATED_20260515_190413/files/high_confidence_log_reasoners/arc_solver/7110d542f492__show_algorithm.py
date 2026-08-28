"""
SYSTEMATIC ARC DEBUGGING ALGORITHM - SUMMARY VERSION

This is the complete workflow for solving ANY ARC task systematically.
"""

import numpy as np
import json
from scipy import ndimage

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']

print("="*80)
print("SYSTEMATIC ARC DEBUGGING ALGORITHM")
print("="*80)
print()
print("WORKFLOW:")
print("1. Extract shapes from INPUT and OUTPUT")
print("2. Match INPUT shapes to OUTPUT shapes (by column position)")
print("3. Analyze movement patterns")
print("4. Test geometric hypotheses")
print("5. Formulate rule")
print("6. Implement operator")
print()
print("="*80)

all_up = []
all_down = []

for ex_idx, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    H, W = inp.shape
    
    print(f"\nEXAMPLE {ex_idx}: {H}x{W} grid")
    print("-" * 80)
    
    # Extract and match shapes
    for color in range(1, 10):
        in_mask = (inp == color)
        if not in_mask.any():
            continue
        
        in_labeled, in_num = ndimage.label(in_mask)
        
        for sid in range(1, in_num + 1):
            shape_mask = (in_labeled == sid)
            rows, cols = np.where(shape_mask)
            
            in_min_r, in_max_r = rows.min(), rows.max()
            in_min_c, in_max_c = cols.min(), cols.max()
            
            # Check center pixel
            center_r = (in_min_r + in_max_r) // 2
            center_c = (in_min_c + in_max_c) // 2
            has_center = inp[center_r, center_c] == color
            
            # Find in output (match by columns)
            out_mask = (out == color)
            if out_mask.any():
                out_labeled, out_num = ndimage.label(out_mask)
                
                for out_sid in range(1, out_num + 1):
                    out_shape = (out_labeled == out_sid)
                    out_rows, out_cols = np.where(out_shape)
                    
                    if out_cols.min() == in_min_c and out_cols.max() == in_max_c:
                        out_min_r = out_rows.min()
                        direction = "UP" if out_min_r < in_min_r else "DOWN"
                        
                        shape_type = "FILLED" if has_center else "HOLLOW"
                        
                        print(f"  Color {color} @ cols {in_min_c}-{in_max_c}: "
                              f"{shape_type:7s} rows {in_min_r}-{in_max_r} -> {out_min_r}-{out_rows.max()} [{direction}]")
                        
                        if direction == "UP":
                            all_up.append((color, has_center))
                        else:
                            all_down.append((color, has_center))
                        break

print("\n" + "="*80)
print("PATTERN ANALYSIS")
print("="*80)

print(f"\nUP shapes ({len(all_up)} total):")
hollow_up = sum(1 for _, has_center in all_up if not has_center)
filled_up = sum(1 for _, has_center in all_up if has_center)
print(f"  HOLLOW (no center pixel): {hollow_up}")
print(f"  FILLED (has center pixel): {filled_up}")

print(f"\nDOWN shapes ({len(all_down)} total):")
hollow_down = sum(1 for _, has_center in all_down if not has_center)
filled_down = sum(1 for _, has_center in all_down if has_center)
print(f"  HOLLOW (no center pixel): {hollow_down}")
print(f"  FILLED (has center pixel): {filled_down}")

print("\n" + "="*80)
print("RULE DISCOVERED")
print("="*80)
print()
print("IF shape has NO center pixel (hollow) -> PACK UPWARD")
print("IF shape has center pixel (filled)    -> PACK DOWNWARD")
print()
print(f"Accuracy: {hollow_up + filled_down}/{len(all_up) + len(all_down)} = "
      f"{100*(hollow_up + filled_down)/(len(all_up) + len(all_down)):.0f}%")

print("\n" + "="*80)
print("IMPLEMENTATION")
print("="*80)
print("""
1. for each color in [1..9]:
2.     labeled, num = ndimage.label(input_grid == color)
3.     for shape_id in range(1, num + 1):
4.         extract pixels, bbox, center
5.         center_r = (min_row + max_row) // 2
6.         center_c = (min_col + max_col) // 2
7.         has_center = input_grid[center_r, center_c] == color
8.         
9.         if has_center:
10.             add to filled_shapes
11.        else:
12.            add to hollow_shapes
13.
14. Pack hollow_shapes upward from row 0:
15.     for shape in sorted(hollow_shapes, key=lambda s: s['min_row']):
16.         for try_row in range(H):
17.             if shape fits at try_row (check column overlap):
18.                 place shape
19.                 break
20.
21. Pack filled_shapes downward from row H-1:
22.     for shape in sorted(filled_shapes, key=lambda s: s['max_row'], reverse=True):
23.         for try_row in range(H-1, -1, -1):
24.             if shape fits at try_row (check column overlap):
25.                 place shape
26.                 break
""")

print("="*80)
print("ALGORITHM COMPLETE")
print("="*80)
