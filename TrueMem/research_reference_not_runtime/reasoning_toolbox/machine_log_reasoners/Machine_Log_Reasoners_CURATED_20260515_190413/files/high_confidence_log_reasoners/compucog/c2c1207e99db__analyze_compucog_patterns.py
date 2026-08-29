"""
COMPUCOG PATTERN CLUSTERING & OPERATOR PROFILING

Analyzes the 53-task master ledger to extract:
1. Per-operator usage profiles (what structural patterns trigger each operator)
2. Feature→Operator correlation matrix
3. Composition prediction rules
4. Procedure-mixing patterns across solved tasks

This transforms the ledger from a static record into an ACTIVE REASONING PRIOR.
"""
import json
import numpy as np
from collections import defaultdict
from pathlib import Path

print("="*80)
print("🧬 COMPUCOG PATTERN CLUSTERING ANALYSIS")
print("="*80)
print()

# Load the master ledger
with open('compucog_616_master_ledger.json') as f:
    ledger = json.load(f)

fingerprints = ledger['fingerprints']
print(f"Loaded {len(fingerprints)} task fingerprints")
print()

# ============================================================================
# STEP 1: BUILD PER-OPERATOR PROFILES
# ============================================================================
print("="*80)
print("📊 STEP 1: OPERATOR PROFILE CARDS")
print("="*80)
print()

operator_profiles = defaultdict(lambda: {
    'tasks_solved': [],
    'grid_sizes': [],
    'transform_types': [],
    'anchors': [],
    'color_counts': [],
    'symmetries': [],
    'spatial_structures': []
})

for fp in fingerprints:
    op = fp['operator']
    operator_profiles[op]['tasks_solved'].append(fp['task_id'])
    operator_profiles[op]['grid_sizes'].append(fp['features_6f']['F1_grid_transform'])
    operator_profiles[op]['transform_types'].append(fp['features_6f']['F6_transformation_type'])
    operator_profiles[op]['anchors'].append(fp['anchor_1a'])
    operator_profiles[op]['color_counts'].append(fp['features_6f']['F2_color_palette'])
    operator_profiles[op]['symmetries'].append(fp['features_6f']['F4_symmetry'])
    operator_profiles[op]['spatial_structures'].append(fp['features_6f']['F5_spatial_structure'])

def classify_operator_role(op_name, transform_dist, spatial_dist, task_count):
    """Classify operator as GENERALIST, SPECIALIST, or TRANSFORMER."""
    if task_count >= 10:
        return "GENERALIST"
    elif 'recolor' in str(transform_dist) and transform_dist.get('recoloring', 0) > task_count * 0.5:
        return "COLOR_SPECIALIST"
    elif 'size_transform' in transform_dist and transform_dist.get('size_transform', 0) > task_count * 0.5:
        return "SPATIAL_TRANSFORMER"
    else:
        return "PATTERN_SPECIALIST"

# Generate profile cards
profile_cards = {}
for op, data in operator_profiles.items():
    # Count transform types
    transform_dist = {}
    for t in data['transform_types']:
        transform_dist[t] = transform_dist.get(t, 0) + 1
    
    # Count spatial structures
    spatial_dist = {}
    for s in data['spatial_structures']:
        spatial_dist[s] = spatial_dist.get(s, 0) + 1
    
    # Count anchor types
    anchor_dist = {}
    for a in data['anchors']:
        anchor_dist[a] = anchor_dist.get(a, 0) + 1
    
    profile_cards[op] = {
        'task_count': len(data['tasks_solved']),
        'tasks': data['tasks_solved'],
        'typical_transform': max(transform_dist.items(), key=lambda x: x[1])[0],
        'transform_distribution': transform_dist,
        'typical_spatial': max(spatial_dist.items(), key=lambda x: x[1])[0],
        'spatial_distribution': spatial_dist,
        'anchor_patterns': anchor_dist,
        'role': classify_operator_role(op, transform_dist, spatial_dist, len(data['tasks_solved']))
    }

# Print profile cards
for op in sorted(profile_cards.keys(), key=lambda x: -profile_cards[x]['task_count']):
    card = profile_cards[op]
    print(f"🔧 {op}")
    print(f"   Role: {card['role']}")
    print(f"   Tasks: {card['task_count']}")
    print(f"   Primary transform: {card['typical_transform']}")
    print(f"   Primary spatial: {card['typical_spatial']}")
    print(f"   Transform breakdown: {card['transform_distribution']}")
    print()

