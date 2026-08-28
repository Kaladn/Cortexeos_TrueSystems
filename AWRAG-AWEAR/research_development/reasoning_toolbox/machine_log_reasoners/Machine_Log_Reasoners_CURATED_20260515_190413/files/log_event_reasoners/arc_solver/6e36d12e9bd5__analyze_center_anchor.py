"""Map the 7x7 Latin square structure with center anchor."""

import json
import numpy as np

# Load one example output
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

out = np.array(solutions['05269061'][0])  # Test output

print("="*80)
print("7x7 LATIN SQUARE WITH CENTER ANCHOR")
print("="*80)
print("\nOutput grid:")
print(out)

# Center is at (3, 3)
center = (3, 3)
center_val = out[center]

print(f"\n{'='*80}")
print(f"CENTER ANCHOR: position {center}, value = {center_val}")
print(f"{'='*80}")

# Map distances from center
print("\nDistance from center (Manhattan):")
dist_grid = np.zeros_like(out)
for r in range(7):
    for c in range(7):
        dist_grid[r, c] = abs(r - 3) + abs(c - 3)
print(dist_grid)

# Map by direction from center
print("\n" + "="*80)
print("STAR PATTERN ANALYSIS")
print("="*80)

directions = {
    'CENTER': [(3, 3)],
    'HORIZONTAL': [(3, 0), (3, 1), (3, 2), (3, 4), (3, 5), (3, 6)],
    'VERTICAL': [(0, 3), (1, 3), (2, 3), (4, 3), (5, 3), (6, 3)],
    'MAIN_DIAG': [(0, 0), (1, 1), (2, 2), (4, 4), (5, 5), (6, 6)],
    'ANTI_DIAG': [(0, 6), (1, 5), (2, 4), (4, 2), (5, 1), (6, 0)],
}

for name, positions in directions.items():
    values = [int(out[r, c]) for r, c in positions]
    print(f"\n{name}:")
    print(f"  Positions: {positions}")
    print(f"  Values: {values}")
    if len(set(values)) <= 3:
        print(f"  Unique: {sorted(set(values))}")

# Check the 3x3 pattern structure
print("\n" + "="*80)
print("3x3 REPEATING PATTERN")
print("="*80)

pattern_3x3 = out[:3, :3]
print("\nBase pattern:")
print(pattern_3x3)

print("\nPattern at each position modulo 3:")
for r in range(7):
    row_str = ""
    for c in range(7):
        val = out[r, c]
        mod_pos = (r % 3, c % 3)
        row_str += f"{val} "
    print(f"Row {r}: {row_str}  (mod3: r={r%3})")

# Map position (r,c) to which value appears
print("\n" + "="*80)
print("VALUE AT EACH (r%3, c%3) POSITION")
print("="*80)

pattern_map = {}
for r in range(7):
    for c in range(7):
        mod_pos = (r % 3, c % 3)
        val = int(out[r, c])
        if mod_pos not in pattern_map:
            pattern_map[mod_pos] = []
        pattern_map[mod_pos].append(val)

for pos in sorted(pattern_map.keys()):
    vals = pattern_map[pos]
    print(f"Position {pos}: {set(vals)} (all {vals[0] if len(set(vals))==1 else 'MIXED'})")

# Distance from center to each (r%3, c%3) position
print("\n" + "="*80)
print("CENTER-RELATIVE PATTERN")
print("="*80)

# Center at (3,3) maps to (0,0) in mod-3 space
center_mod = (3 % 3, 3 % 3)  # = (0, 0)
print(f"Center (3,3) → mod-3 position {center_mod} → value {out[3, 3]}")

print("\nAll (r%3, c%3) = (0,0) positions:")
for r in range(7):
    for c in range(7):
        if (r % 3, c % 3) == (0, 0):
            dist = abs(r - 3) + abs(c - 3)
            print(f"  ({r},{c}): value={out[r,c]}, dist_from_center={dist}")
