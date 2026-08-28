"""
Fill interior operator: Fill enclosed regions within object boundaries.

Task 00d62c1b pattern: Find hollow interiors and fill with new color.
"""

import numpy as np
from scipy.ndimage import binary_fill_holes


def fill_object_interior(grid: np.ndarray, target_color: int, fill_color: int) -> np.ndarray:
    """
    Fill enclosed interiors of objects with a new color.
    
    Args:
        grid: Input grid
        target_color: Color of boundary objects to process
        fill_color: Color to fill interiors with
    
    Returns:
        Grid with interiors filled
    """
    result = grid.copy()
    
    # Create binary mask of target color
    mask = (grid == target_color)
    
    # Fill holes in the mask (finds enclosed regions)
    filled_mask = binary_fill_holes(mask)
    
    # The interior is: filled - original
    interior_mask = filled_mask & ~mask
    
    # Fill interior with new color
    result[interior_mask] = fill_color
    
    return result


def test_fill_interior():
    """Test the fill interior operator on task 00d62c1b."""
    import json
    
    tasks = json.load(open('arc-prize-2024/arc-agi_training_challenges.json'))
    task = tasks['00d62c1b']
    
    print("\n" + "="*80)
    print("TESTING: Fill Interior Operator (Task 00d62c1b)")
    print("="*80)
    
    correct = 0
    total = 0
    
    for i, ex in enumerate(task['train']):
        grid_in = np.array(ex['input'])
        grid_out = np.array(ex['output'])
        
        # Apply operator: fill interiors of color 3 with color 4
        prediction = fill_object_interior(grid_in, target_color=3, fill_color=4)
        
        match = np.array_equal(prediction, grid_out)
        total += 1
        if match:
            correct += 1
        
        print(f"\nExample {i+1}: {'✓ MATCH' if match else '✗ FAIL'}")
        
        if not match:
            print(f"Expected shape: {grid_out.shape}")
            print(f"Got shape: {prediction.shape}")
            
            # Show difference
            diff = (prediction != grid_out)
            if diff.any():
                print(f"Differences at {np.sum(diff)} positions")
    
    print(f"\n{'='*80}")
    print(f"Training Accuracy: {correct}/{total} ({100*correct/total:.1f}%)")
    
    if correct == total:
        print("\n✓ OPERATOR VALIDATED - Testing on test input...")
        
        test_grid = np.array(task['test'][0]['input'])
        test_prediction = fill_object_interior(test_grid, target_color=3, fill_color=4)
        
        print(f"\nTest prediction shape: {test_prediction.shape}")
        print("\nTest OUTPUT:")
        for row in test_prediction:
            print('  ' + ' '.join(str(x) if x else '.' for x in row))
        
        return test_prediction
    
    return None


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    prediction = test_fill_interior()
    
    if prediction is not None:
        print("\n✓ READY TO SUBMIT")
