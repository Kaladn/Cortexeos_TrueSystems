"""
MATHEMATICAL OPERATOR TRANSLATION ENGINE

Converts all ARC operators and transformation rules from natural language
into formal mathematical representations.

Each operator becomes:
- Set-theoretic definitions
- Coordinate transforms
- Constraint systems
- Algebraic operations

Output: JSONL with embedded LaTeX/symbolic math for each rule.
"""
import json
import numpy as np
from pathlib import Path

print("="*80)
print("🧮 MATHEMATICAL OPERATOR TRANSLATION ENGINE")
print("="*80)
print()

# Mathematical definitions for all operators
OPERATOR_MATH = {
    'position_based_recolor': {
        'name': 'Position-Based Recolor',
        'math_type': 'function_mapping',
        'definitions': {
            'domain': 'Grid G with dimensions H × W',
            'function': 'f: (r, c) → color',
            'operation': 'G\'[r][c] = f(r, c) for all (r,c) ∈ [0,H) × [0,W)'
        },
        'formal_notation': {
            'input': 'G ∈ ℕ^(H×W)',
            'output': 'G\' ∈ ℕ^(H×W)',
            'mapping': 'f: ℤ² → {0,1,...,9}',
            'constraint': '∀(r,c): G\'[r][c] = f(r,c)'
        },
        'latex': r'''
\textbf{Position-Based Recolor:}
\begin{align}
G' &= f(G) \\
G'[r][c] &= \phi(r, c) \quad \forall (r,c) \in [0,H) \times [0,W) \\
\text{where } \phi &: \mathbb{Z}^2 \to \{0,1,\ldots,9\}
\end{align}
'''
    },
    
    'recolor_mapping': {
        'name': 'Recolor Mapping',
        'math_type': 'color_substitution',
        'definitions': {
            'domain': 'Set of colors C = {0,1,...,9}',
            'mapping': 'σ: C → C (bijection or injection)',
            'operation': 'G\'[r][c] = σ(G[r][c])'
        },
        'formal_notation': {
            'substitution': 'σ: {0,1,...,9} → {0,1,...,9}',
            'application': '∀(r,c): G\'[r][c] = σ(G[r][c])',
            'preservation': 'Shape(G\') = Shape(G) where Shape = {(r,c) | G[r][c] ≠ 0}'
        },
        'latex': r'''
\textbf{Recolor Mapping:}
\begin{align}
\sigma &: C \to C \text{ (color substitution)} \\
G'[r][c] &= \sigma(G[r][c]) \quad \forall (r,c) \\
\text{Shape}(G) &= \{(r,c) \mid G[r][c] \neq 0\} \\
\text{Shape}(G') &= \text{Shape}(G)
\end{align}
'''
    },
    
    'block_expansion': {
        'name': 'Block Expansion',
        'math_type': 'dilation_operator',
        'definitions': {
            'expansion_factor': 'k ∈ ℕ (typically k=3)',
            'dilation': 'Each pixel → k×k block',
            'transform': 'G\'[kr+a][kc+b] = G[r][c] for a,b ∈ [0,k)'
        },
        'formal_notation': {
            'input_size': '(H, W)',
            'output_size': '(kH, kW)',
            'operation': 'E_k: ℕ^(H×W) → ℕ^(kH×kW)',
            'formula': 'E_k(G)[kr+a][kc+b] = G[r][c], ∀a,b ∈ [0,k)'
        },
        'latex': r'''
\textbf{Block Expansion:}
\begin{align}
E_k &: \mathbb{N}^{H \times W} \to \mathbb{N}^{kH \times kW} \\
E_k(G)[i][j] &= G\left[\left\lfloor \frac{i}{k} \right\rfloor\right]\left[\left\lfloor \frac{j}{k} \right\rfloor\right] \\
\text{Alt: } &\forall r,c \in [0,H) \times [0,W), \, \forall a,b \in [0,k): \\
&E_k(G)[kr+a][kc+b] = G[r][c]
\end{align}
'''
    },
    
    'center_repulsion': {
        'name': 'Center Repulsion (Hollow/Filled Segregation)',
        'math_type': 'geometric_constraint_packing',
        'definitions': {
            'shapes': 'S = {S_i | S_i ⊆ ℤ² is connected component}',
            'center': 'c(S) = ((r_min + r_max)/2, (c_min + c_max)/2)',
            'hollow': 'H = {S | c(S) ∉ S}',
            'filled': 'F = {S | c(S) ∈ S}',
            'interval': 'I(S) = [c_min(S), c_max(S)]',
            'constraint': 'I(S_a) ∩ I(S_b) = ∅ for shapes in same row'
        },
        'formal_notation': {
            'partition': '𝒮 = ℋ ∪ ℱ where ℋ ∩ ℱ = ∅',
            'hollow_condition': 'S ∈ ℋ ⟺ center(S) ∉ S',
            'filled_condition': 'S ∈ ℱ ⟺ center(S) ∈ S',
            'packing_up': 'ℋ: Sort by r_min, pack from row 0 upward',
            'packing_down': 'ℱ: Sort by r_max desc, pack from row H-1 downward',
            'interval_constraint': '∀S_i, S_j sharing rows: [c_min(S_i), c_max(S_i)] ∩ [c_min(S_j), c_max(S_j)] = ∅'
        },
        'latex': r'''
\textbf{Center Repulsion:}
\begin{align}
\text{Shapes: } &\mathcal{S} = \{S_1, S_2, \ldots, S_n\} \text{ (connected components)} \\
\text{Center: } &c(S) = \left( \frac{r_{\min} + r_{\max}}{2}, \frac{c_{\min} + c_{\max}}{2} \right) \\
\text{Partition: } &\mathcal{H} = \{S \mid c(S) \notin S\} \text{ (hollow)} \\
&\mathcal{F} = \{S \mid c(S) \in S\} \text{ (filled)} \\
\text{Interval: } &I(S) = [c_{\min}(S), c_{\max}(S)] \\
\text{Constraint: } &I(S_i) \cap I(S_j) = \emptyset \text{ for shapes in same band} \\
\text{Upward: } &\text{Sort } \mathcal{H} \text{ by } r_{\min}, \text{ pack from } R=0 \\
\text{Downward: } &\text{Sort } \mathcal{F} \text{ by } r_{\max} \text{ desc, pack from } R=H-1
\end{align}
'''
    },
    
    'mirror': {
        'name': 'Mirror Reflection',
        'math_type': 'linear_transformation',
        'definitions': {
            'horizontal': 'G\'[r][c] = G[r][W-1-c]',
            'vertical': 'G\'[r][c] = G[H-1-r][c]',
            'matrix_form': 'Reflection matrix R applied to coordinate space'
        },
        'formal_notation': {
            'h_reflection': 'R_H: (r,c) ↦ (r, W-1-c)',
            'v_reflection': 'R_V: (r,c) ↦ (H-1-r, c)',
            'isometry': 'R ∈ O(2) (orthogonal group)',
            'determinant': 'det(R) = -1'
        },
        'latex': r'''
\textbf{Mirror Reflection:}
\begin{align}
\text{Horizontal: } &G'[r][c] = G[r][W-1-c] \\
\text{Vertical: } &G'[r][c] = G[H-1-r][c] \\
\text{Matrix form: } &R_H = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix} \\
&R_V = \begin{pmatrix} -1 & 0 \\ 0 & 1 \end{pmatrix} \\
\text{Isometry: } &R \in O(2), \, \det(R) = -1
\end{align}
'''
    },
    
    'diagonal_reflection': {
        'name': 'Diagonal Reflection',
        'math_type': 'transpose_operation',
        'definitions': {
            'main_diagonal': 'G\'[i][j] = G[j][i]',
            'anti_diagonal': 'G\'[i][j] = G[N-1-j][N-1-i]',
            'dimension_swap': '(H,W) → (W,H)'
        },
        'formal_notation': {
            'transpose': 'T: ℕ^(H×W) → ℕ^(W×H)',
            'operation': 'T(G)[i][j] = G[j][i]',
            'matrix': 'Coordinate swap (r,c) ↦ (c,r)'
        },
        'latex': r'''
\textbf{Diagonal Reflection:}
\begin{align}
T(G)[i][j] &= G[j][i] \quad \forall i,j \\
\text{Coordinate map: } &(r, c) \mapsto (c, r) \\
\text{Dimension change: } &(H, W) \to (W, H) \\
\text{Matrix: } &D = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}
\end{align}
'''
    },
    
    'crop_to_bounding_box': {
        'name': 'Crop to Bounding Box',
        'math_type': 'set_restriction',
        'definitions': {
            'nonzero': 'N = {(r,c) | G[r][c] ≠ 0}',
            'bounds': 'r_min = min{r | (r,c)∈N}, r_max = max{r | (r,c)∈N}',
            'extraction': 'G\' = G[r_min:r_max+1, c_min:c_max+1]'
        },
        'formal_notation': {
            'bbox': 'B = [r_min, r_max] × [c_min, c_max]',
            'projection': 'π: G → G|_B',
            'size': '(r_max - r_min + 1, c_max - c_min + 1)'
        },
        'latex': r'''
\textbf{Crop to Bounding Box:}
\begin{align}
\mathcal{N} &= \{(r,c) \mid G[r][c] \neq 0\} \\
r_{\min} &= \min\{r \mid (r,c) \in \mathcal{N}\} \\
r_{\max} &= \max\{r \mid (r,c) \in \mathcal{N}\} \\
c_{\min} &= \min\{c \mid (r,c) \in \mathcal{N}\} \\
c_{\max} &= \max\{c \mid (r,c) \in \mathcal{N}\} \\
G' &= G\big|_{[r_{\min}, r_{\max}] \times [c_{\min}, c_{\max}]}
\end{align}
'''
    },
    
    'symmetry_completion': {
        'name': 'Symmetry Completion',
        'math_type': 'group_action',
        'definitions': {
            'group': 'D_4 dihedral group (rotations + reflections)',
            'detection': 'Find partial symmetry axis',
            'completion': 'Apply group element to complete pattern'
        },
        'formal_notation': {
            'group': 'G ∈ D_4 = {e, r, r², r³, s, sr, sr², sr³}',
            'orbit': 'Orbit(p) = {g·p | g ∈ G}',
            'completion': 'Fill missing elements of orbit'
        },
        'latex': r'''
\textbf{Symmetry Completion:}
\begin{align}
G &\in D_4 \text{ (dihedral group)} \\
D_4 &= \{e, r, r^2, r^3, s, sr, sr^2, sr^3\} \\
\text{Orbit: } &\mathcal{O}(p) = \{g \cdot p \mid g \in G\} \\
\text{Complete: } &\text{Fill } \mathcal{O}(p) \text{ for all } p \in \text{Pattern}
\end{align}
'''
    },
    
    'tiling_expand': {
        'name': 'Tiling Expansion',
        'math_type': 'periodic_function',
        'definitions': {
            'period': 'P = (H, W) original grid size',
            'tiling': 'G\'[r][c] = G[r mod H][c mod W]',
            'repetition': 'n×m copies'
        },
        'formal_notation': {
            'modular': 'T_{n,m}(G)[i][j] = G[i mod H][j mod W]',
            'size': '(nH, mW)',
            'periodicity': 'G\'[r+H][c+W] = G\'[r][c]'
        },
        'latex': r'''
\textbf{Tiling Expansion:}
\begin{align}
T_{n,m}(G)[i][j] &= G[i \bmod H][j \bmod W] \\
\text{Output size: } &(nH, mW) \\
\text{Periodicity: } &G'[r+H][c+W] = G'[r][c] \\
\text{Translation: } &\tau_{(H,W)} \text{ applied } n \times m \text{ times}
\end{align}
'''
    },
    
    'self_masking_tiling': {
        'name': 'Self-Masking Tiling',
        'math_type': 'conditional_tiling',
        'definitions': {
            'tile': 'T_{n,m}(G) = tiled version',
            'mask': 'M = G itself',
            'operation': 'G\'[i][j] = T[i][j] if M[i mod H][j mod W] ≠ 0 else 0'
        },
        'formal_notation': {
            'tiling': 'T = T_{n,m}(G)',
            'masking': 'G\'[i][j] = T[i][j] · 𝟙(G[i mod H][j mod W] ≠ 0)',
            'self_reference': 'G is both content and mask'
        },
        'latex': r'''
\textbf{Self-Masking Tiling:}
\begin{align}
T &= T_{n,m}(G) \text{ (tile } G \text{ into } nH \times mW \text{)} \\
G'[i][j] &= T[i][j] \cdot \mathbb{1}(G[i \bmod H][j \bmod W] \neq 0) \\
\text{where } &\mathbb{1}(\cdot) \text{ is indicator function} \\
\text{Self-reference: } &G \text{ serves as both pattern and mask}
\end{align}
'''
    },
    
    'color_histogram_fill': {
        'name': 'Color Histogram Fill',
        'math_type': 'statistical_operator',
        'definitions': {
            'histogram': 'H(c) = |{(r,i) | G[r][i] = c}|',
            'statistic': 'Compute mode, median, or threshold',
            'fill': 'Replace cells based on histogram property'
        },
        'formal_notation': {
            'frequency': 'f(c) = ∑_{r,i} 𝟙(G[r][i] = c)',
            'mode': 'c* = argmax_c f(c)',
            'operation': 'G\'[r][c] depends on f(G[r][c])'
        },
        'latex': r'''
\textbf{Color Histogram Fill:}
\begin{align}
f(c) &= \sum_{r,i} \mathbb{1}(G[r][i] = c) \\
c^* &= \arg\max_c f(c) \text{ (mode)} \\
G'[r][c] &= \phi(G[r][c], f) \\
\text{where } \phi &\text{ is histogram-based rule}
\end{align}
'''
    },
    
    'swap_mapping': {
        'name': 'Swap Mapping',
        'math_type': 'involution',
        'definitions': {
            'swap': 'Exchange colors a ↔ b',
            'involution': 'σ² = identity',
            'operation': 'G\'[r][c] = b if G[r][c]=a, a if G[r][c]=b, else unchanged'
        },
        'formal_notation': {
            'permutation': 'σ ∈ S_n with σ(a)=b, σ(b)=a',
            'involution': 'σ ∘ σ = id',
            'fixed_points': 'σ(c) = c for c ≠ a,b'
        },
        'latex': r'''
\textbf{Swap Mapping:}
\begin{align}
\sigma(a) &= b, \quad \sigma(b) = a \\
\sigma(c) &= c \quad \forall c \notin \{a,b\} \\
\sigma \circ \sigma &= \text{id} \quad \text{(involution)} \\
G'[r][c] &= \sigma(G[r][c])
\end{align}
'''
    },
    
    'hollow_frame_extraction': {
        'name': 'Hollow Frame Extraction',
        'math_type': 'morphological_operation',
        'definitions': {
            'erosion': 'ε(S) = {p ∈ S | B(p) ⊆ S} (interior)',
            'boundary': '∂S = S \\ ε(S)',
            'extraction': 'Keep only boundary pixels'
        },
        'formal_notation': {
            'dilation': 'S ⊕ B = {p + b | p ∈ S, b ∈ B}',
            'erosion': 'S ⊖ B = {p | B_p ⊆ S}',
            'boundary': '∂S = S \\ (S ⊖ B)',
            'operation': 'G\' keeps only ∂S pixels'
        },
        'latex': r'''
\textbf{Hollow Frame Extraction:}
\begin{align}
\varepsilon(S) &= \{p \in S \mid B_p \subseteq S\} \quad \text{(erosion)} \\
\partial S &= S \setminus \varepsilon(S) \quad \text{(boundary)} \\
G' &= \mathbb{1}_{\partial S} \cdot G \\
\text{Morphology: } &S \ominus B \text{ (erosion with structuring element)}
\end{align}
'''
    },
    
    'grid_subdivision_majority': {
        'name': 'Grid Subdivision with Majority Vote',
        'math_type': 'quantization_operator',
        'definitions': {
            'partition': 'Divide grid into k×k blocks',
            'majority': 'mode(block) = most frequent color',
            'quantize': 'Replace entire block with mode'
        },
        'formal_notation': {
            'blocks': 'B_{i,j} = G[ik:(i+1)k, jk:(j+1)k]',
            'mode': 'm(B) = argmax_c |{p ∈ B | B[p] = c}|',
            'quantization': 'G\'[B_{i,j}] = m(B_{i,j})'
        },
        'latex': r'''
\textbf{Grid Subdivision Majority:}
\begin{align}
B_{i,j} &= G[ik:(i+1)k, \, jk:(j+1)k] \quad \text{(block)} \\
m(B) &= \arg\max_c \left|\{p \in B \mid B[p] = c\}\right| \\
G'[r][c] &= m(B_{\lfloor r/k \rfloor, \lfloor c/k \rfloor}) \\
\text{Quantization: } &\text{Q}_k: \mathbb{N}^{H \times W} \to \text{piecewise const}
\end{align}
'''
    },
    
    'largest_blob_extract': {
        'name': 'Largest Blob Extraction',
        'math_type': 'connected_component_filtering',
        'definitions': {
            'components': 'CC(G) = {S_1, S_2, ..., S_n} via 4/8-connectivity',
            'size': '|S| = number of pixels',
            'selection': 'S* = argmax |S|',
            'extraction': 'Keep only S*, zero out rest'
        },
        'formal_notation': {
            'adjacency': 'G = (V, E) graph with 4-connectivity',
            'components': 'CC = connected components of G',
            'largest': 'S* = argmax_{S ∈ CC} |S|',
            'indicator': 'G\'[r][c] = G[r][c] · 𝟙((r,c) ∈ S*)'
        },
        'latex': r'''
\textbf{Largest Blob Extraction:}
\begin{align}
\text{CC}(G) &= \{S_1, S_2, \ldots, S_n\} \quad \text{(connected components)} \\
|S| &= \text{cardinality of } S \\
S^* &= \arg\max_{S \in \text{CC}(G)} |S| \\
G'[r][c] &= G[r][c] \cdot \mathbb{1}((r,c) \in S^*)
\end{align}
'''
    },
    
    'center_halo_expansion': {
        'name': 'Center Halo Expansion',
        'math_type': 'morphological_dilation',
        'definitions': {
            'dilation': 'S ⊕ B = {s + b | s ∈ S, b ∈ B}',
            'structuring': 'B = unit square or cross',
            'growth': 'Expand each colored region by 1 pixel'
        },
        'formal_notation': {
            'operation': 'G\' = G ⊕ B',
            'kernel': 'B = {(0,0), (0,±1), (±1,0)} (cross)',
            'minkowski': 'S ⊕ B Minkowski sum'
        },
        'latex': r'''
\textbf{Center Halo Expansion:}
\begin{align}
S \oplus B &= \{s + b \mid s \in S, \, b \in B\} \quad \text{(dilation)} \\
B &= \{(0,0), (0,\pm1), (\pm1,0)\} \quad \text{(cross kernel)} \\
G' &= G \oplus B \\
\text{Minkowski sum: } &\text{Morphological dilation}
\end{align}
'''
    },
    
    'horizontal_replicate': {
        'name': 'Horizontal Replication',
        'math_type': 'horizontal_tiling',
        'definitions': {
            'replication': 'Concatenate G horizontally n times',
            'size': '(H, nW)',
            'operation': 'G\'[:, iW:(i+1)W] = G for i=0..n-1'
        },
        'formal_notation': {
            'concat': 'G\' = G || G || ... || G (n times)',
            'indexing': 'G\'[r][c] = G[r][c mod W]',
            'dimension': '(H, W) → (H, nW)'
        },
        'latex': r'''
\textbf{Horizontal Replication:}
\begin{align}
G' &= \underbrace{G \, \| \, G \, \| \, \cdots \, \| \, G}_{n \text{ times}} \\
G'[r][c] &= G[r][c \bmod W] \\
\text{Size: } &(H, W) \to (H, nW)
\end{align}
'''
    }
}

