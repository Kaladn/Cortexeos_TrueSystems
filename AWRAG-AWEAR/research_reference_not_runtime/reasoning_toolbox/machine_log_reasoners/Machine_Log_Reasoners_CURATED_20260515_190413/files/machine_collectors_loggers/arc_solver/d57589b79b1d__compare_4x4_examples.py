"""
Compare Example 4 (4×4) with test case to find the exact rule
"""
import numpy as np
import json

with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task = eval_challenges['310f3251']

# Example 4 (4×4 like test case)
ex4_inp = np.array(task['train'][3]['input'])
ex4_out = np.array(task['train'][3]['output'])

print("Example 4 (4×4 → 12×12):")
print(f"\nInput:\n{ex4_inp}")
print(f"\nOutput:\n{ex4_out}")

tiled = np.tile(ex4_inp, (3, 3))
print(f"\nSimple tile:\n{tiled}")

print("\n" + "="*70)
print("FINDING WHERE 2s APPEAR:")
print("="*70)

positions_with_2 = []
for i in range(ex4_out.shape[0]):
    for j in range(ex4_out.shape[1]):
        if ex4_out[i,j] == 2:
            in_i = i % ex4_inp.shape[0]
            in_j = j % ex4_inp.shape[1]
            positions_with_2.append((in_i, in_j))
            print(f"Output[{i:2d},{j:2d}] = 2  →  input position ({in_i},{in_j}), input value = {ex4_inp[in_i, in_j]}")

# Find unique input positions
unique_positions = list(set(positions_with_2))
print(f"\n{' Unique input positions that become 2:'}")
for pos in sorted(unique_positions):
    print(f"  Input[{pos[0]},{pos[1]}] = {ex4_inp[pos[0], pos[1]]} → becomes 2")

print("\n" + "="*70)
print("TEST CASE:")
print("="*70)

test_inp = np.array(task['test'][0]['input'])
test_out = np.array(eval_solutions['310f3251'][0])

print(f"\nTest Input:\n{test_inp}")
print(f"\nExpected Output:\n{test_out}")

print("\n" + "="*70)
print("WHERE 2s APPEAR IN TEST OUTPUT:")
print("="*70)

test_positions = []
for i in range(test_out.shape[0]):
    for j in range(test_out.shape[1]):
        if test_out[i,j] == 2:
            in_i = i % test_inp.shape[0]
            in_j = j % test_inp.shape[1]
            test_positions.append((in_i, in_j))

unique_test_positions = list(set(test_positions))
print(f"Unique input positions that become 2 in test:")
for pos in sorted(unique_test_positions):
    print(f"  Input[{pos[0]},{pos[1]}] = {test_inp[pos[0], pos[1]]} → should become 2")

print("\n" + "="*70)
print("COMPARISON:")
print("="*70)
print(f"Example 4 positions: {sorted(unique_positions)}")
print(f"Test case positions: {sorted(unique_test_positions)}")
