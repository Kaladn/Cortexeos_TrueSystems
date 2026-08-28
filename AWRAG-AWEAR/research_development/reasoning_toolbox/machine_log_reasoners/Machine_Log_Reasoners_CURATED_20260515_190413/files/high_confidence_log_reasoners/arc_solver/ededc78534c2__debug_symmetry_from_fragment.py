"""
DEBUG HARNESS — Symmetry From Fragment

Target Task: 017c7c7b
Expected Behavior: Partial pattern → Complete symmetric pattern

Math DSL Oracle:
- Objects: Fragment F, Symmetry type σ ∈ {H, V, R90, R180, R270}
- Conditions: F occupies quadrant/half of output
- Transform: 
    Reflect F across detected axis
    Or rotate F by detected angle
    Composite result into full pattern

Debug Checkpoints:
1. Fragment identification (non-background region)
2. Symmetry type detection (H/V/4-fold)
3. Reflection/rotation correctness
4. Fragment position logic
"""
import json
import numpy as np
import sys
import os

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cod_616', 'arc_organ'))

from operators.symmetry_from_fragment import SymmetryFromFragmentOperator

def display_grid(grid):
    """Visual display of grid"""
    for row in grid:
        print(' '.join(str(c) for c in row))

def load_task(task_id):
    """Load task from dataset"""
    train_path = f'cod_616/arc_data/training/{task_id}.json'
    eval_path = f'cod_616/arc_data/evaluation/{task_id}.json'
    
    if os.path.exists(train_path):
        with open(train_path) as f:
            return json.load(f)
    elif os.path.exists(eval_path):
        with open(eval_path) as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"Task {task_id} not found")

def check_symmetry(grid):
    """Check what symmetries exist in grid"""
    results = {}
    
    # Horizontal symmetry (flip up/down)
    h_sym = np.array_equal(grid, np.flipud(grid))
    results['horizontal'] = h_sym
    
    # Vertical symmetry (flip left/right)
    v_sym = np.array_equal(grid, np.fliplr(grid))
    results['vertical'] = v_sym
    
    # Rotational symmetries
    rot90 = np.rot90(grid, k=1)
    rot180 = np.rot90(grid, k=2)
    rot270 = np.rot90(grid, k=3)
    
    results['rot90'] = np.array_equal(grid, rot90)
    results['rot180'] = np.array_equal(grid, rot180)
    results['rot270'] = np.array_equal(grid, rot270)
    
    return results

