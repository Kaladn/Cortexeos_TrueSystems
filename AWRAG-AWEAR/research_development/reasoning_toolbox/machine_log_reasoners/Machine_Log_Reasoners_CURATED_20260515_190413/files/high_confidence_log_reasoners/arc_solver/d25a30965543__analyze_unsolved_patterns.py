"""
ANALYZE UNSOLVED TASKS - Pattern Discovery

Examines the 947 unsolved tasks to identify:
1. Common visual patterns
2. Transformation types not covered by current operators
3. Potential new operator candidates
"""
import json
import numpy as np
from scipy import ndimage
from collections import Counter

print("="*80)
print("🔍 ANALYZING UNSOLVED TASKS FOR NEW PATTERNS")
print("="*80)
print()

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    all_data = json.load(f)

with open('math_dsl_solutions_2025.json') as f:
    solved = json.load(f)

unsolved_ids = [tid for tid in all_data.keys() if tid not in solved]
print(f"Total tasks: {len(all_data)}")
print(f"Solved: {len(solved)}")
print(f"Unsolved: {len(unsolved_ids)}")
print()

def analyze_task_features(task_data):
    """Extract comprehensive features from a task."""
    features = {
        'grid_transforms': set(),
        'color_changes': set(),
        'spatial_patterns': set(),
        'structural_features': set()
    }
    
    for example in task_data['train']:
        inp = np.array(example['input'])
        out = np.array(example['output'])
        
        h_in, w_in = inp.shape
        h_out, w_out = out.shape
        
        # Grid transform
        if (h_out, w_out) == (h_in, w_in):
            features['grid_transforms'].add('same_size')
        elif h_out > h_in or w_out > w_in:
            features['grid_transforms'].add('expansion')
        else:
            features['grid_transforms'].add('contraction')
        
        # Color analysis
        colors_in = set(inp.flatten()) - {0}
        colors_out = set(out.flatten()) - {0}
        
        if colors_out == colors_in:
            features['color_changes'].add('preserved')
        elif colors_out < colors_in:
            features['color_changes'].add('reduced')
        elif colors_out > colors_in:
            features['color_changes'].add('introduced')
        
        # Spatial patterns
        if h_out == h_in and w_out == w_in:
            # Check if it's pure recoloring
            if np.array_equal((inp > 0), (out > 0)):
                features['spatial_patterns'].add('pure_recolor')
            else:
                features['spatial_patterns'].add('spatial_rearrange')
        
        # Check for shapes
        nonzero_in = (inp > 0).astype(int)
        labeled_in, num_in = ndimage.label(nonzero_in)
        
        nonzero_out = (out > 0).astype(int)
        labeled_out, num_out = ndimage.label(nonzero_out)
        
        if num_in > 1:
            features['structural_features'].add('multiple_shapes')
        if num_out > num_in:
            features['structural_features'].add('shape_duplication')
        elif num_out < num_in:
            features['structural_features'].add('shape_reduction')
        
        # Check for repetition/tiling
        if h_out >= 2*h_in or w_out >= 2*w_in:
            features['structural_features'].add('potential_tiling')
        
        # Check for symmetry
        h_sym = np.array_equal(out, np.fliplr(out))
        v_sym = np.array_equal(out, np.flipud(out))
        if h_sym or v_sym:
            features['structural_features'].add('symmetric_output')
        
        # Check for partial patterns
        if np.sum(out > 0) < 0.3 * out.size:
            features['structural_features'].add('sparse_output')
        elif np.sum(out > 0) > 0.7 * out.size:
            features['structural_features'].add('dense_output')
        
        # Check for lines/grids
        if check_has_lines(out):
            features['structural_features'].add('has_lines')
        
        # Check for background patterns
        if has_background_pattern(inp, out):
            features['structural_features'].add('background_pattern')
    
    return features

def check_has_lines(grid):
    """Check if grid contains straight lines."""
    # Horizontal lines
    for row in grid:
        if len(set(row)) == 1 and row[0] != 0:
            return True
    # Vertical lines
    for col_idx in range(grid.shape[1]):
        col = grid[:, col_idx]
        if len(set(col)) == 1 and col[0] != 0:
            return True
    return False

def has_background_pattern(inp, out):
    """Check if background (zeros) becomes patterned."""
    bg_in = (inp == 0).sum()
    bg_out = (out == 0).sum()
    return bg_out < bg_in * 0.5  # Background significantly reduced

print("Analyzing unsolved tasks...")
print()

# Analyze sample of unsolved tasks
sample_size = min(200, len(unsolved_ids))
sample_ids = unsolved_ids[:sample_size]

all_features = {
    'grid_transforms': Counter(),
    'color_changes': Counter(),
    'spatial_patterns': Counter(),
    'structural_features': Counter()
}

for task_id in sample_ids:
    task_data = all_data[task_id]
    features = analyze_task_features(task_data)
    
    for category, values in features.items():
        for value in values:
            all_features[category][value] += 1