print("Translating all operators to mathematical form...")
print()

# Convert all rules from JSONL to math-enhanced JSONL
with open('arc_transformation_rules.jsonl', 'r') as f:
    rules = [json.loads(line) for line in f]

print(f"Loaded {len(rules)} transformation rules")
print()

# Enhance each rule with mathematical definitions
math_enhanced_rules = []

for rule in rules:
    task_id = rule['task_id']
    operators = rule['operators']
    
    # Add mathematical definitions for each operator
    math_defs = []
    for op_name in operators:
        if op_name in OPERATOR_MATH:
            math_defs.append(OPERATOR_MATH[op_name])
        else:
            math_defs.append({
                'name': op_name,
                'math_type': 'undefined',
                'note': 'Mathematical formulation pending'
            })
    
    # Create enhanced rule
    enhanced = rule.copy()
    enhanced['mathematical_definitions'] = math_defs
    
    # For multi-step, show composition
    if len(operators) > 1:
        enhanced['composition'] = {
            'notation': ' ∘ '.join(reversed(operators)),
            'explanation': f"Apply {operators[0]}, then {operators[1]}" + (f", then {operators[2]}" if len(operators) > 2 else ""),
            'latex': r' \circ '.join([f'\\text{{{op}}}' for op in reversed(operators)])
        }
    
    math_enhanced_rules.append(enhanced)
    
    print(f"✓ {task_id}: {' → '.join(operators)}")

