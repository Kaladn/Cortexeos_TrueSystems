"""
Analyze example 3 placement
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from arc_organ.arc_operators import CenterRepulsionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']
ex = task['train'][2]  # Example 3

inp = np.array(ex['input'])
expected = np.array(ex['output'])

op = CenterRepulsionOperator()
shapes = op._extract_shapes(expected)

print("EXAMPLE 3 - OUTPUT SHAPE PLACEMENT:")
print("="*80)

# Group by type
by_type = {}
for s in shapes:
    stype = s['type']
    if stype not in by_type:
        by_type[stype] = []
    by_type[stype].append(s)

for stype in sorted(by_type.keys()):
    print(f"\n{stype.upper()}S:")
    for s in sorted(by_type[stype], key=lambda x: x['bbox'][1]):  # Sort by column
        print(f"  Color {s['color']}: {s['height']}x{s['width']}")
        print(f"    rows {s['bbox'][0]:2d}-{s['bbox'][2]:2d}, cols {s['bbox'][1]:2d}-{s['bbox'][3]:2d}")

print("\n\nExpected output:")
print(expected)

params = op.analyze(inp, expected)
result = op.apply(inp, params)

print("\nOur result:")
print(result)

print("\nDifferences:")
diffs = np.argwhere(result != expected)
for r, c in diffs[:20]:
    print(f"  ({r:2d}, {c:2d}): expected {expected[r,c]}, got {result[r,c]}")
