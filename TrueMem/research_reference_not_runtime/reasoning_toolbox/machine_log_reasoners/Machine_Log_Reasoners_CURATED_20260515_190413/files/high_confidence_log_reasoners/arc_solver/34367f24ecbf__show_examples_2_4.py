"""Show what the operator produces for examples 2 and 4"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import DiagonalReflectionOperator

data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
task = data['b8cdaf2b']
op = DiagonalReflectionOperator()

for i in [2, 4]:
    ex = task['train'][i-1]
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\n{'='*60}")
    print(f"EXAMPLE {i}")
    print('='*60)
    
    print("\nInput:")
    for row in inp:
        print("  " + " ".join(str(x) for x in row))
    
    print("\nExpected Output:")
    for row in out:
        print("  " + " ".join(str(x) for x in row))
    
    # Try to apply anyway (even if analyze fails)
    # Manually set inner_color based on what we see
    if i == 2:
        params = {"inner_color": 3}
    else:  # i == 4
        params = {"inner_color": 4}
    
    predicted = op.apply(inp, params)
    
    print("\nOur Output:")
    for row in predicted:
        print("  " + " ".join(str(x) for x in row))
    
    print("\nMatch:", "✅" if np.array_equal(predicted, out) else "❌")
    
    if not np.array_equal(predicted, out):
        print("\nDifferences:")
        diff_coords = np.where(predicted != out)
        for r, c in zip(diff_coords[0], diff_coords[1]):
            print(f"  [{r},{c}]: expected {out[r,c]}, got {predicted[r,c]}")
