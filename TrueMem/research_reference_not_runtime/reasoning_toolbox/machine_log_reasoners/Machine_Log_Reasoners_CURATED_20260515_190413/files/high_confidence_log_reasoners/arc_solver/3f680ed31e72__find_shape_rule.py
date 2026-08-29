import numpy as np
import json
from scipy import ndimage

with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

ex = data['ac2e8ecf']['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])
H, W = inp.shape

print(f"Example 1: {H}x{W} grid")
print("="*80)

print("\nREASONING - Matching input shapes to output by column position:\n")

# Match shapes by columns (they don't move horizontally)
matches = [
    ("INPUT: Color 1 @ rows 2-4, cols 4-6", "OUTPUT: Color 1 @ rows 0-2, cols 4-6", "UP by 2"),
    ("INPUT: Color 1 @ rows 2-4, cols 10-12", "OUTPUT: Color 1 @ rows 10-12, cols 10-12", "DOWN by 8"),
    ("INPUT: Color 2 @ rows 4-6, cols 0-2", "OUTPUT: Color 2 @ rows 10-12, cols 0-2", "DOWN by 6"),
    ("INPUT: Color 2 @ rows 9-11, cols 10-12", "OUTPUT: Color 2 @ rows 0-2, cols 10-12", "UP by 9"),
    ("INPUT: Color 5 @ rows 8-10, cols 2-5", "OUTPUT: Color 5 @ rows 3-5, cols 2-5", "UP by 5"),
    ("INPUT: Color 8 @ rows 5-7, cols 6-9", "OUTPUT: Color 8 @ rows 10-12, cols 6-9", "DOWN by 5"),
]

for inp_desc, out_desc, move in matches:
    print(f"{inp_desc}")
    print(f"  → {out_desc} [{move}]")
    print()

print("="*80)
print("\nGrouping by movement direction:")
print()

print("UP GROUP (moved towards row 0):")
up_group = [
    ("Color 1 @ cols 4-6", "rows 2-4 → 0-2"),
    ("Color 2 @ cols 10-12", "rows 9-11 → 0-2"),
    ("Color 5 @ cols 2-5", "rows 8-10 → 3-5"),
]
for name, move in up_group:
    print(f"  {name:25s} {move}")

print("\nDOWN GROUP (moved towards row 12):")
down_group = [
    ("Color 1 @ cols 10-12", "rows 2-4 → 10-12"),
    ("Color 2 @ cols 0-2", "rows 4-6 → 10-12"),
    ("Color 8 @ cols 6-9", "rows 5-7 → 10-12"),
]
for name, move in down_group:
    print(f"  {name:25s} {move}")

print("\n" + "="*80)
print("\nNow checking what differentiates UP vs DOWN shapes:")
print("Checking geometry (hollow vs filled center)...\n")

# Check each input shape for center pixel
for color in [1, 2, 5, 8]:
    mask = (inp == color)
    if not mask.any():
        continue
    
    labeled, num = ndimage.label(mask)
    for sid in range(1, num + 1):
        shape_mask = (labeled == sid)
        rows, cols = np.where(shape_mask)
        min_r, max_r = rows.min(), rows.max()
        min_c, max_c = cols.min(), cols.max()
        
        # Check center pixel
        center_r = (min_r + max_r) // 2
        center_c = (min_c + max_c) // 2
        has_center = inp[center_r, center_c] == color
        
        # Determine which group
        col_range = f"cols {min_c}-{max_c}"
        if (color == 1 and min_c == 4) or (color == 2 and min_c == 10) or (color == 5):
            group = "UP"
        else:
            group = "DOWN"
        
        print(f"Color {color} @ {col_range}: center_pixel={has_center} → {group}")

print("\n" + "="*80)
print("\nPATTERN CHECK:")
print("If center pixel is EMPTY (hollow shape) → UP")
print("If center pixel is FILLED (solid/cross shape) → DOWN")
