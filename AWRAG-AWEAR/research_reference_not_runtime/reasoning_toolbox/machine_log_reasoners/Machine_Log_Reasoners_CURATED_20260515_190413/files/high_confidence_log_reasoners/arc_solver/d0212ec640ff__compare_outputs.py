"""
Detailed comparison of what we produce vs expected
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
ex = task['train'][0]

inp = np.array(ex['input'])
expected = np.array(ex['output'])

op = CenterRepulsionOperator()
params = op.analyze(inp, expected)
result = op.apply(inp, params)

print("EXPECTED OUTPUT:")
print(expected)
print("\nOUR RESULT:")
print(result)

print("\nDIFFERENCES (row, col, expected, got):")
diffs = np.argwhere(result != expected)
for r, c in diffs[:20]:  # Show first 20
    print(f"  ({r:2d}, {c:2d}): expected {expected[r,c]}, got {result[r,c]}")
