"""Validate the updated LatinSquareFromDiagonalOperator."""
import sys
sys.path.insert(0, 'cod_616')

import json
import numpy as np
from arc_organ.arc_operators import LatinSquareFromDiagonalOperator

# Load task 05269061
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']
task_solutions = solutions['05269061']

operator = LatinSquareFromDiagonalOperator()

print("="*80)
print("Testing LatinSquareFromDiagonalOperator with LINEAR SEQUENCE formula")
print("="*80)

# Test on training examples
all_pass = True
for i, ex in enumerate(task['train']):
    inp = np.array(ex['input'])
    expected = np.array(ex['output'])
    
    # Analyze
    params = operator.analyze(inp, expected)
    if params is None:
        print(f"\n❌ T{i+1}: analyze() failed")
        all_pass = False
        continue
    
    print(f"\nT{i+1}:")
    print(f"  Params: {params}")
    
    # Apply
    result = operator.apply(inp, params)
    
    if np.array_equal(result, expected):
        print(f"  ✅ PASS: Generated output matches expected")
    else:
        print(f"  ❌ FAIL: Mismatch")
        print(f"     Expected first row: {expected[0,:].tolist()}")
        print(f"     Got first row:      {result[0,:].tolist()}")
        all_pass = False

# Test on test case
print(f"\nTest:")
test_inp = np.array(task['test'][0]['input'])
test_expected = np.array(task_solutions[0])

# Use params from last training example (for output_shape)
test_params = {"output_shape": test_expected.shape}
test_result = operator.apply(test_inp, test_params)

if np.array_equal(test_result, test_expected):
    print(f"  ✅ PASS: Generated output matches expected")
else:
    print(f"  ❌ FAIL: Mismatch")
    print(f"     Expected first row: {test_expected[0,:].tolist()}")
    print(f"     Got first row:      {test_result[0,:].tolist()}")
    all_pass = False

print("\n" + "="*80)
if all_pass:
    print("✅ ALL TESTS PASSED - Operator is ready!")
else:
    print("❌ Some tests failed - needs debugging")
print("="*80)
