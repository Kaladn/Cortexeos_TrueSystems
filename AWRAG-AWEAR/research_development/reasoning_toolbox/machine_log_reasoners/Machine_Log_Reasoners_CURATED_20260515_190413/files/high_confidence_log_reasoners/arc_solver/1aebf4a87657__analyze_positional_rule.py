"""
Analyze 0d3d703e to find the positional/structural recoloring rule.
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

task = load_task("0d3d703e")

print("Analyzing 0d3d703e - POSITIONAL RECOLORING RULE")
print("=" * 60)
print()

# Analyze column-wise
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"Example {i}:")
    print(f"  Input:  {inp[0].tolist()}")
    print(f"  Output: {out[0].tolist()}")
    
    # Check mapping per column
    for col in range(3):
        in_col = inp[:, col]
        out_col = out[:, col]
        
        # All cells in column should be same (uniform column)
        in_color = in_col[0]
        out_color = out_col[0]
        
        print(f"    Column {col}: {in_color} → {out_color} (diff: {out_color - in_color})")
    print()

print("=" * 60)
print("HYPOTHESIS:")
print("Looking for mathematical relationship...")
print()

# Check if there's a positional rule
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"Example {i}:")
    for col in range(3):
        in_color = inp[0, col]
        out_color = out[0, col]
        
        # Try different transformations
        diff = out_color - in_color
        ratio = out_color / in_color if in_color != 0 else None
        
        print(f"  Col {col}: in={in_color}, out={out_color}, diff={diff}, ratio={ratio}")
    print()

print("=" * 60)
print("ALTERNATE: Check if output is based on POSITION itself")
print()

# Maybe output is determined by column index and something about input?
for i, ex in enumerate(task['train'], 1):
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"Example {i}: Output row = {out[0].tolist()}")

print()
print("Observation: Output always has form [a, b, c]")
print("Let me check if outputs follow a pattern...")
print()

outputs = []
for ex in task['train']:
    out = np.array(ex['output'])
    outputs.append(out[0].tolist())

print("Output patterns:")
for i, row in enumerate(outputs, 1):
    print(f"  Example {i}: {row}")

print()
print("Is there a relationship between output values within a row?")
for i, row in enumerate(outputs, 1):
    print(f"  Example {i}: {row[0]}, {row[1]}, {row[2]} -> diffs: {row[1]-row[0]}, {row[2]-row[1]}")
