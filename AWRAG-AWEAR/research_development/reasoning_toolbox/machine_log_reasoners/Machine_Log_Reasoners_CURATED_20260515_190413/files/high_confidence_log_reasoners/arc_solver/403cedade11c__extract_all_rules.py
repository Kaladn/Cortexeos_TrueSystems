"""
EXTRACT AND DOCUMENT ALL TRANSFORMATION RULES

For each of the 53 solved tasks, extract:
1. The operator(s) used (single or multi-step)
2. The SEMANTIC RULE that the operator implements
3. The conditions under which it applies
4. Input/output examples

Output: One massive JSONL file with all rules documented.
"""
import json
import numpy as np
from pathlib import Path
from cod_616.arc_organ.arc_operators import OPERATORS
from scipy import ndimage

print("="*80)
print("📋 EXTRACTING ALL TRANSFORMATION RULES")
print("="*80)
print()

# Load all data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    all_data = json.load(f)

with open('compucog_616_master_ledger.json') as f:
    ledger = json.load(f)

# Build operator dict
op_dict = {op.name: op for op in OPERATORS}

# Define semantic rules for each operator
OPERATOR_RULES = {
    'position_based_recolor': {
        'rule': 'Recolor cells based on their (row, column) position coordinates. Each position maps to a specific output color.',
        'semantic_conditions': [
            'Grid stays same size',
            'Transformation is deterministic per position',
            'Color mapping depends on spatial location'
        ],
        'key_concepts': ['position_mapping', 'coordinate_based_logic', 'deterministic_recolor']
    },
    
    'recolor_mapping': {
        'rule': 'Apply a direct color substitution map. Every cell with color A becomes color B.',
        'semantic_conditions': [
            'Grid shape preserved',
            'Only colors change',
            'One-to-one or many-to-one color mapping'
        ],
        'key_concepts': ['color_substitution', 'palette_mapping', 'shape_preservation']
    },
    
    'block_expansion': {
        'rule': 'Expand each non-zero cell into an NxN block. Grid size multiplies by expansion factor.',
        'semantic_conditions': [
            'Output grid is larger (typically 3x expansion)',
            'Each pixel becomes a solid block',
            'Relative positions preserved'
        ],
        'key_concepts': ['spatial_expansion', 'pixel_to_block', 'uniform_scaling']
    },
    
    'self_masking_tiling': {
        'rule': 'Tile the input grid NxN times, using the input itself as a mask for which tiles to show.',
        'semantic_conditions': [
            'Output is tiled repetition',
            'Input serves as both content and mask',
            'Grid size multiplies'
        ],
        'key_concepts': ['self_reference', 'tiling', 'masking']
    },
    
    'mirror': {
        'rule': 'Reflect the grid horizontally or vertically.',
        'semantic_conditions': [
            'Grid size unchanged',
            'Spatial positions flipped',
            'Creates or preserves symmetry'
        ],
        'key_concepts': ['reflection', 'symmetry', 'flip_operation']
    },
    
    'symmetry_completion': {
        'rule': 'Detect partial symmetry and complete it. Fill in missing symmetric portions.',
        'semantic_conditions': [
            'Input has partial symmetry pattern',
            'Output completes the symmetry',
            'Grid size typically unchanged'
        ],
        'key_concepts': ['symmetry_detection', 'pattern_completion', 'reflection']
    },
    
    'tiling_expand': {
        'rule': 'Tile the input pattern NxN times to create larger output.',
        'semantic_conditions': [
            'Output is exact repetition',
            'Grid size multiplies',
            'No masking or modification'
        ],
        'key_concepts': ['tiling', 'repetition', 'pattern_multiplication']
    },
    
    'crop_to_bounding_box': {
        'rule': 'Find all non-zero pixels and crop grid to their bounding box.',
        'semantic_conditions': [
            'Output is smaller or same size',
            'Removes empty borders',
            'Content preserved exactly'
        ],
        'key_concepts': ['bounding_box', 'cropping', 'border_removal']
    },
    
    'center_halo_expansion': {
        'rule': 'Expand colored cells by adding a halo/border around them.',
        'semantic_conditions': [
            'Shapes grow larger',
            'New pixels added around existing ones',
            'Grid size typically unchanged'
        ],
        'key_concepts': ['morphological_dilation', 'halo_effect', 'border_expansion']
    },
    
    'center_repulsion': {
        'rule': 'Separate shapes based on geometric property (hollow vs filled center). Hollow shapes pack UPWARD, filled shapes pack DOWNWARD using 2D bin packing.',
        'semantic_conditions': [
            'Shapes must be extractable as connected components',
            'Center pixel determines direction (empty=UP, filled=DOWN)',
            'Shapes at different columns can share rows'
        ],
        'key_concepts': ['shape_extraction', 'hollow_detection', 'vertical_packing', 'geometric_property']
    },
    
    'color_histogram_fill': {
        'rule': 'Analyze color frequency and fill cells based on histogram statistics.',
        'semantic_conditions': [
            'Color distribution matters',
            'Statistical color properties used',
            'Grid size unchanged'
        ],
        'key_concepts': ['histogram_analysis', 'color_frequency', 'statistical_fill']
    },
    
    'horizontal_replicate': {
        'rule': 'Replicate the pattern horizontally (columns multiply).',
        'semantic_conditions': [
            'Width increases',
            'Height unchanged',
            'Horizontal tiling'
        ],
        'key_concepts': ['horizontal_tiling', 'column_replication']
    },
    
    'diagonal_reflection': {
        'rule': 'Reflect the grid across its main diagonal (transpose-like operation).',
        'semantic_conditions': [
            'Rows become columns',
            'Diagonal symmetry created',
            'Grid may change aspect ratio'
        ],
        'key_concepts': ['diagonal_symmetry', 'transpose', 'axis_swap']
    },
    
    'swap_mapping': {
        'rule': 'Swap two specific colors throughout the grid.',
        'semantic_conditions': [
            'Only 2 colors affected',
            'Grid structure unchanged',
            'Bidirectional color swap'
        ],
        'key_concepts': ['color_swap', 'bidirectional_mapping']
    },
    
    'hollow_frame_extraction': {
        'rule': 'Extract the outer frame/border of shapes, removing interior.',
        'semantic_conditions': [
            'Shapes become hollow outlines',
            'Interior pixels removed',
            'Border preserved'
        ],
        'key_concepts': ['edge_detection', 'hollow_extraction', 'frame_isolation']
    },
    
    'grid_subdivision_majority': {
        'rule': 'Subdivide grid into regions and fill each with majority color.',
        'semantic_conditions': [
            'Grid divided into blocks',
            'Each block becomes single color',
            'Majority voting per region'
        ],
        'key_concepts': ['subdivision', 'majority_vote', 'quantization']
    },
    
    'largest_blob_extract': {
        'rule': 'Find the largest connected component and extract only it.',
        'semantic_conditions': [
            'Multiple objects present',
            'Largest by pixel count selected',
            'Others removed'
        ],
        'key_concepts': ['connected_components', 'size_filtering', 'object_extraction']
    }
}

