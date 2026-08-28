"""Show the complete star pattern map from center anchor (3,3)."""

import json
import numpy as np

# Load training data
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

# Use Test example
test_inp = np.array(task['test'][0]['input'])
test_out = np.array(solutions['05269061'][0])

print("="*80)
print("7×7 STAR PATTERN MAP - CENTER ANCHOR AT (3,3)")
print("="*80)

print("\nOUTPUT GRID:")
print(test_out)

center = (3, 3)
center_val = test_out[center]

print(f"\n{'='*80}")
print(f"CENTER ANCHOR: position {center} = {center_val}")
print(f"{'='*80}")

# Define the star pattern rays from center
rays = {
    'CENTER': [(3, 3)],
    
    'HORIZONTAL_LEFT': [(3, 0), (3, 1), (3, 2)],
    'HORIZONTAL_RIGHT': [(3, 4), (3, 5), (3, 6)],
    
    'VERTICAL_UP': [(0, 3), (1, 3), (2, 3)],
    'VERTICAL_DOWN': [(4, 3), (5, 3), (6, 3)],
    
    'MAIN_DIAG_UP': [(0, 0), (1, 1), (2, 2)],
    'MAIN_DIAG_DOWN': [(4, 4), (5, 5), (6, 6)],
    
    'ANTI_DIAG_UP': [(0, 6), (1, 5), (2, 4)],
    'ANTI_DIAG_DOWN': [(4, 2), (5, 1), (6, 0)],
}

print("\nSTAR PATTERN RAYS (from center):")
print("="*80)

for name, positions in rays.items():
    values = [int(test_out[r, c]) for r, c in positions]
    print(f"\n{name}:")
    print(f"  Positions: {positions}")
    print(f"  Values: {values}")
    if len(set(values)) == 1:
        print(f"  ★ UNIFORM: {values[0]}")
    else:
        print(f"  Pattern: {' → '.join(map(str, values))}")

# Check all 8 directions for uniformity
print(f"\n{'='*80}")
print("UNIFORMITY CHECK")
print(f"{'='*80}")

uniform_rays = {}
for name, positions in rays.items():
    values = [int(test_out[r, c]) for r, c in positions]
    if len(set(values)) == 1:
        uniform_rays[name] = values[0]
        print(f"✅ {name}: ALL {values[0]}")
    else:
        print(f"❌ {name}: {values}")

# Visualize the grid with ray labels
print(f"\n{'='*80}")
print("GRID WITH STAR PATTERN OVERLAY")
print(f"{'='*80}")

print("\n     c0  c1  c2  c3  c4  c5  c6")
print("    " + "─"*28)

ray_map = {}
for name, positions in rays.items():
    for pos in positions:
        ray_map[pos] = name[:4]  # First 4 chars

for r in range(7):
    row_str = f"r{r} │ "
    for c in range(7):
        val = test_out[r, c]
        if (r, c) == center:
            row_str += f" [{val}]"
        else:
            row_str += f"  {val} "
    print(row_str)

print("\n" + "="*80)
print("PATTERN SUMMARY")
print("="*80)

pattern = test_out[0, :3]
print(f"Latin Square Pattern: [{pattern[0]}, {pattern[1]}, {pattern[2]}]")
print(f"  c0 (first color):  {pattern[0]} ← ANTI-DIAGONAL")
print(f"  c1 (second color): {pattern[1]} ← ???")
print(f"  c2 (third color):  {pattern[2]} ← ???")
