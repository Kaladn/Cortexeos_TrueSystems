"""
Test if operator correctly solves all examples
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
op = CenterRepulsionOperator()

print("Testing CenterRepulsionOperator on ac2e8ecf")
print("="*60)

all_pass = True
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    expected = np.array(ex['output'])
    
    params = op.analyze(inp, expected)
    if params is None:
        print(f"\nExample {i}: ✗ Analyze failed")
        all_pass = False
        continue
    
    result = op.apply(inp, params)
    
    if np.array_equal(result, expected):
        print(f"Example {i}: ✓ PASS")
    else:
        print(f"Example {i}: ✗ FAIL")
        all_pass = False

if all_pass:
    print("\n✓✓✓ ALL EXAMPLES PASS! ✓✓✓")
    print("\nOperator is ready to solve task ac2e8ecf")
else:
    print("\n✗ Some examples failed")
