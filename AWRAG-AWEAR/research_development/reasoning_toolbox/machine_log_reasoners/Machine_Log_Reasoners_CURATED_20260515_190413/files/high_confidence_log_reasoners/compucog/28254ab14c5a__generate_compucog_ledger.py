"""
Generate the CompuCog 6-1-6 Master Ledger for all 53 solved tasks.

This creates the systematic reasoning fingerprints you requested:
- 6 Features (F)
- 1 Anchor (A) 
- 6 Derivations (D)

For EVERY solved task, to enable:
- Pattern mining across tasks
- Operator generalization
- Composition discovery
- Procedure reuse
"""
import json
import numpy as np
from pathlib import Path
from cod_616.arc_organ.arc_operators import OPERATORS

# The 53 SOLVED TASK IDs (from scan)
SOLVED_TASKS = [
    '007bbfb7', '05269061', '0d3d703e', '1cf80156', '25d8a9c8', '25ff71a9',
    '332efdb3', '3befdf3e', '3c9b0459', '496994bd', '4cd1b7b2', '50a16a69',
    '5582e5ca', '5b6cbef5', '60c09cac', '6150a2bd', '66e6c45b', '67a3c6ac',
    '68b16354', '6e02f1e3', '6ea4a07e', '74dd1130', '794b24be', '833966f4',
    '85c4e7cd', '87ab05b8', '880c1354', '9172f3a0', '9565186b', 'a416b8f3',
    'a59b95c0', 'a85d4709', 'ac0a08a4', 'ac2e8ecf', 'ad173014', 'b1948b0a',
    'b8cdaf2b', 'b91ae062', 'bda2d7a6', 'c59eb873', 'c8f0f002', 'caa06a1f',
    'ccd554ac', 'd037b0a7', 'd4b1c2b1', 'd511f180', 'd5d6de2d', 'e26a3af2',
    'e9afcf9a', 'ed36ccf7', 'f25ffba3', 'f76d97a5', 'f823c43c'
]

def extract_6f_features(inp_grid, out_grid):
    """Extract the 6 key features for CompuCog analysis."""
    H_in, W_in = inp_grid.shape
    H_out, W_out = out_grid.shape
    
    colors_in = set(inp_grid.flatten()) - {0}
    colors_out = set(out_grid.flatten()) - {0}
    
    # Count connected components
    from scipy import ndimage
    nonzero_in = (inp_grid > 0).astype(int)
    labeled_in, num_shapes_in = ndimage.label(nonzero_in)
    nonzero_out = (out_grid > 0).astype(int)
    labeled_out, num_shapes_out = ndimage.label(nonzero_out)
    
    features = {
        'F1_grid_transform': f"{H_in}x{W_in} → {H_out}x{W_out}",
        'F2_color_palette': f"In:{len(colors_in)} Out:{len(colors_out)} Colors:{colors_in}→{colors_out}",
        'F3_shape_count': f"{num_shapes_in} → {num_shapes_out} objects",
        'F4_symmetry': detect_symmetry(inp_grid, out_grid),
        'F5_spatial_structure': detect_spatial_structure(inp_grid, out_grid),
        'F6_transformation_type': classify_transform_type(inp_grid, out_grid)
    }
    return features

def detect_symmetry(inp, out):
    """Detect if symmetry is created/preserved."""
    def is_symmetric(grid):
        H, W = grid.shape
        h_sym = np.array_equal(grid, np.fliplr(grid))
        v_sym = np.array_equal(grid, np.flipud(grid))
        return h_sym, v_sym
    
    h_in, v_in = is_symmetric(inp)
    h_out, v_out = is_symmetric(out)
    
    if h_out and not h_in:
        return "H_symmetry_created"
    elif v_out and not v_in:
        return "V_symmetry_created"
    elif h_in and h_out:
        return "H_symmetry_preserved"
    elif v_in and v_out:
        return "V_symmetry_preserved"
    else:
        return "asymmetric"

def detect_spatial_structure(inp, out):
    """Detect spatial patterns: tiling, packing, expansion, etc."""
    H_in, W_in = inp.shape
    H_out, W_out = out.shape
    
    if H_out > H_in or W_out > W_in:
        return "expansion/tiling"
    elif H_out < H_in or W_out < W_in:
        return "cropping/compression"
    elif H_out == H_in and W_out == W_in:
        return "in-place_transform"
    else:
        return "unknown"

def classify_transform_type(inp, out):
    """Classify the type of transformation."""
    # Check if it's pure recoloring
    if inp.shape == out.shape and np.array_equal((inp > 0), (out > 0)):
        return "recoloring"
    
    # Check if size changed
    if inp.shape != out.shape:
        return "size_transform"
    
    # Check if shape positions changed
    return "spatial_rearrange"

