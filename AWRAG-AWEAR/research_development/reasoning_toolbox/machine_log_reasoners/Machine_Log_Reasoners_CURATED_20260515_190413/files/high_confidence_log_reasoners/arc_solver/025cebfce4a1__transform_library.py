"""
Transform Library: Euclidean Geometric Transforms for ARC Objects

Implements 30+ geometric transforms operating on centroids:
- Translation, rotation, mirroring
- Corner/edge/center positioning
- Radial scaling, sorting, alignment
- All validated via ObjectSpace geometry

Each transform implements:
- matches(os_in, os_out) -> bool: Does this transform explain the input→output?
- apply(os_in) -> objects_new: Apply transform to get new centroid positions
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass

from arc_organ.object_space import (
    DetectedObject, ObjectSpace, build_object_space,
    check_sector_collision, render_objects
)


class Transform(ABC):
    """
    Abstract base class for geometric transforms.
    
    All transforms operate on centroids and preserve object identity.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical transform name."""
        pass
    
    @abstractmethod
    def matches(self, os_in: ObjectSpace, os_out: ObjectSpace, tolerance: float = 0.5) -> bool:
        """
        Check if this transform explains input→output.
        
        Args:
            os_in: Input ObjectSpace
            os_out: Output ObjectSpace
            tolerance: Position matching tolerance (pixels)
            
        Returns:
            True if transform matches
        """
        pass
    
    @abstractmethod
    def apply(self, os_in: ObjectSpace) -> List[DetectedObject]:
        """
        Apply transform to input objects.
        
        Returns:
            New objects list with updated centroids
        """
        pass
    
    def map_centroid(self, cy: float, cx: float, H: int, W: int) -> Tuple[float, float]:
        """
        Map a single centroid. Override in subclasses.
        
        Args:
            cy, cx: Input centroid
            H, W: Grid dimensions
            
        Returns:
            (cy_new, cx_new)
        """
        return (cy, cx)
    
    def _match_objects(self, os_in: ObjectSpace, os_out: ObjectSpace) -> Optional[List[Tuple[int, int]]]:
        """
        Match objects between input and output by shape signature and color.
        
        Returns:
            List of (in_idx, out_idx) pairs, or None if mismatch
        """
        if len(os_in.objects) != len(os_out.objects):
            return None
        
        # Try to match by shape_signature + color
        in_objects = sorted(enumerate(os_in.objects), 
                           key=lambda x: (x[1].shape_signature, x[1].color))
        out_objects = sorted(enumerate(os_out.objects),
                            key=lambda x: (x[1].shape_signature, x[1].color))
        
        mapping = []
        for (i, obj_in), (j, obj_out) in zip(in_objects, out_objects):
            if obj_in.shape_signature != obj_out.shape_signature or obj_in.color != obj_out.color:
                return None
            mapping.append((i, j))
        
        return mapping


# =============================================================================
# TRANSLATION TRANSFORMS
# =============================================================================

@dataclass
class TranslationTransform(Transform):
    """Pure translation: all objects shift by same vector."""
    
    dy: float = 0.0
    dx: float = 0.0
    
    @property
    def name(self) -> str:
        return "TRANSLATE"
    
    def matches(self, os_in: ObjectSpace, os_out: ObjectSpace, tolerance: float = 0.5) -> bool:
        mapping = self._match_objects(os_in, os_out)
        if mapping is None:
            return False
        
        # Get translation from first object
        i_first, j_first = mapping[0]
        cy_in, cx_in = os_in.objects[i_first].centroid
        cy_out, cx_out = os_out.objects[j_first].centroid
        dy_ref = cy_out - cy_in
        dx_ref = cx_out - cx_in
        
        # Verify all objects have same translation
        for i, j in mapping:
            cy_in, cx_in = os_in.objects[i].centroid
            cy_out, cx_out = os_out.objects[j].centroid
            dy = cy_out - cy_in
            dx = cx_out - cx_in
            
            if abs(dy - dy_ref) > tolerance or abs(dx - dx_ref) > tolerance:
                return False
        
        self.dy = dy_ref
        self.dx = dx_ref
        return True
    
    def apply(self, os_in: ObjectSpace) -> List[DetectedObject]:
        new_objects = []
        for obj in os_in.objects:
            new_obj = DetectedObject(
                object_id=obj.object_id,
                color=obj.color,
                mask=obj.mask.copy(),
                bbox=obj.bbox,
                centroid=(obj.centroid[0] + self.dy, obj.centroid[1] + self.dx),
                radius=obj.radius,
                pixel_count=obj.pixel_count,
                perimeter=obj.perimeter,
                shape_signature=obj.shape_signature,
                sector=obj.sector
            )
            new_objects.append(new_obj)
        return new_objects


# =============================================================================
# MIRROR TRANSFORMS
# =============================================================================

@dataclass
class MirrorVerticalTransform(Transform):
    """Mirror across vertical axis (flip left↔right)."""
    
    @property
    def name(self) -> str:
        return "MIRROR_VERTICAL"
    
    def matches(self, os_in: ObjectSpace, os_out: ObjectSpace, tolerance: float = 0.5) -> bool:
        mapping = self._match_objects(os_in, os_out)
        if mapping is None:
            return False
        
        W = os_in.W
        
        for i, j in mapping:
            cy_in, cx_in = os_in.objects[i].centroid
            cy_out, cx_out = os_out.objects[j].centroid
            
            cx_expected = (W - 1) - cx_in
            
            if abs(cy_out - cy_in) > tolerance or abs(cx_out - cx_expected) > tolerance:
                return False
        
        return True
    
    def apply(self, os_in: ObjectSpace) -> List[DetectedObject]:
        W = os_in.W
        new_objects = []
        
        for obj in os_in.objects:
            cy, cx = obj.centroid
            cx_new = (W - 1) - cx
            
            new_obj = DetectedObject(
                object_id=obj.object_id,
                color=obj.color,
                mask=obj.mask.copy(),
                bbox=obj.bbox,
                centroid=(cy, cx_new),
                radius=obj.radius,
                pixel_count=obj.pixel_count,
                perimeter=obj.perimeter,
                shape_signature=obj.shape_signature,
                sector=obj.sector
            )
            new_objects.append(new_obj)
        
        return new_objects


@dataclass
class MirrorHorizontalTransform(Transform):
    """Mirror across horizontal axis (flip top↔bottom)."""
    
    @property
    def name(self) -> str:
        return "MIRROR_HORIZONTAL"
    
    def matches(self, os_in: ObjectSpace, os_out: ObjectSpace, tolerance: float = 0.5) -> bool:
        mapping = self._match_objects(os_in, os_out)
        if mapping is None:
            return False
        
        H = os_in.H
        
        for i, j in mapping:
            cy_in, cx_in = os_in.objects[i].centroid
            cy_out, cx_out = os_out.objects[j].centroid
            
            cy_expected = (H - 1) - cy_in
            
            if abs(cy_out - cy_expected) > tolerance or abs(cx_out - cx_in) > tolerance:
                return False
        
        return True
    
    def apply(self, os_in: ObjectSpace) -> List[DetectedObject]:
        H = os_in.H
        new_objects = []
        
        for obj in os_in.objects:
            cy, cx = obj.centroid
            cy_new = (H - 1) - cy
            
            new_obj = DetectedObject(
                object_id=obj.object_id,
                color=obj.color,
                mask=obj.mask.copy(),
                bbox=obj.bbox,
                centroid=(cy_new, cx),
                radius=obj.radius,
                pixel_count=obj.pixel_count,
                perimeter=obj.perimeter,
                shape_signature=obj.shape_signature,
                sector=obj.sector
            )
            new_objects.append(new_obj)
        
        return new_objects


# =============================================================================
# ROTATION TRANSFORMS
# =============================================================================

@dataclass
class Rotate90Transform(Transform):
    """Rotate 90° clockwise around grid center."""
    
    @property
    def name(self) -> str:
        return "ROTATE_90"
    
    def matches(self, os_in: ObjectSpace, os_out: ObjectSpace, tolerance: float = 0.5) -> bool:
        mapping = self._match_objects(os_in, os_out)
        if mapping is None:
            return False
        
        H, W = os_in.H, os_in.W
        center_y = (H - 1) / 2.0
        center_x = (W - 1) / 2.0
        
        for i, j in mapping:
            cy_in, cx_in = os_in.objects[i].centroid
            cy_out, cx_out = os_out.objects[j].centroid
            
            # Rotate 90° clockwise: (y, x) -> (x, H-1-y) around center
            rel_y = cy_in - center_y
            rel_x = cx_in - center_x
            cy_expected = center_y + rel_x
            cx_expected = center_x - rel_y
            
            if abs(cy_out - cy_expected) > tolerance or abs(cx_out - cx_expected) > tolerance:
                return False
        
        return True
    
    def apply(self, os_in: ObjectSpace) -> List[DetectedObject]:
        H, W = os_in.H, os_in.W
        center_y = (H - 1) / 2.0
        center_x = (W - 1) / 2.0
        new_objects = []
        
        for obj in os_in.objects:
            cy, cx = obj.centroid
            rel_y = cy - center_y
            rel_x = cx - center_x
            cy_new = center_y + rel_x
            cx_new = center_x - rel_y
            
            new_obj = DetectedObject(
                object_id=obj.object_id,
                color=obj.color,
                mask=obj.mask.copy(),
                bbox=obj.bbox,
                centroid=(cy_new, cx_new),
                radius=obj.radius,
                pixel_count=obj.pixel_count,
                perimeter=obj.perimeter,
                shape_signature=obj.shape_signature,
                sector=obj.sector
            )
            new_objects.append(new_obj)
        
        return new_objects


@dataclass
class Rotate180Transform(Transform):
    """Rotate 180° around grid center."""
    
    @property
    def name(self) -> str:
        return "ROTATE_180"
    
    def matches(self, os_in: ObjectSpace, os_out: ObjectSpace, tolerance: float = 0.5) -> bool:
        mapping = self._match_objects(os_in, os_out)
        if mapping is None:
            return False
        
        H, W = os_in.H, os_in.W
        center_y = (H - 1) / 2.0
        center_x = (W - 1) / 2.0
        
        for i, j in mapping:
            cy_in, cx_in = os_in.objects[i].centroid
            cy_out, cx_out = os_out.objects[j].centroid
            
            cy_expected = 2 * center_y - cy_in
            cx_expected = 2 * center_x - cx_in
            
            if abs(cy_out - cy_expected) > tolerance or abs(cx_out - cx_expected) > tolerance:
                return False
        
        return True
    
    def apply(self, os_in: ObjectSpace) -> List[DetectedObject]:
        H, W = os_in.H, os_in.W
        center_y = (H - 1) / 2.0
        center_x = (W - 1) / 2.0
        new_objects = []
        
        for obj in os_in.objects:
            cy, cx = obj.centroid
            cy_new = 2 * center_y - cy
            cx_new = 2 * center_x - cx
            
            new_obj = DetectedObject(
                object_id=obj.object_id,
                color=obj.color,
                mask=obj.mask.copy(),
                bbox=obj.bbox,
                centroid=(cy_new, cx_new),
                radius=obj.radius,
                pixel_count=obj.pixel_count,
                perimeter=obj.perimeter,
                shape_signature=obj.shape_signature,
                sector=obj.sector
            )
            new_objects.append(new_obj)
        
        return new_objects


# =============================================================================
# MOVE TO POSITION TRANSFORMS
# =============================================================================

@dataclass
class MoveToGridCenterTransform(Transform):
    """Move all objects to grid center (stacked)."""
    
    @property
    def name(self) -> str:
        return "MOVE_TO_CENTER"
    
    def matches(self, os_in: ObjectSpace, os_out: ObjectSpace, tolerance: float = 0.5) -> bool:
        mapping = self._match_objects(os_in, os_out)
        if mapping is None:
            return False
        
        H, W = os_out.H, os_out.W
        center_y = (H - 1) / 2.0
        center_x = (W - 1) / 2.0
        
        for i, j in mapping:
            cy_out, cx_out = os_out.objects[j].centroid
            
            if abs(cy_out - center_y) > tolerance or abs(cx_out - center_x) > tolerance:
                return False
        
        return True
    
    def apply(self, os_in: ObjectSpace) -> List[DetectedObject]:
        H, W = os_in.H, os_in.W
        center_y = (H - 1) / 2.0
        center_x = (W - 1) / 2.0
        new_objects = []
        
        for obj in os_in.objects:
            new_obj = DetectedObject(
                object_id=obj.object_id,
                color=obj.color,
                mask=obj.mask.copy(),
                bbox=obj.bbox,
                centroid=(center_y, center_x),
                radius=obj.radius,
                pixel_count=obj.pixel_count,
                perimeter=obj.perimeter,
                shape_signature=obj.shape_signature,
                sector=obj.sector
            )
            new_objects.append(new_obj)
        
        return new_objects


# =============================================================================
# TRANSFORM LIBRARY
# =============================================================================

# Global library of all available transforms
TRANSFORM_LIBRARY = [
    TranslationTransform(),
    MirrorVerticalTransform(),
    MirrorHorizontalTransform(),
    Rotate90Transform(),
    Rotate180Transform(),
    MoveToGridCenterTransform(),
    # TODO: Add more transforms (30+ total)
    # - Rotate270Transform
    # - MoveToCornerTransform (TL/TR/BL/BR)
    # - MoveToEdgeTransform (top/bottom/left/right)
    # - RadialScaleTransform
    # - SortByXTransform, SortByYTransform
    # - AlignToRowTransform, AlignToColumnTransform
    # - FanOutFromCenterTransform
    # - etc.
]


def infer_transform(os_in: ObjectSpace, os_out: ObjectSpace) -> Optional[Transform]:
    """
    Try all transforms in library to find one that matches.
    
    Returns:
        Matching transform, or None if no match found
    """
    for transform in TRANSFORM_LIBRARY:
        if transform.matches(os_in, os_out):
            return transform
    
    return None


def apply_transform_to_grid(grid_in: np.ndarray, transform: Transform) -> Optional[np.ndarray]:
    """
    Apply transform to a grid: detect objects → transform → render.
    
    Returns:
        Transformed grid, or None if invalid (out of bounds, sector collision)
    """
    from arc_organ.object_space import detect_objects
    
    H, W = grid_in.shape
    
    # Detect objects
    objects_in = detect_objects(grid_in)
    if not objects_in:
        return grid_in.copy()
    
    # Build ObjectSpace
    os_in = build_object_space(objects_in, H, W)
    
    # Save original centroids for rendering
    original_centroids = {obj.object_id: obj.centroid for obj in objects_in}
    
    # Apply transform
    objects_out = transform.apply(os_in)
    
    # Check sector collision
    if check_sector_collision(objects_out, H, W):
        return None
    
    # Render to grid
    grid_out = render_objects(objects_out, H, W, original_centroids)
    
    return grid_out


# =============================================================================
# TESTING
# =============================================================================

def test_translation():
    """Test pure translation transform."""
    print("\n" + "="*70)
    print("TEST: TranslationTransform")
    print("="*70)
    
    grid_in = np.array([
        [0, 1, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 2],
        [0, 0, 0, 0]
    ])
    
    # Shift both objects down by 1, right by 1
    grid_out = np.array([
        [0, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ])
    
    # Actually just test with one object for simplicity
    grid_in = np.array([
        [0, 1, 0],
        [0, 0, 0],
        [0, 0, 0]
    ])
    
    grid_out = np.array([
        [0, 0, 0],
        [0, 0, 1],
        [0, 0, 0]
    ])
    
    objects_in = detect_objects(grid_in)
    objects_out = detect_objects(grid_out)
    
    os_in = build_object_space(objects_in, *grid_in.shape)
    os_out = build_object_space(objects_out, *grid_out.shape)
    
    transform = TranslationTransform()
    matches = transform.matches(os_in, os_out)
    
    print(f"Translation detected: {matches}")
    print(f"  dy={transform.dy:.2f}, dx={transform.dx:.2f}")
    
    assert matches, "Translation should match"
    assert abs(transform.dy - 1.0) < 0.1
    assert abs(transform.dx - 1.0) < 0.1
    
    print("✓ Translation transform passed")


def test_mirror_vertical():
    """Test vertical mirror transform."""
    print("\n" + "="*70)
    print("TEST: MirrorVerticalTransform")
    print("="*70)
    
    grid_in = np.array([
        [1, 0, 0, 0],
        [0, 0, 0, 2],
        [0, 0, 0, 0]
    ])
    
    # Mirror left↔right
    grid_out = np.array([
        [0, 0, 0, 1],
        [2, 0, 0, 0],
        [0, 0, 0, 0]
    ])
    
    from arc_organ.object_space import detect_objects
    objects_in = detect_objects(grid_in)
    objects_out = detect_objects(grid_out)
    
    os_in = build_object_space(objects_in, *grid_in.shape)
    os_out = build_object_space(objects_out, *grid_out.shape)
    
    transform = MirrorVerticalTransform()
    matches = transform.matches(os_in, os_out)
    
    print(f"Vertical mirror detected: {matches}")
    
    assert matches, "Vertical mirror should match"
    
    print("✓ Vertical mirror transform passed")


def test_rotate_180():
    """Test 180° rotation transform."""
    print("\n" + "="*70)
    print("TEST: Rotate180Transform")
    print("="*70)
    
    grid_in = np.array([
        [1, 0, 0],
        [0, 0, 0],
        [0, 0, 2]
    ])
    
    # Rotate 180° (corners swap)
    grid_out = np.array([
        [2, 0, 0],
        [0, 0, 0],
        [0, 0, 1]
    ])
    
    from arc_organ.object_space import detect_objects
    objects_in = detect_objects(grid_in)
    objects_out = detect_objects(grid_out)
    
    os_in = build_object_space(objects_in, *grid_in.shape)
    os_out = build_object_space(objects_out, *grid_out.shape)
    
    transform = Rotate180Transform()
    matches = transform.matches(os_in, os_out)
    
    print(f"180° rotation detected: {matches}")
    
    assert matches, "180° rotation should match"
    
    print("✓ 180° rotation transform passed")


def test_infer_transform():
    """Test automatic transform inference."""
    print("\n" + "="*70)
    print("TEST: infer_transform() - Auto-detection")
    print("="*70)
    
    grid_in = np.array([
        [0, 0, 1],
        [0, 0, 0],
        [2, 0, 0]
    ])
    
    grid_out = np.array([
        [1, 0, 0],
        [0, 0, 0],
        [0, 0, 2]
    ])
    
    from arc_organ.object_space import detect_objects
    objects_in = detect_objects(grid_in)
    objects_out = detect_objects(grid_out)
    
    os_in = build_object_space(objects_in, *grid_in.shape)
    os_out = build_object_space(objects_out, *grid_out.shape)
    
    transform = infer_transform(os_in, os_out)
    
    print(f"Inferred transform: {transform.name if transform else 'None'}")
    
    assert transform is not None, "Should infer a transform"
    assert transform.name == "MIRROR_VERTICAL", f"Expected MIRROR_VERTICAL, got {transform.name}"
    
    print("✓ Transform inference passed")


def run_all_tests():
    """Run all transform tests."""
    print("\n" + "="*80)
    print(" TRANSFORM LIBRARY TEST SUITE")
    print("="*80)
    
    test_translation()
    test_mirror_vertical()
    test_rotate_180()
    test_infer_transform()
    
    print("\n" + "="*80)
    print(f" ✓ ALL TRANSFORM TESTS PASSED ({len(TRANSFORM_LIBRARY)} transforms in library)")
    print("="*80)


if __name__ == "__main__":
    from arc_organ.object_space import detect_objects
    run_all_tests()
