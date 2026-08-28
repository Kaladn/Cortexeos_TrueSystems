import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))
import json
import numpy as np
from arc_organ.arc_operators import OPERATORS, merge_operator_params

with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['b8cdaf2b']
train_pairs = [
    (np.array(ex['input']), np.array(ex['output']))
    for ex in task['train']
]

# Find diagonal_reflection operator
diag_op = None
for op in OPERATORS:
    if op.name == "diagonal_reflection":
        diag_op = op
        break

if not diag_op:
    print("diagonal_reflection not found in OPERATORS!")
else:
    print(f"Testing {diag_op.name}...")
    
    # Test analyze on all examples
    params_list = []
    for i, (inp, out) in enumerate(train_pairs, 1):
        params = diag_op.analyze(inp, out)
        print(f"Example {i}: analyze returned {params}")
        if params:
            params_list.append(params)
    
    # Try merge
    if len(params_list) == len(train_pairs):
        merged = merge_operator_params(diag_op, params_list)
        print(f"\nMerged params: {merged}")
        
        # Test apply with merged params
        print("\nTesting apply() with merged params:")
        for i, (inp, exp_out) in enumerate(train_pairs, 1):
            result = diag_op.apply(inp, merged)
            match = np.array_equal(result, exp_out)
            print(f"Example {i}: {'✓' if match else '✗'}")
            if not match:
                print(f"  Expected shape: {exp_out.shape}, got {result.shape}")
                diff = np.where(result != exp_out)
                if len(diff[0]) > 0:
                    print(f"  First diff at [{diff[0][0]},{diff[1][0]}]: expected {exp_out[diff[0][0],diff[1][0]]}, got {result[diff[0][0],diff[1][0]]}")
