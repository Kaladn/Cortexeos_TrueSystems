"""Test the rotation hypothesis: align diagonal vertically, fill pattern, rotate back."""

import json
import numpy as np
from scipy.ndimage import rotate as scipy_rotate
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# Load task
with open('arc-prize-2024/arc-agi_training_challenges.json') as f:
    challenges = json.load(f)
with open('arc-prize-2024/arc-agi_training_solutions.json') as f:
    solutions = json.load(f)

task = challenges['05269061']

def extract_diagonal_colors_vertical(inp):
    """Extract the unique non-zero colors seen when reading top to bottom."""
    H, W = inp.shape
    
    # Find leftmost column that has non-zero values
    for c in range(W):
        col_colors = []
        for r in range(H):
            if inp[r, c] != 0:
                col_colors.append(int(inp[r, c]))
        if len(col_colors) > 0:
            # Get unique colors in order of first appearance
            seen = []
            for color in col_colors:
                if color not in seen:
                    seen.append(color)
            if len(seen) == 3:  # We expect 3 colors
                return seen
    
    # If not found in columns, try rows
    for r in range(H):
        row_colors = []
        for c in range(W):
            if inp[r, c] != 0:
                row_colors.append(int(inp[r, c]))
        if len(row_colors) > 0:
            seen = []
            for color in row_colors:
                if color not in seen:
                    seen.append(color)
            if len(seen) == 3:
                return seen
    
    # Fallback: just get unique non-zero colors
    unique = []
    for r in range(H):
        for c in range(W):
            color = int(inp[r, c])
            if color != 0 and color not in unique:
                unique.append(color)
    return unique

def create_pattern_from_colors(colors, size=7):
    """
    Create 3x3 repeating pattern from 3 colors.
    Pattern is:
    [c0, c1, c2]
    [c1, c2, c0]
    [c2, c0, c1]
    (a rotation pattern)
    """
    if len(colors) != 3:
        return None
    
    # Create the base 3x3 pattern (Latin square rotation)
    pattern_3x3 = np.array([
        [colors[0], colors[1], colors[2]],
        [colors[1], colors[2], colors[0]],
        [colors[2], colors[0], colors[1]]
    ])
    
    # Tile it to fill the output
    tiles_needed = (size + 2) // 3
    tiled = np.tile(pattern_3x3, (tiles_needed, tiles_needed))
    
    return tiled[:size, :size]

print("="*80)
print("ROTATION HYPOTHESIS TEST")
print("="*80)
print("\nStrategy:")
print("1. Extract colors from diagonal (reading vertically when aligned)")
print("2. Create 3x3 Latin square pattern with those colors")
print("3. Tile to 7x7")
print("="*80)

examples = [
    ("Train 1", np.array(task['train'][0]['input']), np.array(task['train'][0]['output'])),
    ("Train 2", np.array(task['train'][1]['input']), np.array(task['train'][1]['output'])),
    ("Train 3", np.array(task['train'][2]['input']), np.array(task['train'][2]['output'])),
    ("Test", np.array(task['test'][0]['input']), np.array(solutions['05269061'][0])),
]

for label, inp, expected_out in examples:
    print(f"\n{'='*80}")
    print(f"{label}")
    print(f"{'='*80}")
    
    # Extract colors
    colors = extract_diagonal_colors_vertical(inp)
    print(f"Extracted colors: {colors}")
    
    # Expected pattern
    expected_pattern = expected_out[:3, :3]
    expected_first_row = [int(expected_pattern[0, 0]), int(expected_pattern[0, 1]), int(expected_pattern[0, 2])]
    print(f"Expected first row: {expected_first_row}")
    
    # Try all 6 permutations of the 3 colors to see which creates the right pattern
    from itertools import permutations
    
    found_match = False
    for perm in permutations(colors):
        test_pattern = create_pattern_from_colors(list(perm))
        if test_pattern is not None:
            test_first_row = [int(test_pattern[0, 0]), int(test_pattern[0, 1]), int(test_pattern[0, 2])]
            if test_first_row == expected_first_row:
                print(f"✅ MATCH with permutation: {list(perm)}")
                print(f"   First row: {test_first_row}")
                
                # Check if full output matches
                if np.array_equal(test_pattern, expected_out):
                    print(f"   ✅ FULL OUTPUT MATCHES!")
                else:
                    print(f"   ⚠️  Pattern correct but checking differences...")
                    diff_count = np.sum(test_pattern != expected_out)
                    print(f"   Differences: {diff_count} pixels")
                
                found_match = True
                break
    
    if not found_match:
        print(f"❌ No permutation matched")

print(f"\n{'='*80}")
print("Now let's try your specific method:")
print("Read diagonal VERTICALLY to get color order, then create pattern")
print(f"{'='*80}")
