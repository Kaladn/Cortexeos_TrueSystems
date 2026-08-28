"""
Scan all 1000 training tasks from 2025 dataset with all operators
"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import infer_rule_for_task

# Load 2025 training data
with open("arc-prize-2025/arc-agi_training_challenges.json", "r") as f:
    train_challenges = json.load(f)

with open("arc-prize-2025/arc-agi_training_solutions.json", "r") as f:
    train_solutions = json.load(f)

print("=" * 70)
print(f"FULL 2025 TRAINING SET OPERATOR SCAN ({len(train_challenges)} tasks)")
print("=" * 70)
print()

solved_tasks = []
operator_counts = {}

for idx, task_id in enumerate(train_challenges.keys(), 1):
    if idx % 100 == 0:
        print(f"Progress: {idx}/{len(train_challenges)} tasks checked...")
    
    task = train_challenges[task_id]
    train_pairs = [
        (np.array(ex["input"]), np.array(ex["output"]))
        for ex in task["train"]
    ]
    
    # Try to infer rule
    try:
        operator, params = infer_rule_for_task(train_pairs)
    except Exception as e:
        # Skip tasks that cause errors in operator detection
        continue
    
    if operator is None:
        continue
    
    # Test on test examples
    test_examples = task["test"]
    solutions = train_solutions[task_id]
    
    all_correct = True
    for i, test_ex in enumerate(test_examples):
        test_input = np.array(test_ex["input"])
        expected_output = np.array(solutions[i])
        
        try:
            predicted = operator.apply(test_input, params)
            if not np.array_equal(predicted, expected_output):
                all_correct = False
                break
        except Exception:
            all_correct = False
            break
    
    if all_correct:
        solved_tasks.append(task_id)
        op_name = operator.name
        if op_name not in operator_counts:
            operator_counts[op_name] = []
        operator_counts[op_name].append(task_id)

print()
print("=" * 70)
print(f"✅ SOLVED: {len(solved_tasks)}/{len(train_challenges)} training tasks")
print()

if operator_counts:
    print("=" * 70)
    print("OPERATOR DISTRIBUTION")
    print("=" * 70)
    print()
    
    for op_name in sorted(operator_counts.keys(), key=lambda x: len(operator_counts[x]), reverse=True):
        tasks = operator_counts[op_name]
        print(f"{op_name}: {len(tasks)} tasks")
        for task_id in sorted(tasks):
            print(f"  - {task_id}")
        print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total solved: {len(solved_tasks)}/{len(train_challenges)} ({100*len(solved_tasks)/len(train_challenges):.2f}%)")
print(f"Operators used: {len(operator_counts)}")