print()
print("="*80)
print("💾 SAVING MATHEMATICAL RULE DATABASE")
print("="*80)
print()

# Save enhanced JSONL
output_file = 'arc_transformation_rules_with_math.jsonl'
with open(output_file, 'w') as f:
    for rule in math_enhanced_rules:
        f.write(json.dumps(rule) + '\n')

print(f"✅ Saved to: {output_file}")
print()

# Generate standalone math reference
math_reference = {
    'title': 'ARC Operator Mathematical Reference',
    'operators': OPERATOR_MATH,
    'fundamental_structures': {
        'grid': {
            'definition': 'G ∈ ℕ^(H×W)',
            'domain': 'H,W ∈ ℕ (height, width)',
            'range': 'G[r][c] ∈ {0,1,2,...,9}',
            'latex': r'G \in \mathbb{N}^{H \times W}, \quad G[r][c] \in \{0,1,\ldots,9\}'
        },
        'shape': {
            'definition': 'S = {(r,c) | G[r][c] = color}',
            'connected': 'Connected component via 4 or 8-adjacency',
            'bbox': 'B(S) = [r_min, r_max] × [c_min, c_max]',
            'center': 'c(S) = ((r_min+r_max)/2, (c_min+c_max)/2)',
            'latex': r'S = \{(r,c) \mid G[r][c] = \text{color}\}'
        },
        'interval': {
            'definition': 'I(S) = [c_min, c_max]',
            'intersection': 'I(A) ∩ I(B) checks column overlap',
            'latex': r'I(S) = [c_{\min}(S), c_{\max}(S)]'
        },
        'transform': {
            'types': ['Linear (reflection, rotation)', 'Nonlinear (dilation, tiling)', 'Conditional (masking)', 'Statistical (histogram)'],
            'composition': 'T = T_n ∘ T_{n-1} ∘ ... ∘ T_1',
            'latex': r'T: \mathbb{N}^{H \times W} \to \mathbb{N}^{H\' \times W\'}'
        }
    }
}

