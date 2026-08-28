"""
Manually trace through apply() to see what it generates
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616/arc_organ')

from arc_operators import CenterHaloExpansionOperator

def main():
    # Load task 3befdf3e
    data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
    with open(data_path) as f:
        tasks = json.load(f)
    
    task = tasks['3befdf3e']
    example = task['train'][0]
    
    input_arr = np.array(example['input'])
    expected_output = np.array(example['output'])
    
    operator = CenterHaloExpansionOperator()
    
    # Get input structure
    input_struct = operator._find_halo_structure(input_arr)
    print(f"Input struct: {input_struct}")
    
    # Apply with those params
    params = {
        'core_color': input_struct['core_color'],  # 6
        'ring_color': input_struct['ring_color']   # 4
    }
    
    generated = operator.apply(input_arr, params)
    
    print("\nINPUT:")
    for row in input_arr:
        print(" ".join(str(x) for x in row))
    
    print("\nGENERATED OUTPUT:")
    for row in generated:
        print(" ".join(str(x) for x in row))
    
    print("\nEXPECTED OUTPUT:")
    for row in expected_output:
        print(" ".join(str(x) for x in row))
    
    print(f"\nMatch: {np.array_equal(generated, expected_output)}")
    
    # Show differences
    if not np.array_equal(generated, expected_output):
        print("\nDIFFERENCES:")
        for r in range(generated.shape[0]):
            for c in range(generated.shape[1]):
                if generated[r, c] != expected_output[r, c]:
                    print(f"  [{r},{c}]: generated={generated[r,c]}, expected={expected_output[r,c]}")

if __name__ == '__main__':
    main()
