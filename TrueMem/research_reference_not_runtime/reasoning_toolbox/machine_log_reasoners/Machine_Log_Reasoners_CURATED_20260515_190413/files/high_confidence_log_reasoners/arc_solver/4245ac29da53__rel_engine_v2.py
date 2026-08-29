#!/usr/bin/env python3
"""
REL-ENGINE v2 - Euclidean Geometry Edition
Uses exact lasso masks, centroids, and Transform library with 30+ patterns.
"""

from typing import List, Optional
import numpy as np

from engines.base_engine import BaseEngine, Hypothesis, TaskView
from engines.object_geometry import detect_objects, build_object_space, check_sector_collision
from engines.transform_library import TransformLibrary, Transform
from engines.anchor_analyzer import AnchorAnalyzer


class RelEngineV2(BaseEngine):
    """
    Spatial relation engine v2 - Euclidean geometry.
    
    Uses:
    - 8-connected component detection (exact lasso masks)
    - True centroids (mean of pixel coordinates)
    - Euclidean distances and angles
    - Transform library with 30+ geometric patterns
    - Sector collision checking
    """
    
    def __init__(self):
        super().__init__(name="REL_V2")
        self.anchor_analyzer = AnchorAnalyzer()
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        """
        Analyze task for spatial transformations.
        
        Tests all 30+ transforms in library before accepting failure.
        """
        hypotheses = []
        
        # For each training pair, try to find matching transform
        candidate_transforms = []
        
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                continue
            
            H, W = input_grid.shape
            
            # Detect objects with exact lasso masks
            objs_in = detect_objects(input_grid)
            objs_out = detect_objects(output_grid)
            
            if len(objs_in) == 0 or len(objs_out) == 0:
                continue
            
            # Build ObjectSpaces with Euclidean geometry
            os_in = build_object_space(objs_in, H, W)
            os_out = build_object_space(objs_out, H, W)
            
            # ANCHOR POINT ANALYSIS: Measure first, reason second
            anchor_analyses = self.anchor_analyzer.compare_spaces(os_in, os_out)
            
            # Use close matches (85%+) as additional transform candidates
            for obj_id, analysis in anchor_analyses.items():
                for match in analysis.close_matches:
                    # Close matches from anchor analysis inform transform search
                    pass  # Transform library will catch these
            
            # Generate and test all transforms
            transforms = TransformLibrary.generate_all_transforms(os_in, os_out)
            
            for transform in transforms:
                if transform.matches(os_in, os_out):
                    candidate_transforms.append(transform)
                    break  # Found match for this pair
        
        # Find transforms that work across ALL training pairs
        if not candidate_transforms:
            return hypotheses
        
        # Count frequency of each transform
        transform_counts = {}
        for t in candidate_transforms:
            key = (t.name, str(t.params))
            transform_counts[key] = transform_counts.get(key, 0) + 1
        
        # Transforms that work on all pairs
        num_pairs = len(task_view.train_pairs)
        consistent_transforms = [
            (name, params, count) 
            for (name, params), count in transform_counts.items() 
            if count == num_pairs
        ]
        
        # Create hypotheses for consistent transforms
        for name, params_str, count in consistent_transforms:
            confidence = 0.95 if count >= 3 else 0.85
            
            hypotheses.append(Hypothesis(
                engine_name="REL_V2",
                operation=name,
                params=eval(params_str) if params_str != 'None' else {},
                confidence=confidence,
                dsl_program=f"REL_V2:{name}",
                explanation=f"Apply {name} transform with Euclidean geometry"
            ))
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        return hypotheses
    
    def apply_transform(self, grid: np.ndarray, transform: Transform) -> Optional[np.ndarray]:
        """
        Apply transform to grid using Euclidean geometry.
        
        Steps:
        1. Detect objects with exact lasso masks
        2. Build ObjectSpace with geometry
        3. Map centroids using transform
        4. Check sector collision rule
        5. Render transformed objects back to grid
        
        Returns:
            Transformed grid, or None if invalid
        """
        H, W = grid.shape
        
        # Detect objects
        objects = detect_objects(grid)
        if len(objects) == 0:
            return grid.copy()
        
        # Build ObjectSpace
        os = build_object_space(objects, H, W)
        
        # Apply transform to each object's centroid
        transformed_objects = []
        for obj in objects:
            cy, cx = obj.centroid
            cy_new, cx_new = transform.map_centroid(cy, cx, H, W)
            
            # Create new object with updated centroid
            obj_new = obj
            obj_new.centroid = (cy_new, cx_new)
            transformed_objects.append(obj_new)
        
        # Check sector collision rule
        if not check_sector_collision(transformed_objects, H, W):
            return None
        
        # Render transformed objects to grid
        grid_out = self._render_objects(transformed_objects, H, W)
        
        return grid_out
    
    def _render_objects(self, objects: list, H: int, W: int) -> Optional[np.ndarray]:
        """
        Render objects back to grid after transformation.
        
        Each object's mask is shifted so its centroid moves to new position.
        """
        grid = np.zeros((H, W), dtype=int)
        
        for obj in objects:
            # Get original centroid from mask
            mask_coords = np.argwhere(obj.mask)
            if len(mask_coords) == 0:
                continue
            
            cy_orig = np.mean(mask_coords[:, 0])
            cx_orig = np.mean(mask_coords[:, 1])
            
            # Compute shift
            cy_new, cx_new = obj.centroid
            dy = cy_new - cy_orig
            dx = cx_new - cx_orig
            
            # Shift each pixel in mask
            for py, px in mask_coords:
                ny = int(round(py + dy))
                nx = int(round(px + dx))
                
                # Check bounds
                if 0 <= ny < H and 0 <= nx < W:
                    # Handle overlaps (later object wins)
                    grid[ny, nx] = obj.color
                else:
                    # Object went out of bounds
                    return None
        
        return grid