# ============================================================================
# STEP 2: FEATURE → OPERATOR CORRELATION MATRIX
# ============================================================================
print("="*80)
print("🎯 STEP 2: FEATURE → OPERATOR PREDICTION RULES")
print("="*80)
print()

# Build correlation rules
def extract_feature_signature(fp):
    """Extract key features for matching."""
    f = fp['features_6f']
    
    # Parse grid transform
    grid_parts = f['F1_grid_transform'].split(' → ')
    same_size = (grid_parts[0] == grid_parts[1])
    
    # Check if expansion
    if 'expansion' in f['F5_spatial_structure'] or 'tiling' in f['F5_spatial_structure']:
        size_category = 'expands'
    elif 'crop' in f['F5_spatial_structure'] or 'compression' in f['F5_spatial_structure']:
        size_category = 'shrinks'
    else:
        size_category = 'same_size'
    
    return {
        'size_category': size_category,
        'transform_type': f['F6_transformation_type'],
        'symmetry': f['F4_symmetry'],
        'spatial_structure': f['F5_spatial_structure']
    }

# Group tasks by feature signatures
feature_to_operators = defaultdict(lambda: defaultdict(int))

for fp in fingerprints:
    sig = extract_feature_signature(fp)
    op = fp['operator']
    
    # Record correlations
    feature_to_operators[f"size:{sig['size_category']}"][op] += 1
    feature_to_operators[f"transform:{sig['transform_type']}"][op] += 1
    feature_to_operators[f"symmetry:{sig['symmetry']}"][op] += 1
    feature_to_operators[f"spatial:{sig['spatial_structure']}"][op] += 1

# Generate prediction rules
print("📋 PREDICTION RULES (Feature → Top Operators):")
print()

prediction_rules = {}
for feature, op_counts in sorted(feature_to_operators.items()):
    top_ops = sorted(op_counts.items(), key=lambda x: -x[1])[:3]
    prediction_rules[feature] = top_ops
    print(f"  {feature:40s} → {', '.join([f'{op}({cnt})' for op, cnt in top_ops])}")

print()

# ============================================================================
# STEP 3: META-PATTERNS ACROSS SOLVED TASKS
# ============================================================================
print("="*80)
print("🔍 STEP 3: META-PATTERNS ACROSS 53 SOLVED TASKS")
print("="*80)
print()

# Compute global statistics
transform_types = [fp['features_6f']['F6_transformation_type'] for fp in fingerprints]
spatial_structures = [fp['features_6f']['F5_spatial_structure'] for fp in fingerprints]
symmetries = [fp['features_6f']['F4_symmetry'] for fp in fingerprints]

from collections import Counter

print("🎨 Transform Type Distribution:")
for t, count in Counter(transform_types).most_common():
    pct = count / len(fingerprints) * 100
    print(f"  {t:25s} {count:3d} tasks ({pct:5.1f}%)")
print()

print("📐 Spatial Structure Distribution:")
for s, count in Counter(spatial_structures).most_common():
    pct = count / len(fingerprints) * 100
    print(f"  {s:25s} {count:3d} tasks ({pct:5.1f}%)")
print()

print("🔄 Symmetry Pattern Distribution:")
for sym, count in Counter(symmetries).most_common():
    pct = count / len(fingerprints) * 100
    print(f"  {sym:25s} {count:3d} tasks ({pct:5.1f}%)")
print()

# ============================================================================
# STEP 4: COMPOSITION PREDICTION RULES
# ============================================================================
print("="*80)
print("🔗 STEP 4: OPERATOR COMPOSITION PATTERNS")
print("="*80)
print()

# Analyze which operators work well as FIRST vs LAST in chains
print("Based on operator roles and transform types:")
print()

good_first_ops = []
good_last_ops = []
good_middle_ops = []

