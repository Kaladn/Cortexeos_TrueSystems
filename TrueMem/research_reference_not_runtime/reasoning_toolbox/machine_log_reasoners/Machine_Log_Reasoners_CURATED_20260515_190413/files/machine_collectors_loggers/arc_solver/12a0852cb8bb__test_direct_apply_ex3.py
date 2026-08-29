"""Test direct apply on example 3"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import CenterHaloExpansionOperator

# Load task
data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
with open(data_path) as f:
    tasks = json.load(f)

task = tasks['3befdf3e']
ex3 = task['train'][2]

input_arr = np.array(ex3['input'])
expected_output = np.array(ex3['output'])

print("Example 3 - Direct Apply Test")
print("=" * 60)

# Manual params
params = {'core_color': 1, 'ring_color': 3}

operator = CenterHaloExpansionOperator()
generated = operator.apply(input_arr, params)

print(f"\nGenerated output:\n{generated}")
print(f"\nExpected output:\n{expected_output}")

match = np.array_equal(generated, expected_output)
print(f"\n✅ MATCH!" if match else f"\n❌ MISMATCH")

if not match:
    diff_mask = generated != expected_output
    print(f"\nDifferences at {np.sum(diff_mask)} positions")
    print(f"First 10 differences:")
    diff_positions = np.argwhere(diff_mask)[:10]
    for r, c in diff_positions:
        print(f"  [{r},{c}]: generated={generated[r,c]}, expected={expected_output[r,c]}")
