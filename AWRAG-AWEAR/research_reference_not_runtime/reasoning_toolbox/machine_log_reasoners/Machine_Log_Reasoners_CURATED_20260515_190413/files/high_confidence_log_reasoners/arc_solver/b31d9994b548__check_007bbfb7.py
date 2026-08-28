"""Check 007bbfb7 pattern in detail."""
import json
import numpy as np

with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
    train_data = json.load(f)

task = train_data['007bbfb7']
ex = task['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])

print("Input:")
print(inp)
print("\nOutput:")
print(out)

# Check if simple 3×3 tiling
expected_simple = np.tile(inp, (3, 3))
print(f"\nSimple 3×3 tiling matches: {np.array_equal(expected_simple, out)}")

# Check differences
if not np.array_equal(expected_simple, out):
    diff_mask = (expected_simple != out)
    print(f"Differences: {diff_mask.sum()} positions")
    print("\nExpected (simple tiling):")
    print(expected_simple)
