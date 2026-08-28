"""
Test New Operators on Original 5 Tasks

Tests the 5 newly implemented operators on their target tasks.
"""
import json
import numpy as np
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cod_616.arc_organ.arc_operators import OPERATORS

print("="*80)
print("TESTING 5 NEW OPERATORS")
print("="*80)
print()

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    all_data = json.load(f)

# Target tasks
test_tasks = {
    '00576224': 'checkerboard_tiling_alternating',
    '009d5c81': 'shape_reference_recolor',
    '00d62c1b': 'enclosed_region_fill',
    '00dbd492': 'pattern_completion_prototype',
    '017c7c7b': 'symmetry_from_fragment'
}

# Build operator dict
op_dict = {op.name: op for op in OPERATORS}

print(f"Total operators loaded: {len(OPERATORS)}")
print()

# Check if new operators are loaded
new_ops = [
    'enclosed_region_fill',
    'checkerboard_tiling_alternating',
    'symmetry_from_fragment',
    'shape_reference_recolor',
    'pattern_completion_prototype'
]

print("New operators status:")
for op_name in new_ops:
    status = "✓ LOADED" if op_name in op_dict else "✗ MISSING"
    print(f"  {op_name}: {status}")
print()

def test_operator_on_task(task_id, task_data, expected_op_name):
    """Test if expected operator solves the task."""
    if expected_op_name not in op_dict:
        return {'success': False, 'reason': 'Operator not loaded'}
    
    operator = op_dict[expected_op_name]
    
    try:
        # Test analyze on all training examples
        all_params = []
        for example in task_data['train']:
            inp = np.array(example['input'])
            out = np.array(example['output'])
            
            params = operator.analyze(inp, out)
            if params is None:
                return {'success': False, 'reason': 'analyze() returned None'}
            
            all_params.append(params)
        
        # Use first params for apply test
        test_params = all_params[0]
        
        # Test apply on first training example
        inp = np.array(task_data['train'][0]['input'])
        expected = np.array(task_data['train'][0]['output'])
        
        result = operator.apply(inp, test_params)
        
        if np.array_equal(result, expected):
            return {'success': True, 'reason': 'Perfect match'}
        else:
            return {'success': False, 'reason': 'Output mismatch'}
    
    except Exception as e:
        return {'success': False, 'reason': f'Exception: {str(e)[:100]}'}

print("="*80)
print("TESTING ON TARGET TASKS")
print("="*80)
print()

results = {}

for task_id, expected_op in test_tasks.items():
    task_data = all_data[task_id]
    result = test_operator_on_task(task_id, task_data, expected_op)
    results[task_id] = result
    
    status = "✓ PASS" if result['success'] else "✗ FAIL"
    print(f"{task_id} ({expected_op}):")
    print(f"  Status: {status}")
    print(f"  Reason: {result['reason']}")
    print()

print("="*80)
print("SUMMARY")
print("="*80)
print()

passed = sum(1 for r in results.values() if r['success'])
total = len(results)

print(f"Passed: {passed}/{total}")
print()

if passed == total:
    print("✓ ALL TESTS PASSED - Ready for full scan!")
elif passed > 0:
    print(f"⚠ {passed} operators working, {total-passed} need debugging")
else:
    print("✗ All tests failed - check operator implementations")
