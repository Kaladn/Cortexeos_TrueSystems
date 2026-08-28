import numpy as np
import json

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

task = data['ac2e8ecf']

print("Analyzing Example 1 separation pattern")
print("="*70)

ex = task['train'][0]
inp = np.array(ex['input'])
out = np.array(ex['output'])
H, W = inp.shape
h_mid = H / 2.0
v_mid = W / 2.0

print(f"Grid: {H}x{W}, horizontal midpoint={h_mid}, vertical midpoint={v_mid}")
print()

# Get all shapes and their movements
from scipy import ndimage

colors = sorted(set(inp.flatten()) - {0})
print(f"Colors: {colors}")
print()

for color in colors:
    in_mask = (inp == color)
    labeled_in, num_in = ndimage.label(in_mask)
    
    out_mask = (out == color)
    labeled_out, num_out = ndimage.label(out_mask)
    
    print(f"Color {color}: {num_in} input shapes, {num_out} output shapes")
    
    for i in range(1, num_in + 1):
        shape_mask = (labeled_in == i)
        positions = np.argwhere(shape_mask)
        
        in_rows = positions[:, 0]
        in_cols = positions[:, 1]
        in_center_row = in_rows.mean()
        in_center_col = in_cols.mean()
        
        # Count quadrants
        upper = np.sum(in_rows < h_mid)
        lower = np.sum(in_rows >= h_mid)
        left = np.sum(in_cols < v_mid)
        right = np.sum(in_cols >= v_mid)
        
        # Find matching output shape
        for j in range(1, num_out + 1):
            out_shape_mask = (labeled_out == j)
            out_positions = np.argwhere(out_shape_mask)
            out_center_col = out_positions[:, 1].mean()
            
            # Match by column position
            if abs(out_center_col - in_center_col) < 1:
                out_center_row = out_positions[:, 0].mean()
                direction = "UP" if out_center_row < in_center_row else "DOWN"
                
                print(f"  Shape at col {in_center_col:.1f}:")
                print(f"    Input: row {in_center_row:.1f} (upper={upper}, lower={lower}, left={left}, right={right})")
                print(f"    Output: row {out_center_row:.1f}")
                print(f"    Movement: {direction}")
                
                # Try to find pattern
                if upper > lower:
                    predict = "UP (majority upper)"
                else:
                    predict = "DOWN (majority lower)"
                
                if left > right:
                    predict2 = "UP (majority left)"
                else:
                    predict2 = "DOWN (majority right)"
                
                correct1 = "✓" if (predict.startswith(direction)) else "✗"
                correct2 = "✓" if (predict2.startswith(direction)) else "✗"
                
                print(f"    H-separation predicts: {predict} {correct1}")
                print(f"    V-separation predicts: {predict2} {correct2}")
                print()
                break
