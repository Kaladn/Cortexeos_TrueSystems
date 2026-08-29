"""Debug why single operator validation is failing."""

import json
import numpy as np
import sys
sys.path.insert(0, 'cod_616')

from cod_616.arc_organ.arc_operators import OPERATORS

# Load one known solvable task
baseline_path = "solutions_with_new_operators.json"
train_dataset_path = "arc-prize-2025/arc-agi_training_challenges.json"

with open(baseline_path, 'r') as f:
    baseline = json.load(f)

with open(train_dataset_path, 'r') as f:
    all_tasks = json.load(f)

# Test first baseline task
task_id = "007bbfb7"
task = all_tasks[task_id]
baseline_op_name = baseline[task_id]["operator"]

print(f"Task: {task_id}")
print(f"Baseline operator: {baseline_op_name}")
print(f"Training examples: {len(task['train'])}")
print()

# Find the operator
target_op = None
for op in OPERATORS:
    if op.name == baseline_op_name:
        target_op = op
        break

if not target_op:
    print(f"ERROR: Operator '{baseline_op_name}' not found in OPERATORS list")
    print("Available operators:")
    for op in OPERATORS:
        print(f"  - {op.name}")
    sys.exit(1)

print(f"Found operator: {target_op.name}")
print()

# Try to analyze
train_ex = task["train"][0]

# Convert lists to numpy arrays
inp = np.array(train_ex['input'])
out = np.array(train_ex['output'])

print(f"Analyzing first training example...")
print(f"Input shape: {inp.shape}")
print(f"Output shape: {out.shape}")

try:
    config = target_op.analyze(inp, out)
    print(f"Config returned: {config}")
    print()
    
    if config:
        print("Validating on all training examples...")
        for i, pair in enumerate(task["train"]):
            pair_inp = np.array(pair["input"])
            pair_out = np.array(pair["output"])
            result = target_op.apply(pair_inp, config)
            matches = np.array_equal(result, pair_out)
            print(f"  Example {i+1}: {'✓' if matches else '✗'}")
            if not matches:
                print(f"    Expected shape: {pair_out.shape}, Got: {result.shape}")
    else:
        print("ERROR: analyze() returned None!")
        
except Exception as e:
    print(f"ERROR during analysis: {e}")
    import traceback
    traceback.print_exc()
