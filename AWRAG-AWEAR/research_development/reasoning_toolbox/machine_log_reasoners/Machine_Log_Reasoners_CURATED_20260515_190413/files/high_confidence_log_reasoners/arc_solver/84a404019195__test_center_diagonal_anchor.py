"""Test center-diagonal anchor rule."""
import json, numpy as np

c = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))
s = json.load(open('arc-prize-2024/arc-agi_training_solutions.json'))
t = c['05269061']

print("="*80)
print("CENTER-DIAGONAL ANCHOR RULE")
print("Center cell: (3,3), so center diagonal: r+c = 6")
print("="*80)

for i, ex in enumerate(t['train']):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    # Find all diagonals with colors
    dm = {}
    for r in range(7):
        for c in range(7):
            if inp[r,c] != 0:
                d = r+c
                if d not in dm:
                    dm[d] = set()
                dm[d].add(int(inp[r,c]))
    
    diags = sorted(dm.keys())
    center_diag = 6
    
    print(f"\nT{i+1}:")
    print(f"  All diagonals: {diags}")
    print(f"  Center diagonal (r+c=6): {'YES' if center_diag in diags else 'NO'}")
    
    if center_diag in dm:
        c0 = list(dm[center_diag])[0]
        print(f"  c0 from center diagonal: {c0}")
    
    exp = [int(x) for x in out[0,:3]]
    print(f"  Expected pattern: {exp}")

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
center_diag = 6

print(f"  All diagonals: {diags}")
print(f"  Center diagonal (r+c=6): {'YES' if center_diag in diags else 'NO'}")

if center_diag in dm:
    c0 = list(dm[center_diag])[0]
    print(f"  c0 from center diagonal: {c0}")

exp = [int(x) for x in out[0,:3]]
print(f"  Expected pattern: {exp}")
print(f"  Expected c0: {exp[0]}")
print(f"  MATCH: {'✅' if center_diag in dm and list(dm[center_diag])[0] == exp[0] else '❌'}")
