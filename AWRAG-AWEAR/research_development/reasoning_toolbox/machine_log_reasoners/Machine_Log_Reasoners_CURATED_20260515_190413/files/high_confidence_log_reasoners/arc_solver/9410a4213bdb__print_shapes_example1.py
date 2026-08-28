import numpy as np
import json
from scipy import ndimage

with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

ex = data['ac2e8ecf']['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])
H, W = inp.shape

print(f"Example 1: {H}x{W} grid, midpoint = {H/2}")
print("="*80)

print("\n*** INPUT SHAPES ***\n")

for color in range(1, 10):
    mask = (inp == color)
    if not mask.any():
        continue
    
    labeled, num_shapes = ndimage.label(mask)
    
    print(f"Color {color}: {num_shapes} shape(s)")
    
    for shape_id in range(1, num_shapes + 1):
        shape_mask = (labeled == shape_id)
        rows, cols = np.where(shape_mask)
        
        pixels = list(zip(rows.tolist(), cols.tolist()))
        min_row, max_row = rows.min(), rows.max()
        min_col, max_col = cols.min(), cols.max()
        center_row = rows.mean()
        center_col = cols.mean()
        
        print(f"\n  Shape {shape_id}:")
        print(f"    Pixels ({len(pixels)} total): {pixels[:10]}{'...' if len(pixels) > 10 else ''}")
        print(f"    Bounding box: rows [{min_row}, {max_row}], cols [{min_col}, {max_col}]")
        print(f"    Center: ({center_row:.2f}, {center_col:.2f})")
        print(f"    Above midpoint: {center_row < H/2}")
        print(f"    PREDICTED: {'TOP (rows 0-{})'.format(max_row-min_row) if center_row < H/2 else 'BOTTOM (rows {}-{})'.format(H-1-(max_row-min_row), H-1)}")

print("\n" + "="*80)
print("\n*** OUTPUT SHAPES ***\n")

for color in range(1, 10):
    mask = (out == color)
    if not mask.any():
        continue
    
    labeled, num_shapes = ndimage.label(mask)
    
    print(f"Color {color}: {num_shapes} shape(s)")
    
    for shape_id in range(1, num_shapes + 1):
        shape_mask = (labeled == shape_id)
        rows, cols = np.where(shape_mask)
        
        pixels = list(zip(rows.tolist(), cols.tolist()))
        min_row, max_row = rows.min(), rows.max()
        min_col, max_col = cols.min(), cols.max()
        center_row = rows.mean()
        center_col = cols.mean()
        
        print(f"\n  Shape {shape_id}:")
        print(f"    Pixels ({len(pixels)} total): {pixels[:10]}{'...' if len(pixels) > 10 else ''}")
        print(f"    Bounding box: rows [{min_row}, {max_row}], cols [{min_col}, {max_col}]")
        print(f"    Center: ({center_row:.2f}, {center_col:.2f})")

print("\n" + "="*80)
print("\nCOMPARISON:")
print("If center_row < 6.5 → TOP (min_row=0)")
print("If center_row >= 6.5 → BOTTOM (max_row=12)")
