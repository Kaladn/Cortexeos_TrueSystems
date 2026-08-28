"""Test LatinSquareFromDiagonalOperator on task 05269061."""

import json
import numpy as np
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import LatinSquareFromDiagonalOperator

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

print("="*80)
print("Testing LatinSquareFromDiagonalOperator on 05269061")
print("="*80)

op = LatinSquareFromDiagonalOperator()

# Test all training examples
params_list = []
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\nTrain example {i}:")
    print(f"  Input shape: {inp.shape}")
    print(f"  Output shape: {out.shape}")
    
    params = op.analyze(inp, out)
    
    if params is None:
        print(f"  ❌ analyze() returned None")
    else:
        print(f"  ✅ analyze() succeeded")
        print(f"     Colors: {params['colors']}")
        print(f"     Output shape: {params['output_shape']}")
        params_list.append(params)

# Try to merge
if len(params_list) == 3:
    print(f"\n{'='*80}")
    print("Checking if all params are identical (for merge):")
    print(f"{'='*80}")
    
    if params_list[0] == params_list[1] == params_list[2]:
        print("✅ All params identical - merge will succeed")
        merged_params = params_list[0]
    else:
        print("⚠️  Params differ:")
        for i, p in enumerate(params_list, 1):
            print(f"  Example {i}: colors={p['colors']}")
        
        # Check if just colors differ
        if (params_list[0]['output_shape'] == params_list[1]['output_shape'] == params_list[2]['output_shape']):
            print("\n  Output shapes match - only color ordering differs")
            print("  This is expected: different diagonals → different permutations")
        
        # For test, we'll use first example params (should fail merge in real engine)
        print("\n  Using first example params for test...")
        merged_params = params_list[0]
else:
    print(f"\n❌ Only got {len(params_list)}/3 training examples")
    merged_params = None

# Test on test input
if merged_params is not None:
    print(f"\n{'='*80}")
    print("Applying to test input:")
    print(f"{'='*80}")
    
    test_inp = np.array(task['test'][0]['input'])
    test_out = np.array(solutions['05269061'][0])
    
    predicted = op.apply(test_inp, merged_params)
    
    print(f"  Test input shape: {test_inp.shape}")
    print(f"  Expected output shape: {test_out.shape}")
    print(f"  Predicted output shape: {predicted.shape}")
    
    # Compare
    if np.array_equal(predicted, test_out):
        print(f"\n  ✅ PERFECT MATCH!")
    else:
        diff_count = np.sum(predicted != test_out)
        total_pixels = test_out.shape[0] * test_out.shape[1]
        print(f"\n  ❌ {diff_count}/{total_pixels} pixels different")
        
        # Show first 3x3
        print(f"\n  Expected first 3x3:")
        print(test_out[:3, :3])
        print(f"\n  Predicted first 3x3:")
        print(predicted[:3, :3])

print(f"\n{'='*80}")
print("DIAGNOSIS:")
print(f"{'='*80}")
print("The operator correctly detects Latin square structure.")
print("BUT: Each training example has DIFFERENT color ordering.")
print("This means merge will FAIL in the real engine.")
print("\nThe operator needs to:")
print("1. Analyze test INPUT to determine its color ordering")
print("2. Generate the correct permutation from test input geometry")
print("3. NOT rely on merged params from training")
