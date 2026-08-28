"""
CONVERT ALL 57 RULES TO MATHEMATICAL DSL

Uses the math DSL schema:
- objects: definitions
- conditions: invariants
- equations: math pieces
- transform: algorithm in math form

This converts natural language → pure mathematics for all solved tasks.
"""
import json
import numpy as np

print("="*80)
print("🔬 CONVERTING 57 RULES TO MATHEMATICAL DSL")
print("="*80)
print()

# Load existing rules
rules = []
with open('arc_transformation_rules_with_math.jsonl', 'r') as f:
    for line in f:
        rules.append(json.loads(line))

print(f"Loaded {len(rules)} rules")
print()

# Math DSL templates for each operator category
MATH_DSL_TEMPLATES = {
    'recolor_mapping': {
        'objects': [
            "G_in ∈ {0..9}^{H×W}",
            "G_out ∈ {0..9}^{H×W}",
            "Color mapping f: {0..9} → {0..9}"
        ],
        'conditions': [
            "Grid size preserved: H_out = H_in, W_out = W_in",
            "Spatial structure preserved: ∀(r,c), G_in(r,c)=k ⟺ G_out(r,c)=f(k)"
        ],
        'equations': [
            "f(k) defined by: {input_color_i → output_color_i}"
        ],
        'transform': [
            "∀ (r,c): G_out(r,c) = f(G_in(r,c))"
        ]
    },
    
    'position_based_recolor': {
        'objects': [
            "G_in ∈ {0..9}^{H×W}",
            "G_out ∈ {0..9}^{H×W}",
            "Bounding box B = [r0,r1]×[c0,c1]",
            "Local coordinates: r' = r - r0, c' = c - c0",
            "Position predicate P: (r',c') → {true,false}"
        ],
        'conditions': [
            "Grid size preserved: H_out = H_in, W_out = W_in",
            "Transform acts only inside bounding box B"
        ],
        'equations': [
            "P(r',c') = condition based on position",
            "Examples: r'=c' (diagonal), r'=0 or c'=0 (border), etc."
        ],
        'transform': [
            "If (r,c) ∈ B and P(r',c') then G_out(r,c) = k",
            "Else if (r,c) ∈ B then G_out(r,c) = 0",
            "Else G_out(r,c) = G_in(r,c)"
        ]
    },
    
    'block_expansion': {
        'objects': [
            "Scale factor k ∈ ℕ",
            "New grid size: H_out = k·H_in, W_out = k·W_in",
            "Block expansion E_k: (r,c) ↦ {(kr+a, kc+b) | a,b∈[0,k-1]}"
        ],
        'conditions': [
            "Grid expands uniformly by factor k",
            "Each input pixel becomes k×k block"
        ],
        'equations': [
            "For each input pixel (r,c), block B(r,c) = {(kr+a, kc+b) | a,b∈[0,k-1]}"
        ],
        'transform': [
            "∀ (r,c) with G_in(r,c) ≠ 0, ∀ a,b∈[0,k-1]:",
            "    G_out(kr+a, kc+b) = G_in(r,c)",
            "∀ other cells in G_out not covered by any block: G_out = 0"
        ]
    },
    
    'center_repulsion': {
        'objects': [
            "Shape set 𝒮 = {S_i | S_i ⊆ ℤ² is 4-connected component of non-zero pixels}",
            "For each S: bounding box (r_min, r_max, c_min, c_max), center c_S = ⌊(r_min+r_max)/2⌋, ⌊(c_min+c_max)/2⌋",
            "Partition ℋ = {S | c_S ∉ S} (hollow), ℱ = {S | c_S ∈ S} (filled)",
            "X-interval I(S) = [c_min(S), c_max(S)]"
        ],
        'conditions': [
            "G_out has same H,W as G_in",
            "Each shape S moves by translation only, no rotation or recolor",
            "Shapes cannot overlap in output grid"
        ],
        'equations': [
            "Upward pack ℋ by finding minimal Δ_S ≥ 0 that satisfies:",
            "    ∀ placed T ∈ ℋ: if row_ranges_overlap(S',T') then I(S) ∩ I(T) = ∅",
            "Where S' rows = [r_min(S)-Δ_S, r_max(S)-Δ_S]",
            "Downward pack ℱ with analogous maximal Δ_S ≤ 0"
        ],
        'transform': [
            "For S ∈ ℋ, compute Δ_S (upward) and set S' = {(r-Δ_S, c) | (r,c)∈S}",
            "For S ∈ ℱ, compute Δ_S (downward) and set S' = {(r+|Δ_S|, c) | (r,c)∈S}",
            "G_out(r,c) = color of S' if (r,c)∈S' for some S; else 0"
        ]
    },
    
    'mirror': {
        'objects': [
            "Reflection operator R_axis",
            "Axes: horizontal R_h, vertical R_v, diagonal R_d"
        ],
        'conditions': [
            "Grid size may change based on reflection type",
            "Colors preserved"
        ],
        'equations': [
            "R_h: (r,c) ↦ (r, W-1-c)  [horizontal flip]",
            "R_v: (r,c) ↦ (H-1-r, c)  [vertical flip]",
            "R_d: (r,c) ↦ (c, r)      [transpose]"
        ],
        'transform': [
            "G_out = R_axis(G_in)",
            "For horizontal: G_out(r,c) = G_in(r, W-1-c)",
            "For vertical: G_out(r,c) = G_in(H-1-r, c)",
            "For diagonal: G_out(r,c) = G_in(c, r) with shape swap"
        ]
    },
    
    'crop_to_bbox': {
        'objects': [
            "Active region A = {(r,c) | G_in(r,c) ≠ 0}",
            "Bounding box B = [r_min, r_max] × [c_min, c_max] where",
            "    r_min = min{r | ∃c: (r,c)∈A}",
            "    r_max = max{r | ∃c: (r,c)∈A}",
            "    c_min = min{c | ∃r: (r,c)∈A}",
            "    c_max = max{c | ∃r: (r,c)∈A}"
        ],
        'conditions': [
            "Output is subgrid of input",
            "H_out = r_max - r_min + 1",
            "W_out = c_max - c_min + 1"
        ],
        'equations': [
            "Crop operation: G_out = G_in[r_min:r_max+1, c_min:c_max+1]"
        ],
        'transform': [
            "∀ (r,c) ∈ [0,H_out)×[0,W_out):",
            "    G_out(r,c) = G_in(r+r_min, c+c_min)"
        ]
    },
    
    'tiling': {
        'objects': [
            "Tile pattern T ∈ {0..9}^{h×w}",
            "Repetition counts: n_rows, n_cols",
            "Output size: H_out = n_rows·h, W_out = n_cols·w"
        ],
        'conditions': [
            "Grid expands by tiling",
            "Each tile is identical copy of pattern T"
        ],
        'equations': [
            "Tile position (i,j) ∈ [0,n_rows)×[0,n_cols)",
            "Tile offset: (i·h, j·w)"
        ],
        'transform': [
            "∀ i∈[0,n_rows), j∈[0,n_cols), (r,c)∈T:",
            "    G_out(i·h+r, j·w+c) = T(r,c)"
        ]
    },
    
    'symmetry_completion': {
        'objects': [
            "Partial pattern P ⊂ G_in with symmetry axis",
            "Symmetry type: horizontal, vertical, or rotational",
            "Missing region M = symmetric_complement(P)"
        ],
        'conditions': [
            "Grid size preserved",
            "Output has complete symmetry"
        ],
        'equations': [
            "For horizontal symmetry: G_out(r,c) = G_out(r, W-1-c)",
            "For vertical symmetry: G_out(r,c) = G_out(H-1-r, c)",
            "For 180° rotation: G_out(r,c) = G_out(H-1-r, W-1-c)"
        ],
        'transform': [
            "Copy existing pattern: ∀(r,c)∈P: G_out(r,c) = G_in(r,c)",
            "Fill symmetric region: ∀(r,c)∈M: G_out(r,c) = G_out(symmetric_point(r,c))"
        ]
    },
    
    'color_histogram_fill': {
        'objects': [
            "Color histogram H: k ↦ |{(r,c) | G_in(r,c)=k}|",
            "Target region T ⊂ G_in (e.g., bounding box or full grid)",
            "Fill color k* = argmax_k H(k) (majority color)"
        ],
        'conditions': [
            "Grid size preserved",
            "Only specified region is filled"
        ],
        'equations': [
            "k* = argmax_{k∈{1..9}} |{(r,c) | G_in(r,c)=k}|"
        ],
        'transform': [
            "∀ (r,c) ∈ T: G_out(r,c) = k*",
            "∀ (r,c) ∉ T: G_out(r,c) = G_in(r,c)"
        ]
    },
    
    'hollow_frame_extraction': {
        'objects': [
            "Shape S = {(r,c) | G_in(r,c) ≠ 0}",
            "Morphological erosion: S ⊖ B where B is structuring element",
            "Interior I = S ⊖ B",
            "Boundary ∂S = S \\ I"
        ],
        'conditions': [
            "Grid size preserved",
            "Extracts only boundary pixels"
        ],
        'equations': [
            "Erosion: S ⊖ B = {p | B_p ⊆ S}",
            "Boundary: ∂S = S \\ (S ⊖ B)"
        ],
        'transform': [
            "∀ (r,c): G_out(r,c) = G_in(r,c) if (r,c) ∈ ∂S",
            "         G_out(r,c) = 0 if (r,c) ∈ I"
        ]
    },
    
    'swap_mapping': {
        'objects': [
            "Color swap function σ: {0..9} → {0..9}",
            "σ is an involution: σ(σ(k)) = k",
            "Typically σ swaps two colors: σ(a)=b, σ(b)=a, σ(k)=k for k∉{a,b}"
        ],
        'conditions': [
            "Grid size preserved",
            "Spatial structure preserved"
        ],
        'equations': [
            "σ²=id (involution property)",
            "For two-color swap: σ(a)=b, σ(b)=a"
        ],
        'transform': [
            "∀ (r,c): G_out(r,c) = σ(G_in(r,c))"
        ]
    },
    
    'self_masking_tiling': {
        'objects': [
            "Base tile T",
            "Mask M derived from T structure",
            "Tiled grid G_tiled = tile(T)",
            "Final output G_out = G_tiled ⊙ M (element-wise product)"
        ],
        'conditions': [
            "Output is tiled version with self-derived mask",
            "Mask preserves certain structural properties"
        ],
        'equations': [
            "G_tiled(i·h+r, j·w+c) = T(r,c)",
            "M(r,c) = mask_function(T)",
            "G_out = G_tiled ⊙ M"
        ],
        'transform': [
            "Step 1: Create tiled grid",
            "Step 2: Apply mask based on tile structure",
            "∀ (r,c): G_out(r,c) = G_tiled(r,c) if M(r,c)=1 else 0"
        ]
    },
    
    'diagonal_reflection': {
        'objects': [
            "Transpose operator T: (r,c) ↦ (c,r)",
            "Grid shape swap: (H,W) → (W,H)"
        ],
        'conditions': [
            "Output dimensions swapped: H_out=W_in, W_out=H_in",
            "Colors preserved"
        ],
        'equations': [
            "T(G)(r,c) = G(c,r)"
        ],
        'transform': [
            "∀ (r,c) ∈ [0,W_in)×[0,H_in):",
            "    G_out(r,c) = G_in(c,r)"
        ]
    },
    
    'extend_by_pattern': {
        'objects': [
            "Core pattern C ⊂ G_in",
            "Extension pattern E derived from C",
            "Extension direction: up/down/left/right",
            "Extension count: n repetitions"
        ],
        'conditions': [
            "Grid expands in specified direction",
            "Pattern repeats n times"
        ],
        'equations': [
            "E = pattern_from_core(C)",
            "Extension: G_out = concatenate(E^n, C) or (C, E^n)"
        ],
        'transform': [
            "Copy core: ∀(r,c)∈C: G_out(r+offset,c+offset) = C(r,c)",
            "Repeat pattern: ∀i∈[1,n]: place E at offset i·size(E)"
        ]
    },
    
    'tiling_expand': {
        'objects': [
            "Base grid G_in of size h×w",
            "Expansion factors: (n_v, n_h)",
            "Output size: H_out = n_v·h, W_out = n_h·w"
        ],
        'conditions': [
            "Exact integer scaling",
            "Input becomes repeating tile"
        ],
        'equations': [
            "Tile indices: (i,j) ∈ [0,n_v)×[0,n_h)",
            "Offset: (i·h, j·w)"
        ],
        'transform': [
            "∀ i∈[0,n_v), j∈[0,n_h), (r,c)∈G_in:",
            "    G_out(i·h+r, j·w+c) = G_in(r,c)"
        ]
    },
    
    'extract_unique_shape': {
        'objects': [
            "Shape set 𝒮 = connected components of G_in",
            "Unique shape S* = S where |{T∈𝒮 | T≅S}|=1",
            "Bounding box B(S*)"
        ],
        'conditions': [
            "Output is cropped to unique shape",
            "All other shapes discarded"
        ],
        'equations': [
            "Shape isomorphism: S≅T if ∃ translation τ: S=T+τ",
            "Uniqueness: |{T | T≅S*}|=1"
        ],
        'transform': [
            "Find S* with uniqueness property",
            "Crop to B(S*)",
            "G_out = G_in[B(S*)]"
        ]
    }
}

