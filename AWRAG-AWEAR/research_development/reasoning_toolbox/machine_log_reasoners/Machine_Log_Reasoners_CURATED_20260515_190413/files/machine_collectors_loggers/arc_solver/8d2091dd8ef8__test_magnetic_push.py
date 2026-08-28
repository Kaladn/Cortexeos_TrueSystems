import numpy as np
import json
from cod_616.arc_organ.arc_operators import CenterRepulsionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)
with open('arc-prize-2025/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = data['ac2e8ecf']
op = CenterRepulsionOperator()

print("Testing CENTER REPULSION with simple magnetic push")
print("="*60)

# Test training examples
print("\nTRAINING EXAMPLES:")
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    expected = np.array(ex['output'])
    
    result = op.apply(inp, {})
    match = np.array_equal(result, expected)
    
    if match:
        print(f"  Example {i}: ✓")
    else:
        diffs = np.sum(result != expected)
        print(f"  Example {i}: ✗ ({diffs} cells differ)")

# Test on test case
print("\nTEST CASE:")
test_input = np.array(task['test'][0]['input'])
expected_output = np.array(solutions['ac2e8ecf'][0])

print(f"Test input: {test_input.shape}")
print(f"Expected output: {expected_output.shape}")

result = op.apply(test_input, {})
print(f"Result: {result.shape}")

match = np.array_equal(result, expected_output)
if match:
    print("✓ TEST PASSED")
else:
    diffs = np.sum(result != expected_output)
    print(f"✗ TEST FAILED ({diffs} cells differ)")
    
    print("\nShowing first difference:")
    diff_mask = result != expected_output
    if np.any(diff_mask):
        diff_rows, diff_cols = np.where(diff_mask)
        first_diff_row = diff_rows[0]
        first_diff_col = diff_cols[0]
        print(f"At ({first_diff_row}, {first_diff_col}):")
        print(f"  Expected: {expected_output[first_diff_row, first_diff_col]}")
        print(f"  Got: {result[first_diff_row, first_diff_col]}")
