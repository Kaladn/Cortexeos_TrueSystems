"""
OPERATOR PRIOR VALIDATION EXPERIMENT

Tests whether the CompuCog operator prior selector actually improves solve rate
compared to random operator testing.

Methodology:
1. Select 100 random unsolved tasks
2. For each task:
   - Extract 6F features
   - Get top-5 operators from prior selector
   - Test those 5 operators (PRIOR strategy)
   - Also test 5 random operators (BASELINE strategy)
3. Compare solve rates:
   - PRIOR vs BASELINE on same tasks
   - Measure speedup and accuracy improvement

This validates whether the 53-task memory actually helps.
"""
import json
import numpy as np
import random
from pathlib import Path
from collections import defaultdict
from cod_616.arc_organ.arc_operators import OPERATORS

print("="*80)
print("🧪 OPERATOR PRIOR VALIDATION EXPERIMENT")
print("="*80)
print()

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    all_data = json.load(f)

# Load pattern analysis (contains operator prior selector)
with open('compucog_616_pattern_analysis.json') as f:
    pattern_analysis = json.load(f)

# Load already solved tasks to exclude them
with open('compucog_616_master_ledger.json') as f:
    ledger = json.load(f)

solved_tasks = {fp['task_id'] for fp in ledger['fingerprints']}
unsolved_tasks = [tid for tid in all_data.keys() if tid not in solved_tasks]

print(f"Total tasks: {len(all_data)}")
print(f"Already solved: {len(solved_tasks)}")
print(f"Unsolved: {len(unsolved_tasks)}")
print()

# Sample 100 random unsolved tasks for experiment
random.seed(42)
experiment_tasks = random.sample(unsolved_tasks, min(100, len(unsolved_tasks)))
print(f"Selected {len(experiment_tasks)} tasks for experiment")
print()

# Build operator dict
op_dict = {op.name: op for op in OPERATORS}

# Extract prediction rules from pattern analysis
prediction_rules = pattern_analysis['prediction_rules']
operator_profiles = pattern_analysis['operator_profiles']

def extract_features_for_prior(task_data):
    """Extract features to query the operator prior."""
    inp = np.array(task_data['train'][0]['input'])
    out = np.array(task_data['train'][0]['output'])
    
    H_in, W_in = inp.shape
    H_out, W_out = out.shape
    
    # Determine size category
    if H_out > H_in or W_out > W_in:
        size_category = 'expands'
    elif H_out < H_in or W_out < W_in:
        size_category = 'shrinks'
    else:
        size_category = 'same_size'
    
    # Determine transform type
    if inp.shape == out.shape and np.array_equal((inp > 0), (out > 0)):
        transform_type = 'recoloring'
    elif inp.shape != out.shape:
        transform_type = 'size_transform'
    else:
        transform_type = 'spatial_rearrange'
    
    # Determine symmetry
    def is_symmetric(grid):
        H, W = grid.shape
        h_sym = np.array_equal(grid, np.fliplr(grid))
        v_sym = np.array_equal(grid, np.flipud(grid))
        return h_sym, v_sym
    
    h_in, v_in = is_symmetric(inp)
    h_out, v_out = is_symmetric(out)
    
    if h_out and not h_in:
        symmetry = 'H_symmetry_created'
    elif v_out and not v_in:
        symmetry = 'V_symmetry_created'
    elif h_in and h_out:
        symmetry = 'H_symmetry_preserved'
    elif v_in and v_out:
        symmetry = 'V_symmetry_preserved'
    else:
        symmetry = 'asymmetric'
    
    # Determine spatial structure
    if H_out > H_in or W_out > W_in:
        spatial_structure = 'expansion/tiling'
    elif H_out < H_in or W_out < W_in:
        spatial_structure = 'cropping/compression'
    else:
        spatial_structure = 'in-place_transform'
    
    return {
        'size_category': size_category,
        'transform_type': transform_type,
        'symmetry': symmetry,
        'spatial_structure': spatial_structure
    }

def rank_operators_with_prior(task_features):
    """Rank operators using the learned prior."""
    scores = defaultdict(float)
    
    # Score based on prediction rules
    for feature_key, feature_val in task_features.items():
        rule_key = f"{feature_key}:{feature_val}"
        if rule_key in prediction_rules:
            for op_name, count in prediction_rules[rule_key].items():
                scores[op_name] += count
    
    # Boost generalists
    for op_name in scores:
        if op_name in operator_profiles and operator_profiles[op_name]['role'] == 'GENERALIST':
            scores[op_name] *= 1.2
    
    # Return top operators
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [op_name for op_name, score in ranked]

def test_operator_on_task(task_data, operator):
    """Test if an operator solves all training examples."""
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

# Run experiment
print("="*80)
print("🔬 RUNNING EXPERIMENT")
print("="*80)
print()

results = {
    'prior_solves': [],
    'baseline_solves': [],
    'prior_operators_tested': [],
    'baseline_operators_tested': []
}

