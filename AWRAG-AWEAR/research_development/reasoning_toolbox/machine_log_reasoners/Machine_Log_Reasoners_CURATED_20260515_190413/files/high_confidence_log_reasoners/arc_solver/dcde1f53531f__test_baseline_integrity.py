"""
Quick test: Verify baseline solver still gets 56/56 solves
"""
import json
import numpy as np
import sys
sys.path.insert(0, 'cod_616')

from arc_organ.arc_operators import infer_rule_for_task, OPERATORS

# Load baseline solutions
with open('solutions_with_new_operators.json', 'r') as f:
    baseline = json.load(f)

# Load datasets
with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
    train_tasks = json.load(f)
with open('arc-prize-2025/arc-agi_evaluation_challenges.json', 'r') as f:
    eval_tasks = json.load(f)

all_tasks = {**train_tasks, **eval_tasks}

print(f"Testing {len(baseline)} baseline tasks...")
print("=" * 60)

solved = 0
failed = []

for task_id in baseline.keys():
    if task_id not in all_tasks:
        print(f"MISSING: {task_id} not in dataset")
        continue
    
    task = all_tasks[task_id]
    train_pairs = [(np.array(p["input"]), np.array(p["output"])) for p in task["train"]]
    
    try:
        op, config = infer_rule_for_task(train_pairs)
        if op is not None:
            solved += 1
            # Quick validation
            valid = True
            for pair in train_pairs:
                result = op.apply(pair[0], config)
                if result is None or not np.array_equal(result, pair[1]):
                    valid = False
                    break
            
            if not valid:
                print(f"INVALID: {task_id} - {op.name} doesn't match training")
                failed.append((task_id, "validation_failed"))
        else:
            print(f"FAIL: {task_id} - baseline says {baseline[task_id]['operator']}")
            failed.append((task_id, "not_found"))
    except Exception as e:
        print(f"ERROR: {task_id} - {e}")
        failed.append((task_id, str(e)))

print("=" * 60)
print(f"✓ Solved: {solved}/{len(baseline)}")
print(f"✗ Failed: {len(failed)}")

if failed:
    print("\nFailed tasks:")
    for task_id, reason in failed[:10]:
        print(f"  {task_id}: {reason}")
