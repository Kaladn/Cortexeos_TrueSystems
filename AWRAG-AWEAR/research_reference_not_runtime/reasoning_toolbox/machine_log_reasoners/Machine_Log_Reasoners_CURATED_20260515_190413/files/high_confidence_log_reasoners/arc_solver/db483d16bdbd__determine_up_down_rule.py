import numpy as np
import json
from scipy import ndimage

with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

ex = data['ac2e8ecf']['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])
H, W = inp.shape
mid = H / 2.0

print(f"Example 1: {H}x{W} grid, midpoint = {mid}")
print("="*80)

# Extract input shapes
input_shapes = []
for color in range(1, 10):
    mask = (inp == color)
    if not mask.any():
        continue
    
    labeled, num = ndimage.label(mask)
    for shape_id in range(1, num + 1):
        shape_mask = (labeled == shape_id)
        rows, cols = np.where(shape_mask)
        
        min_row, max_row = rows.min(), rows.max()
        min_col, max_col = cols.min(), cols.max()
        center_row = rows.mean()
        
        input_shapes.append({
            'color': color,
            'min_row': min_row,
            'max_row': max_row,
            'center_row': center_row,
            'min_col': min_col,
            'max_col': max_col,
            'height': max_row - min_row + 1
        })

# Extract output shapes and determine which went UP vs DOWN
print("\nDetermining UP vs DOWN by checking output position:\n")

for s in input_shapes:
    # Find this shape in output by matching color and column range
    out_mask = (out == s['color'])
    if not out_mask.any():
        continue
    
    labeled, num = ndimage.label(out_mask)
    
    # Find matching shape by column position
    for shape_id in range(1, num + 1):
        shape_mask = (labeled == shape_id)
        rows, cols = np.where(shape_mask)
        
        out_min_col, out_max_col = cols.min(), cols.max()
        
        # Match by column range
        if out_min_col == s['min_col'] and out_max_col == s['max_col']:
            out_min_row = rows.min()
            
            # Determine if it went UP or DOWN
            if out_min_row < s['min_row']:
                direction = "UP"
            elif out_min_row > s['min_row']:
                direction = "DOWN"
            else:
                direction = "SAME"
            
            # Check various properties
            above_mid = s['center_row'] < mid
            in_upper_half = s['min_row'] < mid
            in_lower_half = s['max_row'] >= mid
            
            print(f"Color {s['color']} @ cols {s['min_col']}-{s['max_col']}:")
            print(f"  Input:  rows {s['min_row']}-{s['max_row']}, center={s['center_row']:.1f}")
            print(f"  Output: rows {out_min_row}-{rows.max()}")
            print(f"  Movement: {direction}")
            print(f"  center_row < mid: {above_mid}")
            print(f"  min_row < mid: {in_upper_half}")
            print(f"  max_row >= mid: {in_lower_half}")
            print()
            break

print("="*80)
print("\nLooking for pattern...")
print("\nShapes that went UP (to top band):")
print("Shapes that went DOWN (to bottom band):")
