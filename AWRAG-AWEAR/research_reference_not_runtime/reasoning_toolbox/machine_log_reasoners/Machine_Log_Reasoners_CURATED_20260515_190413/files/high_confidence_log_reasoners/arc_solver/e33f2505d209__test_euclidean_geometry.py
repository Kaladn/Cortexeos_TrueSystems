#!/usr/bin/env python3
"""
Test Euclidean Geometry System
Validates object detection, ObjectSpace, and Transform library.
"""

import numpy as np
from engines.object_geometry import detect_objects, build_object_space, check_sector_collision
from engines.transform_library import TransformLibrary
from engines.rel_engine_v2 import RelEngineV2


def test_exact_lasso_detection():
    """Test 8-connected component detection with exact masks."""
    print("TEST: Exact lasso detection (8-connected)")
    
    # Create grid with diagonal shape (8-connected)
    grid = np.array([
        [0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 0, 1, 1, 0],
        [0, 0, 0, 0, 0],
    ])
    
    objects = detect_objects(grid)
    
    assert len(objects) == 1, f"Expected 1 object, got {len(objects)}"
    
    obj = objects[0]
    assert obj.pixel_count == 5, f"Expected 5 pixels, got {obj.pixel_count}"
    assert obj.color == 1, f"Expected color 1, got {obj.color}"
    
    # Check centroid is geometric center (not bbox center)
    expected_cy = (1 + 2 + 2 + 3 + 3) / 5  # 2.2
    expected_cx = (1 + 1 + 2 + 2 + 3) / 5  # 1.8
    
    cy, cx = obj.centroid
    assert abs(cy - expected_cy) < 0.01, f"Expected cy={expected_cy}, got {cy}"
    assert abs(cx - expected_cx) < 0.01, f"Expected cx={expected_cx}, got {cx}"
    
    print(f"  ✓ Object detected: {obj.pixel_count} pixels, centroid=({cy:.2f}, {cx:.2f})")
    print(f"  ✓ Radius: {obj.radius:.2f}")
    print(f"  ✓ Perimeter: {obj.perimeter}")
    print()