def extract_task_data(task_id, task, operator_name):
    """Extract all relevant data for a task."""
    inp_example = np.array(task['train'][0]['input'])
    out_example = np.array(task['train'][0]['output'])
    
    # Get operator rule
    rule_info = OPERATOR_RULES.get(operator_name, {
        'rule': 'Custom transformation (rule not yet documented)',
        'semantic_conditions': ['Unknown'],
        'key_concepts': ['undocumented']
    })
    
    # Extract semantic features
    semantic_features = extract_semantic_features(inp_example, out_example)
    
    return {
        'task_id': task_id,
        'steps': 1,
        'operators': [operator_name],
        'rule_description': rule_info['rule'],
        'semantic_conditions': rule_info['semantic_conditions'],
        'key_concepts': rule_info['key_concepts'],
        'semantic_features': semantic_features,
        'examples': [
            {
                'input': inp_example.tolist(),
                'output': out_example.tolist(),
                'input_shape': list(inp_example.shape),
                'output_shape': list(out_example.shape)
            }
        ]
    }

def extract_semantic_features(inp, out):
    """Extract deep semantic features from input/output pair."""
    features = {}
    
    # Shape analysis
    features['has_connected_shapes'] = check_has_shapes(inp)
    features['shape_count_changes'] = count_shapes(inp) != count_shapes(out)
    
    # Movement analysis
    features['shapes_move'] = check_shapes_move(inp, out)
    features['grid_size_changes'] = inp.shape != out.shape
    
    # Geometric properties
    features['has_hollow_shapes'] = check_hollow_shapes(inp)
    features['has_symmetry'] = check_symmetry(out)
    
    # Color properties
    colors_in = set(inp.flatten()) - {0}
    colors_out = set(out.flatten()) - {0}
    features['color_count_in'] = len(colors_in)
    features['color_count_out'] = len(colors_out)
    features['colors_change'] = colors_in != colors_out
    
    # Transformation type
    if inp.shape == out.shape and np.array_equal((inp > 0), (out > 0)):
        features['transform_category'] = 'recoloring'
    elif inp.shape != out.shape:
        features['transform_category'] = 'size_change'
    else:
        features['transform_category'] = 'spatial_rearrange'
    
    return features

