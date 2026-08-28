"""
Debug CenterHaloExpansionOperator to see what's happening
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
    output_arr = np.array(example['output'])
    
    print("INPUT:")
    for row in input_arr:
        print(" ".join(str(x) for x in row))
    
    print("\nEXPECTED OUTPUT:")
    for row in output_arr:
        print(" ".join(str(x) for x in row))
    
    operator = CenterHaloExpansionOperator()
    
    # Test _find_halo_structure on input
    print("\n" + "="*60)
    print("Testing _find_halo_structure on INPUT:")
    input_struct = operator._find_halo_structure(input_arr)
    print(f"Result: {input_struct}")
    
    if input_struct:
        min_r, min_c, max_r, max_c = input_struct['bbox']
        region = input_arr[min_r:max_r, min_c:max_c]
        print(f"\nExtracted region ({region.shape}):")
        for row in region:
            print(" ".join(str(x) for x in row))
        print(f"Core color: {input_struct['core_color']}")
        print(f"Ring color: {input_struct['ring_color']}")
    
    # Test _find_halo_structure on output
    print("\n" + "="*60)
    print("Testing _find_halo_structure on OUTPUT:")
    output_struct = operator._find_halo_structure(output_arr)
    print(f"Result: {output_struct}")
    
    if output_struct:
        min_r, min_c, max_r, max_c = output_struct['bbox']
        region = output_arr[min_r:max_r, min_c:max_c]
        print(f"\nExtracted region ({region.shape}):")
        for row in region:
            print(" ".join(str(x) for x in row))
        print(f"Core color: {output_struct['core_color']}")
        print(f"Ring color: {output_struct['ring_color']}")
    
    # Test analyze
    print("\n" + "="*60)
    print("Testing analyze():")
    params = operator.analyze(input_arr, output_arr)
    print(f"Params: {params}")
    
    # If params exist, test apply
    if params:
        print("\n" + "="*60)
        print("Testing apply():")
        generated = operator.apply(input_arr, params)
        print("\nGENERATED OUTPUT:")
        for row in generated:
            print(" ".join(str(x) for x in row))
        
        print(f"\nMatch: {np.array_equal(generated, output_arr)}")

if __name__ == '__main__':
    main()
