"""
MATH DSL SOLVER - Fresh Run on ARC 2025

Uses the complete mathematical DSL ruleset to solve tasks.
Applies all 57 mathematically formalized operators.
"""
import json
import numpy as np
from pathlib import Path
from cod_616.arc_organ.arc_operators import OPERATORS
import time

print("="*80)
print("🔬 MATH DSL SOLVER - ARC 2025 FRESH RUN")
print("="*80)
print()

# Load mathematical DSL rules
print("Loading mathematical DSL ruleset...")
math_rules = []
with open('arc_transformation_rules_math_dsl.jsonl', 'r') as f:
    for line in f:
        math_rules.append(json.loads(line))

print(f"✅ Loaded {len(math_rules)} mathematical rules")
print()

# Load ARC 2025 data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    training_data = json.load(f)

print(f"📊 ARC 2025 Training Set: {len(training_data)} tasks")
print()

# Build operator dictionary
op_dict = {op.name: op for op in OPERATORS}

print(f"🔧 Available operators: {len(op_dict)}")
print()

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

def apply_operator_to_test(task_data, operator):
    """Apply operator to test inputs using params from training."""
    try:
        # Get params from first training example
        inp = np.array(task_data['train'][0]['input'])
        out = np.array(task_data['train'][0]['output'])
        
        params = operator.analyze(inp, out)
        if params is None:
            return None
        
        # Apply to all test inputs
        predictions = []
        for test_case in task_data['test']:
            test_inp = np.array(test_case['input'])
            pred = operator.apply(test_inp, params)
            predictions.append(pred.tolist())
        
        return predictions
    except:
        return None

# Priority order based on mathematical coverage
operator_priority = [
    'position_based_recolor',
    'recolor_mapping',
    'block_expansion',
    'self_masking_tiling',
    'symmetry_completion',
    'mirror',
    'tiling_expand',
    'color_histogram_fill',
    'center_repulsion',
    'diagonal_reflection',
    'swap_mapping',
    'hollow_frame_extraction',
    'crop_to_bbox',
    'tiling',
    'extend_by_pattern',
    'extract_unique_shape',
    'noiseless_repeat',
    'extend_to_symmetry',
]

# Add remaining operators
for op_name in op_dict.keys():
    if op_name not in operator_priority:
        operator_priority.append(op_name)

print("="*80)
print("🚀 SOLVING ARC 2025 TASKS")
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
        print(f"Progress: {task_idx+1}/{len(training_data)} tasks | {solve_count} solved | {remaining:.0f}s remaining")
    
    # Try operators in priority order
    for op_name in operator_priority:
        if op_name not in op_dict:
            continue
        
        operator = op_dict[op_name]
        
        # Test if operator solves training examples
        if test_operator_on_task(task_data, operator):
            # Apply to test cases
            predictions = apply_operator_to_test(task_data, operator)
            
            if predictions is not None:
                solutions[task_id] = {
                    'operator': op_name,
                    'predictions': predictions
                }
                solve_count += 1
                print(f"✓ {task_id} → {op_name}")
                break

elapsed = time.time() - start_time

print()
print("="*80)
print("📊 SOLVE RESULTS")
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
    print(f"  {op}: {count}")
print()

# Save solutions
output_file = 'math_dsl_solutions_2025.json'
with open(output_file, 'w') as f:
    json.dump(solutions, f, indent=2)

print(f"💾 Solutions saved to: {output_file}")
print()

# Generate submission format
submission = {}
for task_id, sol in solutions.items():
    # Format: each test case gets 2 attempts (we only have 1 prediction)
    attempts = []
    for pred in sol['predictions']:
        attempts.append({
            'attempt_1': pred,
            'attempt_2': pred  # Same prediction twice
        })
    submission[task_id] = attempts

submission_file = 'submission_math_dsl_2025.json'
with open(submission_file, 'w') as f:
    json.dump(submission, f, indent=2)

print(f"📤 Submission format saved to: {submission_file}")
print()

# Detailed analysis
print("="*80)
print("🔍 DETAILED ANALYSIS")
print("="*80)
print()

# Categorize by math DSL category
category_solves = {}
for task_id, sol in solutions.items():
    op_name = sol['operator']
    # Find category from math rules
    matching_rules = [r for r in math_rules if op_name in r['operators']]
    if matching_rules:
        category = matching_rules[0]['math_dsl']['category']
        category_solves[category] = category_solves.get(category, 0) + 1

print("Solves by mathematical category:")
for cat, count in sorted(category_solves.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")
print()

# Compare to baseline
print("Comparison to previous results:")
print(f"  Previous solve count: 53 (from get_all_solved_tasks.py)")
print(f"  Current solve count: {solve_count}")
if solve_count > 53:
    print(f"  ✨ Improvement: +{solve_count - 53} tasks!")
elif solve_count == 53:
    print(f"  ✓ Consistent with previous results")
else:
    print(f"  ⚠️  {53 - solve_count} fewer solves (check operator implementations)")
print()

print("="*80)
print("✅ MATH DSL SOLVER COMPLETE")
print("="*80)
print()
print("Next steps:")
print("  1. Analyze unsolved tasks for patterns")
print("  2. Design new operators for uncovered patterns")
print("  3. Expand mathematical DSL with new operators")
print("  4. Iterate to improve coverage")
