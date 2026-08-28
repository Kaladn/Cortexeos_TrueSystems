"""Find the FIRST occurrence of each unique color along the diagonal."""

import json
import numpy as np

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

def find_first_occurrence_order(inp):
    """Find the order of first occurrence of each non-zero color."""
    H, W = inp.shape
    
    # Try multiple scanning strategies
    strategies = {}
    
    # Strategy 1: Row-major order (left to right, top to bottom)
    seen = {}
    order_row_major = []
    for r in range(H):
        for c in range(W):
            color = int(inp[r, c])
            if color != 0 and color not in seen:
                seen[color] = (r, c)
                order_row_major.append(color)
    strategies['row_major'] = order_row_major
    
    # Strategy 2: Column-major order (top to bottom, left to right)
    seen = {}
    order_col_major = []
    for c in range(W):
        for r in range(H):
            color = int(inp[r, c])
            if color != 0 and color not in seen:
                seen[color] = (r, c)
                order_col_major.append(color)
    strategies['col_major'] = order_col_major
    
    # Strategy 3: Main diagonal scan (top-left to bottom-right)
    seen = {}
    order_diag_main = []
    for diag_sum in range(H + W - 1):
        for r in range(H):
            c = diag_sum - r
            if 0 <= c < W:
                color = int(inp[r, c])
                if color != 0 and color not in seen:
                    seen[color] = (r, c)
                    order_diag_main.append(color)
    strategies['diag_main'] = order_diag_main
    
    # Strategy 4: Anti-diagonal scan (top-right to bottom-left)
    seen = {}
    order_diag_anti = []
    for diag_diff in range(-(W-1), H):
        for r in range(H):
            c = r - diag_diff
            if 0 <= c < W:
                color = int(inp[r, c])
                if color != 0 and color not in seen:
                    seen[color] = (r, c)
                    order_diag_anti.append(color)
    strategies['diag_anti'] = order_diag_anti
    
    # Strategy 5: Reverse diagonal scans
    strategies['diag_main_rev'] = list(reversed(order_diag_main))
    strategies['diag_anti_rev'] = list(reversed(order_diag_anti))
    
    # Strategy 6: Distance from origin
    seen = {}
    positions = []
    for r in range(H):
        for c in range(W):
            color = int(inp[r, c])
            if color != 0 and color not in seen:
                dist = np.sqrt(r**2 + c**2)
                positions.append((dist, r, c, color))
                seen[color] = (r, c)
    positions.sort()
    strategies['dist_origin'] = [color for _, _, _, color in positions]
    
    return strategies

print("="*80)
print("FIRST OCCURRENCE ANALYSIS - Task 05269061")
print("="*80)

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
    
    strategies = find_first_occurrence_order(inp)
    pattern = out[:3, :3]
    first_row = [int(pattern[0, 0]), int(pattern[0, 1]), int(pattern[0, 2])]
    
    print(f"Output 3x3 pattern first row: {first_row}")
    print(f"\nFirst occurrence orderings:")
    
    for name, order in strategies.items():
        match = "✅ MATCH!" if order == first_row else ""
        print(f"  {name:20s}: {order} {match}")

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print("Looking for which scanning strategy consistently matches the output pattern...")
