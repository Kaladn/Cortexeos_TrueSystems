"""
Find the PERIODIC LATTICE pattern - where do 2s appear in the tiled grid?
"""
import numpy as np
import json

with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task = eval_challenges['310f3251']

print("="*70)
print("FINDING THE PERIODIC LATTICE MASK")
print("="*70)

# Analyze each example to find the period
for ex_num in range(len(task['train'])):
    inp = np.array(task['train'][ex_num]['input'])
    out = np.array(task['train'][ex_num]['output'])
    
    print(f"\n{'='*70}")
    print(f"Example {ex_num+1}: Input shape {inp.shape}")
    print(f"{'='*70}")
    
    # Find all positions with 2s in OUTPUT (not input positions, actual output coordinates)
    positions_with_2 = []
    for i in range(out.shape[0]):
        for j in range(out.shape[1]):
            if out[i,j] == 2:
                positions_with_2.append((i, j))
    
    print(f"\nAll output positions with 2: {len(positions_with_2)} total")
    print("First 10:", positions_with_2[:10])
    
    # Find the period (spacing between 2s)
    if len(positions_with_2) >= 2:
        rows = [p[0] for p in positions_with_2]
        cols = [p[1] for p in positions_with_2]
        
        # Check row spacing
        unique_rows = sorted(set(rows))
        if len(unique_rows) > 1:
            row_diffs = [unique_rows[i+1] - unique_rows[i] for i in range(len(unique_rows)-1)]
            print(f"\nRow spacing between 2s: {set(row_diffs)}")
        
        # Check col spacing
        unique_cols = sorted(set(cols))
        if len(unique_cols) > 1:
            col_diffs = [unique_cols[i+1] - unique_cols[i] for i in range(len(unique_cols)-1)]
            print(f"Col spacing between 2s: {set(col_diffs)}")
        
        # Check modulo pattern
        print(f"\nChecking modulo patterns:")
        for m in range(2, 10):
            row_mods = set([r % m for r in rows])
            col_mods = set([c % m for c in cols])
            
            if len(row_mods) == 1:
                print(f"  ✓ ALL 2s at row % {m} == {list(row_mods)[0]}")
            if len(col_mods) == 1:
                print(f"  ✓ ALL 2s at col % {m} == {list(col_mods)[0]}")
        
        # Also check offset from input shape
        h, w = inp.shape
        print(f"\nInput shape is ({h}, {w}) - tiling period")
        
        # Check if 2s follow input-shape modulo
        row_mod_by_h = set([r % h for r in rows])
        col_mod_by_w = set([c % w for c in cols])
        
        print(f"Row positions mod {h}: {sorted(row_mod_by_h)}")
        print(f"Col positions mod {w}: {sorted(col_mod_by_w)}")
        
        if len(row_mod_by_h) == 1:
            print(f"  ✓✓✓ ALL 2s at row % {h} == {list(row_mod_by_h)[0]}")
        if len(col_mod_by_w) == 1:
            print(f"  ✓✓✓ ALL 2s at col % {w} == {list(col_mod_by_w)[0]}")

print("\n" + "="*70)
print("SUMMARY: LOOKING FOR CONSISTENT MODULO PATTERN")
print("="*70)