for op, card in profile_cards.items():
    # Operators that prepare/transform space → good FIRST
    if card['role'] in ['SPATIAL_TRANSFORMER', 'PATTERN_SPECIALIST']:
        if 'size_transform' in card['transform_distribution']:
            good_first_ops.append(op)
    
    # Operators that finalize/recolor → good LAST
    if card['role'] in ['COLOR_SPECIALIST', 'GENERALIST']:
        if 'recoloring' in card['transform_distribution']:
            good_last_ops.append(op)
    
    # Generalists can go anywhere
    if card['role'] == 'GENERALIST':
        good_middle_ops.append(op)

print("🥇 GOOD FIRST OPERATORS (space preparation):")
for op in good_first_ops:
    print(f"   - {op}")
print()

print("🥈 GOOD MIDDLE OPERATORS (transform refinement):")
for op in good_middle_ops:
    print(f"   - {op}")
print()

print("🥉 GOOD LAST OPERATORS (finalization):")
for op in good_last_ops:
    print(f"   - {op}")
print()

# Suggest promising compositions
print("💡 SUGGESTED 2-STEP COMPOSITIONS TO TEST:")
print()
suggested_compositions = []
for first in good_first_ops[:3]:
    for last in good_last_ops[:3]:
        suggested_compositions.append((first, last))
        print(f"   {first} → {last}")
print()

# ============================================================================
# STEP 5: SAVE ENRICHED ANALYSIS
# ============================================================================
print("="*80)
print("💾 SAVING PATTERN ANALYSIS")
print("="*80)
print()

analysis_output = {
    'operator_profiles': profile_cards,
    'prediction_rules': {k: dict(v) for k, v in prediction_rules.items()},
    'meta_patterns': {
        'transform_types': dict(Counter(transform_types)),
        'spatial_structures': dict(Counter(spatial_structures)),
        'symmetries': dict(Counter(symmetries))
    },
    'composition_recommendations': {
        'good_first': good_first_ops,
        'good_middle': good_middle_ops,
        'good_last': good_last_ops,
        'suggested_pairs': suggested_compositions
    }
}

with open('compucog_616_pattern_analysis.json', 'w') as f:
    json.dump(analysis_output, f, indent=2)

print("✅ Pattern analysis saved to: compucog_616_pattern_analysis.json")
print()

# ============================================================================
# STEP 6: OPERATOR PRIOR SELECTOR (PROOF OF CONCEPT)
# ============================================================================
print("="*80)
print("🎯 STEP 6: OPERATOR PRIOR SELECTOR (DEMO)")
print("="*80)
print()

def rank_operators_for_task(task_features):
    """
    Given task features, rank operators by likelihood.
    This is the ACTIVE REASONING PRIOR in action.
    """
    scores = defaultdict(float)
    
    # Check each feature against prediction rules
    for feature_key, feature_val in task_features.items():
        rule_key = f"{feature_key}:{feature_val}"
        if rule_key in prediction_rules:
            for op, count in prediction_rules[rule_key]:
                scores[op] += count
    
    # Boost generalists slightly (they solve more diverse tasks)
    for op in scores:
        if profile_cards[op]['role'] == 'GENERALIST':
            scores[op] *= 1.2
    
    # Return sorted list
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return ranked

# Demo: rank operators for a hypothetical task
print("📊 DEMO: Ranking operators for a hypothetical task:")
print()

demo_task = {
    'size_category': 'same_size',
    'transform_type': 'recoloring',
    'symmetry': 'asymmetric',
    'spatial_structure': 'in-place_transform'
}

print("Task features:")
for k, v in demo_task.items():
    print(f"  {k}: {v}")
print()

ranked_ops = rank_operators_for_task(demo_task)
print("🎯 Recommended operators (ranked by fit):")
for i, (op, score) in enumerate(ranked_ops[:10], 1):
    role = profile_cards[op]['role']
    print(f"  {i:2d}. {op:30s} (score: {score:5.1f}, role: {role})")
print()

print("="*80)
print("✅ PATTERN CLUSTERING COMPLETE")
print("="*80)
print()
print("Your ARC system now has:")
print("  1. Operator profile cards (what each op typically does)")
print("  2. Feature→Operator prediction rules (structural priors)")
print("  3. Meta-pattern statistics (global trends)")
print("  4. Composition recommendations (which ops chain well)")
print("  5. Active operator prior selector (ranks ops for new tasks)")
print()
print("Next: Test this prior on unsolved tasks to see if it beats random search.")
