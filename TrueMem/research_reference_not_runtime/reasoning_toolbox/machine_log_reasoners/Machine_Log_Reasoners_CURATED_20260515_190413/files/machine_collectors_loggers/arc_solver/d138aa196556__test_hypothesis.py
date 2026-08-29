"""
Test hypothesis: Shapes repel from centerline.
Closer to center = pushed further away = cross to opposite side
Farther from center = pushed less = stay on same side, just closer to edge
"""
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

# Match shapes by color and column
for s_in in shapes:
    # Find matching output shape (same color, similar column)
    matches = [s for s in out_shapes if s['color'] == s_in['color'] and 
               abs(s['center_col'] - s_in['center_col']) < 1]
    
    if matches:
        s_out = matches[0]
        out_shapes.remove(s_out)  # Remove so we don't match again
        
        dist_from_center = abs(s_in['center_row'] - midpoint)
        shift = s_out['bbox'][0] - s_in['bbox'][0]
        crosses = (s_in['center_row'] < midpoint) != (s_out['center_row'] < midpoint)
        
        print(f"Color {s_in['color']}:")
        print(f"  Input row: {s_in['bbox'][0]}, center={s_in['center_row']:.1f}, dist from mid={dist_from_center:.1f}")
        print(f"  Output row: {s_out['bbox'][0]}, center={s_out['center_row']:.1f}")
        print(f"  Shift: {shift:+d} rows, crosses={crosses}")
        print()

print("\nHypothesis: distance from center determines if you cross?")
print("Let's check: closest to center should cross, far from center should stay")
