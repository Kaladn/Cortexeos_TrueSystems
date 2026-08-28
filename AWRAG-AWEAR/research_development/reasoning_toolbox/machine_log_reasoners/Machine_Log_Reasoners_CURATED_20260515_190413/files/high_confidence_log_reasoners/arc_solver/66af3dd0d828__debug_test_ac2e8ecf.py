"""
Debug why ac2e8ecf test case fails
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from arc_organ.arc_operators import CenterRepulsionOperator, infer_rule_for_task

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

with open('arc-prize-2025/arc-agi_training_solutions.json', 'r') as f:
    solutions = json.load(f)

task = data['ac2e8ecf']
op = CenterRepulsionOperator()

print("Testing ac2e8ecf")
print("="*60)

# Test training examples
print("\nTRAINING EXAMPLES:")
train_pairs = []
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    train_pairs.append((inp, out))
    
    params = op.analyze(inp, out)
    if params:
        result = op.apply(inp, params)
        match = np.array_equal(result, out)
        print(f"  Example {i}: {'✓' if match else '✗'}")
    else:
        print(f"  Example {i}: ✗ (analyze failed)")

# Get operator via infer_rule_for_task
detected_op, params = infer_rule_for_task(train_pairs)
print(f"\nDetected operator: {detected_op.name if detected_op else None}")
print(f"Params: {params}")

# Test on test input
print("\nTEST CASE:")
test_input = np.array(task['test'][0]['input'])
expected_output = np.array(solutions['ac2e8ecf'][0])

print(f"Test input shape: {test_input.shape}")
print(f"Expected output shape: {expected_output.shape}")

result = detected_op.apply(test_input, params)
print(f"Result shape: {result.shape}")

if np.array_equal(result, expected_output):
    print("✓ TEST PASSED")
else:
    print("✗ TEST FAILED")
    print(f"\nExpected output:")
    print(expected_output)
    print(f"\nOur result:")
    print(result)
    print(f"\nDifferences:")
    diffs = np.argwhere(result != expected_output)
    print(f"  {len(diffs)} cells differ")
    if len(diffs) <= 20:
        for r, c in diffs:
            print(f"  ({r:2d}, {c:2d}): expected {expected_output[r,c]}, got {result[r,c]}")
