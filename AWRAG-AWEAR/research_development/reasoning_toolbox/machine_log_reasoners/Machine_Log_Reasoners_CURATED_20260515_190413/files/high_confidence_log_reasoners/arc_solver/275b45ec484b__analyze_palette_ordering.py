"""Find palette ordering rule for ALL examples."""
import json, numpy as np
from itertools import permutations

c = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))
s = json.load(open('arc-prize-2024/arc-agi_training_solutions.json'))
t = c['05269061']

print("="*80)
print("FINDING PALETTE ORDERING RULE")
print("="*80)

results = []

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
    colors_from_diags = [sorted(dm[d])[0] for d in diags]
    
    # Try all permutations
    found = False
    for perm in permutations(colors_from_diags):
        for offset in diags + [0, 6]:  # Try diagonal offsets and special values
            generated = np.array([[perm[(r+c-offset) % 3] for c in range(7)] for r in range(7)])
            if np.array_equal(generated, out):
                results.append({
                    'name': f'T{i+1}',
                    'diags': diags,
                    'colors_from_diags': colors_from_diags,
                    'palette': list(perm),
                    'offset': offset,
                    'expected_first_row': [int(x) for x in out[0,:3]]
                })
                found = True
                break
        if found:
            break

# Test
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
colors_from_diags = [sorted(dm[d])[0] for d in diags]

found = False
for perm in permutations(colors_from_diags):
    for offset in diags + [0, 6]:
        generated = np.array([[perm[(r+c-offset) % 3] for c in range(7)] for r in range(7)])
        if np.array_equal(generated, out):
            results.append({
                'name': 'Test',
                'diags': diags,
                'colors_from_diags': colors_from_diags,
                'palette': list(perm),
                'offset': offset,
                'expected_first_row': [int(x) for x in out[0,:3]]
            })
            found = True
            break
    if found:
        break

# Print results
for r in results:
    print(f"\n{r['name']}:")
    print(f"  Diagonals:         {r['diags']}")
    print(f"  Colors from diags: {r['colors_from_diags']}")
    print(f"  Working palette:   {r['palette']}")
    print(f"  Offset:            {r['offset']}")
    print(f"  Expected 1st row:  {r['expected_first_row']}")
    
    # Check if palette matches diagonal order
    if r['palette'] == r['colors_from_diags']:
        print(f"  → Palette = diagonal order ✅")
    else:
        # Find mapping
        mapping = []
        for i, color in enumerate(r['palette']):
            diag_idx = r['colors_from_diags'].index(color)
            mapping.append(f"palette[{i}] = diag[{diag_idx}] (diagonal {r['diags'][diag_idx]})")
        print(f"  → Palette mapping:")
        for m in mapping:
            print(f"      {m}")

print("\n" + "="*80)
print("PATTERN ANALYSIS")
print("="*80)