def check_has_shapes(grid):
    """Check if grid has extractable shapes."""
    nonzero = (grid > 0).astype(int)
    labeled, num = ndimage.label(nonzero)
    return num > 0

def count_shapes(grid):
    """Count connected components."""
    nonzero = (grid > 0).astype(int)
    labeled, num = ndimage.label(nonzero)
    return num

def check_shapes_move(inp, out):
    """Check if shapes change position."""
    if inp.shape != out.shape:
        return False  # Can't compare movement if size changed
    
    # Simple check: are non-zero positions different?
    return not np.array_equal((inp > 0), (out > 0))

def check_hollow_shapes(grid):
    """Check if any shapes have hollow centers."""
    for color in range(1, 10):
        mask = (grid == color)
        labeled, num = ndimage.label(mask)
        
        for shape_id in range(1, num + 1):
            shape_mask = (labeled == shape_id)
            coords = np.argwhere(shape_mask)
            
            if len(coords) < 5:  # Too small to be hollow
                continue
            
            min_r, min_c = coords.min(axis=0)
            max_r, max_c = coords.max(axis=0)
            center_r = (min_r + max_r) // 2
            center_c = (min_c + max_c) // 2
            
            # Check if center is empty
            if not shape_mask[center_r, center_c]:
                return True
    
    return False

def check_symmetry(grid):
    """Check if grid has any symmetry."""
    h_sym = np.array_equal(grid, np.fliplr(grid))
    v_sym = np.array_equal(grid, np.flipud(grid))
    return h_sym or v_sym

print("Processing single-step tasks...")
print()

all_rules = []

# Process all solved tasks from ledger
for fp in ledger['fingerprints']:
    task_id = fp['task_id']
    operator_name = fp['operator']
    task_data = all_data[task_id]
    
    rule_entry = extract_task_data(task_id, task_data, operator_name)
    all_rules.append(rule_entry)
    print(f"✓ {task_id} → {operator_name}")

print()
print(f"Processed {len(all_rules)} single-step tasks")
print()

# Now add multi-step compositions (from earlier scan results)
print("="*80)
print("Adding multi-step compositions...")
print("="*80)
print()

# The multi-step scan found these patterns (from earlier terminal output)
MULTI_STEP_COMPOSITIONS = [
    # From the full scan that completed
    ('b8cdaf2b', ['center_repulsion', 'diagonal_reflection']),
    ('b91ae062', ['diagonal_reflection', 'block_expansion']),
    ('b94a9452', ['crop_to_bounding_box', 'center_halo_expansion']),
    ('bda2d7a6', ['recolor_mapping', 'block_expansion']),
    ('be94b721', ['largest_blob_extract', 'crop_to_bounding_box']),
    ('c59eb873', ['crop_to_bounding_box', 'block_expansion']),
    ('caa06a1f', ['position_based_recolor', 'position_based_recolor']),
    ('ccd554ac', ['crop_to_bounding_box', 'tiling_expand']),
    ('d037b0a7', ['position_based_recolor', 'position_based_recolor']),
    ('d4b1c2b1', ['crop_to_bounding_box', 'block_expansion']),
    ('d511f180', ['swap_mapping', 'crop_to_bounding_box']),
    ('d5d6de2d', ['center_halo_expansion', 'hollow_frame_extraction']),
    ('e26a3af2', ['grid_subdivision_majority', 'grid_subdivision_majority']),
    ('e9afcf9a', ['position_based_recolor', 'position_based_recolor']),
    ('ed36ccf7', ['position_based_recolor', 'position_based_recolor']),
    ('f25ffba3', ['center_halo_expansion', 'symmetry_completion']),
    ('f76d97a5', ['recolor_mapping', 'diagonal_reflection']),
    ('f823c43c', ['position_based_recolor', 'position_based_recolor']),
    # Additional from earlier part of scan
    ('1e0a9b12', ['crop_to_bounding_box', 'center_repulsion']),
    ('1f85a75f', ['largest_blob_extract', 'crop_to_bounding_box']),
    ('3befdf3e', ['center_halo_expansion', 'block_expansion']),
    ('496994bd', ['diagonal_reflection', 'symmetry_completion']),
    ('5b6cbef5', ['center_halo_expansion', 'self_masking_tiling']),
    ('60c09cac', ['diagonal_reflection', 'block_expansion']),
    ('67a3c6ac', ['mirror', 'crop_to_bounding_box']),
    ('68b16354', ['mirror', 'crop_to_bounding_box']),
    ('6ea4a07e', ['recolor_mapping', 'position_based_recolor']),
    ('833966f4', ['recolor_mapping', 'center_repulsion']),
    ('85c4e7cd', ['recolor_mapping', 'crop_to_bounding_box']),
    ('880c1354', ['recolor_mapping', 'crop_to_bounding_box']),
    ('9172f3a0', ['crop_to_bounding_box', 'block_expansion']),
    ('a416b8f3', ['horizontal_replicate', 'diagonal_reflection']),
    ('a59b95c0', ['crop_to_bounding_box', 'tiling_expand']),
    ('ac0a08a4', ['diagonal_reflection', 'block_expansion']),
    ('ac2e8ecf', ['center_repulsion', 'center_repulsion']),
    ('ad173014', ['recolor_mapping', 'center_halo_expansion']),
    ('007bbfb7', ['center_halo_expansion', 'self_masking_tiling']),
]

