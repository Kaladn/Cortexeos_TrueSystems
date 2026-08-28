"""Extract all solved task IDs from single operators and compositions."""
import sys
sys.path.insert(0, 'cod_616')

import json
import numpy as np
from pathlib import Path
from cod_616.arc_organ.arc_operators import OPERATORS

def load_data():
    with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
        return json.load(f)

def test_single_operator(task, operator):
    """Test if single operator solves all examples."""
    for example in task['train']:
        inp = np.array(example['input'])
        expected = np.array(example['output'])
        
        params = operator.analyze(inp, expected)
        if params is None:
            return False
        
        result = operator.apply(inp, params)
        if not np.array_equal(result, expected):
            return False
    
    return True

print("="*80)
print("SCANNING ALL 1000 TASKS FOR SOLVED STATUS")
print("="*80)
print()

data = load_data()
single_operator_solves = {}
operator_usage_count = {op.name: 0 for op in OPERATORS}

print("Testing single operators on all 1000 tasks...")
print()

for task_id, task in sorted(data.items()):
    for operator in OPERATORS:
        try:
            if test_single_operator(task, operator):
                single_operator_solves[task_id] = operator.name
                operator_usage_count[operator.name] += 1
                print(f"✓ {task_id} → {operator.name}")
                break
        except Exception:
            continue

print()
print("="*80)
print("SINGLE OPERATOR RESULTS")
print("="*80)
print(f"Solved: {len(single_operator_solves)}/1000 ({len(single_operator_solves)/10:.1f}%)")
print()
print("Solved task IDs:")
for task_id in sorted(single_operator_solves.keys()):
    print(f"  {task_id} → {single_operator_solves[task_id]}")

print()
print("="*80)
print("OPERATOR USAGE STATISTICS")
print("="*80)
for op_name, count in sorted(operator_usage_count.items(), key=lambda x: -x[1]):
    if count > 0:
        print(f"  {op_name}: {count} tasks")

# Now load multi-step results
print()
print("="*80)
print("MULTI-STEP COMPOSITION RESULTS")
print("="*80)

multi_step_file = Path('multi_step_solutions.json')
if multi_step_file.exists():
    with open(multi_step_file) as f:
        multi_step = json.load(f)
    print(f"Additional tasks solved by composition: {len(multi_step)}")
    print()
    for task_id, ops in sorted(multi_step.items()):
        print(f"  {task_id} → {' → '.join(ops)}")
else:
    print("No multi-step solutions file found.")
    print("(Run find_multi_step_tasks.py to generate)")

print()
print("="*80)
print("TOTAL SUMMARY")
print("="*80)
total = len(single_operator_solves)
if multi_step_file.exists():
    total += len(multi_step)
print(f"Total solved: {total}/1000 ({total/10:.1f}%)")
print(f"  Single operators: {len(single_operator_solves)}")
if multi_step_file.exists():
    print(f"  Multi-step: {len(multi_step)}")
