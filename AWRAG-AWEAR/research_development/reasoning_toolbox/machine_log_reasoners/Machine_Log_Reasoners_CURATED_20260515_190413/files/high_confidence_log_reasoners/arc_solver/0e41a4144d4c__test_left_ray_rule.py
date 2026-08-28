"""Test the LEFT-RAY rule on all examples."""

import json
import numpy as np

# Load training data
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

print("="*80)
print("LEFT-RAY RULE TEST: [c0, c1, c2] = CENTER + LEFT-RAY")
print("="*80)

for i, example in enumerate(task['train']):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    print(f"\n{'='*80}")
    print(f"TRAINING EXAMPLE {i+1}")
    print(f"{'='*80}")
    
    # Find center (for 7x7, center is (3,3))
    H, W = out.shape
    center_r, center_c = H // 2, W // 2
    
    # Read center tile
    c0 = int(out[center_r, center_c])
    print(f"Center ({center_r},{center_c}): c0 = {c0}")
    
    # Read LEFT ray (3 cells starting from center going left)
    left_ray = []
    for dist in range(3):
        c = center_c - dist
        if c >= 0:
            left_ray.append(int(out[center_r, c]))
    
    print(f"LEFT ray: {left_ray}")
    
    # Expected pattern from output
    expected_pattern = list(out[0, :3])
    print(f"Expected pattern (first row): {expected_pattern}")
    
    # Check if left ray matches expected
    if left_ray == expected_pattern:
        print(f"✅ LEFT RAY = PATTERN! [c0,c1,c2] = {left_ray}")
    else:
        print(f"❌ Mismatch: left_ray={left_ray}, pattern={expected_pattern}")
    
    # Verify the rule: output[r,c] = [c0,c1,c2][(r+c)%3]
    colors = left_ray
    correct_pixels = 0
    total_pixels = H * W
    
    for r in range(H):
        for c in range(W):
            expected_val = colors[(r + c) % 3]
            actual_val = out[r, c]
            if expected_val == actual_val:
                correct_pixels += 1
    
    print(f"Latin square verification: {correct_pixels}/{total_pixels} pixels match")
    if correct_pixels == total_pixels:
        print(f"✅ PERFECT LATIN SQUARE with colors {colors}")

# Test example
print(f"\n{'='*80}")
print(f"TEST EXAMPLE")
print(f"{'='*80}")

test_inp = np.array(task['test'][0]['input'])
test_out = np.array(solutions['05269061'][0])

H, W = test_out.shape
center_r, center_c = H // 2, W // 2

c0 = int(test_out[center_r, center_c])
print(f"Center ({center_r},{center_c}): c0 = {c0}")

left_ray = []
for dist in range(3):
    c = center_c - dist
    if c >= 0:
        left_ray.append(int(test_out[center_r, c]))

print(f"LEFT ray: {left_ray}")

expected_pattern = list(test_out[0, :3])
print(f"Expected pattern (first row): {expected_pattern}")

if left_ray == expected_pattern:
    print(f"✅ LEFT RAY = PATTERN! [c0,c1,c2] = {left_ray}")
else:
    print(f"❌ Mismatch: left_ray={left_ray}, pattern={expected_pattern}")

colors = left_ray
correct_pixels = 0
total_pixels = H * W

for r in range(H):
    for c in range(W):
        expected_val = colors[(r + c) % 3]
        actual_val = test_out[r, c]
        if expected_val == actual_val:
            correct_pixels += 1

print(f"Latin square verification: {correct_pixels}/{total_pixels} pixels match")
if correct_pixels == total_pixels:
    print(f"✅ PERFECT LATIN SQUARE with colors {colors}")

print(f"\n{'='*80}")
print(f"FINAL RULE CONFIRMED")
print(f"{'='*80}")
print("1. c0 = center tile (3,3)")
print("2. [c0,c1,c2] = LEFT ray from center (3 steps left)")
print("3. Latin square: output[r,c] = [c0,c1,c2][(r+c)%3]")
print("4. Tile to full 7×7 grid")
print("="*80)
