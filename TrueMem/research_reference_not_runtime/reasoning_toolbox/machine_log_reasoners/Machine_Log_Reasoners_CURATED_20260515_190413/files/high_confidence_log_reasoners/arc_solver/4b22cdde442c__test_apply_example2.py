"""
Test apply() directly without analyze checking
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616')

from arc_organ.arc_operators import CenterHaloExpansionOperator

def main():
    data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
    with open(data_path) as f:
        tasks = json.load(f)
    
    task = tasks['3befdf3e']
    example = task['train'][1]  # Example 2
    
    input_arr = np.array(example['input'])
    output_arr = np.array(example['output'])
    
    operator = CenterHaloExpansionOperator()
    input_struct = operator._find_halo_structure(input_arr)
    
    print(f"Input core: {input_struct['core_color']}")
    print(f"Input ring: {input_struct['ring_color']}")
    print(f"Core positions (relative to bbox): {input_struct['core_positions']}")
    
    params = {
        'core_color': input_struct['core_color'],
        'ring_color': input_struct['ring_color']
    }
    
    generated = operator.apply(input_arr, params)
    
    print("\nGENERATED:")
    for row in generated:
        print(" ".join(str(x) for x in row))
    
    print("\nEXPECTED:")
    for row in output_arr:
        print(" ".join(str(x) for x in row))
    
    match = np.array_equal(generated, output_arr)
    print(f"\nMatch: {match}")
    
    if not match:
        print("\nFirst 10 differences:")
        count = 0
        for r in range(generated.shape[0]):
            for c in range(generated.shape[1]):
                if generated[r, c] != output_arr[r, c]:
                    print(f"  [{r},{c}]: gen={generated[r,c]}, exp={output_arr[r,c]}")
                    count += 1
                    if count >= 10:
                        break
            if count >= 10:
                break

if __name__ == '__main__':
    main()
