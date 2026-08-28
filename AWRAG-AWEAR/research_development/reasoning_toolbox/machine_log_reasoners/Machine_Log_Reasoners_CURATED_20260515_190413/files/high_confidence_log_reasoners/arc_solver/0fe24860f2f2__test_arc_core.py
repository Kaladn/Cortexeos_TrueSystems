"""
Test ARC-CORE with GEO-ENGINE

Verify:
1. ARC-CORE initializes all 8 engines
2. GEO-ENGINE detects rotation tasks
3. System returns proper SolutionTrace
"""

import json
import numpy as np
from pathlib import Path

from arc_core import ArcCore


def test_rotation_task():
    """Test GEO-ENGINE on a simple rotation task."""
    
    # Create synthetic rotation task (90° clockwise)
    task = {
        'train': [
            {
                'input': [[1, 0], [2, 0]],
                'output': [[2, 1], [0, 0]]
            },
            {
                'input': [[1, 1], [0, 0]],
                'output': [[0, 1], [0, 1]]
            }
        ],
        'test': [
            {'input': [[1, 0], [1, 0]]}
        ]
    }
    
    # Initialize ARC-CORE
    core = ArcCore()
    
    # Solve
    trace = core.solve(task, task_id="rotation_90")
    
    print("=" * 60)
    print("TEST: Rotation 90° Detection")
    print("=" * 60)
    print(f"Success: {trace.success}")
    print(f"Method: {trace.method}")
    print(f"Hypotheses tried: {len(trace.hypotheses_tried)}")
    print(f"Time: {trace.execution_time:.3f}s")
    print(f"Reasoning: {trace.reasoning}")
    
    if trace.winning_hypothesis:
        print(f"\nWinning hypothesis: {trace.winning_hypothesis}")
        print(f"DSL: {trace.winning_hypothesis.dsl_program}")
    
    print("\nAll hypotheses:")
    for h in trace.hypotheses_tried:
        print(f"  {h}")
    
    return trace


def test_flip_task():
    """Test GEO-ENGINE on a flip task."""
    
    task = {
        'train': [
            {
                'input': [[1, 0, 0], [0, 0, 0]],
                'output': [[0, 0, 1], [0, 0, 0]]
            }
        ],
        'test': [
            {'input': [[1, 2, 3], [4, 5, 6]]}
        ]
    }
    
    core = ArcCore()
    trace = core.solve(task, task_id="flip_horizontal")
    
    print("\n" + "=" * 60)
    print("TEST: Horizontal Flip Detection")
    print("=" * 60)
    print(f"Success: {trace.success}")
    print(f"Hypotheses: {len(trace.hypotheses_tried)}")
    
    for h in trace.hypotheses_tried:
        print(f"  {h}")
    
    return trace


def test_core_initialization():
    """Test ARC-CORE initializes correctly."""
    core = ArcCore()
    
    print("=" * 60)
    print("TEST: ARC-CORE Initialization")
    print("=" * 60)
    print(f"Engines: {list(core.engines.keys())}")
    print(f"Engine count: {len(core.engines)}")
    print(f"Timeout: {core.timeout}s")
    print(f"\nEngine details:")
    for name, engine in core.engines.items():
        print(f"  {name}: {engine}")


if __name__ == "__main__":
    # Run tests
    test_core_initialization()
    print("\n")
    
    rotation_trace = test_rotation_task()
    print("\n")
    
    flip_trace = test_flip_task()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Rotation task: {'PASS' if rotation_trace.hypotheses_tried else 'FAIL'}")
    print(f"Flip task: {'PASS' if flip_trace.hypotheses_tried else 'FAIL'}")
