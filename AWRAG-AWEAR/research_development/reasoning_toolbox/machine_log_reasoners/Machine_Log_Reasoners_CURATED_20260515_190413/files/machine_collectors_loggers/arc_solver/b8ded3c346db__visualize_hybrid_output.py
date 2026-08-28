import numpy as np
import json
from cod_616.arc_organ.arc_operators import CenterRepulsionOperator

with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

for ex_idx in range(3):
    ex = data['ac2e8ecf']['train'][ex_idx]
    inp = np.array(ex['input'])
    expected = np.array(ex['output'])
    
    op = CenterRepulsionOperator()
    got = op.apply(inp, {})
    
    diff_mask = (got != expected)
    num_diff = diff_mask.sum()
    
    print(f"\nExample {ex_idx + 1}: {num_diff} cells differ")
    
    if num_diff > 0:
        print("\nExpected output:")
        print(expected)
        print("\nGot output:")
        print(got)
        print("\nDifference mask (True = mismatch):")
        print(diff_mask.astype(int))
