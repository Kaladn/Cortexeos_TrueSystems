import numpy as np
import json
from cod_616.arc_organ.arc_operators import CenterRepulsionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']
op = CenterRepulsionOperator()

ex = task['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])
H, W = inp.shape
midpoint = H / 2.0

print(f"Example 1: H={H}, midpoint={midpoint}")
print()

shapes = op._extract_shapes(inp)
out_shapes = op._extract_shapes(out)

print("Checking majority rule for each shape:")
print()

for s in shapes:
    min_row, min_col, max_row, max_col = s['bbox']
    cells_above = 0
    cells_below = 0
    
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            if inp[r, c] == s['color']:
                if r < midpoint:
                    cells_above += 1
                else:
                    cells_below += 1
    
    predicted_direction = "UP" if cells_above > cells_below else "DOWN"
    
    # Find actual output position
    out_match = [os for os in out_shapes if os['color'] == s['color'] and abs(os['center_col'] - s['center_col']) < 1]
    if out_match:
        actual_out = out_match[0]
        actual_direction = "UP" if actual_out['bbox'][0] < midpoint else "DOWN"
        match = "✓" if predicted_direction == actual_direction else "✗"
    else:
        actual_direction = "?"
        match = "?"
    
    print(f"Color {s['color']}, cols {min_col}-{max_col}:")
    print(f"  Input rows {min_row}-{max_row}, center={s['center_row']:.1f}")
    print(f"  Cells: {cells_above} above, {cells_below} below midpoint")
    print(f"  Predicted: {predicted_direction}, Actual: {actual_direction} {match}")
    if out_match:
        print(f"  Output rows {out_match[0]['bbox'][0]}-{out_match[0]['bbox'][2]}")
    print()
