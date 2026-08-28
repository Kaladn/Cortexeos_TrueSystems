"""
INTELLIGENT OPERATOR PRIOR TEST

Instead of random tasks, find tasks that are STRUCTURALLY SIMILAR
to the 53 we already solved, then test if the prior helps there.

Strategy:
1. Compute structural similarity between unsolved tasks and solved tasks
2. Select the top 50 most similar unsolved tasks
3. Test prior vs baseline on those
4. This validates: "Does memory help on SIMILAR tasks?"
"""
import json
import numpy as np
import random
from pathlib import Path
from collections import defaultdict
from cod_616.arc_organ.arc_operators import OPERATORS

print("="*80)
print("🧠 INTELLIGENT OPERATOR PRIOR TEST")
print("="*80)
print()

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    all_data = json.load(f)

with open('compucog_616_master_ledger.json') as f:
    ledger = json.load(f)

with open('compucog_616_pattern_analysis.json') as f:
    pattern_analysis = json.load(f)

solved_tasks = {fp['task_id']: fp for fp in ledger['fingerprints']}
unsolved_task_ids = [tid for tid in all_data.keys() if tid not in solved_tasks]

print(f"Solved tasks: {len(solved_tasks)}")
print(f"Unsolved tasks: {len(unsolved_task_ids)}")
print()

# Build operator dict
op_dict = {op.name: op for op in OPERATORS}
prediction_rules = pattern_analysis['prediction_rules']
operator_profiles = pattern_analysis['operator_profiles']

def extract_features(task_data):
    """Extract structural features from a task."""
    inp = np.array(task_data['train'][0]['input'])
    out = np.array(task_data['train'][0]['output'])
    
    H_in, W_in = inp.shape
    H_out, W_out = out.shape
    
    colors_in = len(set(inp.flatten()) - {0})
    colors_out = len(set(out.flatten()) - {0})
    
    # Size change
    if H_out > H_in or W_out > W_in:
        size_cat = 'expands'
    elif H_out < H_in or W_out < W_in:
        size_cat = 'shrinks'
    else:
        size_cat = 'same_size'
    
    # Transform type
    if inp.shape == out.shape and np.array_equal((inp > 0), (out > 0)):
        transform = 'recoloring'
    elif inp.shape != out.shape:
        transform = 'size_transform'
    else:
        transform = 'spatial_rearrange'
    
    return {
        'grid_in': (H_in, W_in),
        'grid_out': (H_out, W_out),
        'colors_in': colors_in,
        'colors_out': colors_out,
        'size_category': size_cat,
        'transform_type': transform
    }

def compute_similarity(feat1, feat2):
    """Compute structural similarity score between two tasks."""
    score = 0.0
    
    # Same size category is very important
    if feat1['size_category'] == feat2['size_category']:
        score += 5.0
    
    # Same transform type
    if feat1['transform_type'] == feat2['transform_type']:
        score += 3.0
    
    # Similar color counts
    color_diff = abs(feat1['colors_in'] - feat2['colors_in'])
    score += max(0, 2.0 - color_diff * 0.5)
    
    # Similar grid sizes
    h_diff_in = abs(feat1['grid_in'][0] - feat2['grid_in'][0])
    w_diff_in = abs(feat1['grid_in'][1] - feat2['grid_in'][1])
    size_penalty = (h_diff_in + w_diff_in) * 0.1
    score -= size_penalty
    
    return max(0, score)

print("Computing structural similarity to solved tasks...")
print()

# For each unsolved task, find its similarity to solved tasks
task_similarities = []
for unsolved_id in unsolved_task_ids:
    unsolved_feat = extract_features(all_data[unsolved_id])
    
    # Find best match among solved tasks
    best_similarity = 0
    best_match = None
    for solved_id, solved_fp in solved_tasks.items():
        solved_task = all_data[solved_id]
        solved_feat = extract_features(solved_task)
        
        sim = compute_similarity(unsolved_feat, solved_feat)
        if sim > best_similarity:
            best_similarity = sim
            best_match = solved_id
    
    task_similarities.append((unsolved_id, best_similarity, best_match))

# Sort by similarity and take top 50
task_similarities.sort(key=lambda x: -x[1])
top_similar_tasks = task_similarities[:50]

print(f"Top 50 most similar unsolved tasks:")
for i, (task_id, sim, match) in enumerate(top_similar_tasks[:10], 1):
    match_op = solved_tasks[match]['operator']
    print(f"  {i:2d}. {task_id} (sim={sim:.2f}, like {match} → {match_op})")
print(f"  ... and 40 more")
print()

