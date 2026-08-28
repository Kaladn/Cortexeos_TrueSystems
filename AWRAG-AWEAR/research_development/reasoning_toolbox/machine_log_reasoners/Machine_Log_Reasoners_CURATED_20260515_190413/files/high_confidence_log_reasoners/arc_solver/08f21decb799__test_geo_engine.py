"""
Test GEO-ENGINE expanded operations

Tests:
1. Translation (shift with wraparound)
2. Scale (upsampling)
3. Transpose
4. Crop detection
"""

import numpy as np
from arc_core import ArcCore


def test_translation():
    """Test translation detection."""
    task = {
        'train': [
            {
                'input': [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
                'output': [[0, 0, 1], [0, 0, 0], [0, 0, 0]]  # Shifted right by 2
            }
        ],
        'test': [
            {'input': [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        ]
    }
    
    core = ArcCore()
    trace = core.solve(task, task_id="translation")
    
    print("=" * 60)
    print("TEST: Translation")
    print("=" * 60)
    print(f"Success: {trace.success}")
    print(f"Hypotheses: {len(trace.hypotheses_tried)}")
    for h in trace.hypotheses_tried:
        print(f"  {h}")
    
    return trace


def test_scale():
    """Test upscaling detection."""
    task = {
        'train': [
            {
                'input': [[1, 0], [0, 1]],
                'output': [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1]]  # 2x scale
            }
        ],
        'test': [
            {'input': [[1, 2], [3, 4]]}
        ]
    }
    
    core = ArcCore()
    trace = core.solve(task, task_id="scale_2x")
    
    print("\n" + "=" * 60)
    print("TEST: Scale 2x")
    print("=" * 60)
    print(f"Success: {trace.success}")
    print(f"Hypotheses: {len(trace.hypotheses_tried)}")
    for h in trace.hypotheses_tried:
        print(f"  {h}")
    
    if trace.success and trace.solution is not None:
        print("\nExpected output:")
        print([[1, 1, 2, 2], [1, 1, 2, 2], [3, 3, 4, 4], [3, 3, 4, 4]])
        print("\nActual output:")
        print(trace.solution.tolist())
    
    return trace


def test_transpose():
    """Test transpose detection."""
    task = {
        'train': [
            {
                'input': [[1, 2, 3], [4, 5, 6]],
                'output': [[1, 4], [2, 5], [3, 6]]
            }
        ],
        'test': [
            {'input': [[1, 0], [0, 1], [1, 1]]}
        ]
    }
    
    core = ArcCore()
    trace = core.solve(task, task_id="transpose")
    
    print("\n" + "=" * 60)
    print("TEST: Transpose")
    print("=" * 60)
    print(f"Success: {trace.success}")
    print(f"Hypotheses: {len(trace.hypotheses_tried)}")
    for h in trace.hypotheses_tried:
        print(f"  {h}")
    
    return trace


def test_geo_summary():
    """Run all GEO-ENGINE tests and summarize."""
    results = {
        'translation': test_translation(),
        'scale': test_scale(),
        'transpose': test_transpose(),
    }
    
    print("\n" + "=" * 60)
    print("GEO-ENGINE TEST SUMMARY")
    print("=" * 60)
    
    for name, trace in results.items():
        status = "PASS" if trace.success else "FAIL"
        hyp_count = len(trace.hypotheses_tried)
        print(f"{name:20s}: {status:4s} ({hyp_count} hypotheses)")
    
    total = len(results)
    passed = sum(1 for t in results.values() if t.success)
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")


if __name__ == "__main__":
    test_geo_summary()
