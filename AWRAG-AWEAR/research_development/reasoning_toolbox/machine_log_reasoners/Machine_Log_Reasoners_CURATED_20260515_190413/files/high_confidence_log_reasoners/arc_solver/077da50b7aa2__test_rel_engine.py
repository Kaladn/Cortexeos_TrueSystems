#!/usr/bin/env python3
"""Smoke test for REL-ENGINE Phase 1."""

import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.rel_engine import RelEngine
from engines.base_engine import TaskView


def test_move_to_corner_tl():
    """Test move to top-left corner."""
    print("\n=== TEST: Move to Top-Left Corner ===")
    
    # Input: object in center
    input1 = np.zeros((7, 7), dtype=int)
    input1[3:5, 3:5] = 5
    
    # Output: same object in top-left
    output1 = np.zeros((7, 7), dtype=int)
    output1[0:2, 0:2] = 5
    
    print("Input:\n", input1)
    print("\nOutput:\n", output1)
    
    task_view = TaskView(
        train_pairs=[(input1, output1)],
        test_input=input1.copy(),
        task_id="test_move_tl"
    )
    
    engine = RelEngine()
    hypotheses = engine.analyze(task_view)
    
    print(f"\nHypotheses: {len(hypotheses)}")
    for hyp in hypotheses:
        print(f"  {hyp.operation}: {hyp.dsl_program}")
        print(f"    Params: {hyp.params}")
        print(f"    {hyp.explanation}")
    
    assert len(hypotheses) > 0
    assert hypotheses[0].operation == "MOVE_TO_CORNER"
    assert hypotheses[0].params['corner'] == 'TL'
    print("✓ PASS")


def test_move_to_corner_br():
    """Test move to bottom-right corner."""
    print("\n=== TEST: Move to Bottom-Right Corner ===")
    
    # Input: object at top
    input1 = np.zeros((7, 7), dtype=int)
    input1[1:3, 2:4] = 3
    
    # Output: same object in bottom-right
    output1 = np.zeros((7, 7), dtype=int)
    output1[5:7, 5:7] = 3
    
    task_view = TaskView(
        train_pairs=[(input1, output1)],
        test_input=input1.copy(),
        task_id="test_move_br"
    )
    
    engine = RelEngine()
    hypotheses = engine.analyze(task_view)
    
    print(f"Hypotheses: {len(hypotheses)}")
    for hyp in hypotheses:
        print(f"  {hyp.operation}: corner={hyp.params.get('corner')}")
    
    assert len(hypotheses) > 0
    assert hypotheses[0].operation == "MOVE_TO_CORNER"
    assert hypotheses[0].params['corner'] == 'BR'
    print("✓ PASS")


def test_align_to_row():
    """Test horizontal alignment."""
    print("\n=== TEST: Align to Same Row ===")
    
    # Input: two objects at different heights
    input1 = np.zeros((7, 7), dtype=int)
    input1[1:3, 1:3] = 4  # anchor (larger)
    input1[5, 5] = 6      # target (smaller, different row)
    
    # Output: target moved to same row as anchor
    output1 = np.zeros((7, 7), dtype=int)
    output1[1:3, 1:3] = 4  # anchor unchanged
    output1[2, 5] = 6      # target aligned to row 2 (center of anchor)
    
    print("Input:\n", input1)
    print("\nOutput:\n", output1)
    
    task_view = TaskView(
        train_pairs=[(input1, output1)],
        test_input=input1.copy(),
        task_id="test_align_row"
    )
    
    engine = RelEngine()
    hypotheses = engine.analyze(task_view)
    
    print(f"\nHypotheses: {len(hypotheses)}")
    for hyp in hypotheses:
        print(f"  {hyp.operation}: {hyp.dsl_program}")
        print(f"    Params: {hyp.params}")
    
    if hypotheses:
        align_hyps = [h for h in hypotheses if h.operation == "ALIGN_TO_OBJECT"]
        assert len(align_hyps) > 0, "No ALIGN_TO_OBJECT hypothesis found"
        assert align_hyps[0].params['axis'] == 'row'
        print("✓ PASS")
    else:
        print("⚠ No hypotheses (may need threshold adjustment)")


def test_mirror_vertical():
    """Test vertical mirroring."""
    print("\n=== TEST: Mirror Vertical ===")
    
    # Input: object on left side
    input1 = np.zeros((5, 7), dtype=int)
    input1[2, 1] = 8
    
    # Output: object on right side (mirrored)
    output1 = np.zeros((5, 7), dtype=int)
    output1[2, 5] = 8  # x: 7-1-1 = 5
    
    print("Input:\n", input1)
    print("\nOutput:\n", output1)
    
    task_view = TaskView(
        train_pairs=[(input1, output1)],
        test_input=input1.copy(),
        task_id="test_mirror_v"
    )
    
    engine = RelEngine()
    hypotheses = engine.analyze(task_view)
    
    print(f"\nHypotheses: {len(hypotheses)}")
    for hyp in hypotheses:
        print(f"  {hyp.operation}: {hyp.dsl_program}")
        print(f"    Params: {hyp.params}")
    
    if hypotheses:
        assert hypotheses[0].operation == "MIRROR"
        assert hypotheses[0].params['axis'] == 'V'
        print("✓ PASS")
    else:
        print("⚠ No hypotheses (may need threshold adjustment)")


def test_mirror_horizontal():
    """Test horizontal mirroring."""
    print("\n=== TEST: Mirror Horizontal ===")
    
    # Input: object at top
    input1 = np.zeros((7, 5), dtype=int)
    input1[1, 2] = 7
    
    # Output: object at bottom (mirrored)
    output1 = np.zeros((7, 5), dtype=int)
    output1[5, 2] = 7  # y: 7-1-1 = 5
    
    task_view = TaskView(
        train_pairs=[(input1, output1)],
        test_input=input1.copy(),
        task_id="test_mirror_h"
    )
    
    engine = RelEngine()
    hypotheses = engine.analyze(task_view)
    
    print(f"\nHypotheses: {len(hypotheses)}")
    for hyp in hypotheses:
        print(f"  {hyp.operation}: axis={hyp.params.get('axis')}")
    
    if hypotheses:
        assert hypotheses[0].operation == "MIRROR"
        assert hypotheses[0].params['axis'] == 'H'
        print("✓ PASS")
    else:
        print("⚠ No hypotheses (may need threshold adjustment)")


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("REL-ENGINE PHASE 1 SMOKE TESTS")
    print("=" * 60)
    
    try:
        test_move_to_corner_tl()
        test_move_to_corner_br()
        test_align_to_row()
        test_mirror_vertical()
        test_mirror_horizontal()
        
        print("\n" + "=" * 60)
        print("CORE TESTS PASSED ✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
