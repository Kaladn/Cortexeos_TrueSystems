"""
DEBUG HARNESS — Checkerboard Tiling Alternating

Target Task: 00576224
Expected Behavior: 2×2 tile → 6×6 output with alternating flips

Math DSL Oracle:
- Objects: Pattern P ∈ ℕ^(h×w), Target size (H,W)
- Transform: For tile position (i,j):
    If (i+j) % 2 == 0: place P unchanged
    If (i+j) % 2 == 1: place flip(P, mode)

Debug Checkpoints:
1. Tile extraction (should find 2×2)
2. Flip detection (H/V/both/none)
3. Checkerboard placement logic
4. Output size calculation (2×2 → 6×6 = 3×3 tiles)
"""
import json
import numpy as np
import sys
import os

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cod_616', 'arc_organ'))

from operators.checkerboard_tiling_alternating import CheckerboardTilingAlternatingOperator

def display_grid(grid):
    """Visual display of grid"""
    for row in grid:
        print(' '.join(str(c) for c in row))

def load_task(task_id):
    """Load task from dataset"""
    # Try training data first
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

def debug_checkerboard_tiling():
    """Debug checkerboard_tiling_alternating operator"""
    print("="*80)
    print("DEBUG: checkerboard_tiling_alternating")
    print("Target Task: 00576224")
    print("="*80)
    print()
    
    # Load task
    task_id = '00576224'
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
    
    # Create operator
    op = CheckerboardTilingAlternatingOperator()
    
    print("="*80)
    print("CHECKPOINT 1: Tile Extraction")
    print("="*80)
    print()
    
    # Try to identify tile
    # The operator should find the 2×2 pattern
    print("Looking for repeating tile pattern...")
    print(f"Input is {inp.shape[0]}×{inp.shape[1]}")
    print(f"Output is {out.shape[0]}×{out.shape[1]}")
    print(f"Tile ratio: {out.shape[0] // inp.shape[0]} × {out.shape[1] // inp.shape[1]}")
    print()
    
    # Manual check: what is the tile?
    print("Input tile (assuming it's the whole input):")
    display_grid(inp)
    print()
    
    print("="*80)
    print("CHECKPOINT 2: Analyze Phase")
    print("="*80)
    print()
    
    # Run analyze
    config = op.analyze(inp, out)
    
    if config is None:
        print("❌ analyze() returned None")
        print()
        print("DIAGNOSIS:")
        print("  - Operator failed to detect checkerboard tiling pattern")
        print("  - Possible causes:")
        print("    1. Tile extraction logic not finding 2×2 pattern")
        print("    2. Flip detection not matching expected alternation")
        print("    3. Size ratio check too strict")
        print("    4. Pattern matching threshold too high")
        print()
        
        # Let's check what the operator is looking for
        print("MANUAL ANALYSIS:")
        print()
        
        # Check if output is exactly 3×3 tiles of input
        h_tiles = out.shape[0] // inp.shape[0]
        w_tiles = out.shape[1] // inp.shape[1]
        print(f"Tiling factor: {h_tiles} × {w_tiles}")
        
        if h_tiles * inp.shape[0] == out.shape[0] and w_tiles * inp.shape[1] == out.shape[1]:
            print("✓ Output size matches integer tiling")
        else:
            print("✗ Output size does NOT match integer tiling")
        print()
        
        # Check checkerboard pattern
        print("Checking for alternating flips:")
        for i in range(h_tiles):
            for j in range(w_tiles):
                tile_i = i * inp.shape[0]
                tile_j = j * inp.shape[1]
                tile_region = out[tile_i:tile_i+inp.shape[0], tile_j:tile_j+inp.shape[1]]
                
                # Compare with original
                match_orig = np.array_equal(tile_region, inp)
                match_h_flip = np.array_equal(tile_region, np.flipud(inp))
                match_v_flip = np.array_equal(tile_region, np.fliplr(inp))
                match_both = np.array_equal(tile_region, np.flipud(np.fliplr(inp)))
                
                print(f"  Tile [{i},{j}] at ({tile_i},{tile_j}):")
                if match_orig:
                    print(f"    Matches: ORIGINAL")
                elif match_h_flip:
                    print(f"    Matches: H_FLIP")
                elif match_v_flip:
                    print(f"    Matches: V_FLIP")
                elif match_both:
                    print(f"    Matches: BOTH_FLIP")
                else:
                    print(f"    Matches: NONE (transformed)")
                print()
        
        print("="*80)
        print("SUGGESTED FIX:")
        print("="*80)
        print()
        print("The operator needs to:")
        print("  1. Recognize input as the tile pattern")
        print("  2. Detect output size is 3×3 × tile size")
        print("  3. Check each tile position for flip pattern")
        print("  4. Identify which flip mode creates checkerboard")
        print()
        print("Current implementation may be:")
        print("  - Looking for smaller sub-tiles within input")
        print("  - Using wrong flip detection logic")
        print("  - Requiring exact alternation that doesn't match")
        
        return
    
    print(f"✓ analyze() returned config:")
    print(json.dumps(config, indent=2))
    print()
    
    print("="*80)
    print("CHECKPOINT 3: Apply Phase")
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
    debug_checkerboard_tiling()