def test_object_space_geometry():
    """Test ObjectSpace with Euclidean distances and angles."""
    print("TEST: ObjectSpace Euclidean geometry")
    
    # Create grid with 3 objects
    grid = np.array([
        [1, 0, 0, 0, 2],
        [0, 0, 0, 0, 0],
        [0, 0, 3, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ])
    
    H, W = grid.shape
    objects = detect_objects(grid)
    
    assert len(objects) == 3, f"Expected 3 objects, got {len(objects)}"
    
    os = build_object_space(objects, H, W)
    
    # Check distance matrix
    assert os.D.shape == (3, 3), f"Expected D shape (3,3), got {os.D.shape}"
    
    # Distance from object 0 to object 1
    d_01 = os.D[0, 1]
    print(f"  ✓ Distance matrix: D[0,1] = {d_01:.2f}")
    
    # Check angles
    assert os.Theta.shape == (3, 3), f"Expected Theta shape (3,3), got {os.Theta.shape}"
    print(f"  ✓ Angle matrix: Theta[0,1] = {np.degrees(os.Theta[0, 1]):.1f}°")
    
    # Check distance from center
    center_y, center_x = (H - 1) / 2, (W - 1) / 2
    print(f"  ✓ Grid center: ({center_y}, {center_x})")
    print(f"  ✓ Distances from center: {os.d_center}")
    
    # Check sectors
    print(f"  ✓ Sector assignments: {[obj.sector for obj in os.objects]}")
    print()


def test_sector_collision():
    """Test sector collision detection."""
    print("TEST: Sector collision rule")
    
    # Create grid with 2 objects
    grid = np.array([
        [1, 0, 0],
        [0, 0, 2],
        [0, 0, 0],
    ])
    
    H, W = grid.shape
    objects = detect_objects(grid)
    
    # Initial: no collision (different sectors)
    valid = check_sector_collision(objects, H, W, num_sectors_y=2, num_sectors_x=2)
    assert valid, "Expected no collision initially"
    print("  ✓ No collision: objects in different sectors")
    
    # Move both objects to same centroid (collision)
    objects[0].centroid = (1.5, 1.5)
    objects[1].centroid = (1.5, 1.5)
    
    collision = not check_sector_collision(objects, H, W, num_sectors_y=2, num_sectors_x=2)
    assert collision, "Expected collision after moving to same sector"
    print("  ✓ Collision detected: objects in same sector")
    print()


def test_transform_translation():
    """Test translation transform."""
    print("TEST: Translation transform")
    
    # Input grid
    grid_in = np.array([
        [0, 1, 0],
        [0, 0, 0],
        [0, 0, 0],
    ])
    
    # Output grid (shifted right by 1)
    grid_out = np.array([
        [0, 0, 1],
        [0, 0, 0],
        [0, 0, 0],
    ])
    
    H, W = grid_in.shape
    objs_in = detect_objects(grid_in)
    objs_out = detect_objects(grid_out)
    
    os_in = build_object_space(objs_in, H, W)
    os_out = build_object_space(objs_out, H, W)
    
    # Test translation(0, 1)
    transform = TransformLibrary.create_translation(0, 1)
    matches = transform.matches(os_in, os_out)
    
    assert matches, "Translation should match"
    print("  ✓ Translation(0, 1) detected")
    print()


def test_transform_mirror():
    """Test mirror transform."""
    print("TEST: Mirror transform")
    
    # Input grid
    grid_in = np.array([
        [1, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ])
    
    # Output grid (mirrored vertically - flip left-right)
    grid_out = np.array([
        [0, 0, 0, 1],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ])
    
    H, W = grid_in.shape
    objs_in = detect_objects(grid_in)
    objs_out = detect_objects(grid_out)
    
    os_in = build_object_space(objs_in, H, W)
    os_out = build_object_space(objs_out, H, W)
    
    # Test vertical mirror
    transform = TransformLibrary.create_mirror_vertical()
    matches = transform.matches(os_in, os_out)
    
    assert matches, "Vertical mirror should match"
    print("  ✓ Mirror vertical detected")
    print()


def test_transform_library_full():
    """Test full transform library generation."""
    print("TEST: Full transform library")
    
    grid_in = np.array([
        [1, 0],
        [0, 2],
    ])
    
    H, W = grid_in.shape
    objs_in = detect_objects(grid_in)
    os_in = build_object_space(objs_in, H, W)
    
    # Generate all transforms
    transforms = TransformLibrary.generate_all_transforms(os_in, os_in)
    
    print(f"  ✓ Generated {len(transforms)} transforms")
    print(f"  ✓ Transform names: {set(t.name for t in transforms)}")
    print()


def test_rel_engine_v2():
    """Test REL-ENGINE v2 integration."""
    print("TEST: REL-ENGINE v2 integration")
    
    from engines.base_engine import TaskView
    
    # Create simple translation task
    grid_in1 = np.array([
        [0, 1, 0],
        [0, 0, 0],
    ])
    
    grid_out1 = np.array([
        [0, 0, 1],
        [0, 0, 0],
    ])
    
    task_view = TaskView(train_pairs=[(grid_in1, grid_out1)], test_input=grid_in1)
    
    engine = RelEngineV2()
    hypotheses = engine.analyze(task_view)
    
    print(f"  ✓ Generated {len(hypotheses)} hypotheses")
    if hypotheses:
        for hyp in hypotheses[:3]:
            print(f"    - {hyp.operation} (confidence={hyp.confidence:.2f})")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("EUCLIDEAN GEOMETRY SYSTEM TEST SUITE")
    print("=" * 60)
    print()
    
    try:
        test_exact_lasso_detection()
        test_object_space_geometry()
        test_sector_collision()
        test_transform_translation()
        test_transform_mirror()
        test_transform_library_full()
        test_rel_engine_v2()
        
        print("=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        raise
