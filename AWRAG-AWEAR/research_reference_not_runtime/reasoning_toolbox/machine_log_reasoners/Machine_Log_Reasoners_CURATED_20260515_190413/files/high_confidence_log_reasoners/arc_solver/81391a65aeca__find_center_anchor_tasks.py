"""
Find tasks where:
1. Input has a central region with one special color (anchor) surrounded by another color (ring/halo)
2. Output is that region extracted or transformed
3. Zeros outside are just padding

Like: 
  0 0 0 0 0
  0 8 8 8 0
  0 8 3 8 0   <- center=3, ring=8, zeros=noise
  0 8 8 8 0
  0 0 0 0 0

Output: 8 8 8
        8 3 8
        8 8 8
"""
import json
import numpy as np
from pathlib import Path
from collections import Counter

def find_non_zero_bbox(grid):
    """Find bounding box of non-zero elements"""
    non_zero = np.argwhere(grid != 0)
    if len(non_zero) == 0:
        return None
    min_r, min_c = non_zero.min(axis=0)
    max_r, max_c = non_zero.max(axis=0)
    return min_r, min_c, max_r + 1, max_c + 1

def has_center_anchor_structure(grid):
    """
    Check if grid has structure:
    - Outer layer: zeros (padding)
    - Middle layer: one color (ring/halo)
    - Center: different color (anchor)
    """
    arr = np.array(grid)
    h, w = arr.shape
    
    # Skip if too small
    if h < 3 or w < 3:
        return False
    
    # Find non-zero region
    bbox = find_non_zero_bbox(arr)
    if bbox is None:
        return False
    
    min_r, min_c, max_r, max_c = bbox
    region = arr[min_r:max_r, min_c:max_c]
    region_h, region_w = region.shape
    
    # Check if region is roughly square and at least 3×3
    if region_h < 3 or region_w < 3:
        return False
    
    if abs(region_h - region_w) > 1:
        return False
    
    # Count unique colors in region
    unique_colors = set(region.flatten()) - {0}
    
    # Should have exactly 2 non-zero colors (anchor + ring)
    if len(unique_colors) != 2:
        return False
    
    # Check if center cell is different from majority of cells
    center_r = region_h // 2
    center_c = region_w // 2
    center_color = region[center_r, center_c]
    
    # Count colors
    color_counts = Counter(region.flatten())
    del color_counts[0]  # Remove zeros
    
    # Center color should be minority
    colors = sorted(color_counts.items(), key=lambda x: x[1])
    if len(colors) == 2:
        minority_color, minority_count = colors[0]
        majority_color, majority_count = colors[1]
        
        # Center should be the minority color
        if center_color == minority_color:
            return True
    
    return False

def is_center_anchor_task(task_data):
    """Check if task involves center-anchor + halo pattern"""
    train_examples = task_data['train']
    
    input_matches = 0
    output_matches = 0
    
    for ex in train_examples:
        if has_center_anchor_structure(ex['input']):
            input_matches += 1
        if has_center_anchor_structure(ex['output']):
            output_matches += 1
    
    # Task matches if inputs OR outputs have the pattern
    return (input_matches >= len(train_examples) * 0.5) or (output_matches >= len(train_examples) * 0.5)

def main():
    # Load training data
    data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
    with open(data_path) as f:
        training_tasks = json.load(f)
    
    print("="*80)
    print("SEARCHING FOR CENTER-ANCHOR + HALO PATTERN")
    print("="*80)
    print()
    print("Pattern: Center cell (anchor) surrounded by one ring of different color")
    print()
    
    candidates = []
    
    for task_id, task_data in training_tasks.items():
        if is_center_anchor_task(task_data):
            candidates.append((task_id, task_data))
    
    if candidates:
        print(f"✅ FOUND {len(candidates)} TASKS WITH CENTER-ANCHOR PATTERN:")
        print()
        
        for task_id, task_data in candidates[:10]:  # Show first 10
            train_ex = task_data['train'][0]
            input_arr = np.array(train_ex['input'])
            output_arr = np.array(train_ex['output'])
            
            print(f"📌 TASK {task_id}")
            print(f"   Input shape: {input_arr.shape}, Output shape: {output_arr.shape}")
            
            # Show input if small enough
            if input_arr.shape[0] <= 10 and input_arr.shape[1] <= 10:
                print("   INPUT:")
                for row in input_arr:
                    print("     " + " ".join(str(x) for x in row))
            
            # Show output if small enough
            if output_arr.shape[0] <= 10 and output_arr.shape[1] <= 10:
                print("   OUTPUT:")
                for row in output_arr:
                    print("     " + " ".join(str(x) for x in row))
            
            print()
    else:
        print("❌ No center-anchor tasks found in training set")
    
    # Check evaluation set
    eval_path = Path('arc-prize-2024/arc-agi_evaluation_challenges.json')
    if eval_path.exists():
        print()
        print("Checking evaluation set...")
        with open(eval_path) as f:
            eval_tasks = json.load(f)
        
        eval_candidates = []
        for task_id, task_data in eval_tasks.items():
            if is_center_anchor_task(task_data):
                eval_candidates.append((task_id, task_data))
        
        if eval_candidates:
            print(f"✅ FOUND {len(eval_candidates)} CENTER-ANCHOR TASKS IN EVAL:")
            for task_id, task_data in eval_candidates[:5]:
                train_ex = task_data['train'][0]
                input_arr = np.array(train_ex['input'])
                output_arr = np.array(train_ex['output'])
                print(f"   {task_id}: {input_arr.shape} → {output_arr.shape}")

if __name__ == '__main__':
    main()
