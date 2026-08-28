"""
Test CenterRepulsionOperator on ac2e8ecf
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from arc_organ.arc_operators import CenterRepulsionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']

print(f"\n{'='*60}")
print(f"Testing CenterRepulsionOperator on ac2e8ecf")
print(f"{'='*60}\n")

op = CenterRepulsionOperator()

for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"Example {i}:")
    
    # Analyze
    params = op.analyze(inp, out)
    if params:
        print(f"  ✓ Analyze: {params}")
        
        # Apply
        result = op.apply(inp, params)
        match = np.array_equal(result, out)
        
        if match:
            print(f"  ✓ Apply: PERFECT MATCH")
        else:
            print(f"  ✗ Apply: MISMATCH")
            print(f"    Expected shape: {out.shape}, Got: {result.shape}")
            print(f"    Differences: {np.sum(result != out)} cells")
            
            # Show where differences are
            if result.shape == out.shape:
                diff_positions = np.argwhere(result != out)
                print(f"    First 5 diffs: {diff_positions[:5].tolist()}")
    else:
        print(f"  ✗ Analyze: FAILED")
    
    print()

# Test with infer_rule_for_task
print(f"{'='*60}")
print(f"Testing with infer_rule_for_task")
print(f"{'='*60}\n")

from arc_organ.arc_operators import infer_rule_for_task

train_pairs = [(np.array(ex['input']), np.array(ex['output'])) 
               for ex in task['train']]

op_found, params_found = infer_rule_for_task(train_pairs)

if op_found:
    print(f"✓ Found operator: {op_found.name}")
    print(f"  Parameters: {params_found}")
    
    # Validate on all examples
    print(f"\n  Validation:")
    for i, (inp, expected_out) in enumerate(train_pairs, 1):
        result = op_found.apply(inp, params_found)
        match = np.array_equal(result, expected_out)
        print(f"    Example {i}: {'✓ PASS' if match else '✗ FAIL'}")
else:
    print(f"✗ No operator found")
