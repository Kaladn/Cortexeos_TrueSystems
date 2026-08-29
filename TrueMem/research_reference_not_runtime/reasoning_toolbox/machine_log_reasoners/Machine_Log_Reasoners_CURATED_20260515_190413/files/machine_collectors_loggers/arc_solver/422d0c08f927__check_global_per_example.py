"""Check if output is determined by COLUMN POSITION alone."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import numpy as np

def load_task(task_id: str) -> dict:
    train_path = "arc-prize-2025/arc-agi_training_challenges.json"
    with open(train_path, 'r') as f:
        data = json.load(f)
    return data[task_id]

task = load_task("0d3d703e")

print("HYPOTHESIS: Output determined by input VALUE (not position)")
print("=" * 60)
print()

# Collect all mappings
all_mappings = {}
for ex in task['train']:
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    for i in range(inp.shape[0]):
        for j in range(inp.shape[1]):
            in_val = int(inp[i, j])
            out_val = int(out[i, j])
            
            if in_val not in all_mappings:
                all_mappings[in_val] = []
            all_mappings[in_val].append(out_val)

print("Mappings observed:")
for in_color, out_colors in sorted(all_mappings.items()):
    unique_outs = set(out_colors)
    print(f"  {in_color} → {unique_outs} (appears {len(out_colors)} times)")

print()
print("FINDING:")
if all(len(set(outs)) == 1 for outs in all_mappings.values()):
    print("✓ Each input color ALWAYS maps to same output color!")
    print("This is a GLOBAL MAPPING (but different per example)")
else:
    print("✗ Input colors map to DIFFERENT outputs (position-dependent)")

print()
print("=" * 60)
print("Let me check the actual task structure...")
print()

# Show full grids
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    print(f"Example {i}:")
    print(f"Input:\n{inp}")
    print(f"Output:\n{out}")
    print()
