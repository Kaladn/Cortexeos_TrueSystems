"""
SYSTEMATIC ARC PUZZLE DEBUGGING ALGORITHM

This script demonstrates the complete reasoning process for solving
an ARC task by carefully matching input shapes to output shapes.

Steps:
1. Extract all shapes from input (with scipy.ndimage.label)
2. Extract all shapes from output (same method)
3. Match input→output by column position (shapes don't move horizontally)
4. Analyze movement patterns (UP/DOWN/displacement)
5. Look for geometric features that predict movement
6. Formulate rule hypothesis
7. Test hypothesis on all examples
8. Implement operator
"""

import numpy as np
import json
from scipy import ndimage
from typing import List, Dict, Tuple

def extract_shapes(grid: np.ndarray) -> List[Dict]:
    """Extract all connected component shapes with full metadata"""
    shapes = []
    H, W = grid.shape
    
    for color in range(1, 10):
        mask = (grid == color)
        if not mask.any():
            continue
        
        labeled, num_shapes = ndimage.label(mask)
        
        for shape_id in range(1, num_shapes + 1):
            shape_mask = (labeled == shape_id)
            rows, cols = np.where(shape_mask)
            
            min_row, max_row = rows.min(), rows.max()
            min_col, max_col = cols.min(), cols.max()
            center_row = rows.mean()
            center_col = cols.mean()
            height = max_row - min_row + 1
            width = max_col - min_col + 1
            
            # Check geometric features
            center_r = (min_row + max_row) // 2
            center_c = (min_col + max_col) // 2
            has_center_pixel = grid[center_r, center_c] == color
            
            # Get full bounding box grid
            bbox_grid = grid[min_row:max_row+1, min_col:max_col+1]
            
            shapes.append({
                'color': color,
                'shape_id': shape_id,
                'pixels': list(zip(rows.tolist(), cols.tolist())),
                'num_pixels': len(rows),
                'min_row': min_row,
                'max_row': max_row,
                'min_col': min_col,
                'max_col': max_col,
                'center_row': center_row,
                'center_col': center_col,
                'height': height,
                'width': width,
                'has_center_pixel': has_center_pixel,
                'bbox_grid': bbox_grid,
            })
    
    return shapes

def match_input_to_output(input_shapes: List[Dict], output_shapes: List[Dict]) -> List[Tuple[Dict, Dict]]:
    """Match input shapes to output shapes by column position and color"""
    matches = []
    
    for in_shape in input_shapes:
        # Find output shape with same color and column range
        for out_shape in output_shapes:
            if (out_shape['color'] == in_shape['color'] and
                out_shape['min_col'] == in_shape['min_col'] and
                out_shape['max_col'] == in_shape['max_col']):
                matches.append((in_shape, out_shape))
                break
    
    return matches

def analyze_movement(in_shape: Dict, out_shape: Dict) -> Dict:
    """Analyze how a shape moved from input to output"""
    row_displacement = out_shape['min_row'] - in_shape['min_row']
    col_displacement = out_shape['min_col'] - in_shape['min_col']
    
    if row_displacement < 0:
        direction = "UP"
    elif row_displacement > 0:
        direction = "DOWN"
    else:
        direction = "SAME"
    
    return {
        'direction': direction,
        'row_displacement': row_displacement,
        'col_displacement': col_displacement,
        'moved_to_top': out_shape['min_row'] == 0,
        'moved_to_bottom': out_shape['max_row'] == (out_shape['bbox_grid'].shape[0] + out_shape['min_row'] - 1),
    }

