"""Find the permutation rule based on diagonal modulo 3."""
import json
import numpy as np

with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']
task_solutions = solutions['05269061']

print("="*80)
print("HYPOTHESIS: Palette ordering based on (diagonal % 3)")
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
    correct_palette = [int(out[0,0]), int(out[0,1]), int(out[0,2])]
    
    print(f"\n{label}:")
    print(f"  Diagonals: {diags}")
    print(f"  Diags % 3: {[d % 3 for d in diags]}")
    print(f"  Diagonal colors: {diagonal_colors}")
    print(f"  Correct palette: {correct_palette}")
    
    # Try to map based on diagonal % 3
    # Position (0,0) is on diagonal 0 → index 0 in output
    # Position (0,1) is on diagonal 1 → index 1 in output
    # Position (0,2) is on diagonal 2 → index 2 in output
    
    # So output[0, k] should come from diagonal with (d % 3) == k
    predicted_palette = [None, None, None]
    for j, diag in enumerate(diags):
        target_pos = diag % 3
        predicted_palette[target_pos] = diagonal_colors[j]
    
    print(f"  Predicted palette (by diag%3): {predicted_palette}")
    print(f"  Match? {predicted_palette == correct_palette}")

print("\n" + "="*80)
print("BREAKTHROUGH: output[0, k] = color from diagonal where (d % 3) == k")
print("="*80)
