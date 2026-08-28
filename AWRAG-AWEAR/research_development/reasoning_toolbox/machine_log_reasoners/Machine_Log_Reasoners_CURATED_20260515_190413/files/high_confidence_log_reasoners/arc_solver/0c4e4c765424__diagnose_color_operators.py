"""
Diagnose position_based_recolor tasks vs recolor_mapping tasks.

Strategy: Load examples of each type and analyze what makes them different.
"""
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

# Load rule database
with open('arc_rules_with_math_expansion.jsonl', 'r') as f:
    rules = [json.loads(line) for line in f]

# Get examples of each operator
recolor_mapping_tasks = [r for r in rules if r.get('operator') == 'recolor_mapping']
position_based_tasks = [r for r in rules if r.get('operator') == 'position_based_recolor']

print("=" * 80)
print("DIAGNOSING COLOR OPERATOR DIFFERENCES")
print("=" * 80)
print()
print(f"recolor_mapping: {len(recolor_mapping_tasks)} tasks")
print(f"position_based_recolor: {len(position_based_tasks)} tasks")
print()

# Analyze first example of each type
print("=" * 80)
print("EXAMPLE 1: recolor_mapping (0d3d703e)")
print("=" * 80)
task = load_task("0d3d703e")

for i, ex in enumerate(task['train'][:2], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\nTraining Example {i}:")
    print(f"  Input shape: {inp.shape}")
    print(f"  Input:\n{inp}")
    print(f"  Output:\n{out}")
    
    # Check if it's a simple global mapping
    flat_in = inp.flatten()
    flat_out = out.flatten()
    
    mapping = {}
    consistent = True
    for j in range(len(flat_in)):
        in_c = int(flat_in[j])
        out_c = int(flat_out[j])
        if in_c in mapping:
            if mapping[in_c] != out_c:
                consistent = False
                break
        else:
            mapping[in_c] = out_c
    
    print(f"  Global mapping: {mapping}")
    print(f"  Consistent per-example: {consistent}")

print()
print("=" * 80)
print("EXAMPLE 2: position_based_recolor (05269061)")
print("=" * 80)
task = load_task("05269061")

for i, ex in enumerate(task['train'][:2], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\nTraining Example {i}:")
    print(f"  Input shape: {inp.shape}")
    print(f"  Input:\n{inp}")
    print(f"  Output:\n{out}")
    
    # Check if it's a simple global mapping
    flat_in = inp.flatten()
    flat_out = out.flatten()
    
    mapping = {}
    conflicts = []
    for j in range(len(flat_in)):
        in_c = int(flat_in[j])
        out_c = int(flat_out[j])
        if in_c in mapping:
            if mapping[in_c] != out_c:
                conflicts.append((j, in_c, mapping[in_c], out_c))
        else:
            mapping[in_c] = out_c
    
    print(f"  Attempted mapping: {mapping}")
    if conflicts:
        print(f"  CONFLICTS (position-dependent!):")
        for pos, in_c, expected, actual in conflicts[:5]:
            print(f"    Position {pos}: color {in_c} → expected {expected}, got {actual}")
    else:
        print(f"  NO CONFLICTS (global mapping works)")

print()
print("=" * 80)
print("KEY DIFFERENCE:")
print("  recolor_mapping: Each example has consistent global color map")
print("  position_based_recolor: Same input color maps to DIFFERENT outputs")
print("                          depending on POSITION in grid")
print("=" * 80)
