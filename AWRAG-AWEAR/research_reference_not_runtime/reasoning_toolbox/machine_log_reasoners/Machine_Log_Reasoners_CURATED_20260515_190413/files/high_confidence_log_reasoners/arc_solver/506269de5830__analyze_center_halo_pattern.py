"""
Analyze tasks for center-anchor + halo pattern:
- Input has zeros (padding/noise) outside
- Center region has anchor cell + one-layer ring around it
- Output is just that cropped region (anchor + halo)
"""
import json
import numpy as np
from pathlib import Path

def find_non_zero_bbox(grid):
    """Find bounding box of non-zero elements"""
    non_zero = np.argwhere(grid != 0)
    if len(non_zero) == 0:
        return None
    min_r, min_c = non_zero.min(axis=0)
    max_r, max_c = non_zero.max(axis=0)
    return min_r, min_c, max_r + 1, max_c + 1

def is_center_halo_crop(input_grid, output_grid):
    """
    Check if transformation is:
    1. Input has padding of zeros
    2. Output is cropped to non-zero region (anchor + halo)
    3. Output is roughly square (3×3, 5×5, etc.)
    """
    input_arr = np.array(input_grid)
    output_arr = np.array(output_grid)
    
    # Find non-zero bounding box in input
    bbox = find_non_zero_bbox(input_arr)
    if bbox is None:
        return False
    
    min_r, min_c, max_r, max_c = bbox
    
    # Extract that region
    cropped = input_arr[min_r:max_r, min_c:max_c]
    
    # Check if output matches cropped region
    if cropped.shape != output_arr.shape:
        return False
    
    if not np.array_equal(cropped, output_arr):
        return False
    
    # Check if output is roughly square (allow ±1 difference)
    h, w = output_arr.shape
    if abs(h - w) > 1:
        return False
    
    # Check if output is small (3×3 to 7×7 range for halo patterns)
    if h < 3 or h > 7:
        return False
    
    return True

def analyze_task_for_center_halo(task_data):
    """Check if all training examples match center-halo crop pattern"""
    train_examples = task_data['train']
    
    matches = 0
    for ex in train_examples:
        if is_center_halo_crop(ex['input'], ex['output']):
            matches += 1
    
    return matches == len(train_examples) and len(train_examples) > 0

def main():
    # Load training data
    data_path = Path('arc-prize-2024/arc-agi_training_challenges.json')
    with open(data_path) as f:
        training_tasks = json.load(f)
    
    print("="*80)
    print("SEARCHING FOR CENTER-HALO CROP PATTERN")
    print("="*80)
    print()
    print("Pattern: Input with zero padding → Output crops to non-zero region")
    print()
    
    candidates = []
    
    for task_id, task_data in training_tasks.items():
        if analyze_task_for_center_halo(task_data):
            candidates.append(task_id)
    
    if candidates:
        print(f"✅ FOUND {len(candidates)} CENTER-HALO CROP TASKS:")
        print()
        
        for task_id in candidates:
            task_data = training_tasks[task_id]
            train_ex = task_data['train'][0]
            input_shape = np.array(train_ex['input']).shape
            output_shape = np.array(train_ex['output']).shape
            
            print(f"  {task_id}: {input_shape} → {output_shape}")
            
            # Show first example
            input_arr = np.array(train_ex['input'])
            output_arr = np.array(train_ex['output'])
            
            print("  INPUT:")
            for row in input_arr:
                print("    " + " ".join(str(x) for x in row))
            
            print("  OUTPUT:")
            for row in output_arr:
                print("    " + " ".join(str(x) for x in row))
            
            print()
    else:
        print("❌ No exact center-halo crop tasks found in training set")
        print()
        print("Let's check evaluation set...")
    
    # Also check evaluation set
    eval_path = Path('arc-prize-2024/arc-agi_evaluation_challenges.json')
    if eval_path.exists():
        with open(eval_path) as f:
            eval_tasks = json.load(f)
        
        eval_candidates = []
        for task_id, task_data in eval_tasks.items():
            if analyze_task_for_center_halo(task_data):
                eval_candidates.append(task_id)
        
        if eval_candidates:
            print(f"✅ FOUND {len(eval_candidates)} CENTER-HALO CROP IN EVAL:")
            for task_id in eval_candidates:
                task_data = eval_tasks[task_id]
                train_ex = task_data['train'][0]
                input_shape = np.array(train_ex['input']).shape
                output_shape = np.array(train_ex['output']).shape
                print(f"  {task_id}: {input_shape} → {output_shape}")

if __name__ == '__main__':
    main()
