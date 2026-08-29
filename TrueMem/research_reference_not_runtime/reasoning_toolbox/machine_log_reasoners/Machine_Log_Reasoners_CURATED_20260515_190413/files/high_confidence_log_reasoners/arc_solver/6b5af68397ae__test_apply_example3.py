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
print("Input:")
print(input_grid)
print("\nExpected output:")
print(expected_output)

# Create operator and apply
operator = CenterHaloExpansionOperator()

# First analyze
params = operator.analyze(input_grid, expected_output)
print(f"\nAnalyze result: {params}")

if params:
    # Apply with detected params
    generated = operator.apply(input_grid, params)
    
    print("\nGenerated:")
    print(generated)
    
    print(f"\nMatch: {np.array_equal(generated, expected_output)}")
    
    if not np.array_equal(generated, expected_output):
        diffs = np.argwhere(generated != expected_output)
        print(f"\nFirst 10 differences:")
        for i, (r, c) in enumerate(diffs[:10]):
            print(f"  [{r},{c}]: gen={generated[r,c]}, exp={expected_output[r,c]}")
else:
    print("FAILED TO DETECT PATTERN")
    
    # Try manually
    print("\nTrying manual params...")
    
    # Look at input
    from cod_616.arc_organ.centering import extract_center_object
    center_obj, meta = extract_center_object(input_grid, background=0)
    print(f"Extracted center object shape: {center_obj.shape}")
    print(center_obj)
    
    unique_colors = sorted(set(np.unique(center_obj)) - {0})
    print(f"Colors: {unique_colors}")
    
    # Count colors
    for color in unique_colors:
        count = np.sum(center_obj == color)
        print(f"  Color {color}: {count} cells")
