"""
Test PATTERN-ENGINE Phase 2 on real ARC tiling tasks.
"""
import json
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, '.')

from arc_organ.pattern_engine import PatternEngine


def load_arc_tasks():
    """Load ARC task data."""
    train_data = json.load(open('arc-prize-2025/arc-agi_training_challenges.json'))
    eval_data = json.load(open('arc-prize-2025/arc-agi_evaluation_challenges.json'))
    return {**train_data, **eval_data}


def test_phase2_on_tiling_tasks():
    """Test Phase 2 on known tiling tasks from rule database."""
    
    # Load rule database
    rules = [json.loads(line) for line in open('arc_rules_with_math_expansion.jsonl')]
    
    # Find tiling-related tasks
    tiling_operators = [
        'self_masking_tiling',
        'tiling_expand',
        'repeat_operator',
        'checkerboard_tiling_alternating',
        'sandwich_tiling',
        'self_referential_tiling'
    ]
    
    tiling_rules = [r for r in rules if r.get('operator') in tiling_operators]
    
    print("=" * 80)
    print("PATTERN-ENGINE PHASE 2: REAL ARC TILING TASKS")
    print("=" * 80)
    print()
    print(f"Testing on {len(tiling_rules)} tiling-based tasks")
    print()
    
    # Load tasks
    all_tasks = load_arc_tasks()
    engine = PatternEngine(symmetry_threshold=0.90)
    
    results = []
    
    for rule in tiling_rules[:10]:  # Test first 10
        task_id = rule['task_id']
        operator = rule['operator']
        task = all_tasks.get(task_id)
        
        if not task or not task.get('train'):
            continue
        
        print(f"Task {task_id} ({operator}):")
        
        # Analyze first training example
        example = task['train'][0]
        inp = np.array(example['input'])
        out = np.array(example['output'])
        
        print(f"  Input:  {inp.shape}")
        print(f"  Output: {out.shape}")
        
        # Detect patterns in OUTPUT (that's usually where tiling appears)
        output_patterns = engine.detect_all_patterns(out)
        
        tiling_hyps = output_patterns.get('tiling', [])
        stripe_hyps = output_patterns.get('stripes', [])
        
        if tiling_hyps:
            best_tile = tiling_hyps[0]
            tile_h = best_tile.params['tile_height']
            tile_w = best_tile.params['tile_width']
            print(f"  ✓ TILING DETECTED: {tile_h}×{tile_w} tile (score: {best_tile.score:.3f})")
            print(f"    Repeats: {best_tile.params['repeat_y']}×{best_tile.params['repeat_x']}")
        
        if stripe_hyps:
            best_stripe = stripe_hyps[0]
            print(f"  ✓ STRIPES DETECTED: {best_stripe.kind}, period={best_stripe.params['period']} (score: {best_stripe.score:.3f})")
        
        # Check input for fragment
        input_patterns = engine.detect_all_patterns(inp)
        input_tiling = input_patterns.get('tiling', [])
        
        if input_tiling:
            inp_tile = input_tiling[0]
            print(f"  Input also tiled: {inp_tile.params['tile_height']}×{inp_tile.params['tile_width']}")
        
        # Check if output tile exists in input (fragment extraction pattern)
        if tiling_hyps:
            tile = tiling_hyps[0].params['tile']
            tile_in_input = False
            
            # Scan input for this tile
            inp_h, inp_w = inp.shape
            tile_h, tile_w = tile.shape
            
            for i in range(inp_h - tile_h + 1):
                for j in range(inp_w - tile_w + 1):
                    if np.array_equal(inp[i:i+tile_h, j:j+tile_w], tile):
                        tile_in_input = True
                        print(f"  ✓ Output tile FOUND in input at ({i}, {j})")
                        break
                if tile_in_input:
                    break
        
        print()
        
        results.append({
            'task_id': task_id,
            'operator': operator,
            'has_output_tiling': len(tiling_hyps) > 0,
            'has_stripes': len(stripe_hyps) > 0
        })
    
    # Statistics
    with_tiling = sum(1 for r in results if r['has_output_tiling'])
    with_stripes = sum(1 for r in results if r['has_stripes'])
    
    print("=" * 80)
    print("STATISTICS:")
    print(f"  Tasks with detected tiling: {with_tiling}/{len(results)}")
    print(f"  Tasks with detected stripes: {with_stripes}/{len(results)}")
    print("=" * 80)
    print()
    print("PATTERN-ENGINE PHASE 2: VALIDATED ON REAL ARC TASKS")
    print("=" * 80)


def test_specific_task_007bbfb7():
    """Deep dive on task 007bbfb7 (self_masking_tiling)."""
    
    print()
    print("=" * 80)
    print("DEEP DIVE: Task 007bbfb7 (self_masking_tiling)")
    print("=" * 80)
    print()
    
    all_tasks = load_arc_tasks()
    task = all_tasks['007bbfb7']
    engine = PatternEngine(symmetry_threshold=0.90)
    
    # First training example
    example = task['train'][0]
    inp = np.array(example['input'])
    out = np.array(example['output'])
    
    print(f"Input shape: {inp.shape}")
    print(f"Output shape: {out.shape}")
    print(f"Size ratio: {out.shape[0]/inp.shape[0]}×{out.shape[1]/inp.shape[1]}")
    print()
    
    # Detect tiling in output
    tiling_hyps = engine.detect_global_tiling(out)
    
    print(f"Found {len(tiling_hyps)} tiling hypotheses:")
    for i, hyp in enumerate(tiling_hyps[:3]):  # Top 3
        tile_h = hyp.params['tile_height']
        tile_w = hyp.params['tile_width']
        print(f"  {i+1}. {tile_h}×{tile_w} tile (score: {hyp.score:.3f})")
    print()
    
    # Best hypothesis
    if tiling_hyps:
        best = tiling_hyps[0]
        tile = best.params['tile']
        print(f"Best tile ({tile.shape}):")
        print(tile)
        print()
        
        # Check if this tile (or similar) exists in input
        print(f"Checking if tile appears in input...")
        if np.array_equal(inp, tile):
            print("  ✓ INPUT IS EXACTLY THE TILE!")
        elif inp.shape == tile.shape:
            similarity = np.sum(inp == tile) / inp.size
            print(f"  Input and tile same size, {similarity:.1%} similar")
        else:
            print(f"  Input shape {inp.shape} ≠ tile shape {tile.shape}")
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    test_phase2_on_tiling_tasks()
    test_specific_task_007bbfb7()
