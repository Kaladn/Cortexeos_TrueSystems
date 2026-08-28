"""
Spatial Reasoning Operators for ARC

These operators handle object-based transformations:
- Object extraction (connected components)
- Spatial sorting (gravity, arrangement)
- Object placement (positioning)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'cod_616'))

import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from scipy import ndimage
from arc_organ.arc_operators import ArcOperator


def extract_objects(grid: np.ndarray) -> List[Dict[str, Any]]:
    """
    Extract connected component objects from grid
    
    Returns list of objects with:
    - mask: binary mask of object
    - bbox: (min_row, min_col, max_row, max_col)
    - color: primary color
    - center: (row, col) center of mass
    - pixels: list of (row, col) positions
    """
    objects = []
    
    # Get all non-zero colors
    colors = set(grid.flatten()) - {0}
    
    for color in colors:
        # Get binary mask for this color
        mask = (grid == color)
        
        # Label connected components
        labeled, num_features = ndimage.label(mask)
        
        for label_id in range(1, num_features + 1):
            obj_mask = (labeled == label_id)
            positions = np.argwhere(obj_mask)
            
            if len(positions) == 0:
                continue
            
            min_row, min_col = positions.min(axis=0)
            max_row, max_col = positions.max(axis=0)
            center_row, center_col = positions.mean(axis=0)
            
            objects.append({
                'mask': obj_mask,
                'bbox': (int(min_row), int(min_col), int(max_row), int(max_col)),
                'color': int(color),
                'center': (center_row, center_col),
                'pixels': positions.tolist(),
                'size': len(positions)
            })
    
    return objects


class GravitySortOperator(ArcOperator):
    """
    Sorts objects by vertical position (gravity effect)
    
    Pattern: Objects in upper half move to top, lower half move to bottom
    
    Solves tasks like ac2e8ecf where scattered objects consolidate
    to top and bottom regions with empty middle.
    """
    name = "gravity_sort"
    
    def analyze(self, input_grid: np.ndarray, output_grid: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Check if output is gravity-sorted version of input
        """
        H, W = input_grid.shape
        midpoint = H // 2
        
        # Extract objects from input
        input_objects = extract_objects(input_grid)
        if len(input_objects) == 0:
            return None
        
        # Classify objects by hemisphere
        upper_objects = [obj for obj in input_objects if obj['center'][0] < midpoint]
        lower_objects = [obj for obj in input_objects if obj['center'][0] >= midpoint]
        
        # Check if output has objects packed at top and bottom
        output_objects = extract_objects(output_grid)
        
        # Upper objects should be in top rows
        upper_out = [obj for obj in output_objects if obj['center'][0] < midpoint]
        
        # Lower objects should be in bottom rows  
        lower_out = [obj for obj in output_objects if obj['center'][0] >= midpoint]
        
        # Check color preservation
        input_colors = sorted([obj['color'] for obj in input_objects])
        output_colors = sorted([obj['color'] for obj in output_objects])
        
        if input_colors != output_colors:
            return None
        
        # Check if objects are arranged compactly
        # This is a complex pattern - for now just verify separation exists
        
        # Find gap in middle
        middle_rows = output_grid[midpoint-2:midpoint+3, :]
        if not np.all(middle_rows == 0):
            return None  # No clear gap
        
        return {
            'midpoint': midpoint,
            'num_upper': len(upper_objects),
            'num_lower': len(lower_objects)
        }
    
    def apply(self, input_grid: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """
        Apply gravity sort: move upper objects to top, lower to bottom
        """
        H, W = input_grid.shape
        midpoint = params.get('midpoint', H // 2)
        
        output = np.zeros_like(input_grid)
        
        # Extract objects
        objects = extract_objects(input_grid)
        
        # Separate by hemisphere
        upper_objects = [obj for obj in objects if obj['center'][0] < midpoint]
        lower_objects = [obj for obj in objects if obj['center'][0] >= midpoint]
        
        # Pack upper objects at top
        current_row = 0
        for obj in sorted(upper_objects, key=lambda o: (o['center'][0], o['center'][1])):
            min_r, min_c, max_r, max_c = obj['bbox']
            height = max_r - min_r + 1
            width = max_c - min_c + 1
            
            # Get object shape
            obj_grid = input_grid[min_r:max_r+1, min_c:max_c+1]
            
            # Place at top, preserving horizontal position
            if current_row + height <= midpoint and min_c + width <= W:
                output[current_row:current_row+height, min_c:min_c+width] = obj_grid
                current_row += height
        
        # Pack lower objects at bottom
        current_row = H - 1
        for obj in sorted(lower_objects, key=lambda o: (-o['center'][0], o['center'][1])):
            min_r, min_c, max_r, max_c = obj['bbox']
            height = max_r - min_r + 1
            width = max_c - min_c + 1
            
            # Get object shape
            obj_grid = input_grid[min_r:max_r+1, min_c:max_c+1]
            
            # Place at bottom, preserving horizontal position
            if current_row - height + 1 >= midpoint and min_c + width <= W:
                output[current_row-height+1:current_row+1, min_c:min_c+width] = obj_grid
                current_row -= height
        
        return output


class ObjectExtractOperator(ArcOperator):
    """
    Extract largest object (by pixel count)
    """
    name = "extract_largest_object"
    
    def analyze(self, input_grid: np.ndarray, output_grid: np.ndarray) -> Optional[Dict[str, Any]]:
        """Check if output is largest object from input"""
        input_objects = extract_objects(input_grid)
        if len(input_objects) == 0:
            return None
        
        # Find largest object
        largest = max(input_objects, key=lambda o: o['size'])
        
        # Check if output matches largest object (cropped)
        min_r, min_c, max_r, max_c = largest['bbox']
        expected = input_grid[min_r:max_r+1, min_c:max_c+1]
        
        if expected.shape != output_grid.shape:
            return None
        
        if not np.array_equal(expected, output_grid):
            return None
        
        return {'target': 'largest'}
    
    def apply(self, input_grid: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Extract and return largest object"""
        objects = extract_objects(input_grid)
        if len(objects) == 0:
            return input_grid
        
        largest = max(objects, key=lambda o: o['size'])
        min_r, min_c, max_r, max_c = largest['bbox']
        
        return input_grid[min_r:max_r+1, min_c:max_c+1].copy()


# Test on ac2e8ecf
if __name__ == "__main__":
    import json
    
    with open('arc-prize-2025/arc-agi_training_challenges.json', 'r') as f:
        data = json.load(f)
    
    task = data['ac2e8ecf']
    
    print(f"\n{'='*60}")
    print(f"Testing Spatial Operators on ac2e8ecf")
    print(f"{'='*60}\n")
    
    op = GravitySortOperator()
    
    for i, ex in enumerate(task['train'], 1):
        inp = np.array(ex['input'])
        out = np.array(ex['output'])
        
        print(f"Example {i}:")
        
        # Analyze
        params = op.analyze(inp, out)
        if params:
            print(f"  Analyze: OK - {params}")
            
            # Apply
            result = op.apply(inp, params)
            match = np.array_equal(result, out)
            print(f"  Apply: {'OK' if match else 'FAIL'}")
            
            if not match:
                print(f"  Expected shape: {out.shape}, Got: {result.shape}")
                print(f"  Differences: {np.sum(result != out)} cells")
        else:
            print(f"  Analyze: FAIL")
        print()
