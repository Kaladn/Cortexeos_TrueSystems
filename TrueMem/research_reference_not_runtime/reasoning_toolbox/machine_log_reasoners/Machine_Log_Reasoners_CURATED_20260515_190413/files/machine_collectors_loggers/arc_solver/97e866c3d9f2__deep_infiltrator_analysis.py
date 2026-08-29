"""
More careful analysis - where EXACTLY do the 2s infiltrate?
"""
import numpy as np
import json

with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task = eval_challenges['310f3251']

# Look at Example 1 very carefully
inp = np.array(task['train'][0]['input'])
out = np.array(task['train'][0]['output'])
tiled = np.tile(inp, (3, 3))

print("Example 1 Deep Dive:")
print(f"\nInput (2×2):\n{inp}")
print(f"\nSimple tile (6×6):\n{tiled}")
print(f"\nActual output (6×6):\n{out}")

print("\n" + "="*70)
print("WHERE DO 2s APPEAR?")
print("="*70)

for i in range(out.shape[0]):
    for j in range(out.shape[1]):
        if out[i,j] == 2:
            # Which position in the tile?
            in_i = i % inp.shape[0]
            in_j = j % inp.shape[1]
            
            print(f"Output[{i},{j}] = 2")
            print(f"  → This is tile position ({in_i},{in_j})")
            print(f"  → Input[{in_i},{in_j}] = {inp[in_i, in_j]}")
            print(f"  → Tiled[{i},{j}] was {tiled[i,j]}")
            print()

print("="*70)
print("HYPOTHESIS: 2s appear where input has 0 at SPECIFIC positions")
print("="*70)

# Check which input positions become 2
print("\nChecking input positions that become 2:")
for in_i in range(inp.shape[0]):
    for in_j in range(inp.shape[1]):
        # Check if this position becomes 2 in output
        becomes_2 = False
        for out_i in range(out.shape[0]):
            for out_j in range(out.shape[1]):
                if out_i % inp.shape[0] == in_i and out_j % inp.shape[1] == in_j:
                    if out[out_i, out_j] == 2:
                        becomes_2 = True
                        break
            if becomes_2:
                break
        
        if becomes_2:
            print(f"  Input[{in_i},{in_j}] = {inp[in_i, in_j]} → becomes 2 in output")
