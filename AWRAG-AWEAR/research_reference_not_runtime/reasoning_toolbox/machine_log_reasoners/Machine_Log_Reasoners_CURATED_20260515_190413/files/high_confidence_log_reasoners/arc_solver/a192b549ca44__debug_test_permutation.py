"""Debug test case permutation."""
import json
import numpy as np

with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']
task_solutions = solutions['05269061']

print("="*80)
print("TRAINING EXAMPLES - Diagonal scanning order")
print("="*80)

for i, ex in enumerate(task['train']):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    # Extract diagonals
    diagonal_map = {}
    for r in range(7):
        for c in range(7):
            color = int(inp[r,c])
            if color != 0:
                diag = r + c
                if diag not in diagonal_map:
                    diagonal_map[diag] = set()
                diagonal_map[diag].add(color)
    
    diags = sorted(diagonal_map.keys())
    diagonal_colors = [sorted(diagonal_map[d])[0] for d in diags]
    
    print(f"\nT{i+1}:")
    print(f"  Diagonals: {diags}")
    print(f"  Diagonal colors (in order): {diagonal_colors}")
    print(f"  Expected first row: {out[0,:].tolist()}")
    print(f"  Match? {diagonal_colors == out[0,:3].tolist()}")

print("\n" + "="*80)
print("TEST CASE")
print("="*80)

test_inp = np.array(task['test'][0]['input'])
test_out = np.array(task_solutions[0])

diagonal_map = {}
for r in range(7):
    for c in range(7):
        color = int(test_inp[r,c])
        if color != 0:
            diag = r + c
            if diag not in diagonal_map:
                diagonal_map[diag] = set()
            diagonal_map[diag].add(color)

diags = sorted(diagonal_map.keys())
diagonal_colors = [sorted(diagonal_map[d])[0] for d in diags]

print(f"\nTest:")
print(f"  Diagonals: {diags}")
print(f"  Diagonal colors (in order): {diagonal_colors}")
print(f"  Expected first row: {test_out[0,:].tolist()}")
print(f"  Match? {diagonal_colors == test_out[0,:3].tolist()}")

# What permutation is needed?
from itertools import permutations
for perm in permutations(diagonal_colors):
    if list(perm) == test_out[0,:3].tolist():
        print(f"  ✅ Need permutation: {list(perm)}")
        # Find which indices
        indices = [diagonal_colors.index(p) for p in perm]
        print(f"     Permutation indices: {indices}")
        break

print("\n" + "="*80)
print("Looking for pattern...")
print("="*80)

# Maybe it's based on which diagonal appears in specific positions?
print("\nScanning input in row-major order:")
print(f"Test input:\n{test_inp}")

colors_in_order = []
for r in range(7):
    for c in range(7):
        color = int(test_inp[r,c])
        if color != 0 and color not in colors_in_order:
            colors_in_order.append(color)
            print(f"  Found color {color} at position ({r},{c}), diag={r+c}")

print(f"\nColors in row-major scan order: {colors_in_order}")
print(f"Expected palette: {test_out[0,:3].tolist()}")
print(f"Match? {colors_in_order == test_out[0,:3].tolist()}")
