"""
COMPLETED MATH DSL FORMALIZATIONS - 5 Unsolved Tasks
Based on manual pattern analysis
"""
import json

# Task 1: 00576224 - Checkerboard Tiling with Alternation
task_00576224 = {
    'task_id': '00576224',
    'pattern_type': 'checkerboard_tiling_with_alternation',
    'human_description': 'Input 2x2 pattern tiles 3x3 times. Odd rows alternate (swap positions). Creates checkerboard effect.',
    'math_dsl': {
        'objects': [
            'Input tile T ∈ {0..9}^{2×2}',
            'Repetition factor n = 3 (both dimensions)',
            'Output grid G_out ∈ {0..9}^{6×6}',
            'Tile variants: T and T_alt (row/col swapped)',
        ],
        'conditions': [
            'Output size: H_out = n·H_in = 6, W_out = n·W_in = 6',
            'Checkerboard pattern: alternate T and T_alt',
            'Color palette preserved'
        ],
        'equations': [
            'T_alt = horizontal_flip(T) OR vertical_flip(T)',
            'Pattern(i,j) = T if (i+j) mod 2 = 0, else T_alt',
            'G_out[i·2:(i+1)·2, j·2:(j+1)·2] = Pattern(i,j) for i,j ∈ [0,3)'
        ],
        'transform': [
            'For each tile position (i,j) in 3×3 grid:',
            '  If (i+j) even: place T at (i·2, j·2)',
            '  If (i+j) odd: place T_alt at (i·2, j·2)',
            'T_alt determined by analyzing which flip creates alternation'
        ]
    },
    'operator_blueprint': {
        'name': 'checkerboard_tiling_alternating',
        'category': 'tiling_with_transformation',
        'preconditions': [
            'Input is small tile (typically 2×2 or 3×3)',
            'Output is exact integer multiple (typically 3× or 4×)',
            'Pattern shows alternation in adjacent tiles'
        ],
        'implementation_notes': 'Detect which flip (H/V) creates the alternation pattern. Apply tiling with conditional transform.'
    }
}

# Task 2: 009d5c81 - Shape Reference Recoloring
task_009d5c81 = {
    'task_id': '009d5c81',
    'pattern_type': 'shape_reference_recoloring',
    'human_description': 'Grid has two separate regions: main shape (color 8) and reference shape (color 1). Output: main shape recolored based on reference shape properties, reference removed.',
    'math_dsl': {
        'objects': [
            'Main shape M = {(r,c) | G_in(r,c) = 8}',
            'Reference shape R = {(r,c) | G_in(r,c) = 1}',
            'Property function φ: R → color (extracts property from reference)',
            'Recolor mapping: 8 → φ(R)'
        ],
        'conditions': [
            'Grid size preserved: G_out ∈ {0..9}^{H×W}',
            'M structure preserved, only color changes',
            'R completely removed in output',
            'φ(R) determines output color (based on shape, orientation, etc.)'
        ],
        'equations': [
            'Property extraction: φ(R) = f(shape_features(R))',
            'Examples: orientation → color, size → color, position → color',
            'Transform: ∀(r,c)∈M: G_out(r,c) = φ(R)',
            'Transform: ∀(r,c)∉M: G_out(r,c) = 0'
        ],
        'transform': [
            'Extract reference shape R (color 1)',
            'Compute property φ(R) by analyzing shape features:',
            '  - Orientation (up/down/left/right)',
            '  - Specific pattern/structure',
            '  - Size or aspect ratio',
            'Map property to target color',
            'Recolor main shape M (color 8) to target color',
            'Remove reference shape from output'
        ]
    },
    'operator_blueprint': {
        'name': 'shape_reference_recolor',
        'category': 'property_transfer',
        'preconditions': [
            'Two distinct color regions (main shape + reference)',
            'Reference is small, single connected component',
            'Main shape is larger pattern',
            'Output removes reference, recolors main'
        ],
        'implementation_notes': 'Need shape property analyzer: detect orientation (arrows, triangles), patterns. Build property→color mapping from training examples.'
    }
}

# Task 3: 00d62c1b - Interior Fill Detection
task_00d62c1b = {
    'task_id': '00d62c1b',
    'pattern_type': 'interior_fill_by_enclosure',
    'human_description': 'Connected boundary (color 3) forms closed regions. Regions with 2×2 or larger interiors filled with color 4.',
    'math_dsl': {
        'objects': [
            'Boundary B = {(r,c) | G_in(r,c) = 3}',
            'Connected components C_i of B',
            'Interior region I(C_i) = cells enclosed by C_i',
            'Fill color k_fill = 4'
        ],
        'conditions': [
            'Grid size preserved',
            'Boundary color 3 preserved in output',
            'Interior cells recolored to 4 if region ≥ 2×2'
        ],
        'equations': [
            'For each component C_i:',
            '  I(C_i) = {(r,c) | (r,c) enclosed by C_i and G_in(r,c) = 0}',
            '  If |I(C_i)| ≥ 4 and bbox(I(C_i)) has min_dim ≥ 2:',
            '    ∀(r,c)∈I(C_i): G_out(r,c) = 4',
            '  Else: G_out(r,c) = G_in(r,c)',
            'Boundary preserved: ∀(r,c)∈B: G_out(r,c) = 3'
        ],
        'transform': [
            'Detect boundary component C (color 3)',
            'For each connected boundary region:',
            '  Find enclosed interior I using flood fill from outside',
            '  Compute interior size and bounding box',
            '  If interior ≥ 2×2: fill with color 4',
            '  Else: leave as background (0)',
            'Preserve all boundary pixels'
        ]
    },
    'operator_blueprint': {
        'name': 'enclosed_region_fill',
        'category': 'topological_fill',
        'preconditions': [
            'Has boundary color forming closed regions',
            'Background (0) exists inside boundaries',
            'Size threshold determines fill'
        ],
        'implementation_notes': 'Use flood fill from exterior to find enclosed regions. Check size/dimensions. Apply conditional fill.'
    }
}

