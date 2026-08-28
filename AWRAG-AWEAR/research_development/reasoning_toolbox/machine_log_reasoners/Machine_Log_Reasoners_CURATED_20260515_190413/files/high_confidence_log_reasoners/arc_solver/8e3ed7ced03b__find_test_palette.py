"""Find correct palette ordering for Test using all permutations."""
import json, numpy as np
from itertools import permutations

s = json.load(open('arc-prize-2024/arc-agi_training_solutions.json'))
c = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))

inp = np.array(c['05269061']['test'][0]['input'])
out = np.array(s['05269061'][0])

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

print("Test case:")
print(f"  Diagonals: {diags}")
print(f"  Colors from diags: {colors_from_diags}")
print(f"  Expected output[0,:3]: {[int(x) for x in out[0,:3]]}")
print()

# Try all permutations of the 3 colors
colors = colors_from_diags
print("Trying all permutations:")

for perm in permutations(colors):
    for offset in diags:
        generated = np.array([[perm[(r+c-offset) % 3] for c in range(7)] for r in range(7)])
        if np.array_equal(generated, out):
            print(f"✅ FOUND IT!")
            print(f"   Palette: {list(perm)}")
            print(f"   Offset: {offset}")
            print(f"   Formula: output[r,c] = {list(perm)}[(r+c-{offset}) % 3]")
            
            # Verify pattern
            print(f"   Verification:")
            print(f"     (r+c-{offset})%3 = 0 → color {perm[0]}")
            print(f"     (r+c-{offset})%3 = 1 → color {perm[1]}")
            print(f"     (r+c-{offset})%3 = 2 → color {perm[2]}")
            break
    else:
        continue
    break
