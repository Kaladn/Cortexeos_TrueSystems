"""
ObjectSpace: Euclidean Geometry for ARC Objects

Implements the canonical object representation with:
- Exact lasso masks (not bounding boxes)
- True geometric centroids
- Euclidean distances and angles
- Sector-based spatial reasoning

This is the foundation for COMP-ENGINE v2, REL-ENGINE v2, and SHAPE-ENGINE.
"""

import numpy as np
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class DetectedObject:
    """
    Canonical object representation with Euclidean geometry.
    
    All engines must use these exact field names (enforced by normalization).
    """
    object_id: int
    color: int
    mask: np.ndarray  # H×W bool array - exact lasso shape
    bbox: Tuple[int, int, int, int]  # (y0, x0, y1, x1) - metadata only
    centroid: Tuple[float, float]  # (cy, cx) - true geometric center
    radius: float  # max Euclidean distance from centroid to any pixel
    pixel_count: int
    perimeter: int
    shape_signature: int  # hash of cropped mask for "same shape?" checks
    sector: Tuple[int, int]  # (sy, sx) - coarse grid position
    
    # Optional geometric invariants
    moment_xx: float = 0.0
    moment_yy: float = 0.0
    moment_xy: float = 0.0


@dataclass
class ObjectSpace:
    """
    Pre-computed Euclidean geometry for all objects in a grid.
    
    Built once per grid and reused across all engines.
    """
    H: int
    W: int
    objects: List[DetectedObject]
    D: np.ndarray  # [N×N] pairwise distances between centroids
    Theta: np.ndarray  # [N×N] pairwise angles between centroids (radians)
    d_center: np.ndarray  # [N] distance from grid center
    sectors: Dict[Tuple[int, int], List[int]] = field(default_factory=dict)  # (sy,sx) -> [obj_ids]
    
    # Sector grid dimensions (3×3 default)
    num_sectors_y: int = 3
    num_sectors_x: int = 3
    
    def get_sector_size(self) -> Tuple[float, float]:
        """Get sector dimensions."""
        return (self.H / self.num_sectors_y, self.W / self.num_sectors_x)


def normalize_object_labels(obj: DetectedObject) -> DetectedObject:
    """
    Enforce canonical field names and validate completeness.
    
    This catches legacy names and raises explicit errors for missing fields.
    Maps: center→centroid, area→pixel_count, region→mask, etc.
    """
    # Check for legacy aliases and map them
    if hasattr(obj, 'center') and not hasattr(obj, 'centroid'):
        obj.centroid = obj.center
    
    if hasattr(obj, 'area') and not hasattr(obj, 'pixel_count'):
        obj.pixel_count = obj.area
    
    if hasattr(obj, 'region') and not hasattr(obj, 'mask'):
        obj.mask = obj.region
    
    if hasattr(obj, 'rect') and not hasattr(obj, 'bbox'):
        obj.bbox = obj.rect
    
    if hasattr(obj, 'shape_id') and not hasattr(obj, 'shape_signature'):
        obj.shape_signature = obj.shape_id
    
    # Validate required fields
    required = [
        'object_id', 'color', 'mask', 'bbox', 'centroid', 'radius',
        'pixel_count', 'perimeter', 'shape_signature', 'sector'
    ]
    
    for field_name in required:
        if not hasattr(obj, field_name):
            raise ValueError(f"Missing required field '{field_name}' in object {obj.object_id if hasattr(obj, 'object_id') else '?'}")
    
    return obj


