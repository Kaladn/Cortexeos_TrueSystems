"""
Test ObjectSpace + Transform Library on real ARC tasks.

Validates the Euclidean geometry pipeline:
1. Detect objects with exact masks
2. Build ObjectSpace with pre-computed geometry
3. Infer geometric transforms
4. Apply and validate on test cases
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from arc_organ.object_space import detect_objects, build_object_space
from arc_organ.transform_library import infer_transform, apply_transform_to_grid, TRANSFORM_LIBRARY


def load_task(task_id: str, dataset: str = 'train'):
    """Load task from ARC dataset."""
    if dataset == 'train':
        path = 'arc-prize-2024/arc-agi_training_challenges.json'
    elif dataset == 'eval':
        path = 'arc-prize-2024/arc-agi_evaluation_challenges.json'
    else:
        raise ValueError(f"Unknown dataset: {dataset}")
    
    with open(path, 'r') as f:
        challenges = json.load(f)
    
    return challenges[task_id]


def test_simple_translation_task():
    """Test on a task with simple translation pattern."""
    print("\n" + "="*70)
    print("TEST: Simple Translation Pattern")
    print("="*70)
    
    # Create synthetic task
    train_examples = [
        {
            'input': [[0, 1, 0], [0, 0, 0], [0, 0, 0]],
            'output': [[0, 0, 0], [0, 0, 1], [0, 0, 0]]
        },
        {
            'input': [[2, 0, 0], [0, 0, 0], [0, 0, 0]],
            'output': [[0, 0, 0], [0, 2, 0], [0, 0, 0]]
        }
    ]
    
    # Learn from training
    grids_in = [np.array(ex['input']) for ex in train_examples]
    grids_out = [np.array(ex['output']) for ex in train_examples]
    
    # Detect pattern from first example
    objects_in = detect_objects(grids_in[0])
    objects_out = detect_objects(grids_out[0])
    
    os_in = build_object_space(objects_in, *grids_in[0].shape)
    os_out = build_object_space(objects_out, *grids_out[0].shape)
    
    transform = infer_transform(os_in, os_out)
    
    print(f"\nInferred transform: {transform.name if transform else 'None'}")
    
    if transform:
        # Validate on second training example
        prediction = apply_transform_to_grid(grids_in[1], transform)
        expected = grids_out[1]
        
        match = np.array_equal(prediction, expected)
        print(f"Second example matches: {match}")
        
        if match:
            print("✓ Translation pattern validated")
            return True
    
    print("✗ Pattern validation failed")
    return False


def test_mirror_pattern():
    """Test mirror transform detection."""
    print("\n" + "="*70)
    print("TEST: Mirror Pattern Detection")
    print("="*70)
    
    # Synthetic mirror task
    train_examples = [
        {
            'input': [[1, 0, 0], [0, 0, 2], [0, 0, 0]],
            'output': [[0, 0, 1], [2, 0, 0], [0, 0, 0]]
        }
    ]
    
    grid_in = np.array(train_examples[0]['input'])
    grid_out = np.array(train_examples[0]['output'])
    
    objects_in = detect_objects(grid_in)
    objects_out = detect_objects(grid_out)
    
    os_in = build_object_space(objects_in, *grid_in.shape)
    os_out = build_object_space(objects_out, *grid_out.shape)
    
    transform = infer_transform(os_in, os_out)
    
    print(f"\nInferred transform: {transform.name if transform else 'None'}")
    
    if transform and 'MIRROR' in transform.name:
        print(f"✓ Mirror pattern detected: {transform.name}")
        return True
    
    print("✗ Mirror pattern not detected")
    return False


def test_rotation_pattern():
    """Test rotation transform detection."""
    print("\n" + "="*70)
    print("TEST: Rotation Pattern Detection")
    print("="*70)
    
    # Synthetic 180° rotation task
    train_examples = [
        {
            'input': [[1, 0, 0], [0, 0, 0], [0, 0, 2]],
            'output': [[2, 0, 0], [0, 0, 0], [0, 0, 1]]
        }
    ]
    
    grid_in = np.array(train_examples[0]['input'])
    grid_out = np.array(train_examples[0]['output'])
    
    objects_in = detect_objects(grid_in)
    objects_out = detect_objects(grid_out)
    
    os_in = build_object_space(objects_in, *grid_in.shape)
    os_out = build_object_space(objects_out, *grid_out.shape)
    
    transform = infer_transform(os_in, os_out)
    
    print(f"\nInferred transform: {transform.name if transform else 'None'}")
    
    if transform and 'ROTATE' in transform.name:
        print(f"✓ Rotation pattern detected: {transform.name}")
        return True
    
    print("✗ Rotation pattern not detected")
    return False


def test_object_space_on_real_task():
    """Test ObjectSpace detection on a real ARC task."""
    print("\n" + "="*70)
    print("TEST: ObjectSpace on Real ARC Task")
    print("="*70)
    
    # Use a simple task
    try:
        task = load_task('007bbfb7', 'train')
        
        grid_in = np.array(task['train'][0]['input'])
        print(f"\nTask 007bbfb7 - Input shape: {grid_in.shape}")
        print(f"Input:\n{grid_in}")
        
        # Detect objects
        objects = detect_objects(grid_in)
        print(f"\n✓ Detected {len(objects)} objects")
        
        for obj in objects:
            print(f"  Object {obj.object_id}: color={obj.color}, "
                  f"centroid=({obj.centroid[0]:.2f},{obj.centroid[1]:.2f}), "
                  f"pixels={obj.pixel_count}")
        
        # Build ObjectSpace
        os = build_object_space(objects, *grid_in.shape)
        print(f"\n✓ Built ObjectSpace with {len(os.objects)} objects")
        print(f"  Distance matrix shape: {os.D.shape}")
        print(f"  Sectors occupied: {len(os.sectors)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_transform_library_coverage():
    """Test that transform library has diverse patterns."""
    print("\n" + "="*70)
    print("TEST: Transform Library Coverage")
    print("="*70)
    
    transform_types = set()
    for transform in TRANSFORM_LIBRARY:
        name_parts = transform.name.split('_')
        transform_types.add(name_parts[0])  # TRANSLATE, MIRROR, ROTATE, etc.
    
    print(f"\nTransform library: {len(TRANSFORM_LIBRARY)} transforms")
    print(f"Transform types: {', '.join(sorted(transform_types))}")
    
    # Check we have basic categories
    expected_types = {'TRANSLATE', 'MIRROR', 'ROTATE', 'MOVE'}
    missing = expected_types - transform_types
    
    if missing:
        print(f"⚠ Missing transform types: {', '.join(missing)}")
    
    if len(TRANSFORM_LIBRARY) >= 5:
        print(f"✓ Library has {len(TRANSFORM_LIBRARY)} transforms")
        return True
    else:
        print(f"✗ Library only has {len(TRANSFORM_LIBRARY)} transforms (need more)")
        return False


def run_all_integration_tests():
    """Run all integration tests."""
    print("\n" + "="*80)
    print(" OBJECTSPACE + TRANSFORM LIBRARY: INTEGRATION TESTS")
    print("="*80)
    
    results = []
    
    results.append(("Simple Translation", test_simple_translation_task()))
    results.append(("Mirror Detection", test_mirror_pattern()))
    results.append(("Rotation Detection", test_rotation_pattern()))
    results.append(("Real ARC Task", test_object_space_on_real_task()))
    results.append(("Library Coverage", test_transform_library_coverage()))
    
    # Summary
    print("\n" + "="*80)
    print(" INTEGRATION TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL INTEGRATION TESTS PASSED")
        print("\n🎯 Euclidean ObjectSpace Prototype: READY")
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
    
    print("="*80)


if __name__ == "__main__":
    run_all_integration_tests()