# Track which task IDs we already have as single-step
single_step_ids = {rule['task_id'] for rule in all_rules}

for task_id, operators in MULTI_STEP_COMPOSITIONS:
    if task_id in single_step_ids:
        # This was solved with single operator, multi-step is alternative solution
        continue
    
    if task_id not in all_data:
        continue
    
    task = all_data[task_id]
    inp_example = np.array(task['train'][0]['input'])
    out_example = np.array(task['train'][0]['output'])
    
    # Build composite rule description
    rule_parts = []
    for op_name in operators:
        if op_name in OPERATOR_RULES:
            rule_parts.append(OPERATOR_RULES[op_name]['rule'])
    
    composite_rule = " THEN ".join(rule_parts)
    
    # Combine key concepts
    all_concepts = []
    for op_name in operators:
        if op_name in OPERATOR_RULES:
            all_concepts.extend(OPERATOR_RULES[op_name]['key_concepts'])
    
    semantic_features = extract_semantic_features(inp_example, out_example)
    
    multi_step_entry = {
        'task_id': task_id,
        'steps': len(operators),
        'operators': operators,
        'rule_description': composite_rule,
        'semantic_conditions': [f'Multi-step: {len(operators)} operators'],
        'key_concepts': list(set(all_concepts)),
        'semantic_features': semantic_features,
        'examples': [
            {
                'input': inp_example.tolist(),
                'output': out_example.tolist(),
                'input_shape': list(inp_example.shape),
                'output_shape': list(out_example.shape)
            }
        ]
    }
    
    all_rules.append(multi_step_entry)
    print(f"✓ {task_id} → {' → '.join(operators)}")

print()
print(f"Added {len(all_rules) - len(single_step_ids)} multi-step tasks")
print()

# Statistics
print("="*80)
print("📊 RULE STATISTICS")
print("="*80)
print()

step_counts = {1: 0, 2: 0, 3: 0}
for rule in all_rules:
    steps = rule['steps']
    if steps <= 3:
        step_counts[steps] += 1

print(f"Total tasks with rules: {len(all_rules)}")
print(f"  1-step (single operator): {step_counts[1]}")
print(f"  2-step (compositions): {step_counts[2]}")
print(f"  3-step (complex chains): {step_counts[3]}")
print()

# Concept frequency
concept_freq = {}
for rule in all_rules:
    for concept in rule['key_concepts']:
        concept_freq[concept] = concept_freq.get(concept, 0) + 1

print("Top 10 most common concepts:")
for concept, count in sorted(concept_freq.items(), key=lambda x: -x[1])[:10]:
    print(f"  {concept}: {count} tasks")
print()

# Save to JSONL
output_file = 'arc_transformation_rules.jsonl'
with open(output_file, 'w') as f:
    for rule in all_rules:
        f.write(json.dumps(rule) + '\n')

print("="*80)
print("✅ COMPLETE")
print("="*80)
print()
print(f"Saved {len(all_rules)} transformation rules to: {output_file}")
print()
print("Each entry contains:")
print("  - task_id")
print("  - steps (1, 2, or 3)")
print("  - operators used")
print("  - rule_description (human-readable)")
print("  - semantic_conditions")
print("  - key_concepts (tags)")
print("  - semantic_features (computed)")
print("  - examples (input/output grids)")