for task_idx, task_id in enumerate(experiment_tasks, 1):
    if task_idx % 10 == 0:
        print(f"Progress: {task_idx}/{len(experiment_tasks)} tasks tested")
    
    task_data = all_data[task_id]
    
    # Extract features
    features = extract_features_for_prior(task_data)
    
    # Get top-5 from prior
    ranked_ops = rank_operators_with_prior(features)
    top_5_prior = ranked_ops[:5] if len(ranked_ops) >= 5 else ranked_ops
    
    # Get 5 random operators for baseline
    all_op_names = list(op_dict.keys())
    top_5_random = random.sample(all_op_names, 5)
    
    # Test PRIOR strategy
    prior_solved = False
    for op_name in top_5_prior:
        if op_name not in op_dict:
            continue
        op = op_dict[op_name]
        if test_operator_on_task(task_data, op):
            prior_solved = True
            results['prior_solves'].append((task_id, op_name))
            print(f"  ✓ PRIOR solved {task_id} with {op_name}")
            break
    
    results['prior_operators_tested'].append(len(top_5_prior))
    
    # Test BASELINE strategy
    baseline_solved = False
    for op_name in top_5_random:
        op = op_dict[op_name]
        if test_operator_on_task(task_data, op):
            baseline_solved = True
            results['baseline_solves'].append((task_id, op_name))
            if not prior_solved:  # Only print if prior missed it
                print(f"  ○ BASELINE solved {task_id} with {op_name}")
            break
    
    results['baseline_operators_tested'].append(5)

print()
print("="*80)
print("📊 EXPERIMENT RESULTS")
print("="*80)
print()

# Calculate statistics
prior_solve_count = len(results['prior_solves'])
baseline_solve_count = len(results['baseline_solves'])
total_tasks = len(experiment_tasks)

prior_rate = prior_solve_count / total_tasks * 100
baseline_rate = baseline_solve_count / total_tasks * 100

print(f"Tasks tested: {total_tasks}")
print()
print(f"PRIOR STRATEGY (top-5 from learned prior):")
print(f"  Solved: {prior_solve_count}/{total_tasks} ({prior_rate:.1f}%)")
print()
print(f"BASELINE STRATEGY (5 random operators):")
print(f"  Solved: {baseline_solve_count}/{total_tasks} ({baseline_rate:.1f}%)")
print()

if prior_solve_count > baseline_solve_count:
    improvement = prior_solve_count - baseline_solve_count
    improvement_pct = (prior_rate - baseline_rate) / baseline_rate * 100 if baseline_rate > 0 else float('inf')
    print(f"🎯 PRIOR WINS!")
    print(f"  Additional tasks solved: {improvement}")
    print(f"  Relative improvement: {improvement_pct:.1f}%")
elif baseline_solve_count > prior_solve_count:
    print(f"⚠️  BASELINE WINS (prior needs improvement)")
    deficit = baseline_solve_count - prior_solve_count
    print(f"  Tasks missed by prior: {deficit}")
else:
    print(f"🤝 TIE (both strategies equivalent on this sample)")

print()
print("="*80)
print("🔍 DETAILED ANALYSIS")
print("="*80)
print()

# Which operators were most successful with prior?
if results['prior_solves']:
    prior_op_counts = defaultdict(int)
    for task_id, op_name in results['prior_solves']:
        prior_op_counts[op_name] += 1
    
    print("Top operators used by PRIOR strategy:")
    for op_name, count in sorted(prior_op_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"  {op_name}: {count} tasks")
    print()

# Which operators were most successful with baseline?
if results['baseline_solves']:
    baseline_op_counts = defaultdict(int)
    for task_id, op_name in results['baseline_solves']:
        baseline_op_counts[op_name] += 1
    
    print("Top operators used by BASELINE strategy:")
    for op_name, count in sorted(baseline_op_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"  {op_name}: {count} tasks")
    print()

# Find tasks solved by one but not the other
prior_task_ids = {tid for tid, _ in results['prior_solves']}
baseline_task_ids = {tid for tid, _ in results['baseline_solves']}

prior_exclusive = prior_task_ids - baseline_task_ids
baseline_exclusive = baseline_task_ids - prior_task_ids

if prior_exclusive:
    print(f"Tasks solved ONLY by PRIOR: {len(prior_exclusive)}")
    for tid in list(prior_exclusive)[:5]:
        op = [op for t, op in results['prior_solves'] if t == tid][0]
        print(f"  {tid} → {op}")
    print()

if baseline_exclusive:
    print(f"Tasks solved ONLY by BASELINE: {len(baseline_exclusive)}")
    for tid in list(baseline_exclusive)[:5]:
        op = [op for t, op in results['baseline_solves'] if t == tid][0]
        print(f"  {tid} → {op}")
    print()

# Save results
experiment_results = {
    'experiment_date': '2025-11-28',
    'total_tasks': total_tasks,
    'prior_strategy': {
        'solved': prior_solve_count,
        'rate': prior_rate,
        'solves': results['prior_solves']
    },
    'baseline_strategy': {
        'solved': baseline_solve_count,
        'rate': baseline_rate,
        'solves': results['baseline_solves']
    },
    'comparison': {
        'prior_exclusive': list(prior_exclusive),
        'baseline_exclusive': list(baseline_exclusive),
        'both': list(prior_task_ids & baseline_task_ids)
    }
}

with open('operator_prior_validation_results.json', 'w') as f:
    json.dump(experiment_results, f, indent=2)

print("="*80)
print("✅ EXPERIMENT COMPLETE")
print("="*80)
print()
print("Results saved to: operator_prior_validation_results.json")
print()

if prior_solve_count > baseline_solve_count:
    print("🎉 CONCLUSION: The CompuCog operator prior IMPROVES solve rate!")
    print("   The 53-task memory is actively helping find solutions faster.")
elif prior_solve_count == baseline_solve_count and prior_solve_count > 0:
    print("✅ CONCLUSION: The prior matches baseline efficiency.")
    print("   The memory provides structured guidance without losing coverage.")
else:
    print("📈 CONCLUSION: The prior needs refinement.")
    print("   Current features may not capture all relevant patterns.")
    print("   Next: Analyze baseline_exclusive tasks to improve feature extraction.")
