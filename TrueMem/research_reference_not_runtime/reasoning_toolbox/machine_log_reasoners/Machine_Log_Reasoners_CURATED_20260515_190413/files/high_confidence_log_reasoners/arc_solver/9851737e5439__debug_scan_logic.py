"""Test why scan is missing baseline solves."""
import json
import numpy as np
import sys
sys.path.insert(0, 'cod_616')

from cod_616.arc_organ.arc_operators import OPERATORS

# Load data
data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
eval_data = json.load(open('arc-prize-2025/arc-agi_evaluation_challenges.json'))
all_tasks = {**data, **eval_data}
baseline = json.load(open('solutions_with_new_operators.json'))

print(f"Total baseline solves: {len(baseline)}")
print(f"Total tasks in dataset: {len(all_tasks)}")
print()

# Test first 10 baseline tasks with exact scan logic
baseline_ids = list(baseline.keys())[:10]

for task_id in baseline_ids:
    if task_id not in all_tasks:
        print(f"{task_id}: NOT IN DATASET")
        continue
    
    task = all_tasks[task_id]
    baseline_op_name = baseline[task_id]['operator']
    
    # Try scan logic
    found = False
    for op in OPERATORS:
        try:
            train_ex = task["train"][0]
            inp = np.array(train_ex["input"])
            out = np.array(train_ex["output"])
            config = op.analyze(inp, out)
            
            if config is None:
                continue
            
            # Validate on all examples
            valid = True
            for pair in task["train"]:
                pair_inp = np.array(pair["input"])
                pair_out = np.array(pair["output"])
                result = op.apply(pair_inp, config)
                if not np.array_equal(result, pair_out):
                    valid = False
                    break
            
            if valid:
                found = True
                found_op = op.name
                break
        except Exception as e:
            continue
    
    status = "OK" if found else "FAIL"
    found_name = found_op if found else "none"
    print(f"{task_id} (baseline: {baseline_op_name}): {status} (found: {found_name})")
