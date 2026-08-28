"""Test DiagonalReflectionOperator on task b8cdaf2b"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import DiagonalReflectionOperator

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['b8cdaf2b']
op = DiagonalReflectionOperator()

print("=" * 60)
print("TESTING: DiagonalReflectionOperator on task b8cdaf2b")
print("=" * 60)

# Test each training example
for i, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    print(f"\nExample {i}: {inp.shape}")
    
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
        print(f"\nExpected:")
        for row in out:
            print(f"  {list(row)}")
        print(f"\nGot:")
        for row in predicted:
            print(f"  {list(row)}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
