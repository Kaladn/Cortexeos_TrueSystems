"""Test BlockExpansionOperator on task ac0a08a4"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import BlockExpansionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac0a08a4']
op = BlockExpansionOperator()

print("=" * 60)
print("TESTING: BlockExpansionOperator on task ac0a08a4")
print("=" * 60)

# Test each training example
for i, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    print(f"\nExample {i}:")
    print(f"  Input: {inp.shape}, Output: {out.shape}")
    
    # Test analyze
    params = op.analyze(inp, out)
    if params is None:
        print("  ❌ ANALYZE FAILED - returned None")
        continue
    
    print(f"  ✓ Analyze: {params}")
    
    # Test apply
    predicted = op.apply(inp, params)
    
    if np.array_equal(predicted, out):
        print("  ✅ APPLY PASSED - output matches exactly")
    else:
        print("  ❌ APPLY FAILED - output mismatch")
        print(f"  Expected shape: {out.shape}, Got: {predicted.shape}")
        
        # Show first difference
        if predicted.shape == out.shape:
            diff = np.where(predicted != out)
            if len(diff[0]) > 0:
                r, c = diff[0][0], diff[1][0]
                print(f"  First diff at ({r},{c}): expected {out[r,c]}, got {predicted[r,c]}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
