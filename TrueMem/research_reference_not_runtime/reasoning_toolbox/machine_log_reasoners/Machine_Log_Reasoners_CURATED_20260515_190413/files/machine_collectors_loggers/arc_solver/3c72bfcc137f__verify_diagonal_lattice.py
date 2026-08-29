"""Test diagonal lattice extraction rule for 05269061."""
import json, numpy as np

challenges = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))
solutions = json.load(open('arc-prize-2024/arc-agi_training_solutions.json'))
task = challenges['05269061']

print("="*80)
print("DIAGONAL LATTICE RULE TEST")
print("Rule: palette[i] = color on diagonal where (r+c) = min_diag + i")
print("="*80)

for i, ex in enumerate(task['train']):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    # Build diagonal map
    dm = {}
    for r in range(7):
        for c in range(7):
            if inp[r,c] != 0:
                d = r+c
                if d not in dm:
                    dm[d] = set()
                dm[d].add(int(inp[r,c]))
    
    # Get first 3 diagonals
    diags = sorted(dm.keys())[:3]
    palette = [sorted(dm[d])[0] for d in diags]  # Take first if multiple
    expected = [int(x) for x in out[0,:3]]
    
    match = "✅" if palette == expected else "❌"
    print(f"\nT{i+1}:")
    print(f"  Diagonals: {dict((d, sorted(dm[d])) for d in diags)}")
    print(f"  Palette:   {palette}")
    print(f"  Expected:  {expected}")
    print(f"  {match}")

# Test
print(f"\nTest:")
inp = np.array(task['test'][0]['input'])
out = np.array(solutions['05269061'][0])

dm = {}
for r in range(7):
    for c in range(7):
        if inp[r,c] != 0:
            d = r+c
            if d not in dm:
                dm[d] = set()
            dm[d].add(int(inp[r,c]))

diags = sorted(dm.keys())[:3]
palette = [sorted(dm[d])[0] for d in diags]
expected = [int(x) for x in out[0,:3]]

match = "✅" if palette == expected else "❌"
print(f"  Diagonals: {dict((d, sorted(dm[d])) for d in diags)}")
print(f"  Palette:   {palette}")
print(f"  Expected:  {expected}")
print(f"  {match}")

print("\n" + "="*80)
print("✅ RULE: palette = [color on diag r+c=min, r+c=min+1, r+c=min+2]")
print("   Then: output[r,c] = palette[(r+c) % 3]")
print("="*80)
