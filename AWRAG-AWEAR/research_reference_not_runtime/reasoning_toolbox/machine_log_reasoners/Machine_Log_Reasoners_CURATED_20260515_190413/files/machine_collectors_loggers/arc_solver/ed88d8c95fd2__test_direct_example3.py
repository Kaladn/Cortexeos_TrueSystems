import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import CenterHaloExpansionOperator

# Load task 3befdf3e
data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
with open(data_path) as f:
    tasks = json.load(f)

task = tasks['3befdf3e']

# Get example 3
example = task['train'][2]
input_grid = np.array(example['input'])
expected_output = np.array(example['output'])

print("Example 3:")
print("Input has structure at rows 3-6, cols 2-5")
print("Output has structure at rows 1-8, cols 0-7 (off-center)")

# Create operator
operator = CenterHaloExpansionOperator()

# Try applying directly with manual params
params = {'core_color': 1, 'ring_color': 3}

generated = operator.apply(input_grid, params)

print("\nGenerated:")
print(generated)

print("\nExpected:")
print(expected_output)

print(f"\nMatch: {np.array_equal(generated, expected_output)}")

if not np.array_equal(generated, expected_output):
    diffs = np.argwhere(generated != expected_output)
    print(f"\nTotal differences: {len(diffs)}")
    print(f"First 15 differences:")
    for i, (r, c) in enumerate(diffs[:15]):
        print(f"  [{r},{c}]: gen={generated[r,c]}, exp={expected_output[r,c]}")
