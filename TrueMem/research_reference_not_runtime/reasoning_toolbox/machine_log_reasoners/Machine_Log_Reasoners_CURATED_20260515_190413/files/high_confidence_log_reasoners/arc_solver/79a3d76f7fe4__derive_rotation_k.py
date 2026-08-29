"""Derive the exact rotation rule for 05269061."""

import json
import numpy as np

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

print("="*80)
print("DERIVING ROTATION OFFSET K")
print("="*80)

examples = [
    ("Train 0", np.array(task['train'][0]['input']), np.array(task['train'][0]['output'])),
    ("Train 1", np.array(task['train'][1]['input']), np.array(task['train'][1]['output'])),
    ("Train 2", np.array(task['train'][2]['input']), np.array(task['train'][2]['output'])),
    ("Test", np.array(task['test'][0]['input']), np.array(solutions['05269061'][0])),
]

k_values = []

for label, inp, out in examples:
    print(f"\n{'-'*80}")
    print(f"{label}")
    print(f"{'-'*80}")
    
    # Step 1: Get centroids of each color
    non_zero_pos = {}
    for r in range(inp.shape[0]):
        for c in range(inp.shape[1]):
            color = int(inp[r, c])
            if color != 0:
                if color not in non_zero_pos:
                    non_zero_pos[color] = []
                non_zero_pos[color].append((r, c))
    
    centroids = []
    for color in non_zero_pos.keys():
        positions = non_zero_pos[color]
        r_avg = np.mean([p[0] for p in positions])
        c_avg = np.mean([p[1] for p in positions])
        centroids.append((color, r_avg, c_avg))
    
    # Step 2: Sort by diagonal position (r+c gives diagonal index)
    # Lower r+c = closer to top-left
    by_diag = sorted(centroids, key=lambda x: x[1] + x[2])
    diag_order = [c for c, r, col in by_diag]
    
    print(f"Centroids:")
    for color, r, c in centroids:
        print(f"  Color {color}: ({r:.1f}, {c:.1f})  diag_sum={r+c:.1f}")
    
    print(f"\nDiagonal order (sorted by r+c): {diag_order}")
    
    # Step 3: Get target from output
    pattern = out[:3, :3]
    target = [int(pattern[0, 0]), int(pattern[0, 1]), int(pattern[0, 2])]
    print(f"Target output pattern: {target}")
    
    # Step 4: Find rotation offset k
    n = len(diag_order)
    k_found = None
    for k in range(n):
        rotated = diag_order[k:] + diag_order[:k]
        if rotated == target:
            k_found = k
            print(f"\n✅ MATCH: k = {k}")
            print(f"   {diag_order} rotated LEFT by {k} → {rotated}")
            break
    
    if k_found is None:
        print(f"\n❌ NO ROTATION MATCHES!")
    else:
        k_values.append(k_found)
    
    # Also check geometric features that might determine k
    # Feature 1: Which corner is the pattern closest to?
    min_r = min(r for r, c in non_zero_pos[diag_order[0]])
    min_c = min(c for r, c in non_zero_pos[diag_order[0]])
    max_r = max(r for r, c in non_zero_pos[diag_order[-1]])
    max_c = max(c for r, c in non_zero_pos[diag_order[-1]])
    
    print(f"\nGeometric features:")
    print(f"  First color ({diag_order[0]}): min position = ({min_r}, {min_c})")
    print(f"  Last color ({diag_order[-1]}): max position = ({max_r}, {max_c})")
    
    # Feature 2: Diagonal direction (top-left to bottom-right vs top-right to bottom-left)
    # Check if r and c are correlated or anti-correlated
    all_positions = [(r, c) for positions in non_zero_pos.values() for r, c in positions]
    rs = [r for r, c in all_positions]
    cs = [c for r, c in all_positions]
    
    # Correlation coefficient
    r_mean = np.mean(rs)
    c_mean = np.mean(cs)
    cov = np.mean([(r - r_mean) * (c - c_mean) for r, c in zip(rs, cs)])
    r_std = np.std(rs)
    c_std = np.std(cs)
    
    if r_std > 0 and c_std > 0:
        corr = cov / (r_std * c_std)
        print(f"  Diagonal correlation: {corr:.2f}")
        if corr > 0:
            print(f"    → Main diagonal (↘)")
        else:
            print(f"    → Anti-diagonal (↙)")

print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"Rotation offsets k: {k_values}")

if len(set(k_values)) == 1:
    print(f"✅ ALL EXAMPLES USE SAME k = {k_values[0]}")
    print(f"\nDETERMINISTIC RULE:")
    print(f"  1. Sort colors by centroid diagonal position (r+c)")
    print(f"  2. Rotate LEFT by k={k_values[0]}")
    print(f"  3. Generate Latin square with that ordering")
else:
    print(f"⚠️  k varies across examples: {k_values}")
    print(f"Need to find geometric feature that determines k")
