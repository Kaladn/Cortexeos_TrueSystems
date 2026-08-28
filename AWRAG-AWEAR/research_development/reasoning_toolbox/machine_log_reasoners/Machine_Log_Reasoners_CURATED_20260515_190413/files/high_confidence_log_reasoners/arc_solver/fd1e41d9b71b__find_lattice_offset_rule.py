"""
The modulo OFFSETS depend on the non-zero positions!
Find the relationship between non-zero positions and the lattice offsets
"""
import numpy as np
import json

with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task = eval_challenges['310f3251']

print("="*70)
print("FINDING RELATIONSHIP: NON-ZERO POSITIONS → LATTICE OFFSETS")
print("="*70)

for ex_num in range(len(task['train'])):
    inp = np.array(task['train'][ex_num]['input'])
    out = np.array(task['train'][ex_num]['output'])
    h, w = inp.shape
    
    print(f"\n{'='*70}")
    print(f"Example {ex_num+1}: Input shape ({h}, {w})")
    print(f"{'='*70}")
    print(f"Input:\n{inp}")
    
    # Find non-zero positions
    nonzero_pos = []
    for i in range(h):
        for j in range(w):
            if inp[i,j] != 0:
                nonzero_pos.append((i, j))
    
    print(f"\nNon-zero positions: {nonzero_pos}")
    
    # Find lattice offsets (which positions mod input-shape have 2s)
    positions_with_2 = []
    for i in range(out.shape[0]):
        for j in range(out.shape[1]):
            if out[i,j] == 2:
                positions_with_2.append((i, j))
    
    row_mods = sorted(set([r % h for r in [p[0] for p in positions_with_2]]))
    col_mods = sorted(set([c % w for c in [p[1] for p in positions_with_2]]))
    
    print(f"\nLattice offsets:")
    print(f"  Rows mod {h}: {row_mods}")
    print(f"  Cols mod {w}: {col_mods}")
    
    # Check if lattice offsets are the DIAGONAL from non-zero positions
    print(f"\nChecking relationship:")
    for nz_r, nz_c in nonzero_pos:
        # Check if 2s appear on diagonals from this non-zero
        print(f"  Non-zero at ({nz_r}, {nz_c}):")
        print(f"    Anti-diagonal would be row={nz_r-1} or {nz_r+1}, col={nz_c-1} or {nz_c+1}")
        
        # Check specific patterns
        if (nz_r - 1) % h in row_mods or (nz_r + 1) % h in row_mods:
            print(f"    ✓ Row offset is adjacent to non-zero row!")
        if (nz_c - 1) % w in col_mods or (nz_c + 1) % w in col_mods:
            print(f"    ✓ Col offset is adjacent to non-zero col!")

print("\n" + "="*70)
print("HYPOTHESIS CHECK: Are 2-lattice positions DIAGONAL from non-zeros?")
print("="*70)
