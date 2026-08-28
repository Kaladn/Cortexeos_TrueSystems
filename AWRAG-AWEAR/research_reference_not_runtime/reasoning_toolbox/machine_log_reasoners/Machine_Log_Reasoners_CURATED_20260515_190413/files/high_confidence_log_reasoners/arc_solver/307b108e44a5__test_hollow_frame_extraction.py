"""Test HollowFrameExtractionOperator on task d5d6de2d"""
import json
import numpy as np
import sys
sys.path.insert(0, 'cod_616')

from arc_organ.arc_operators import HollowFrameExtractionOperator

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['d5d6de2d']
op = HollowFrameExtractionOperator()

print("="*60)
print("TESTING HollowFrameExtractionOperator on task d5d6de2d")
print("="*60)

all_pass = True

for i, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    expected_out = np.array(example['output'])
    
    print(f"\nExample {i}:")
    print(f"  Input shape: {inp.shape}")
    print(f"  Output shape: {expected_out.shape}")
    
    # Test analyze
    params = op.analyze(inp, expected_out)
    
    if params is None:
        print(f"  ❌ ANALYZE FAILED - returned None")
        all_pass = False
        continue
    
    print(f"  ✓ Analyze succeeded")
    print(f"    Frame color: {params['frame_color']}")
    print(f"    Fill color: {params['fill_color']}")
    
    # Test apply
    result = op.apply(inp, params)
    
    if np.array_equal(result, expected_out):
        print(f"  ✅ APPLY PASSED - output matches expected")
    else:
        print(f"  ❌ APPLY FAILED - output doesn't match")
        print(f"\n  Expected output:")
        for row in expected_out:
            print(f"    {row.tolist()}")
        print(f"\n  Got output:")
        for row in result:
            print(f"    {row.tolist()}")
        all_pass = False

print(f"\n{'='*60}")
if all_pass:
    print("✅ ALL TESTS PASSED - Operator is ready!")
else:
    print("❌ SOME TESTS FAILED - Debug needed")
print(f"{'='*60}\n")
