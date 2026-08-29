import json
import numpy as np
import sys
sys.path.insert(0, 'cod_616')

from cod_616.arc_organ.arc_operators import OPERATORS

# Load data
data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
baseline = json.load(open('solutions_with_new_operators.json'))

# Test task 007bbfb7
task_id = '007bbfb7'
task = data[task_id]
baseline_op_name = baseline[task_id]['operator']

print(f"Task: {task_id}")
print(f"Baseline operator: {baseline_op_name}")

# Find operator
ops = {op.name: op for op in OPERATORS}
op = ops[baseline_op_name]

# Test single op
train = task['train'][0]
inp = np.array(train['input'])
out = np.array(train['output'])

cfg = op.analyze(inp, out)
print(f"Config: {cfg}")

if cfg:
    result = op.apply(inp, cfg)
    match = np.array_equal(result, out)
    print(f"Single op works: {match}")
    
    # Test on all training examples
    all_match = True
    for i, pair in enumerate(task['train']):
        inp_i = np.array(pair['input'])
        out_i = np.array(pair['output'])
        result_i = op.apply(inp_i, cfg)
        matches = np.array_equal(result_i, out_i)
        print(f"  Example {i+1}: {matches}")
        if not matches:
            all_match = False
    
    print(f"All examples match: {all_match}")
