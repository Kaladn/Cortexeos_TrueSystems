"""
Full Scan with New Operators

Test all 1000 tasks with expanded operator library (29 operators).
"""
import json
import numpy as np
from pathlib import Path
from cod_616.arc_organ.arc_operators import OPERATORS
import time

print("="*80)
print("FULL SCAN WITH 29 OPERATORS")
print("="*80)
print()

# Load ARC 2025 data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    training_data = json.load(f)

print(f"Dataset: {len(training_data)} tasks")
print(f"Operators: {len(OPERATORS)}")
print()

# Build operator dictionary
op_dict = {op.name: op for op in OPERATORS}

def test_operator_on_task(task_data, operator):
    """Test if operator solves all training examples."""
    try:
        for example in task_data['train']:
            inp = np.array(example['input'])
            expected = np.array(example['output'])
            
            params = operator.analyze(inp, expected)
            if params is None:
                return False
            
            result = operator.apply(inp, params)
            if not np.array_equal(result, expected):
                return False
        return True
    except:
        return False

# Priority order
operator_priority = list(op_dict.keys())

print("="*80)
print("SOLVING ALL TASKS")
print("="*80)
print()

solutions = {}
solve_count = 0
start_time = time.time()

for task_idx, (task_id, task_data) in enumerate(sorted(training_data.items())):
    if (task_idx + 1) % 100 == 0:
        elapsed = time.time() - start_time
        rate = (task_idx + 1) / elapsed
        remaining = (len(training_data) - task_idx - 1) / rate
        print(f"Progress: {task_idx+1}/{len(training_data)} | {solve_count} solved | {remaining:.0f}s remaining")
    
    # Try operators in priority order
    for op_name in operator_priority:
        operator = op_dict[op_name]
        
        if test_operator_on_task(task_data, operator):
            solutions[task_id] = {
                'operator': op_name
            }
            solve_count += 1
            if solve_count <= 60:  # Print first 60 to see new ones
                print(f"  ✓ {task_id} → {op_name}")
            break

elapsed = time.time() - start_time

print()
print("="*80)
print("FINAL RESULTS")
print("="*80)
print()
print(f"Total tasks: {len(training_data)}")
print(f"Solved: {solve_count}")
print(f"Solve rate: {solve_count/len(training_data)*100:.2f}%")
print(f"Time elapsed: {elapsed:.1f}s")
print()

# Operator usage statistics
op_counts = {}
for sol in solutions.values():
    op = sol['operator']
    op_counts[op] = op_counts.get(op, 0) + 1

print("Solutions by operator:")
for op, count in sorted(op_counts.items(), key=lambda x: -x[1]):
    is_new = "🆕" if op in ['enclosed_region_fill', 'checkerboard_tiling_alternating', 
                             'symmetry_from_fragment', 'shape_reference_recolor', 
                             'pattern_completion_prototype'] else ""
    print(f"  {op}: {count} {is_new}")
print()

# Check improvement
baseline = 53
improvement = solve_count - baseline

print("="*80)
print("COVERAGE ANALYSIS")
print("="*80)
print()
print(f"Baseline (17 operators): 53/1000 (5.3%)")
print(f"Current (29 operators):  {solve_count}/1000 ({solve_count/10:.1f}%)")
if improvement > 0:
    print(f"✨ Improvement: +{improvement} tasks ({improvement/baseline*100:.1f}% increase)")
elif improvement == 0:
    print(f"→ No change (new operators didn't match additional tasks)")
else:
    print(f"⚠️ Regression: {improvement} tasks (check operator priority)")

# Save solutions
output_file = 'solutions_with_new_operators.json'
with open(output_file, 'w') as f:
    json.dump(solutions, f, indent=2)

print()
print(f"💾 Solutions saved to: {output_file}")
