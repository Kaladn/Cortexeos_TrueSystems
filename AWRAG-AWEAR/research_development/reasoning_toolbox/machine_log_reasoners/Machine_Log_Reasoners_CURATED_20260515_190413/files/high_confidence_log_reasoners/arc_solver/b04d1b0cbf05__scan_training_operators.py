"""
Test the expanded 6-1-6 operator system (11 operators) on full ARC training set.
"""
import json
import numpy as np
from cod_616.arc_organ.arc_operators import infer_rule_for_task

# Load training data
with open("arc-prize-2024/arc-agi_training_challenges.json", "r") as f:
    train_challenges = json.load(f)

with open("arc-prize-2024/arc-agi_training_solutions.json", "r") as f:
    train_solutions = json.load(f)

print("=" * 70)
print("FULL TRAINING SET OPERATOR SCAN (11 OPERATORS)")
print("=" * 70)

solved_tasks = []
operator_counts = {}

for task_id in train_challenges.keys():
    task = train_challenges[task_id]
    train_pairs = [
        (np.array(ex["input"]), np.array(ex["output"]))
        for ex in task["train"]
    ]
    
    # Try to infer rule
    operator, params = infer_rule_for_task(train_pairs)
    
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
        solved_tasks.append({
            "task_id": task_id,
            "operator": operator.name,
            "params": params
        })
        
        # Count operator usage
        if operator.name not in operator_counts:
            operator_counts[operator.name] = 0
        operator_counts[operator.name] += 1

print(f"\n✅ SOLVED: {len(solved_tasks)}/400 training tasks\n")

# Group by operator
from collections import defaultdict
by_operator = defaultdict(list)
for result in solved_tasks:
    by_operator[result["operator"]].append(result["task_id"])

print("=" * 70)
print("OPERATOR DISTRIBUTION")
print("=" * 70)
for op_name in sorted(by_operator.keys(), key=lambda x: len(by_operator[x]), reverse=True):
    task_ids = by_operator[op_name]
    print(f"\n{op_name}: {len(task_ids)} tasks")
    for tid in task_ids:
        print(f"  - {tid}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total solved: {len(solved_tasks)}/400 ({100*len(solved_tasks)/400:.2f}%)")
print(f"Operators used: {len(operator_counts)}")
