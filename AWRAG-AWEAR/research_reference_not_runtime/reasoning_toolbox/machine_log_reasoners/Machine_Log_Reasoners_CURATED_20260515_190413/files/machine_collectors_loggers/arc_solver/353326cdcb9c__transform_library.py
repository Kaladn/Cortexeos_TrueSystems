#!/usr/bin/env python3
"""
Transform Library - Euclidean Geometry Operations
30+ pre-defined spatial transforms for rigid-body object manipulation.
"""

from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
import numpy as np
from engines.object_geometry import DetectedObject, ObjectSpace


@dataclass
class Transform:
    """
    Base transform with centroid mapping function.
    
    All transforms must implement:
    - name: str (canonical operation name)
    - map_centroid: function (cy, cx, H, W) -> (cy_new, cx_new)
    - matches: function (ObjectSpace_in, ObjectSpace_out) -> bool
    """
    name: str
    map_centroid: Callable[[float, float, int, int], Tuple[float, float]]
    matches: Callable[[ObjectSpace, ObjectSpace], bool]
    params: dict = None  # Transform-specific parameters
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


class TransformLibrary:
    """
    Library of 30+ geometric transforms.
    
    Each transform operates on centroids and preserves object masks.
    Transforms are tested in order until one matches input→output.
    """
    
    @staticmethod
    def create_translation(dy: float, dx: float) -> Transform:
        """Pure translation - all objects shift by same vector."""
        def map_centroid(cy, cx, H, W):
            return (cy + dy, cx + dx)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            if len(os_in.objects) != len(os_out.objects):
                return False
            
            if len(os_in.objects) == 0:
                return False
            
            # Match objects by shape_signature + color
            mapping = TransformLibrary._match_objects_by_signature(os_in, os_out)
            if mapping is None:
                return False
            
            # Verify all share same translation
            i_first, j_first = mapping[0]
            dy_ref = os_out.objects[j_first].centroid[0] - os_in.objects[i_first].centroid[0]
            dx_ref = os_out.objects[j_first].centroid[1] - os_in.objects[i_first].centroid[1]
            
            for i, j in mapping:
                dy_test = os_out.objects[j].centroid[0] - os_in.objects[i].centroid[0]
                dx_test = os_out.objects[j].centroid[1] - os_in.objects[i].centroid[1]
                
                if not (abs(dy_test - dy_ref) < 0.5 and abs(dx_test - dx_ref) < 0.5):
                    return False
            
            return True
        
        return Transform(
            name="TRANSLATE",
            map_centroid=map_centroid,
            matches=matches,
            params={'dy': dy, 'dx': dx}
        )
    
    @staticmethod
    def create_mirror_vertical() -> Transform:
        """Mirror all objects across vertical axis (flip left-right)."""
        def map_centroid(cy, cx, H, W):
            cx_new = (W - 1) - cx
            return (cy, cx_new)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            mapping = TransformLibrary._match_objects_by_signature(os_in, os_out)
            if mapping is None:
                return False
            
            for i, j in mapping:
                cy_i, cx_i = os_in.objects[i].centroid
                cy_j, cx_j = os_out.objects[j].centroid
                
                cx_expected = (os_in.W - 1) - cx_i
                
                if not (abs(cy_j - cy_i) < 0.5 and abs(cx_j - cx_expected) < 0.5):
                    return False
            
            return True
        
        return Transform(
            name="MIRROR_VERTICAL",
            map_centroid=map_centroid,
            matches=matches
        )
    
    @staticmethod
    def create_mirror_horizontal() -> Transform:
        """Mirror all objects across horizontal axis (flip top-bottom)."""
        def map_centroid(cy, cx, H, W):
            cy_new = (H - 1) - cy
            return (cy_new, cx)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            mapping = TransformLibrary._match_objects_by_signature(os_in, os_out)
            if mapping is None:
                return False
            
            for i, j in mapping:
                cy_i, cx_i = os_in.objects[i].centroid
                cy_j, cx_j = os_out.objects[j].centroid
                
                cy_expected = (os_in.H - 1) - cy_i
                
                if not (abs(cy_j - cy_expected) < 0.5 and abs(cx_j - cx_i) < 0.5):
                    return False
            
            return True
        
        return Transform(
            name="MIRROR_HORIZONTAL",
            map_centroid=map_centroid,
            matches=matches
        )
    
    @staticmethod
    def create_rotate_90cw() -> Transform:
        """Rotate 90° clockwise around grid center."""
        def map_centroid(cy, cx, H, W):
            center_y = (H - 1) / 2.0
            center_x = (W - 1) / 2.0
            
            dy = cy - center_y
            dx = cx - center_x
            
            # 90° CW: (x, y) -> (y, -x)
            dy_new = dx
            dx_new = -dy
            
            return (center_y + dy_new, center_x + dx_new)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            mapping = TransformLibrary._match_objects_by_signature(os_in, os_out)
            if mapping is None:
                return False
            
            center_y = (os_in.H - 1) / 2.0
            center_x = (os_in.W - 1) / 2.0
            
            for i, j in mapping:
                cy_i, cx_i = os_in.objects[i].centroid
                cy_j, cx_j = os_out.objects[j].centroid
                
                dy = cy_i - center_y
                dx = cx_i - center_x
                
                cy_expected = center_y + dx
                cx_expected = center_x - dy
                
                if not (abs(cy_j - cy_expected) < 0.5 and abs(cx_j - cx_expected) < 0.5):
                    return False
            
            return True
        
        return Transform(
            name="ROTATE_90CW",
            map_centroid=map_centroid,
            matches=matches
        )
    
    @staticmethod
    def create_rotate_180() -> Transform:
        """Rotate 180° around grid center."""
        def map_centroid(cy, cx, H, W):
            center_y = (H - 1) / 2.0
            center_x = (W - 1) / 2.0
            
            cy_new = 2 * center_y - cy
            cx_new = 2 * center_x - cx
            
            return (cy_new, cx_new)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            mapping = TransformLibrary._match_objects_by_signature(os_in, os_out)
            if mapping is None:
                return False
            
            center_y = (os_in.H - 1) / 2.0
            center_x = (os_in.W - 1) / 2.0
            
            for i, j in mapping:
                cy_i, cx_i = os_in.objects[i].centroid
                cy_j, cx_j = os_out.objects[j].centroid
                
                cy_expected = 2 * center_y - cy_i
                cx_expected = 2 * center_x - cx_i
                
                if not (abs(cy_j - cy_expected) < 0.5 and abs(cx_j - cx_expected) < 0.5):
                    return False
            
            return True
        
        return Transform(
            name="ROTATE_180",
            map_centroid=map_centroid,
            matches=matches
        )
    
    @staticmethod
    def create_move_to_corner(corner: str) -> Transform:
        """
        Move largest object to canonical corner.
        
        Args:
            corner: 'TL', 'TR', 'BL', 'BR'
        """
        def map_centroid(cy, cx, H, W):
            # Margin from edge (half object size)
            margin = 1.0
            
            if corner == 'TL':
                return (margin, margin)
            elif corner == 'TR':
                return (margin, W - 1 - margin)
            elif corner == 'BL':
                return (H - 1 - margin, margin)
            elif corner == 'BR':
                return (H - 1 - margin, W - 1 - margin)
            else:
                return (cy, cx)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            if len(os_in.objects) != len(os_out.objects):
                return False
            
            # Find largest object in input
            largest_idx = max(range(len(os_in.objects)), 
                            key=lambda i: os_in.objects[i].pixel_count)
            
            obj_out = os_out.objects[largest_idx]
            cy, cx = obj_out.centroid
            
            # Check if at specified corner (within margin)
            margin = 2.0
            H, W = os_in.H, os_in.W
            
            at_corner = False
            if corner == 'TL':
                at_corner = (cy < margin and cx < margin)
            elif corner == 'TR':
                at_corner = (cy < margin and cx > W - margin)
            elif corner == 'BL':
                at_corner = (cy > H - margin and cx < margin)
            elif corner == 'BR':
                at_corner = (cy > H - margin and cx > W - margin)
            
            return at_corner
        
        return Transform(
            name=f"MOVE_TO_CORNER_{corner}",
            map_centroid=map_centroid,
            matches=matches,
            params={'corner': corner}
        )
    
    @staticmethod
    def create_radial_scale(scale_factor: float) -> Transform:
        """
        Scale distance from grid center by factor.
        
        Objects move radially in/out from center.
        """
        def map_centroid(cy, cx, H, W):
            center_y = (H - 1) / 2.0
            center_x = (W - 1) / 2.0
            
            dy = cy - center_y
            dx = cx - center_x
            
            dy_new = dy * scale_factor
            dx_new = dx * scale_factor
            
            return (center_y + dy_new, center_x + dx_new)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            mapping = TransformLibrary._match_objects_by_signature(os_in, os_out)
            if mapping is None or len(mapping) == 0:
                return False
            
            # Check if all objects scale by same factor
            center_y = (os_in.H - 1) / 2.0
            center_x = (os_in.W - 1) / 2.0
            
            scales = []
            for i, j in mapping:
                cy_i, cx_i = os_in.objects[i].centroid
                cy_j, cx_j = os_out.objects[j].centroid
                
                r_in = np.sqrt((cy_i - center_y)**2 + (cx_i - center_x)**2)
                r_out = np.sqrt((cy_j - center_y)**2 + (cx_j - center_x)**2)
                
                if r_in > 0.5:  # Avoid division by zero
                    scales.append(r_out / r_in)
            
            if not scales:
                return False
            
            # All scales should be similar
            scale_mean = np.mean(scales)
            return all(abs(s - scale_mean) < 0.3 for s in scales)
        
        return Transform(
            name=f"RADIAL_SCALE",
            map_centroid=map_centroid,
            matches=matches,
            params={'scale': scale_factor}
        )
    
    @staticmethod
    def create_align_horizontal(target_y: float) -> Transform:
        """Align all objects to same horizontal line."""
        def map_centroid(cy, cx, H, W):
            return (target_y, cx)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            if len(os_out.objects) < 2:
                return False
            
            # Check if all output objects have same y coordinate
            y_coords = [obj.centroid[0] for obj in os_out.objects]
            return max(y_coords) - min(y_coords) < 1.0
        
        return Transform(
            name="ALIGN_HORIZONTAL",
            map_centroid=map_centroid,
            matches=matches,
            params={'target_y': target_y}
        )
    
    @staticmethod
    def create_align_vertical(target_x: float) -> Transform:
        """Align all objects to same vertical line."""
        def map_centroid(cy, cx, H, W):
            return (cy, target_x)
        
        def matches(os_in: ObjectSpace, os_out: ObjectSpace) -> bool:
            if len(os_out.objects) < 2:
                return False
            
            # Check if all output objects have same x coordinate
            x_coords = [obj.centroid[1] for obj in os_out.objects]
            return max(x_coords) - min(x_coords) < 1.0
        
        return Transform(
            name="ALIGN_VERTICAL",
            map_centroid=map_centroid,
            matches=matches,
            params={'target_x': target_x}
        )
    
    @staticmethod
    def _match_objects_by_signature(os_in: ObjectSpace, os_out: ObjectSpace) -> Optional[List[Tuple[int, int]]]:
        """
        Match objects between input and output by shape_signature + color.
        
        Returns:
            List of (input_idx, output_idx) pairs, or None if no valid mapping
        """
        if len(os_in.objects) != len(os_out.objects):
            return None
        
        # Try to match by (color, shape_signature)
        mapping = []
        used_out = set()
        
        for i, obj_in in enumerate(os_in.objects):
            found = False
            for j, obj_out in enumerate(os_out.objects):
                if j in used_out:
                    continue
                
                if (obj_in.color == obj_out.color and 
                    obj_in.shape_signature == obj_out.shape_signature):
                    mapping.append((i, j))
                    used_out.add(j)
                    found = True
                    break
            
            if not found:
                return None
        
        return mapping if len(mapping) == len(os_in.objects) else None
    
    @staticmethod
    def generate_all_transforms(os_in: ObjectSpace, os_out: ObjectSpace) -> List[Transform]:
        """
        Generate library of 30+ transforms to test.
        
        Returns list of transforms in priority order.
        """
        transforms = []
        
        # 1. Identity (no-op)
        transforms.append(TransformLibrary.create_translation(0, 0))
        
        # 2. Simple translations (common offsets)
        for dy in [-2, -1, 0, 1, 2]:
            for dx in [-2, -1, 0, 1, 2]:
                if dy != 0 or dx != 0:
                    transforms.append(TransformLibrary.create_translation(dy, dx))
        
        # 3. Mirrors
        transforms.append(TransformLibrary.create_mirror_vertical())
        transforms.append(TransformLibrary.create_mirror_horizontal())
        
        # 4. Rotations
        transforms.append(TransformLibrary.create_rotate_90cw())
        transforms.append(TransformLibrary.create_rotate_180())
        
        # 5. Corner moves
        for corner in ['TL', 'TR', 'BL', 'BR']:
            transforms.append(TransformLibrary.create_move_to_corner(corner))
        
        # 6. Radial scaling
        for scale in [0.5, 2.0, 3.0]:
            transforms.append(TransformLibrary.create_radial_scale(scale))
        
        # 7. Alignments
        if os_out.H > 0:
            transforms.append(TransformLibrary.create_align_horizontal(os_out.H / 2))
            transforms.append(TransformLibrary.create_align_horizontal(0))
            transforms.append(TransformLibrary.create_align_horizontal(os_out.H - 1))
        
        if os_out.W > 0:
            transforms.append(TransformLibrary.create_align_vertical(os_out.W / 2))
            transforms.append(TransformLibrary.create_align_vertical(0))
            transforms.append(TransformLibrary.create_align_vertical(os_out.W - 1))
        
        return transforms
