"""
What determines which 0s become 2s? Look at the NON-ZERO positions!
"""
import numpy as np
import json

with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task = eval_challenges['310f3251']

print("="*70)
print("HYPOTHESIS: 2s appear at 0 positions that are ADJACENT to non-zeros?")
print("="*70)

for ex_num in range(len(task['train'])):
    inp = np.array(task['train'][ex_num]['input'])
    out = np.array(task['train'][ex_num]['output'])
    
    print(f"\nExample {ex_num+1}:")
    print(f"Input:\n{inp}")
    
    # Find where 2s appear in output
    positions_with_2 = set()
    for i in range(out.shape[0]):
        for j in range(out.shape[1]):
            if out[i,j] == 2:
                in_i = i % inp.shape[0]
                in_j = j % inp.shape[1]
                positions_with_2.add((in_i, in_j))
    
    print(f"\nInput positions that become 2: {sorted(positions_with_2)}")
    
    # Find non-zero positions
    nonzero_positions = []
    for i in range(inp.shape[0]):
        for j in range(inp.shape[1]):
            if inp[i,j] != 0:
                nonzero_positions.append((i,j))
    
    print(f"Non-zero positions: {nonzero_positions}")
    
    # Check adjacency
    print(f"\nChecking if 2-positions are adjacent to non-zeros:")
    for pos in sorted(positions_with_2):
        i, j = pos
        # Check all 8 neighbors
        neighbors = [
            (i-1, j-1), (i-1, j), (i-1, j+1),
            (i, j-1),             (i, j+1),
            (i+1, j-1), (i+1, j), (i+1, j+1)
        ]
        
        adjacent_nonzeros = []
        for ni, nj in neighbors:
            if 0 <= ni < inp.shape[0] and 0 <= nj < inp.shape[1]:
                if inp[ni, nj] != 0:
                    adjacent_nonzeros.append((ni, nj))
        
        print(f"  Position {pos}: adjacent to {adjacent_nonzeros}")
    
    print("\n" + "-"*70)
