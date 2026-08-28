"""
Debug example 2 specifically
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616/arc_organ')

from arc_operators import CenterHaloExpansionOperator

def main():
    data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
    with open(data_path) as f:
        tasks = json.load(f)
    
    task = tasks['3befdf3e']
    example = task['train'][1]  # Example 2
    
    input_arr = np.array(example['input'])
    output_arr = np.array(example['output'])
    
    print("INPUT:")
    for row in input_arr:
        print(" ".join(str(x) for x in row))
    
    print("\nOUTPUT:")
    for row in output_arr:
        print(" ".join(str(x) for x in row))
    
    operator = CenterHaloExpansionOperator()
    
    # Test structure detection on input
    print("\n" + "="*60)
    print("INPUT structure:")
    input_struct = operator._find_halo_structure(input_arr)
    if input_struct:
        print(f"Core color: {input_struct['core_color']}")
        print(f"Ring color: {input_struct['ring_color']}")
        print(f"Core positions: {input_struct['core_positions']}")
        print(f"Bbox: {input_struct['bbox']}")
    else:
        print("FAILED to detect structure")
    
    # Test structure detection on output
    print("\n" + "="*60)
    print("OUTPUT structure:")
    output_struct = operator._find_halo_structure(output_arr)
    if output_struct:
        print(f"Core color: {output_struct['core_color']}")
        print(f"Ring color: {output_struct['ring_color']}")
        print(f"Core positions: {output_struct['core_positions']}")
        print(f"Bbox: {output_struct['bbox']}")
    else:
        print("FAILED to detect structure")
    
    # Test analyze
    print("\n" + "="*60)
    print("ANALYZE:")
    params = operator.analyze(input_arr, output_arr)
    print(f"Params: {params}")
    
    # If we have params, test apply
    if params:
        print("\n" + "="*60)
        print("APPLY:")
        generated = operator.apply(input_arr, params)
        match = np.array_equal(generated, output_arr)
        print(f"Match: {match}")
        
        if not match:
            print("\nDIFFERENCES:")
            for r in range(min(generated.shape[0], 15)):
                for c in range(generated.shape[1]):
                    if generated[r, c] != output_arr[r, c]:
                        print(f"  [{r},{c}]: gen={generated[r,c]}, exp={output_arr[r,c]}")

if __name__ == '__main__':
    main()