def detect_objects(grid: np.ndarray) -> List[DetectedObject]:
    """
    Detect objects using 8-connected components with exact lasso masks.
    
    Returns objects with canonical labels (no bbox approximations).
    """
    H, W = grid.shape
    visited = np.zeros((H, W), dtype=bool)
    objects = []
    next_id = 0
    
    for y in range(H):
        for x in range(W):
            color = int(grid[y, x])
            
            # Skip background (0) and already visited
            if color == 0 or visited[y, x]:
                continue
            
            # 8-connected BFS for this color
            queue = [(y, x)]
            pixels = []
            visited[y, x] = True
            
            while queue:
                cy, cx = queue.pop(0)
                pixels.append((cy, cx))
                
                # Check all 8 neighbors
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        
                        ny, nx = cy + dy, cx + dx
                        
                        if 0 <= ny < H and 0 <= nx < W:
                            if not visited[ny, nx] and grid[ny, nx] == color:
                                visited[ny, nx] = True
                                queue.append((ny, nx))
            
            # Build exact boolean mask
            mask = np.zeros((H, W), dtype=bool)
            y_coords = []
            x_coords = []
            
            for py, px in pixels:
                mask[py, px] = True
                y_coords.append(py)
                x_coords.append(px)
            
            # Bounding box (metadata only)
            y0, y1 = min(y_coords), max(y_coords) + 1
            x0, x1 = min(x_coords), max(x_coords) + 1
            
            # True geometric centroid (mean of pixel coordinates)
            cy = float(np.mean(y_coords))
            cx = float(np.mean(x_coords))
            
            # Radius (max Euclidean distance from centroid)
            distances = [np.sqrt((py - cy)**2 + (px - cx)**2) for py, px in pixels]
            radius = float(max(distances)) if distances else 0.0
            
            # Perimeter (pixels with at least one non-object 4-connected neighbor)
            perimeter = 0
            for py, px in pixels:
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ny, nx = py + dy, px + dx
                    if 0 <= ny < H and 0 <= nx < W:
                        if not mask[ny, nx]:
                            perimeter += 1
                            break
                    else:
                        # Edge of grid counts as perimeter
                        perimeter += 1
                        break
            
            # Shape signature (hash of cropped mask)
            cropped = mask[y0:y1, x0:x1]
            shape_signature = hash(cropped.tobytes())
            
            # Moment invariants (optional, for orientation)
            moment_xx = float(np.sum([(py - cy)**2 for py, px in pixels]))
            moment_yy = float(np.sum([(px - cx)**2 for py, px in pixels]))
            moment_xy = float(np.sum([(py - cy) * (px - cx) for py, px in pixels]))
            
            obj = DetectedObject(
                object_id=next_id,
                color=color,
                mask=mask,
                bbox=(y0, x0, y1, x1),
                centroid=(cy, cx),
                radius=radius,
                pixel_count=len(pixels),
                perimeter=perimeter,
                shape_signature=shape_signature,
                sector=(0, 0),  # Will be set in build_object_space
                moment_xx=moment_xx,
                moment_yy=moment_yy,
                moment_xy=moment_xy
            )
            
            objects.append(obj)
            next_id += 1
    
    return objects


def build_object_space(objects: List[DetectedObject], H: int, W: int,
                       num_sectors_y: int = 3, num_sectors_x: int = 3) -> ObjectSpace:
    """
    Build ObjectSpace with pre-computed Euclidean geometry.
    
    Computes:
    - Pairwise distances and angles
    - Distances from grid center
    - Sector assignments
    """
    N = len(objects)
    
    # Initialize matrices
    D = np.zeros((N, N))
    Theta = np.zeros((N, N))
    d_center = np.zeros(N)
    sectors = defaultdict(list)
    
    # Grid center
    center_y = (H - 1) / 2.0
    center_x = (W - 1) / 2.0
    
    # Sector dimensions
    sector_h = H / num_sectors_y
    sector_w = W / num_sectors_x
    
    # Per-object geometry
    for i, obj in enumerate(objects):
        cy, cx = obj.centroid
        
        # Distance from grid center
        d_center[i] = np.sqrt((cy - center_y)**2 + (cx - center_x)**2)
        
        # Sector assignment
        sy = int(cy / sector_h)
        sx = int(cx / sector_w)
        sy = max(0, min(sy, num_sectors_y - 1))
        sx = max(0, min(sx, num_sectors_x - 1))
        obj.sector = (sy, sx)
        sectors[(sy, sx)].append(obj.object_id)
    
    # Pairwise geometry
    for i in range(N):
        cy_i, cx_i = objects[i].centroid
        for j in range(N):
            cy_j, cx_j = objects[j].centroid
            
            dy = cy_j - cy_i
            dx = cx_j - cx_i
            
            D[i, j] = np.sqrt(dy**2 + dx**2)
            Theta[i, j] = np.arctan2(dy, dx)
    
    return ObjectSpace(
        H=H,
        W=W,
        objects=objects,
        D=D,
        Theta=Theta,
        d_center=d_center,
        sectors=dict(sectors),
        num_sectors_y=num_sectors_y,
        num_sectors_x=num_sectors_x
    )