def get_operator_category(op_name):
    """Map operator to DSL template category."""
    category_map = {
        'recolor_mapping': 'recolor_mapping',
        'position_based_recolor': 'position_based_recolor',
        'block_expansion': 'block_expansion',
        'center_repulsion': 'center_repulsion',
        'mirror': 'mirror',
        'crop_to_bbox': 'crop_to_bbox',
        'tiling': 'tiling',
        'symmetry_completion': 'symmetry_completion',
        'color_histogram_fill': 'color_histogram_fill',
        'hollow_frame_extraction': 'hollow_frame_extraction',
        'swap_mapping': 'swap_mapping',
        'self_masking_tiling': 'self_masking_tiling',
        'diagonal_reflection': 'diagonal_reflection',
        'extend_by_pattern': 'extend_by_pattern',
        'tiling_expand': 'tiling_expand',
        'extract_unique_shape': 'extract_unique_shape',
        'noiseless_repeat': 'tiling_expand',
        'extend_to_symmetry': 'symmetry_completion',
    }
    return category_map.get(op_name, 'generic')

def convert_rule_to_math_dsl(rule):
    """Convert a rule to full math DSL format."""
    op_name = rule['operators'][0]
    category = get_operator_category(op_name)
    
    # Get template
    if category in MATH_DSL_TEMPLATES:
        template = MATH_DSL_TEMPLATES[category]
    else:
        # Generic template
        template = {
            'objects': ["G_in ∈ {0..9}^{H×W}", "G_out ∈ {0..9}^{H×W}"],
            'conditions': ["Transformation specific to operator"],
            'equations': ["Mathematical description not yet formalized"],
            'transform': ["Algorithm pending formalization"]
        }
    
    # Customize with actual task data
    if 'semantic_features' in rule:
        features = rule['semantic_features']
        
        # Update grid sizes if available
        if 'H_in' in features:
            template = template.copy()
            template['objects'] = [
                f"G_in ∈ {{0..9}}^{{{features['H_in']}×{features['W_in']}}}",
                f"G_out ∈ {{0..9}}^{{{features['H_out']}×{features['W_out']}}}"
            ] + template['objects'][2:]
    
    # Create full math DSL rule
    math_dsl = {
        'operator': op_name,
        'category': category,
        'objects': template['objects'],
        'conditions': template['conditions'],
        'equations': template['equations'],
        'transform': template['transform']
    }
    
    # Add any existing mathematical definitions
    if 'mathematical_definitions' in rule and len(rule['mathematical_definitions']) > 0:
        math_def = rule['mathematical_definitions'][0]
        if 'latex' in math_def:
            math_dsl['latex_formulation'] = math_def['latex']
        if 'formal_notation' in math_def:
            math_dsl['formal_notation'] = math_def['formal_notation']
    
    return math_dsl

