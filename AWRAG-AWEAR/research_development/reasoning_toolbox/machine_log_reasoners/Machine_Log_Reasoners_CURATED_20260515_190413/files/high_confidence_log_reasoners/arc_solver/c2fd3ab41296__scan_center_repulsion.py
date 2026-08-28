"""
Scan ALL 1000 training tasks for CenterRepulsionOperator specifically
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import json
import numpy as np
from arc_organ.arc_operators import CenterRepulsionOperator

# Load tasks
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

op = CenterRepulsionOperator()

print(f"Scanning {len(data)} training tasks for CenterRepulsionOperator")
print("="*60)

solved = []
for task_id, task in data.items():
    train_pairs = [(np.array(ex['input']), np.array(ex['output'])) 
                   for ex in task['train']]
    
    # Check if operator can analyze all training examples
    all_match = True
    params_list = []
    
    for inp, out in train_pairs:
        params = op.analyze(inp, out)
        if params is None:
            all_match = False
            break
        
        # Verify apply works
        result = op.apply(inp, params)
        if not np.array_equal(result, out):
            all_match = False
            break
        
        params_list.append(params)
    
    if all_match and len(params_list) > 0:
        # Try to merge params
        merged = params_list[0]
        for p in params_list[1:]:
            if p != merged:
                all_match = False
                break
        
        if all_match:
            solved.append(task_id)
            print(f"✓ {task_id}")

print(f"\n{'='*60}")
print(f"CenterRepulsionOperator solved: {len(solved)}/{len(data)} tasks")
if solved:
    print(f"\nSolved tasks:")
    for task_id in solved:
        print(f"  - {task_id}")