def check_sector_collision(objects: List[DetectedObject], H: int, W: int,
                           num_sectors_y: int = 3, num_sectors_x: int = 3) -> bool:
    """
    Check if any two objects rest in the same sector (illegal).
    
    Objects may pass through each other's sectors during movement,
    but cannot have final centroids in the same sector.
    """
    sector_h = H / num_sectors_y
    sector_w = W / num_sectors_x
    
    occupied = {}
    
    for obj in objects:
        cy, cx = obj.centroid
        sy = int(cy / sector_h)
        sx = int(cx / sector_w)
        sy = max(0, min(sy, num_sectors_y - 1))
        sx = max(0, min(sx, num_sectors_x - 1))
        
        if (sy, sx) in occupied:
            # Two objects in same sector - collision!
            return True
        
        occupied[(sy, sx)] = obj.object_id
    
    return False


def render_objects(objects: List[DetectedObject], H: int, W: int,
                   original_centroids: Optional[Dict[int, Tuple[float, float]]] = None) -> Optional[np.ndarray]:
    """
    Render objects to grid by shifting masks to new centroid positions.
    
    Args:
        objects: Objects with updated centroids
        H, W: Grid dimensions
        original_centroids: Optional dict of {obj_id: (cy, cx)} for computing shifts
        
    Returns:
        Grid with objects rendered, or None if objects go out of bounds
    """
    grid = np.zeros((H, W), dtype=int)
    
    for obj in objects:
        cy_new, cx_new = obj.centroid
        
        # Get original centroid (if not provided, assume mask is already positioned)
        if original_centroids and obj.object_id in original_centroids:
            cy_old, cx_old = original_centroids[obj.object_id]
        else:
            # Use current mask position (centroid of mask)
            mask_y, mask_x = np.where(obj.mask)
            if len(mask_y) == 0:
                continue
            cy_old = float(np.mean(mask_y))
            cx_old = float(np.mean(mask_x))
        
        # Compute shift
        dy = cy_new - cy_old
        dx = cx_new - cx_old
        
        # Shift each pixel in the mask
        mask_y, mask_x = np.where(obj.mask)
        
        for py, px in zip(mask_y, mask_x):
            ny = int(round(py + dy))
            nx = int(round(px + dx))
            
            # Check bounds
            if not (0 <= ny < H and 0 <= nx < W):
                return None  # Object went out of bounds
            
            # Place pixel (assume no overlaps after sector check)
            grid[ny, nx] = obj.color
    
    return grid


# ============================================================================
# Testing
# ============================================================================

