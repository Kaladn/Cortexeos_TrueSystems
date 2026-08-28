"""Find the exact geometric rule for color ordering."""

import json
import numpy as np

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

examples = [
    ("Train 1", np.array(task['train'][0]['input']), np.array(task['train'][0]['output'])),
    ("Train 2", np.array(task['train'][1]['input']), np.array(task['train'][1]['output'])),
    ("Train 3", np.array(task['train'][2]['input']), np.array(task['train'][2]['output'])),
    ("Test", np.array(task['test'][0]['input']), np.array(solutions['05269061'][0])),
]

for label, inp, out in examples:
    print(f"\n{'='*80}")
    print(f"{label}")
    print(f"{'='*80}")
    
    # Find all non-zero positions
    non_zero_pos = {}
    for r in range(inp.shape[0]):
        for c in range(inp.shape[1]):
            color = int(inp[r, c])
            if color != 0:
                if color not in non_zero_pos:
                    non_zero_pos[color] = []
                non_zero_pos[color].append((r, c))
    
    # Expected pattern from output
    pattern = out[:3, :3]
    expected_order = [int(pattern[0, 0]), int(pattern[0, 1]), int(pattern[0, 2])]
    
    print(f"Expected pattern: {expected_order}")
    print(f"\nColor positions:")
    
    for color in sorted(non_zero_pos.keys()):
        positions = non_zero_pos[color]
        # Find centroid
        r_avg = np.mean([p[0] for p in positions])
        c_avg = np.mean([p[1] for p in positions])
        # Find topmost-leftmost
        topmost = min(positions, key=lambda p: (p[0], p[1]))
        # Find bottommost-rightmost  
        bottommost = max(positions, key=lambda p: (p[0], p[1]))
        
        print(f"  Color {color}:")
        print(f"    Centroid: ({r_avg:.1f}, {c_avg:.1f})")
        print(f"    First: {topmost}")
        print(f"    Last: {bottommost}")
    
    # Try ordering by centroid position
    centroids = []
    for color in non_zero_pos.keys():
        positions = non_zero_pos[color]
        r_avg = np.mean([p[0] for p in positions])
        c_avg = np.mean([p[1] for p in positions])
        centroids.append((color, r_avg, c_avg))
    
    print(f"\nOrdering strategies:")
    
    # By row (r coordinate)
    by_row = sorted(centroids, key=lambda x: x[1])
    order_by_row = [c for c, r, col in by_row]
    match_row = "✅" if order_by_row == expected_order else ""
    print(f"  By row (top to bottom): {order_by_row} {match_row}")
    
    # By column (c coordinate)
    by_col = sorted(centroids, key=lambda x: x[2])
    order_by_col = [c for c, r, col in by_col]
    match_col = "✅" if order_by_col == expected_order else ""
    print(f"  By col (left to right): {order_by_col} {match_col}")
    
    # By diagonal (r+c)
    by_diag = sorted(centroids, key=lambda x: x[1] + x[2])
    order_by_diag = [c for c, r, col in by_diag]
    match_diag = "✅" if order_by_diag == expected_order else ""
    print(f"  By diagonal (r+c): {order_by_diag} {match_diag}")
    
    # By anti-diagonal (r-c)
    by_antidiag = sorted(centroids, key=lambda x: x[1] - x[2])
    order_by_antidiag = [c for c, r, col in by_antidiag]
    match_antidiag = "✅" if order_by_antidiag == expected_order else ""
    print(f"  By anti-diagonal (r-c): {order_by_antidiag} {match_antidiag}")
    
    # By distance from origin
    by_dist = sorted(centroids, key=lambda x: x[1]**2 + x[2]**2)
    order_by_dist = [c for c, r, col in by_dist]
    match_dist = "✅" if order_by_dist == expected_order else ""
    print(f"  By distance from origin: {order_by_dist} {match_dist}")