# Now test prior vs baseline on these similar tasks
def rank_operators_with_prior(task_features):
    """Rank operators using the learned prior."""
    scores = defaultdict(float)
    
    for feature_key, feature_val in task_features.items():
        rule_key = f"{feature_key}:{feature_val}"
        if rule_key in prediction_rules:
            for op_name, count in prediction_rules[rule_key].items():
                scores[op_name] += count
    
    for op_name in scores:
        if op_name in operator_profiles and operator_profiles[op_name]['role'] == 'GENERALIST':
            scores[op_name] *= 1.2
    
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [op_name for op_name, score in ranked]

def test_operator_on_task(task_data, operator):
    """Test if operator solves task."""
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

print("="*80)
print("🔬 TESTING ON STRUCTURALLY SIMILAR TASKS")
print("="*80)
print()

prior_solves = []
baseline_solves = []

for task_id, sim_score, matched_solved_id in top_similar_tasks:
    task_data = all_data[task_id]
    features = extract_features(task_data)
    
    # Strategy 1: PRIOR (use learned ranking)
    ranked_ops = rank_operators_with_prior(features)
    top_5_prior = ranked_ops[:5] if len(ranked_ops) >= 5 else ranked_ops
    
    # Strategy 2: BASELINE (use operator from matched solved task)
    matched_op_name = solved_tasks[matched_solved_id]['operator']
    
    # Test PRIOR
    prior_solved = False
    for op_name in top_5_prior:
        if op_name not in op_dict:
            continue
        op = op_dict[op_name]
        if test_operator_on_task(task_data, op):
            prior_solved = True
            prior_solves.append((task_id, op_name))
            print(f"  ✓ PRIOR: {task_id} with {op_name} (similar to {matched_solved_id})")
            break
    
    # Test BASELINE (just try the operator that worked on similar task)
    if matched_op_name in op_dict:
        op = op_dict[matched_op_name]
        if test_operator_on_task(task_data, op):
            baseline_solves.append((task_id, matched_op_name))
            if not prior_solved:
                print(f"  ○ BASELINE: {task_id} with {matched_op_name} (copied from {matched_solved_id})")

print()
print("="*80)
print("📊 RESULTS ON SIMILAR TASKS")
print("="*80)
print()

prior_count = len(prior_solves)
baseline_count = len(baseline_solves)
total = len(top_similar_tasks)

print(f"Tasks tested: {total} (structurally similar to solved tasks)")
print()
print(f"PRIOR STRATEGY (top-5 from prior):")
print(f"  Solved: {prior_count}/{total} ({prior_count/total*100:.1f}%)")
print()
print(f"BASELINE STRATEGY (copy operator from matched task):")
print(f"  Solved: {baseline_count}/{total} ({baseline_count/total*100:.1f}%)")
print()

if prior_count > 0 or baseline_count > 0:
    print("🎯 KEY INSIGHT:")
    if prior_count > baseline_count:
        print("  Prior outperforms simple operator copying!")
        print("  The pattern analysis generalizes beyond exact operator matching.")
    elif baseline_count > prior_count:
        print("  Direct operator matching works better than prior.")
        print("  Consider: similarity-based operator selection as primary strategy.")
    else:
        print("  Both strategies perform similarly.")
        print("  The operators we have DO generalize to similar structural patterns.")
    print()
    
    # Show which operators worked
    if prior_solves:
        op_counts = defaultdict(int)
        for _, op in prior_solves:
            op_counts[op] += 1
        print("Operators that succeeded on similar tasks:")
        for op, cnt in sorted(op_counts.items(), key=lambda x: -x[1]):
            print(f"  {op}: {cnt}")
else:
    print("⚠️  NO SOLVES on structurally similar tasks")
    print()
    print("This suggests:")
    print("  1. Structural similarity ≠ same operator applicability")
    print("  2. Need deeper semantic features (not just grid size/colors)")
    print("  3. The 53 solved tasks may represent narrow operator domains")
    print()
    print("Next step: Analyze WHAT makes the 53 solvable vs the rest")

# Save analysis
results = {
    'strategy': 'similarity_based_testing',
    'tested_tasks': total,
    'prior_solves': prior_count,
    'baseline_solves': baseline_count,
    'prior_details': prior_solves,
    'baseline_details': baseline_solves,
    'task_similarities': [(tid, float(sim), match) for tid, sim, match in top_similar_tasks]
}

with open('similarity_based_validation.json', 'w') as f:
    json.dump(results, f, indent=2)

print()
print("Results saved to: similarity_based_validation.json")