print("Converting rules to mathematical DSL...")
print()

# Convert all rules
converted_rules = []
for rule in rules:
    math_dsl = convert_rule_to_math_dsl(rule)
    
    # Create new rule with math DSL
    new_rule = {
        'task_id': rule['task_id'],
        'steps': rule['steps'],
        'operators': rule['operators'],
        'rule_description': rule.get('rule_description', ''),
        'semantic_features': rule.get('semantic_features', {}),
        'mathematical_definitions': rule.get('mathematical_definitions', []),
        'math_dsl': math_dsl,
        'examples': rule.get('examples', [])
    }
    
    converted_rules.append(new_rule)

print(f"✅ Converted {len(converted_rules)} rules to math DSL")
print()

# Write to new file
output_file = 'arc_transformation_rules_math_dsl.jsonl'
with open(output_file, 'w') as f:
    for rule in converted_rules:
        f.write(json.dumps(rule, indent=None) + '\n')

print(f"💾 Saved to: {output_file}")
print()

# Statistics
print("="*80)
print("📊 MATHEMATICAL DSL SUMMARY")
print("="*80)
print()

category_counts = {}
for rule in converted_rules:
    cat = rule['math_dsl']['category']
    category_counts[cat] = category_counts.get(cat, 0) + 1

print("Rules by mathematical category:")
for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")
print()

