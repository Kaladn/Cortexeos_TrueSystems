"""
WHAT THE FUCK IS THE 2? - Clean forensic analysis
"""
import numpy as np
import json

with open('arc-prize-2024/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_challenges = json.load(f)

with open('arc-prize-2024/arc-agi_evaluation_solutions.json', 'r') as f:
    eval_solutions = json.load(f)

task = eval_challenges['310f3251']

print("="*80)
print("WHAT THE FUCK IS THE 2?")
print("="*80)

for ex_num in range(len(task['train'])):
    inp = np.array(task['train'][ex_num]['input'])
    out = np.array(task['train'][ex_num]['output'])
    h, w = inp.shape
    
    print(f"\n{'='*80}")
    print(f"EXAMPLE {ex_num+1}: Input {h}×{w}, Output {out.shape[0]}×{out.shape[1]}")
    print(f"{'='*80}")
    
    # Show side by side
    print(f"\nINPUT:")
    for row in inp:
        print(' '.join(f'{x:2d}' for x in row))
    
    print(f"\nOUTPUT (showing where 2s are):")
    for i, row in enumerate(out):
        line = ' '.join(f'{x:2d}' for x in row)
        if 2 in row:
            line += f"  ← Row {i} has 2s"
        print(line)
    
    # Extract 2 positions
    twos_output = [(i,j) for i in range(out.shape[0]) for j in range(out.shape[1]) if out[i,j] == 2]
    twos_input_coords = sorted(set([(i%h, j%w) for i,j in twos_output]))
    
    print(f"\n2s map to these INPUT tile positions: {twos_input_coords}")
    
    # Show what's at those input positions
    for r, c in twos_input_coords:
        print(f"  Input[{r},{c}] = {inp[r,c]}")
    
    # Non-zeros
    nonzeros = [(i,j) for i in range(h) for j in range(w) if inp[i,j] != 0]
    print(f"\nNon-zero positions in input: {nonzeros}")
    
    # THE REAL QUESTION: Is there a simple geometric relationship?
    print(f"\n🎯 RELATIONSHIP:")
    for nz_r, nz_c in nonzeros:
        print(f"  Non-zero at ({nz_r},{nz_c})")
        for two_r, two_c in twos_input_coords:
            r_dist = (two_r - nz_r) % h
            c_dist = (two_c - nz_c) % w
            print(f"    2 at ({two_r},{two_c}) → distance: row_offset={r_dist}, col_offset={c_dist}")

print("\n" + "="*80)
print("LOOKING FOR CONSISTENT PATTERN ACROSS ALL EXAMPLES")
print("="*80)
