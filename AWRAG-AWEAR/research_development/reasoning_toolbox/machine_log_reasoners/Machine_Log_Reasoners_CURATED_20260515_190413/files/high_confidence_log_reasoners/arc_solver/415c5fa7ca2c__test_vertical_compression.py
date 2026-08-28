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

# Extract all shapes
shapes = []
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
        height = max_row - min_row + 1
        
        shapes.append({
            'color': color,
            'min_row': min_row,
            'max_row': max_row,
            'min_col': min_col,
            'max_col': max_col,
            'height': height,
            'pixels': list(zip(rows.tolist(), cols.tolist()))
        })

# Sort by min_row (topmost point)
shapes.sort(key=lambda s: s['min_row'])

print("\nShapes sorted by min_row:")
for i, s in enumerate(shapes):
    print(f"{i+1}. Color {s['color']}: rows {s['min_row']}-{s['max_row']} (height={s['height']}), cols {s['min_col']}-{s['max_col']}")

print("\n" + "="*80)
print("\nNow compress upward while preserving order:")
print("Place each shape as high as possible without overlapping previous shapes")

# Simulate upward compression
current_row = 0
placements = []

for s in shapes:
    # Place this shape starting at current_row
    new_min_row = current_row
    new_max_row = current_row + s['height'] - 1
    
    placements.append({
        'color': s['color'],
        'old_rows': f"{s['min_row']}-{s['max_row']}",
        'new_rows': f"{new_min_row}-{new_max_row}",
        'cols': f"{s['min_col']}-{s['max_col']}"
    })
    
    # Move to next available row
    current_row = new_max_row + 1

print("\nPredicted placements (upward compression):")
for p in placements:
    print(f"Color {p['color']}: {p['old_rows']} → {p['new_rows']}, cols {p['cols']}")

print("\n" + "="*80)
print("\nActual output:")
for color in range(1, 10):
    mask = (out == color)
    if not mask.any():
        continue
    
    labeled, num = ndimage.label(mask)
    for shape_id in range(1, num + 1):
        shape_mask = (labeled == shape_id)
        rows, cols = np.where(shape_mask)
        min_row, max_row = rows.min(), rows.max()
        min_col, max_col = cols.min(), cols.max()
        print(f"Color {color}: rows {min_row}-{max_row}, cols {min_col}-{max_col}")