print(f"Total rules with formal math DSL: {len(converted_rules)}")
print()

# Show example
print("="*80)
print("📝 EXAMPLE MATH DSL RULE")
print("="*80)
print()

# Pick an interesting example (center_repulsion if available)
example = next((r for r in converted_rules if r['operators'][0] == 'center_repulsion'), converted_rules[0])

print(f"Task: {example['task_id']}")
print(f"Operator: {example['operators'][0]}")
print()
print("MATH DSL:")
print()

math_dsl = example['math_dsl']

print("OBJECTS (Definitions):")
for obj in math_dsl['objects']:
    print(f"  • {obj}")
print()

print("CONDITIONS (Invariants):")
for cond in math_dsl['conditions']:
    print(f"  • {cond}")
print()

print("EQUATIONS (Math Pieces):")
for eq in math_dsl['equations']:
    print(f"  • {eq}")
print()

print("TRANSFORM (Algorithm):")
for trans in math_dsl['transform']:
    print(f"  • {trans}")
print()

if 'latex_formulation' in math_dsl:
    print("LaTeX FORMULATION:")
    print(math_dsl['latex_formulation'])
    print()

print("="*80)
print("✅ CONVERSION COMPLETE")
print("="*80)
print()
print("Output file structure:")
print("  task_id: identifier")
print("  operators: [operator_name]")
print("  rule_description: natural language")
print("  math_dsl:")
print("    objects: definitions")
print("    conditions: invariants")
print("    equations: math pieces")
print("    transform: algorithm in math form")
print("  examples: input/output pairs")
print()
print("Next steps:")
print("  1. Review math DSL for correctness")
print("  2. Use DSL for symbolic reasoning")
print("  3. Generate code from math specs")
print("  4. Prove operator properties")