print("="*80)
print("📊 UNSOLVED TASK PATTERNS (first 200 tasks)")
print("="*80)
print()

print("GRID TRANSFORMATIONS:")
for pattern, count in all_features['grid_transforms'].most_common():
    pct = count / sample_size * 100
    print(f"  {pattern}: {count} ({pct:.1f}%)")
print()

print("COLOR CHANGES:")
for pattern, count in all_features['color_changes'].most_common():
    pct = count / sample_size * 100
    print(f"  {pattern}: {count} ({pct:.1f}%)")
print()

print("SPATIAL PATTERNS:")
for pattern, count in all_features['spatial_patterns'].most_common():
    pct = count / sample_size * 100
    print(f"  {pattern}: {count} ({pct:.1f}%)")
print()

print("STRUCTURAL FEATURES:")
for pattern, count in all_features['structural_features'].most_common():
    pct = count / sample_size * 100
    print(f"  {pattern}: {count} ({pct:.1f}%)")
print()

# Deep dive into specific patterns
print("="*80)
print("🎯 DEEP PATTERN ANALYSIS")
print("="*80)
print()

# Find tasks with specific interesting patterns
pattern_examples = {
    'spatial_rearrange': [],
    'shape_duplication': [],
    'has_lines': [],
    'symmetric_output': [],
    'background_pattern': []
}

for task_id in sample_ids[:50]:  # Check first 50 in detail
    task_data = all_data[task_id]
    features = analyze_task_features(task_data)
    
    for pattern in pattern_examples.keys():
        if pattern in features['spatial_patterns'] or pattern in features['structural_features']:
            pattern_examples[pattern].append(task_id)

print("Example tasks by pattern:")
for pattern, task_ids in pattern_examples.items():
    if task_ids:
        print(f"\n{pattern}:")
        for tid in task_ids[:5]:  # Show up to 5 examples
            print(f"  - {tid}")

print()
print("="*80)
print("💡 OPERATOR RECOMMENDATIONS")
print("="*80)
print()

recommendations = []

# Based on frequency analysis
if all_features['spatial_patterns'].get('spatial_rearrange', 0) > 50:
    recommendations.append({
        'name': 'gravity_operator',
        'description': 'Objects fall/rise based on gravity simulation',
        'justification': f"{all_features['spatial_patterns']['spatial_rearrange']} tasks have spatial rearrangement"
    })

if all_features['structural_features'].get('shape_duplication', 0) > 20:
    recommendations.append({
        'name': 'object_replication',
        'description': 'Duplicate shapes based on rules (by color, position, etc.)',
        'justification': f"{all_features['structural_features']['shape_duplication']} tasks duplicate shapes"
    })

if all_features['structural_features'].get('has_lines', 0) > 30:
    recommendations.append({
        'name': 'line_grid_detector',
        'description': 'Detect and manipulate line patterns and grids',
        'justification': f"{all_features['structural_features']['has_lines']} tasks have line structures"
    })

if all_features['structural_features'].get('symmetric_output', 0) > 25:
    recommendations.append({
        'name': 'symmetry_enforcer',
        'description': 'Force symmetry on asymmetric inputs',
        'justification': f"{all_features['structural_features']['symmetric_output']} tasks create symmetry"
    })

if all_features['structural_features'].get('background_pattern', 0) > 20:
    recommendations.append({
        'name': 'background_fill',
        'description': 'Fill background with patterns based on foreground',
        'justification': f"{all_features['structural_features']['background_pattern']} tasks pattern the background"
    })

# High-level pattern recognition needs
if all_features['grid_transforms'].get('same_size', 0) > 150:
    recommendations.append({
        'name': 'pattern_recognition_operators',
        'description': 'Detect higher-order patterns (sequences, relationships, rules)',
        'justification': 'Many same-size transforms suggest complex in-place pattern recognition'
    })

print("Recommended new operators:")
for i, rec in enumerate(recommendations, 1):
    print(f"\n{i}. {rec['name']}")
    print(f"   Description: {rec['description']}")
    print(f"   Why: {rec['justification']}")

print()
print("="*80)
print("📈 COVERAGE POTENTIAL")
print("="*80)
print()

print("Current coverage: 53/1000 (5.3%)")
print()
print("Estimated potential with new operators:")
print("  + gravity_operator: ~10-15 additional tasks")
print("  + object_replication: ~5-10 additional tasks")
print("  + line_grid_detector: ~8-12 additional tasks")
print("  + symmetry_enforcer: ~3-5 additional tasks")
print("  + background_fill: ~3-5 additional tasks")
print("  + pattern_recognition: ~20-30 additional tasks")
print()
print("Projected coverage: ~100-130/1000 (10-13%)")
print()
print("⚠️  Note: Remaining 870+ tasks likely require:")
print("   - Abstract reasoning (relationships, analogies)")
print("   - Multi-step compositions")
print("   - Context-dependent rules")
print("   - Novel pattern types not in training set")

print()
print("="*80)
print("✅ ANALYSIS COMPLETE")
print("="*80)
