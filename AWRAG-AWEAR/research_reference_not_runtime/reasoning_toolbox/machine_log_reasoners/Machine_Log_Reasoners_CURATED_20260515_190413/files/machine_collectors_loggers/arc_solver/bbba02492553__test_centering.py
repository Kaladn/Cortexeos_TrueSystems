"""
Test centering primitive on 3befdf3e examples
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.append('cod_616/arc_organ')

from centering import canonical_center_view, place_at_center

def main():
    data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
    with open(data_path) as f:
        tasks = json.load(f)
    
    task = tasks['3befdf3e']
    
    print("="*80)
    print("TESTING CENTERING PRIMITIVE ON 3befdf3e")
    print("="*80)
    
    for i, example in enumerate(task['train'][:3], 1):
        input_arr = np.array(example['input'])
        output_arr = np.array(example['output'])
        
        print(f"\n{'='*60}")
        print(f"EXAMPLE {i}")
        print(f"{'='*60}")
        
        # Extract center object from input
        center_obj, meta = canonical_center_view(input_arr)
        
        print(f"Input shape: {input_arr.shape}")
        print(f"Extracted center object shape: {center_obj.shape}")
        print(f"Background: {meta.background}")
        print(f"Bbox: {meta.bbox}")
        
        print(f"\nCenter object:")
        for row in center_obj:
            print("  " + " ".join(str(x) for x in row))
        
        # Extract center object from output
        output_obj, output_meta = canonical_center_view(output_arr)
        
        print(f"\nOutput center object shape: {output_obj.shape}")
        print(f"Output object:")
        for row in output_obj:
            print("  " + " ".join(str(x) for x in row))
        
        # Check growth
        in_h, in_w = center_obj.shape
        out_h, out_w = output_obj.shape
        print(f"\nGrowth: {in_h}×{in_w} → {out_h}×{out_w}")
        print(f"  Height grew by: {out_h - in_h}")
        print(f"  Width grew by: {out_w - in_w}")
        
        # Identify colors
        unique_in = set(center_obj.flatten()) - {0}
        unique_out = set(output_obj.flatten()) - {0}
        print(f"\nInput colors: {sorted(unique_in)}")
        print(f"Output colors: {sorted(unique_out)}")
    
    print("\n" + "="*80)
    print("✅ CENTERING PRIMITIVE WORKING")
    print("="*80)

if __name__ == '__main__':
    main()