def debug_task(task_name: str, examples: List[Dict]):
    """Complete debugging workflow for an ARC task"""
    print("="*80)
    print(f"DEBUGGING TASK: {task_name}")
    print("="*80)
    
    all_matches = []
    
    for ex_idx, example in enumerate(examples, 1):
        inp = np.array(example['input'])
        out = np.array(example['output'])
        H, W = inp.shape
        
        print(f"\n{'='*80}")
        print(f"EXAMPLE {ex_idx}: {H}x{W} grid")
        print(f"{'='*80}\n")
        
        # Step 1: Extract shapes
        print("STEP 1: Extract shapes from input and output")
        print("-" * 80)
        input_shapes = extract_shapes(inp)
        output_shapes = extract_shapes(out)
        print(f"Found {len(input_shapes)} input shapes, {len(output_shapes)} output shapes\n")
        
        # Step 2: Match input to output
        print("STEP 2: Match input shapes to output shapes")
        print("-" * 80)
        matches = match_input_to_output(input_shapes, output_shapes)
        all_matches.extend(matches)
        
        for in_s, out_s in matches:
            movement = analyze_movement(in_s, out_s)
            print(f"Color {in_s['color']} @ cols {in_s['min_col']}-{in_s['max_col']}:")
            print(f"  Input:  rows {in_s['min_row']}-{in_s['max_row']}, center=({in_s['center_row']:.1f}, {in_s['center_col']:.1f})")
            print(f"  Output: rows {out_s['min_row']}-{out_s['max_row']}, center=({out_s['center_row']:.1f}, {out_s['center_col']:.1f})")
            print(f"  Movement: {movement['direction']} by {movement['row_displacement']} rows")
            print()
    
    # Step 3: Look for patterns across all matches
    print("\n" + "="*80)
    print("STEP 3: Analyze patterns across all examples")
    print("="*80 + "\n")
    
    up_shapes = [(m[0], m[1]) for m in all_matches if analyze_movement(m[0], m[1])['direction'] == 'UP']
    down_shapes = [(m[0], m[1]) for m in all_matches if analyze_movement(m[0], m[1])['direction'] == 'DOWN']
    
    print(f"Shapes that moved UP: {len(up_shapes)}")
    print(f"Shapes that moved DOWN: {len(down_shapes)}\n")
    
    # Step 4: Test various hypotheses
    print("STEP 4: Test hypotheses for what determines UP vs DOWN")
    print("-" * 80 + "\n")
    
    # Hypothesis 1: Center row vs midpoint
    print("Hypothesis 1: center_row < midpoint → UP")
    correct = 0
    total = 0
    for in_s, out_s in all_matches:
        movement = analyze_movement(in_s, out_s)
        # Get grid height from bbox_grid shape (this is hacky, should pass H)
        # For now just check if prediction matches
        predicted = "UP" if in_s['center_row'] < 6.5 else "DOWN"  # Approximate
        if predicted == movement['direction']:
            correct += 1
        total += 1
    print(f"  Accuracy: {correct}/{total} = {100*correct/total:.1f}%\n")
    
    # Hypothesis 2: Center col vs midpoint
    print("Hypothesis 2: center_col < midpoint → UP")
    correct = 0
    for in_s, out_s in all_matches:
        movement = analyze_movement(in_s, out_s)
        predicted = "UP" if in_s['center_col'] < 6.5 else "DOWN"  # Approximate
        if predicted == movement['direction']:
            correct += 1
    print(f"  Accuracy: {correct}/{total} = {100*correct/total:.1f}%\n")
    
    # Hypothesis 3: Has center pixel (hollow vs filled)
    print("Hypothesis 3: hollow shape (no center pixel) → UP, filled → DOWN")
    correct = 0
    for in_s, out_s in all_matches:
        movement = analyze_movement(in_s, out_s)
        predicted = "UP" if not in_s['has_center_pixel'] else "DOWN"
        match_symbol = "✓" if predicted == movement['direction'] else "✗"
        if predicted == movement['direction']:
            correct += 1
        
        print(f"  Color {in_s['color']} @ cols {in_s['min_col']}-{in_s['max_col']}: "
              f"center_pixel={in_s['has_center_pixel']} → predict {predicted}, actual {movement['direction']} {match_symbol}")
    
    print(f"\n  Accuracy: {correct}/{total} = {100*correct/total:.1f}%\n")
    
    if correct == total:
        print("✓ RULE FOUND: Hollow shapes (empty center) → UP, Filled shapes → DOWN")
        print("\nSTEP 5: Implementation strategy")
        print("-" * 80)
        print("1. Extract all shapes using scipy.ndimage.label()")
        print("2. Check center pixel: grid[center_row, center_col] == color")
        print("3. Separate into hollow_shapes and filled_shapes lists")
        print("4. Pack hollow_shapes upward from row 0 using 2D bin packing")
        print("5. Pack filled_shapes downward from row H-1 using 2D bin packing")
        print("6. 2D bin packing: shapes can share rows if columns don't overlap")
    
    return all_matches

# Main execution
if __name__ == "__main__":
    # Load task
    with open('arc-prize-2025/arc-agi_training_challenges.json') as f:
        data = json.load(f)
    
    task = data['ac2e8ecf']
    
    # Run complete debugging workflow
    matches = debug_task('ac2e8ecf', task['train'])
    
    print("\n" + "="*80)
    print("DEBUGGING COMPLETE")
    print("="*80)
