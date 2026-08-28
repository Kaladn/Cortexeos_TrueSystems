"""Test INPUT diagonal rule with offset normalization."""
import json, numpy as np

challenges=json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))
solutions=json.load(open('arc-prize-2024/arc-agi_training_solutions.json'))
task=challenges['05269061']

print("="*80)
print("DIAGONAL EXTRACTION (OFFSET-NORMALIZED)")
print("="*80)

for i,ex in enumerate(task['train']):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    # Extract color on each diagonal
    diags = {}
    for r in range(7):
        for c in range(7):
            if inp[r,c] != 0:
                s = r+c
                if s not in diags:
                    diags[s] = []
                diags[s].append(int(inp[r,c]))
    
    # Get first 3 diagonals
    keys = sorted(diags.keys())[:3]
    min_diag = keys[0]
    palette = [diags[k][0] for k in keys]
    
    expected = [int(x) for x in out[0,:3]]
    
    # Verify Latin square
    correct = sum(1 for r in range(7) for c in range(7) 
                  if palette[(r+c-min_diag)%3] == int(out[r,c]))
    
    match = "✅" if palette == expected else "❌"
    print(f"T{i+1}: diags={keys} offset={min_diag} palette={palette} expected={expected} {match} latin={correct}/49")

inp = np.array(task['test'][0]['input'])
out = np.array(solutions['05269061'][0])

diags = {}
for r in range(7):
    for c in range(7):
        if inp[r,c] != 0:
            s = r+c
            if s not in diags:
                diags[s] = []
            diags[s].append(int(inp[r,c]))

keys = sorted(diags.keys())[:3]
min_diag = keys[0]
palette = [diags[k][0] for k in keys]
expected = [int(x) for x in out[0,:3]]

correct = sum(1 for r in range(7) for c in range(7) 
              if palette[(r+c-min_diag)%3] == int(out[r,c]))

match = "✅" if palette == expected else "❌"
print(f"Test: diags={keys} offset={min_diag} palette={palette} expected={expected} {match} latin={correct}/49")

print("\n" + "="*80)
print("RULE: output[r,c] = palette[(r+c - min_diag) % 3]")
print("="*80)
