"""
DEBUG HARNESS — Pattern Completion Prototype

Target Task: 00dbd492
Expected Behavior: Multiple shapes (one complete, others partial) → All completed

Math DSL Oracle:
- Objects: Prototype P, Partial instances {S₁, S₂, ...}
- Conditions: Each Sᵢ ⊂ P (partial match)
- Transform: For each Sᵢ:
    Find best alignment with P
    Complete Sᵢ → P at aligned position

Debug Checkpoints:
1. Prototype identification (largest connected component?)
2. Partial instance detection
3. Template matching
4. Alignment/placement correctness
"""
import json
import numpy as np
import sys
import os
from scipy.ndimage import label

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cod_616', 'arc_organ'))

from operators.pattern_completion_prototype import PatternCompletionPrototypeOperator

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

def extract_shapes(grid):
    """Extract all connected components"""
    shapes = []
    
    # Get unique colors (excluding background 0)
    colors = [c for c in np.unique(grid) if c != 0]
    
    for color in colors:
        mask = (grid == color)
        labeled, num_features = label(mask)
        
        for i in range(1, num_features + 1):
            component_mask = (labeled == i)
            rows, cols = np.where(component_mask)
            
            if len(rows) == 0:
                continue
            
            # Get bounding box
            r_min, r_max = rows.min(), rows.max()
            c_min, c_max = cols.min(), cols.max()
            
            # Extract shape
            shape_grid = grid[r_min:r_max+1, c_min:c_max+1].copy()
            shape_mask = component_mask[r_min:r_max+1, c_min:c_max+1]
            
            shapes.append({
                'color': color,
                'position': (r_min, c_min),
                'size': (r_max - r_min + 1, c_max - c_min + 1),
                'pixels': np.sum(shape_mask),
                'grid': shape_grid,
                'mask': shape_mask
            })
    
    return shapes

def debug_pattern_completion():
    """Debug pattern_completion_prototype operator"""
    print("="*80)
    print("DEBUG: pattern_completion_prototype")
    print("Target Task: 00dbd492")
    print("="*80)
    print()
    
    # Load task
    task_id = '00dbd492'
    try:
        data = load_task(task_id)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    
    # Show first training example
    train_ex = data['train'][0]
    inp = np.array(train_ex['input'])
    out = np.array(train_ex['output'])
    
    print("INPUT:")
    display_grid(inp)
    print(f"Shape: {inp.shape}")
    print()
    
    print("EXPECTED OUTPUT:")
    display_grid(out)
    print(f"Shape: {out.shape}")
    print()
    
    print("="*80)
    print("CHECKPOINT 1: Shape Extraction")
    print("="*80)
    print()
    
    # Extract shapes from input
    inp_shapes = extract_shapes(inp)
    print(f"Found {len(inp_shapes)} shapes in input:")
    for i, shape in enumerate(inp_shapes):
        print(f"  Shape {i+1}:")
        print(f"    Color: {shape['color']}")
        print(f"    Position: {shape['position']}")
        print(f"    Size: {shape['size']}")
        print(f"    Pixels: {shape['pixels']}")
        print()
    
    # Extract shapes from output
    out_shapes = extract_shapes(out)
    print(f"Found {len(out_shapes)} shapes in output:")
    for i, shape in enumerate(out_shapes):
        print(f"  Shape {i+1}:")
        print(f"    Color: {shape['color']}")
        print(f"    Position: {shape['position']}")
        print(f"    Size: {shape['size']}")
        print(f"    Pixels: {shape['pixels']}")
        print()
    
    print("="*80)
    print("CHECKPOINT 2: Prototype Identification")
    print("="*80)
    print()
    
    # Find largest shape (likely prototype)
    if inp_shapes:
        largest = max(inp_shapes, key=lambda s: s['pixels'])
        print("Largest shape (potential prototype):")
        print(f"  Color: {largest['color']}")
        print(f"  Size: {largest['size']}")
        print(f"  Pixels: {largest['pixels']}")
        print()
        print("Prototype grid:")
        display_grid(largest['grid'])
        print()
    
    # Check if smaller shapes are partial versions
    if len(inp_shapes) > 1:
        print("Checking if smaller shapes are partial:")
        smaller_shapes = [s for s in inp_shapes if s['pixels'] < largest['pixels']]
        
        for i, small in enumerate(smaller_shapes):
            print(f"\n  Shape {i+1} (color {small['color']}, {small['pixels']} pixels):")
            display_grid(small['grid'])
            
            # Check if it could be a partial match
            if small['size'][0] <= largest['size'][0] and small['size'][1] <= largest['size'][1]:
                print(f"    Could fit inside prototype")
                
                # Simple overlap check
                small_nonzero = np.sum(small['mask'])
                print(f"    Has {small_nonzero} non-zero pixels")
            else:
                print(f"    Larger than prototype in some dimension")
    
    print()
    
    print("="*80)
    print("CHECKPOINT 3: Input → Output Changes")
    print("="*80)
    print()
    
    # Compare input and output
    changed = (inp != out)
    num_changes = np.sum(changed)
    print(f"Number of changed cells: {num_changes}")
    
    if num_changes > 0 and num_changes <= 50:
        print("\nChanged positions:")
        changed_pos = np.argwhere(changed)
        for r, c in changed_pos[:20]:  # Show first 20
            print(f"  ({r},{c}): {inp[r,c]} → {out[r,c]}")
        if len(changed_pos) > 20:
            print(f"  ... and {len(changed_pos) - 20} more")
    
    print()
    
    print("="*80)
    print("CHECKPOINT 4: Analyze Phase")
    print("="*80)
    print()
    
    # Create operator
    op = PatternCompletionPrototypeOperator()
    
    # Run analyze
    config = op.analyze(inp, out)
    
    if config is None:
        print("❌ analyze() returned None")
        print()
        print("DIAGNOSIS:")
        print("  - Operator failed to detect pattern completion")
        print("  - Possible causes:")
        print("    1. Prototype identification not finding largest shape")
        print("    2. Partial instance detection threshold too strict")
        print("    3. Template matching not aligning correctly")
        print("    4. Completion logic not matching transformation")
        print()
        
        print("SUGGESTED FIX:")
        print("  1. Verify largest shape is identified as prototype")
        print("  2. Check partial ratio threshold (currently may be too high)")
        print("  3. Test if smaller shapes align with prototype")
        print("  4. Verify completion fills in missing pixels")
        print()
        
        # Manual check
        if len(inp_shapes) > 1:
            print("MANUAL CHECK:")
            print()
            
            # Find what changed per shape
            for shape in inp_shapes:
                r, c = shape['position']
                h, w = shape['size']
                
                inp_region = inp[r:r+h, c:c+w]
                out_region = out[r:r+h, c:c+w]
                
                region_changed = not np.array_equal(inp_region, out_region)
                
                if region_changed:
                    print(f"Shape at {shape['position']} changed:")
                    print("  Input:")
                    display_grid(inp_region)
                    print("  Output:")
                    display_grid(out_region)
                    print()
        
        return
    
    print(f"✓ analyze() returned config:")
    print(json.dumps(config, indent=2))
    print()
    
    print("="*80)
    print("CHECKPOINT 5: Apply Phase")
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
    debug_pattern_completion()
