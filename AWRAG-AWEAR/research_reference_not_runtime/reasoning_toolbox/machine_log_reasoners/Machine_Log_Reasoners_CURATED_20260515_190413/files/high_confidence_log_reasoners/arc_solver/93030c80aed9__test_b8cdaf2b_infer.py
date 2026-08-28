import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))
import json
import numpy as np
from arc_organ.arc_operators import infer_rule_for_task

with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    data = json.load(f)

task_id = 'b8cdaf2b'
task = data[task_id]

train_pairs = [
    (np.array(ex['input']), np.array(ex['output']))
    for ex in task['train']
]

print(f"Testing task {task_id} with {len(train_pairs)} training examples")

op, params = infer_rule_for_task(train_pairs)

if op:
    print(f"✓ Found operator: {op.name}")
    print(f"  Parameters: {params}")
    
    # Verify all training examples
    for i, (inp, exp_out) in enumerate(train_pairs, 1):
        result = op.apply(inp, params)
        match = np.array_equal(result, exp_out)
        print(f"  Example {i}: {'✓' if match else '✗'}")
else:
    print("✗ No operator found")