def debug_symmetry_from_fragment():
    """Debug symmetry_from_fragment operator"""
    print("="*80)
    print("DEBUG: symmetry_from_fragment")
    print("Target Task: 017c7c7b")
    print("="*80)
    print()
    
    # Load task
    task_id = '017c7c7b'
    try:
        data = load_task(task_id)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    
    # Show first training example
    train_ex = data['train'][0]
    inp = np.array(train_ex['input'])
    out = np.array(train_ex['output'])
    
    print("INPUT (Fragment):")
    display_grid(inp)
    print(f"Shape: {inp.shape}")
    print()
    
    print("EXPECTED OUTPUT (Complete Symmetric):")
    display_grid(out)
    print(f"Shape: {out.shape}")
    print()
    
    print("="*80)
    print("CHECKPOINT 1: Symmetry Detection in Output")
    print("="*80)
    print()
    
    sym_check = check_symmetry(out)
    print("Output symmetries:")
    for sym_type, present in sym_check.items():
        status = "✓" if present else "✗"
        print(f"  {status} {sym_type}: {present}")
    print()
    
    print("="*80)
    print("CHECKPOINT 2: Fragment Analysis")
    print("="*80)
    print()
    
    # Check if input is subset of output
    if inp.shape == out.shape:
        print("Input and output same size")
        # Find non-zero regions
        inp_mask = inp != 0
        out_mask = out != 0
        
        inp_coverage = np.sum(inp_mask)
        out_coverage = np.sum(out_mask)
        
        print(f"Input has {inp_coverage} non-zero cells")
        print(f"Output has {out_coverage} non-zero cells")
        print(f"Ratio: {inp_coverage / out_coverage * 100:.1f}%")
        print()
        
        # Check if input non-zero cells are subset of output
        inp_in_out = np.all(inp_mask <= out_mask)
        print(f"Input is subset of output: {inp_in_out}")
        
        # Check where input cells are
        if inp_coverage > 0:
            inp_rows, inp_cols = np.where(inp_mask)
            print(f"Input occupies rows {inp_rows.min()}-{inp_rows.max()}, cols {inp_cols.min()}-{inp_cols.max()}")
            
            center_r = inp.shape[0] / 2
            center_c = inp.shape[1] / 2
            frag_center_r = (inp_rows.min() + inp_rows.max()) / 2
            frag_center_c = (inp_cols.min() + inp_cols.max()) / 2
            
            print(f"Grid center: ({center_r:.1f}, {center_c:.1f})")
            print(f"Fragment center: ({frag_center_r:.1f}, {frag_center_c:.1f})")
            
            # Determine quadrant
            if frag_center_r < center_r and frag_center_c < center_c:
                print("Fragment in: TOP-LEFT quadrant")
            elif frag_center_r < center_r and frag_center_c >= center_c:
                print("Fragment in: TOP-RIGHT quadrant")
            elif frag_center_r >= center_r and frag_center_c < center_c:
                print("Fragment in: BOTTOM-LEFT quadrant")
            else:
                print("Fragment in: BOTTOM-RIGHT quadrant")
    else:
        print(f"Different sizes: input {inp.shape}, output {out.shape}")
        # Input might be embedded or cropped
        if inp.shape[0] <= out.shape[0] and inp.shape[1] <= out.shape[1]:
            print("Input is smaller - might be a fragment to expand")
        else:
            print("Input is larger - might need cropping")
    
    print()
    
    print("="*80)
    print("CHECKPOINT 3: Analyze Phase")
    print("="*80)
    print()
    
    # Create operator
    op = SymmetryFromFragmentOperator()
    
    # Run analyze
    config = op.analyze(inp, out)
    
    if config is None:
        print("❌ analyze() returned None")
        print()
        print("DIAGNOSIS:")
        print("  - Operator failed to detect symmetric completion pattern")
        print("  - Possible causes:")
        print("    1. Fragment detection not working")
        print("    2. Symmetry type inference incorrect")
        print("    3. Fragment position logic wrong")
        print("    4. Size mismatch handling broken")
        print()
        
        print("SUGGESTED FIX:")
        print("  1. Check if operator requires same-size input/output")
        print("  2. Verify fragment identification (non-zero region)")
        print("  3. Test each symmetry type manually:")
        
        # Manual symmetry tests
        print()
        print("Manual Symmetry Tests:")
        
        if inp.shape == out.shape:
            # Try horizontal reflection
            h_reflect = np.flipud(inp)
            h_composite = np.maximum(inp, h_reflect)
            h_match = np.array_equal(h_composite, out)
            print(f"  {'✓' if h_match else '✗'} Horizontal reflection: {h_match}")
            
            # Try vertical reflection
            v_reflect = np.fliplr(inp)
            v_composite = np.maximum(inp, v_reflect)
            v_match = np.array_equal(v_composite, out)
            print(f"  {'✓' if v_match else '✗'} Vertical reflection: {v_match}")
            
            # Try 180° rotation
            rot180 = np.rot90(inp, k=2)
            rot_composite = np.maximum(inp, rot180)
            rot_match = np.array_equal(rot_composite, out)
            print(f"  {'✓' if rot_match else '✗'} 180° rotation: {rot_match}")
        
        return
    
    print(f"✓ analyze() returned config:")
    print(json.dumps(config, indent=2))
    print()
    
    print("="*80)
    print("CHECKPOINT 4: Apply Phase")
    print("="*80)
    print()
    
    # Apply to test input
    test_inp = np.array(data['test'][0]['input'])
    result = op.apply(test_inp, config)
    
    print("TEST INPUT:")
    display_grid(test_inp)
    print()
    
    print("ACTUAL OUTPUT:")
    display_grid(result)
    print()
    
    print("EXPECTED OUTPUT:")
    expected = np.array(data['test'][0]['output'])
    display_grid(expected)
    print()
    
    # Compare
    match = np.array_equal(result, expected)
    print(f"{'✅' if match else '❌'} Match: {match}")
    
    if not match:
        print()
        print("DIFFERENCES:")
        diff = result != expected
        diff_positions = np.argwhere(diff)
        print(f"  {len(diff_positions)} cells differ")
        if len(diff_positions) <= 20:
            for r, c in diff_positions:
                print(f"    ({r},{c}): got {result[r,c]}, expected {expected[r,c]}")

if __name__ == '__main__':
    debug_symmetry_from_fragment()