# Task 4: 00dbd492 - Pattern completion based on prototype
task_00dbd492 = {
    'task_id': '00dbd492',
    'pattern_type': 'pattern_completion_from_prototype',
    'human_description': 'Grid contains partial repetitions of a pattern plus one complete prototype. Complete all partial patterns to match prototype structure.',
    'math_dsl': {
        'objects': [
            'Shape set S = {S_1, S_2, ..., S_n}',
            'Prototype P = largest/complete shape in set',
            'Partial shapes {S_i | S_i ⊂ P structurally}',
            'Completion mapping: S_i → P alignment'
        ],
        'conditions': [
            'Grid size preserved or expanded',
            'All shapes become complete copies of P',
            'Relative positions maintained'
        ],
        'equations': [
            'Identify prototype: P = argmax_{S∈S} |S| or complexity(S)',
            'For each partial S_i:',
            '  Find best alignment: τ_i = argmin_τ distance(S_i, P + τ)',
            '  Complete: S_i\' = P + τ_i',
            'G_out = union of all completed shapes'
        ],
        'transform': [
            'Extract all connected shapes',
            'Identify prototype (largest or most complete)',
            'For each partial shape:',
            '  Align to prototype',
            '  Copy missing pixels from prototype',
            '  Place completed shape in output',
            'Handle overlaps by precedence or merging'
        ]
    },
    'operator_blueprint': {
        'name': 'pattern_completion_prototype',
        'category': 'structure_completion',
        'preconditions': [
            'Multiple similar shapes with varying completeness',
            'One clear prototype (complete example)',
            'Partials are subsets or projections of prototype'
        ],
        'implementation_notes': 'Shape matching with partial alignment. Template matching allowing gaps. Structural similarity metrics.'
    }
}

# Task 5: 017c7c7b - Symmetry from fragment
task_017c7c7b = {
    'task_id': '017c7c7b',
    'pattern_type': 'fragment_to_full_symmetry',
    'human_description': 'Input contains fragment of pattern. Output creates full symmetric pattern by reflecting/rotating fragment to complete symmetry.',
    'math_dsl': {
        'objects': [
            'Fragment F ⊂ G_in (non-zero pixels)',
            'Symmetry type σ ∈ {horizontal, vertical, 4-fold rotational}',
            'Reflection operators: R_h, R_v',
            'Rotation operator: Rot_{90}',
            'Complete pattern P = symmetrize(F, σ)'
        ],
        'conditions': [
            'Grid size preserved or expanded to accommodate symmetry',
            'Output has perfect symmetry under σ',
            'Fragment F is subset of output'
        ],
        'equations': [
            'For horizontal symmetry:',
            '  P = F ∪ R_h(F)',
            'For vertical symmetry:',
            '  P = F ∪ R_v(F)',
            'For 4-fold rotational:',
            '  P = F ∪ Rot_{90}(F) ∪ Rot_{180}(F) ∪ Rot_{270}(F)',
            'Merge rule: max color at overlapping positions'
        ],
        'transform': [
            'Detect fragment F (non-zero region)',
            'Infer symmetry type from fragment position/structure',
            'Apply symmetry operations:',
            '  Generate reflected/rotated copies',
            '  Place in appropriate positions',
            '  Merge overlapping regions',
            'Output complete symmetric pattern'
        ]
    },
    'operator_blueprint': {
        'name': 'symmetry_from_fragment',
        'category': 'symmetry_completion_advanced',
        'preconditions': [
            'Input is partial/fragment (high asymmetry)',
            'Fragment suggests symmetry type (position, structure)',
            'Output is fully symmetric'
        ],
        'implementation_notes': 'Detect fragment position relative to grid center. Infer symmetry type. Apply geometric transforms with proper centering.'
    }
}

# Compile all formalizations
all_formalizations = [
    task_00576224,
    task_009d5c81,
    task_00d62c1b,
    task_00dbd492,
    task_017c7c7b
]

# Save to file
output_file = 'manual_math_dsl_complete.jsonl'
with open(output_file, 'w') as f:
    for form in all_formalizations:
        f.write(json.dumps(form, indent=2) + '\n\n')

print("="*80)
print("COMPLETED MATH DSL FORMALIZATIONS")
print("="*80)
print()
print(f"Formalized {len(all_formalizations)} unsolved tasks")
print(f"Saved to: {output_file}")
print()
print("Task Patterns Identified:")
for form in all_formalizations:
    print(f"  {form['task_id']}: {form['pattern_type']}")
print()
print("Operator Blueprints Created:")
for form in all_formalizations:
    print(f"  - {form['operator_blueprint']['name']}")
    print(f"    Category: {form['operator_blueprint']['category']}")
print()
print("="*80)
print("SUMMARY")
print("="*80)
print()
print("5 New Patterns Discovered:")
print("  1. checkerboard_tiling_alternating - Tiling with alternating transforms")
print("  2. shape_reference_recolor - Property transfer via reference shape")
print("  3. enclosed_region_fill - Topological interior detection + fill")
print("  4. pattern_completion_prototype - Complete partials from prototype")
print("  5. symmetry_from_fragment - Infer and complete symmetry")
print()
print("Next Steps:")
print("  1. Implement these 5 operators")
print("  2. Test on original tasks + similar patterns")
print("  3. Add to mathematical operator library")
print("  4. Measure coverage improvement")
print()
print("Estimated new coverage: +5 to +15 tasks (depending on pattern prevalence)")
