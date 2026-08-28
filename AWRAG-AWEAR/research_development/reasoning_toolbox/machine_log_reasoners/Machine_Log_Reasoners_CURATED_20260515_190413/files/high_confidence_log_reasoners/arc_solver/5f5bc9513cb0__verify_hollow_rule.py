import numpy as np
import json
from scipy import ndimage

with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']

for ex_idx, example in enumerate(task['train'], 1):
    inp = np.array(example['input'])
    out = np.array(example['output'])
    H, W = inp.shape
    
    print(f"\n{'='*80}")
    print(f"Example {ex_idx}: {H}x{W} grid")
    print(f"{'='*80}\n")
    
    # Extract shapes and check center pixel
    for color in range(1, 10):
        mask = (inp == color)
        if not mask.any():
            continue
        
        labeled, num = ndimage.label(mask)
        for sid in range(1, num + 1):
            shape_mask = (labeled == sid)
            rows, cols = np.where(shape_mask)
            
            min_r, max_r = rows.min(), rows.max()
            min_c, max_c = cols.min(), cols.max()
            
            # Check center pixel
            center_r = (min_r + max_r) // 2
            center_c = (min_c + max_c) // 2
            has_center = inp[center_r, center_c] == color
            
            # Find in output
            out_mask = (out == color)
            if out_mask.any():
                out_labeled, out_num = ndimage.label(out_mask)
                for out_sid in range(1, out_num + 1):
                    out_shape = (out_labeled == out_sid)
                    out_rows, out_cols = np.where(out_shape)
                    
                    # Match by columns
                    if out_cols.min() == min_c and out_cols.max() == max_c:
                        out_min_r = out_rows.min()
                        direction = "UP" if out_min_r < min_r else "DOWN" if out_min_r > min_r else "SAME"
                        
                        predicted = "UP" if not has_center else "DOWN"
                        match = "✓" if predicted == direction else "✗"
                        
                        print(f"Color {color} @ cols {min_c}-{max_c}: center={'FILLED' if has_center else 'HOLLOW'} → predict {predicted}, actual {direction} {match}")
                        break

print("\n" + "="*80)
print("RULE VERIFICATION COMPLETE")
print("="*80)
