"""Test LINEAR SEQUENCE across rows."""
import json, numpy as np

c = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))
s = json.load(open('arc-prize-2024/arc-agi_training_solutions.json'))
t = c['05269061']

print("="*80)
print("LINEAR SEQUENCE TEST: palette cycles continuously across rows")
print("Row A: 1231231 (ends with 1)")
print("Row B: 2312312 (starts with 2, continues sequence)")
print("="*80)

for i, ex in enumerate(t['train']):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    # Extract diagonals
    dm = {}
    for r in range(7):
        for c in range(7):
            if inp[r,c] != 0:
                d = r+c
                if d not in dm:
                    dm[d] = set()
                dm[d].add(int(inp[r,c]))
    
    diags = sorted(dm.keys())
    colors = [sorted(dm[d])[0] for d in diags]
    
    print(f"\nT{i+1}:")
    print(f"  Diagonals: {diags}")
    print(f"  Colors: {colors}")
    print(f"  Expected first row: {[int(x) for x in out[0,:3]]}")
    
    from itertools import permutations
    found = False
    for perm in permutations(colors):
        # Generate with linear indexing: position = r*7 + c
        generated = np.array([[perm[(r*7 + c) % 3] for c in range(7)] for r in range(7)])
        if np.array_equal(generated, out):
            print(f"  ✅ LINEAR WORKS with palette {list(perm)}")
            print(f"     Formula: output[r,c] = palette[(r*7 + c) % 3]")
            print(f"     Actual row 0: {[int(x) for x in out[0,:]]}")
            print(f"     Actual row 1: {[int(x) for x in out[1,:]]}")
            print(f"     Actual row 2: {[int(x) for x in out[2,:]]}")
            found = True
            break
    
    if not found:
        print(f"  ❌ Linear doesn't work")

# Test
print(f"\nTest:")
inp = np.array(t['test'][0]['input'])
out = np.array(s['05269061'][0])

dm = {}
for r in range(7):
    for c in range(7):
        if inp[r,c] != 0:
            d = r+c
            if d not in dm:
                dm[d] = set()
            dm[d].add(int(inp[r,c]))

diags = sorted(dm.keys())
colors = [sorted(dm[d])[0] for d in diags]

print(f"  Diagonals: {diags}")
print(f"  Colors: {colors}")

from itertools import permutations
found = False
for perm in permutations(colors):
    generated = np.array([[perm[(r*7 + c) % 3] for c in range(7)] for r in range(7)])
    if np.array_equal(generated, out):
        print(f"  ✅ LINEAR WORKS with palette {list(perm)}")
        print(f"     Formula: output[r,c] = palette[(r*7 + c) % 3]")
        print(f"     Actual row 0: {[int(x) for x in out[0,:]]}")
        print(f"     Actual row 1: {[int(x) for x in out[1,:]]}")
        found = True
        break

if not found:
    print(f"  ❌ Linear doesn't work")