def find_anchor(inp_grid, out_grid, task_data):
    """Find the 1 Anchor - the key structural element that drives the transformation."""
    H_in, W_in = inp_grid.shape
    H_out, W_out = out_grid.shape
    
    # Is there a dominant shape?
    from scipy import ndimage
    for color in range(1, 10):
        mask = (inp_grid == color)
        if mask.sum() > H_in * W_in * 0.3:  # >30% of grid
            return f"dominant_shape_color_{color}"
    
    # Is there a central element?
    center_r, center_c = H_in // 2, W_in // 2
    if inp_grid[center_r, center_c] != 0:
        return f"center_anchor_color_{inp_grid[center_r, center_c]}"
    
    # Is there a grid/tiling pattern?
    if H_out > H_in and H_out % H_in == 0:
        return f"tile_pattern_{H_out//H_in}x{W_out//W_in}"
    
    # Is there a boundary marker?
    boundary_colors = set()
    boundary_colors.update(inp_grid[0, :])
    boundary_colors.update(inp_grid[-1, :])
    boundary_colors.update(inp_grid[:, 0])
    boundary_colors.update(inp_grid[:, -1])
    boundary_colors.discard(0)
    if len(boundary_colors) == 1:
        return f"boundary_marker_color_{list(boundary_colors)[0]}"
    
    return "no_clear_anchor"

def generate_6d_derivations(inp_grid, out_grid, operator_name, task_data):
    """Generate the 6 derivation steps showing the reasoning chain."""
    # This is operator-specific - we'll generate a template
    derivations = {
        'D1_input_analysis': f"Extract grid {inp_grid.shape}, detect patterns",
        'D2_anchor_identification': f"Identify key structural element",
        'D3_transformation_rule': f"Apply operator: {operator_name}",
        'D4_intermediate_state': "Compute intermediate transformation",
        'D5_final_synthesis': "Generate output grid",
        'D6_validation': "Verify output matches expected"
    }
    return derivations

def generate_fingerprint(task_id, task_data, operator_name):
    """Generate full 6-1-6 CompuCog fingerprint for a task."""
    inp = np.array(task_data['train'][0]['input'])
    out = np.array(task_data['train'][0]['output'])
    
    features = extract_6f_features(inp, out)
    anchor = find_anchor(inp, out, task_data)
    derivations = generate_6d_derivations(inp, out, operator_name, task_data)
    
    fingerprint = {
        'task_id': task_id,
        'operator': operator_name,
        'features_6f': features,
        'anchor_1a': anchor,
        'derivations_6d': derivations
    }
    
    return fingerprint

print("="*80)
print("🧠 COMPUCOG 6-1-6 MASTER LEDGER GENERATION")
print("="*80)
print()
print(f"Generating fingerprints for {len(SOLVED_TASKS)} solved tasks...")
print()

# Load data
with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
    data = json.load(f)

# Map operators
op_dict = {op.name: op for op in OPERATORS}

# Find which operator solves each task
task_to_operator = {}
for task_id in SOLVED_TASKS:
    task = data[task_id]
    for op_name, op in op_dict.items():
        try:
            inp = np.array(task['train'][0]['input'])
            out = np.array(task['train'][0]['output'])
            params = op.analyze(inp, out)
            if params is not None:
                result = op.apply(inp, params)
                if np.array_equal(result, out):
                    task_to_operator[task_id] = op_name
                    break
        except:
            continue

# Generate fingerprints
fingerprints = []
for task_id in SOLVED_TASKS:
    if task_id in task_to_operator:
        task = data[task_id]
        operator_name = task_to_operator[task_id]
        fp = generate_fingerprint(task_id, task, operator_name)
        fingerprints.append(fp)
        print(f"✓ {task_id} → {operator_name}")

print()
print("="*80)
print("📘 MASTER LEDGER TABLE")
print("="*80)
print()
print(f"{'Task ID':<12} {'Operator':<30} {'Grid Transform':<20} {'Transform Type':<20}")
print("-"*80)

for fp in fingerprints:
    print(f"{fp['task_id']:<12} {fp['operator']:<30} {fp['features_6f']['F1_grid_transform']:<20} {fp['features_6f']['F6_transformation_type']:<20}")

# Save to JSON
output = {
    'total_tasks': len(fingerprints),
    'fingerprints': fingerprints
}

with open('compucog_616_master_ledger.json', 'w') as f:
    json.dump(output, f, indent=2)

print()
print("="*80)
print("✅ MASTER LEDGER SAVED")
print("="*80)
print(f"File: compucog_616_master_ledger.json")
print(f"Contains {len(fingerprints)} full 6-1-6 fingerprints")
print()
print("Next steps:")
print("  1. Pattern clustering analysis")
print("  2. Operator generalization mining")
print("  3. Composition blueprint extraction")
print("  4. Auto-fingerprint generator for new tasks")
