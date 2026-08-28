import numpy as np
import json
from cod_616.arc_organ.arc_operators import CenterRepulsionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']
op = CenterRepulsionOperator()

# Look at Example 1 in detail
ex = task['train'][0]
inp = np.array(ex['input'])
expected = np.array(ex['output'])

print("Example 1 Analysis")
print("="*60)
print(f"Grid size: {inp.shape}")

# Extract shapes from input
shapes = op._extract_shapes(inp)
print(f"\nInput shapes: {len(shapes)}")
for i, s in enumerate(shapes):
    print(f"  Shape {i+1}: color={s['color']}, center=({s['center_row']:.1f}, {s['center_col']:.1f}), bbox={s['bbox']}, size={s['height']}x{s['width']}")

# Extract shapes from expected output
out_shapes = op._extract_shapes(expected)
print(f"\nExpected output shapes: {len(out_shapes)}")
for i, s in enumerate(out_shapes):
    print(f"  Shape {i+1}: color={s['color']}, center=({s['center_row']:.1f}, {s['center_col']:.1f}), bbox={s['bbox']}, size={s['height']}x{s['width']}")

# Run our operator
result = op.apply(inp, {})
result_shapes = op._extract_shapes(result)
print(f"\nOur result shapes: {len(result_shapes)}")
for i, s in enumerate(result_shapes):
    print(f"  Shape {i+1}: color={s['color']}, center=({s['center_row']:.1f}, {s['center_col']:.1f}), bbox={s['bbox']}, size={s['height']}x{s['width']}")

print("\n" + "="*60)
print("EXPECTED OUTPUT:")
print(expected)
print("\nOUR RESULT:")
print(result)
print("\nDIFFERENCE:")
print((expected != result).astype(int))
