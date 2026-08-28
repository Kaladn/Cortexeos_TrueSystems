"""
Debug center repulsion - show what's happening
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from scipy import ndimage

# Load task
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task = data['ac2e8ecf']

ex = task['train'][0]  # Example 1
inp = np.array(ex['input'])
out = np.array(ex['output'])

print("INPUT OBJECTS:")
colors = set(inp.flatten()) - {0}
for color in sorted(colors):
    mask = (inp == color)
    labeled, num = ndimage.label(mask)
    
    for lid in range(1, num + 1):
        obj_mask = (labeled == lid)
        positions = np.argwhere(obj_mask)
        min_r, min_c = positions.min(axis=0)
        max_r, max_c = positions.max(axis=0)
        center_r, center_c = positions.mean(axis=0)
        
        print(f"  Color {color}: rows {min_r}-{max_r}, cols {min_c}-{max_c}, center=({center_r:.1f}, {center_c:.1f})")

print("\nOUTPUT OBJECTS:")
colors = set(out.flatten()) - {0}
for color in sorted(colors):
    mask = (out == color)
    labeled, num = ndimage.label(mask)
    
    for lid in range(1, num + 1):
        obj_mask = (labeled == lid)
        positions = np.argwhere(obj_mask)
        min_r, min_c = positions.min(axis=0)
        max_r, max_c = positions.max(axis=0)
        center_r, center_c = positions.mean(axis=0)
        
        print(f"  Color {color}: rows {min_r}-{max_r}, cols {min_c}-{max_c}, center=({center_r:.1f}, {center_c:.1f})")

print("\nKEY INSIGHT:")
print("Objects maintain EXACT horizontal positions (columns)")
print("Objects shift ONLY vertically to top or bottom edge")