with open('arc_mathematical_reference.json', 'w') as f:
    json.dump(math_reference, f, indent=2)

print(f"✅ Saved math reference to: arc_mathematical_reference.json")
print()

# Generate LaTeX document with all operators
latex_doc = r'''\documentclass{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}

\title{ARC Transformation Operators: Mathematical Formulation}
\author{CompuCog ARC Engine}
\date{November 2025}

\begin{document}
\maketitle

\section{Fundamental Structures}

\subsection{Grid}
A grid $G$ is a matrix:
\[ G \in \mathbb{N}^{H \times W}, \quad G[r][c] \in \{0,1,\ldots,9\} \]

\subsection{Shape}
A shape $S$ is a set of pixel coordinates:
\[ S = \{(r,c) \mid G[r][c] = \text{color}\} \]

Bounding box:
\[ B(S) = [r_{\min}, r_{\max}] \times [c_{\min}, c_{\max}] \]

Center:
\[ c(S) = \left( \frac{r_{\min} + r_{\max}}{2}, \frac{c_{\min} + c_{\max}}{2} \right) \]

\subsection{Interval}
Column interval of a shape:
\[ I(S) = [c_{\min}(S), c_{\max}(S)] \]

\section{Operators}

'''

for op_name, op_math in sorted(OPERATOR_MATH.items()):
    latex_doc += f"\n\subsection{{{op_math['name']}}}\n"
    latex_doc += f"Type: \\textit{{{op_math['math_type']}}}\n\n"
    latex_doc += op_math['latex'] + "\n"

