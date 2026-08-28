"""
Test CenterHaloExpansionOperator on task 3befdf3e
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import CenterHaloExpansionOperator

def main():
    # Load task 3befdf3e
    data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
    with open(data_path) as f:
        tasks = json.load(f)
    
    task = tasks['3befdf3e']
    
    print("="*80)
    print("TESTING CenterHaloExpansionOperator ON TASK 3befdf3e")
    print("="*80)
    print()
    
    operator = CenterHaloExpansionOperator()
    
    # Test on all training examples
    all_pass = True
    for i, example in enumerate(task['train'], 1):
        input_arr = np.array(example['input'])
        expected_output = np.array(example['output'])
        
        print(f"TRAINING EXAMPLE {i}:")
        print(f"  Input shape: {input_arr.shape}")
        print(f"  Output shape: {expected_output.shape}")
        
        # Analyze
        params = operator.analyze(input_arr, expected_output)
        
        if params is None:
            print(f"  ❌ FAIL: Operator did not detect pattern")
            all_pass = False
            continue
        
        print(f"  Params: {params}")
        
        # Apply
        generated = operator.apply(input_arr, params)
        
        # Check match
        if np.array_equal(generated, expected_output):
            print(f"  ✅ PASS: Generated output matches expected")
        else:
            print(f"  ❌ FAIL: Generated output does not match")
            print(f"  Expected:")
            for row in expected_output:
                print(f"    {' '.join(str(x) for x in row)}")
            print(f"  Generated:")
            for row in generated:
                print(f"    {' '.join(str(x) for x in row)}")
            all_pass = False
        
        print()
    
    if all_pass:
        print("="*80)
        print("✅ ALL TESTS PASSED - Operator is ready!")
        print("="*80)
    else:
        print("="*80)
        print("❌ SOME TESTS FAILED")
        print("="*80)

if __name__ == '__main__':
    main()
