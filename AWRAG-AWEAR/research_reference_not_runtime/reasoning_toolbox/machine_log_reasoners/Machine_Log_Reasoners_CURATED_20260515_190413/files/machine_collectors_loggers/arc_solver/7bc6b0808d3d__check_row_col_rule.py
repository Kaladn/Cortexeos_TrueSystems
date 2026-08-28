"""
Check if 2s appear in rows/columns adjacent to rows/columns with non-zeros
"""
import numpy as np
import json

with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

task = eval_challenges['310f3251']

print("="*70)
print("NEW HYPOTHESIS: 2s mark positions adjacent to (but not in) non-zero rows/cols")
print("="*70)

for ex_num in [0, 3, 4]:  # Check examples 1, 4, 5
    inp = np.array(task['train'][ex_num]['input'])
    out = np.array(task['train'][ex_num]['output'])
    
    print(f"\nExample {ex_num+1}:")
    print(f"Input:\n{inp}")
    
    # Find rows and columns with non-zeros
    rows_with_nonzero = set()
    cols_with_nonzero = set()
    for i in range(inp.shape[0]):
        for j in range(inp.shape[1]):
            if inp[i,j] != 0:
                rows_with_nonzero.add(i)
                cols_with_nonzero.add(j)
    
    print(f"\nRows with non-zeros: {sorted(rows_with_nonzero)}")
    print(f"Cols with non-zeros: {sorted(cols_with_nonzero)}")
    
    # Find where 2s appear
    positions_with_2 = set()
    for i in range(out.shape[0]):
        for j in range(out.shape[1]):
            if out[i,j] == 2:
                in_i = i % inp.shape[0]
                in_j = j % inp.shape[1]
                positions_with_2.add((in_i, in_j))
    
    print(f"\nPositions that become 2: {sorted(positions_with_2)}")
    
    for pos in sorted(positions_with_2):
        i, j = pos
        row_adjacent_to_nonzero = (i-1 in rows_with_nonzero or i+1 in rows_with_nonzero)
        col_adjacent_to_nonzero = (j-1 in cols_with_nonzero or j+1 in cols_with_nonzero)
        
        print(f"  ({i},{j}): row adjacent? {row_adjacent_to_nonzero}, col adjacent? {col_adjacent_to_nonzero}")
    
    print("\n" + "-"*70)