latex_doc += r'''
\section{Composition}

Multi-step transformations are compositions:
\[ T = T_n \circ T_{n-1} \circ \cdots \circ T_1 \]

Applied right-to-left:
\[ G' = T_n(T_{n-1}(\cdots T_1(G) \cdots)) \]

\end{document}
'''

with open('arc_operators_math.tex', 'w') as f:
    f.write(latex_doc)

print(f"✅ Saved LaTeX document to: arc_operators_math.tex")
print()

print("="*80)
print("📊 MATHEMATICAL TRANSLATION SUMMARY")
print("="*80)
print()
print(f"Operators translated: {len(OPERATOR_MATH)}")
print(f"Rules enhanced: {len(math_enhanced_rules)}")
print()
print("Mathematical types:")
math_types = {}
for op_math in OPERATOR_MATH.values():
    mtype = op_math['math_type']
    math_types[mtype] = math_types.get(mtype, 0) + 1

for mtype, count in sorted(math_types.items(), key=lambda x: -x[1]):
    print(f"  {mtype}: {count} operators")

print()
print("="*80)
print("✅ MATHEMATICAL ENGINE COMPLETE")
print("="*80)
print()
print("Every transformation is now PURE MATH:")
print("  • Set theory (shapes, components)")
print("  • Linear algebra (reflections, rotations)")
print("  • Morphology (dilation, erosion)")
print("  • Graph theory (connectivity)")
print("  • Statistics (histogram operations)")
print("  • Constraint systems (packing, intervals)")
print()
print("Natural language → EQUATIONS")
print("Visual reasoning → SYMBOLIC COMPUTATION")
print()
print("Next: Query engine that matches NEW tasks to operators via MATHEMATICAL SIMILARITY")