def test_detect_objects():
    """Test 8-connected object detection with exact masks."""
    print("\n" + "="*70)
    print("TEST: detect_objects() - 8-connected exact masks")
    print("="*70)
    
    # Test grid with multiple objects
    grid = np.array([
        [0, 0, 0, 0, 0],
        [0, 1, 1, 0, 2],
        [0, 1, 1, 0, 0],
        [0, 0, 0, 3, 3],
        [0, 0, 0, 3, 0]
    ])
    
    objects = detect_objects(grid)
    
    print(f"\nDetected {len(objects)} objects")
    assert len(objects) == 3, f"Expected 3 objects, got {len(objects)}"
    
    for obj in objects:
        print(f"\nObject {obj.object_id}:")
        print(f"  Color: {obj.color}")
        print(f"  Centroid: ({obj.centroid[0]:.2f}, {obj.centroid[1]:.2f})")
        print(f"  Radius: {obj.radius:.2f}")
        print(f"  Pixel count: {obj.pixel_count}")
        print(f"  Perimeter: {obj.perimeter}")
        print(f"  BBox: {obj.bbox}")
        
        # Validate centroid is actually center of pixels
        mask_y, mask_x = np.where(obj.mask)
        expected_cy = np.mean(mask_y)
        expected_cx = np.mean(mask_x)
        assert abs(obj.centroid[0] - expected_cy) < 0.01
        assert abs(obj.centroid[1] - expected_cx) < 0.01
    
    print("\n✓ Object detection passed")


def test_object_space():
    """Test ObjectSpace construction with geometry."""
    print("\n" + "="*70)
    print("TEST: build_object_space() - Euclidean geometry")
    print("="*70)
    
    grid = np.array([
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 2]
    ])
    
    objects = detect_objects(grid)
    H, W = grid.shape
    
    os = build_object_space(objects, H, W)
    
    print(f"\nObjectSpace: {len(os.objects)} objects")
    print(f"Grid size: {os.H}×{os.W}")
    print(f"Sectors: {os.num_sectors_y}×{os.num_sectors_x}")
    
    print("\nDistance matrix:")
    print(os.D)
    
    print("\nAngle matrix (radians):")
    print(os.Theta)
    
    print("\nDistance from center:")
    print(os.d_center)
    
    print("\nSector occupancy:")
    for sector, obj_ids in os.sectors.items():
        print(f"  Sector {sector}: objects {obj_ids}")
    
    # Validate distances
    if len(objects) >= 2:
        cy1, cx1 = objects[0].centroid
        cy2, cx2 = objects[1].centroid
        expected_dist = np.sqrt((cy2 - cy1)**2 + (cx2 - cx1)**2)
        assert abs(os.D[0, 1] - expected_dist) < 0.01
        print(f"\n✓ Distance validation passed: {os.D[0, 1]:.2f}")
    
    print("\n✓ ObjectSpace construction passed")


def test_sector_collision():
    """Test sector collision detection."""
    print("\n" + "="*70)
    print("TEST: check_sector_collision() - Sector logic")
    print("="*70)
    
    # Create objects with same sector (should collide)
    obj1 = DetectedObject(
        object_id=0, color=1, mask=np.zeros((5, 5), bool),
        bbox=(0, 0, 1, 1), centroid=(1.0, 1.0), radius=1.0,
        pixel_count=1, perimeter=4, shape_signature=123, sector=(0, 0)
    )
    
    obj2 = DetectedObject(
        object_id=1, color=2, mask=np.zeros((5, 5), bool),
        bbox=(0, 0, 1, 1), centroid=(1.5, 1.5), radius=1.0,
        pixel_count=1, perimeter=4, shape_signature=456, sector=(0, 0)
    )
    
    collision = check_sector_collision([obj1, obj2], 5, 5, 3, 3)
    assert collision, "Expected collision in same sector"
    print("✓ Detected collision when objects in same sector")
    
    # Create objects in different sectors (no collision)
    obj2.centroid = (4.0, 4.0)
    collision = check_sector_collision([obj1, obj2], 5, 5, 3, 3)
    assert not collision, "Expected no collision in different sectors"
    print("✓ No collision when objects in different sectors")
    
    print("\n✓ Sector collision detection passed")


def run_all_tests():
    """Run all ObjectSpace tests."""
    print("\n" + "="*80)
    print(" OBJECT SPACE TEST SUITE")
    print("="*80)
    
    test_detect_objects()
    test_object_space()
    test_sector_collision()
    
    print("\n" + "="*80)
    print(" ✓ ALL OBJECT SPACE TESTS PASSED")
    print("="*80)


if __name__ == "__main__":
    run_all_tests()
