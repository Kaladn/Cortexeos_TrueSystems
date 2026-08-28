"""
Find position_based_recolor tasks that are NOT tiling/pattern-based.
Look for simpler row/column-based recoloring rules.
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

position_based_tasks = [r for r in rules if r.get('operator') == 'position_based_recolor']

print(f"Analyzing {len(position_based_tasks)} position_based_recolor tasks")
print("=" * 60)
print()

# Check each for tiling patterns
for rule in position_based_tasks[:5]:
    task_id = rule['task_id']
    task = load_task(task_id)
    
    ex = task['train'][0]
    inp = np.array(ex['input'])
    out = np.array(ex['output'])
    
    print(f"\nTask: {task_id}")
    print(f"  Grid size: {inp.shape}")
    
    # Check if output is tiled
    is_tiled = rule['math_expansion_slot']['geometric_properties']['tiling_candidate']
    print(f"  Tiling candidate: {is_tiled}")
    
    # Check color transformation
    color_transform = rule['math_expansion_slot']['color_properties']['color_transformation']
    print(f"  Color transformation: {color_transform}")
    
    # Quick visual
    if inp.shape[0] <= 5 and inp.shape[1] <= 5:
        print(f"  Input:\n{inp}")
        print(f"  Output:\n{out}")
