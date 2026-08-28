"""Check if palette matches position (0,0), (0,1), (0,2) from output."""
import json
import numpy as np

with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']
task_solutions = solutions['05269061']

print("="*80)
print("KEY INSIGHT: Palette = [output[0,0], output[0,1], output[0,2]]")
print("="*80)

for i, ex in enumerate(task['train'] + [{'input': task['test'][0]['input']}]):
    inp = np.array(ex['input'])
    if i < 3:
        out = np.array(task['train'][i]['output'])
        label = f"T{i+1}"
    else:
        out = np.array(task_solutions[0])
        label = "Test"
    
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
    
    # The CORRECT palette is just the first row!
    correct_palette = [int(out[0,0]), int(out[0,1]), int(out[0,2])]
    
    print(f"\n{label}:")
    print(f"  Diagonals: {diags}")
    print(f"  Diagonal colors: {diagonal_colors}")
    print(f"  Correct palette (from output[0,:]): {correct_palette}")
    
    # Which permutation of diagonal_colors gives correct_palette?
    from itertools import permutations
    for perm in permutations(diagonal_colors):
        if list(perm) == correct_palette:
            indices = [diagonal_colors.index(p) for p in perm]
            print(f"  Permutation of diagonals: {indices} → {list(perm)}")
            break
    
    # Now check if this position is predictable from INPUT geometry
    print(f"  Input diagonal positions:")
    for j, diag in enumerate(diags):
        # Find a cell on this diagonal
        for r in range(7):
            for c in range(7):
                if r+c == diag and inp[r,c] != 0:
                    print(f"    Diagonal {diag} (color {diagonal_colors[j]}): cell ({r},{c})")
                    break
            else:
                continue
            break

print("\n" + "="*80)
print("Pattern analysis:")
print("="*80)
print("Can we predict the palette permutation from input geometry?")
print("Need to find the rule that maps diagonal indices → palette order")
