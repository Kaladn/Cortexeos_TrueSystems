import numpy as np
import json
from cod_616.arc_organ.arc_operators import CenterRepulsionOperator

# Load Example 2
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

ex = data['ac2e8ecf']['train'][1]  # Example 2
inp = np.array(ex['input'])
expected = np.array(ex['output'])

print("Example 2 Trace")
print("="*70)
print(f"Input shape: {inp.shape}")
print(f"Vertical midpoint: {inp.shape[1] / 2.0}")
print()

op = CenterRepulsionOperator()
shapes = op._extract_shapes(inp)

print(f"Extracted {len(shapes)} shapes:")
v_mid = inp.shape[1] / 2.0

for i, s in enumerate(shapes, 1):
    min_r, min_c, max_r, max_c = s['bbox']
    
    # Count left/right
    cells_left = 0
    cells_right = 0
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            if inp[r, c] == s['color']:
                if c < v_mid:
                    cells_left += 1
                else:
                    cells_right += 1
    
    direction = "UP" if cells_left > cells_right else "DOWN"
    
    print(f"\nShape {i}:")
    print(f"  Color: {s['color']}")
    print(f"  Bbox: rows {min_r}-{max_r}, cols {min_c}-{max_c}")
    print(f"  Size: {s['height']}x{s['width']}")
    print(f"  Cells: {cells_left} left, {cells_right} right")
    print(f"  Direction: {direction}")

print("\n" + "="*70)
print("Running operator...")
result = op.apply(inp, {})

print("\nExpected output:")
print(expected)
print("\nOur result:")
print(result)

match = np.array_equal(result, expected)
print(f"\nMatch: {match}")
if not match:
    print(f"Differences: {np.sum(result != expected)} cells")
