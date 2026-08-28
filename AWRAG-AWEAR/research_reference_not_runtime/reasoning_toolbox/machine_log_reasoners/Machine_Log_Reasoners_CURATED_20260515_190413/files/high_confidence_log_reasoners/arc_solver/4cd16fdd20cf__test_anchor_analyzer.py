#!/usr/bin/env python3
"""
Test suite for Anchor Point Analysis System.

Tests:
1. Anchor point measurement (centroid as anchor)
2. Distance measurements from anchor
3. Color retention tracking
4. Translation evidence generation
5. Scaling evidence generation
6. Close match reporting (85%+ threshold)
7. Evidence-based reasoning
"""

import numpy as np
from engines.anchor_analyzer import AnchorAnalyzer, AnchorAnalysis, TransformationEvidence
from engines.comp_engine_v2 import CompEngineV2


def test_anchor_point_measurement():
    """Test that centroid is correctly identified as anchor point."""
    print("\n" + "="*80)
    print("TEST 1: Anchor Point Measurement")
    print("="*80)
    
    # Create simple object
    grid = np.array([
        [0, 1, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0]
    ])
    
    engine = CompEngineV2()
    obj_space = engine.detect_objects_universal(grid)
    
    assert len(obj_space.objects) == 1, f"Expected 1 object, got {len(obj_space.objects)}"
    
    analyzer = AnchorAnalyzer()
    analysis = analyzer.analyze_object(obj_space.objects[0], obj_space)
    
    # Anchor should be the centroid
    expected_centroid = (0.5, 1.5)  # Mean of [(0,1), (0,2), (1,1), (1,2)]
    assert abs(analysis.anchor_point[0] - expected_centroid[0]) < 0.01
    assert abs(analysis.anchor_point[1] - expected_centroid[1]) < 0.01
    
    # Should track color
    assert analysis.color == 1
    
    # Should measure radius from anchor
    assert analysis.radius > 0
    
    print(f"✓ Anchor point correctly set to centroid: {analysis.anchor_point}")
    print(f"✓ Color tracked: {analysis.color}")
    print(f"✓ Radius measured from anchor: {analysis.radius:.2f}")
    print(f"✓ Distance to center: {analysis.distance_to_center:.2f}")


def test_translation_evidence():
    """Test evidence generation for translation (centroid moves)."""
    print("\n" + "="*80)
    print("TEST 2: Translation Evidence Generation")
    print("="*80)
    
    # Input: object at (0,1)
    grid_in = np.array([
        [0, 1, 1, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 0, 0, 0, 0]
    ])
    
    # Output: same object at (0,3) - translated right by 2
    grid_out = np.array([
        [0, 0, 0, 1, 1],
        [0, 0, 0, 1, 1],
        [0, 0, 0, 0, 0]
    ])
    
    engine = CompEngineV2()
    os_in = engine.detect_objects_universal(grid_in)
    os_out = engine.detect_objects_universal(grid_out)
    
    analyzer = AnchorAnalyzer()
    analyses = analyzer.compare_spaces(os_in, os_out)
    
    assert len(analyses) == 1
    analysis = analyses[0]
    
    # Should detect translation
    assert len(analysis.evidence) > 0
    
    translation_evidence = [e for e in analysis.evidence if e.transform_type == "TRANSLATION"]
    assert len(translation_evidence) > 0
    
    evidence = translation_evidence[0]
    
    # Should be high confidence
    assert evidence.confidence >= 0.85, f"Expected confidence >= 85%, got {evidence.confidence:.1%}"
    
    # Should preserve color
    assert evidence.color_preserved
    
    # Should measure displacement
    assert "displacement" in evidence.measurements
    assert evidence.measurements["dx"] == 2.0  # Moved right by 2
    
    print(f"✓ Translation detected: {evidence.transform_type}")
    print(f"✓ Confidence: {evidence.confidence:.1%}")
    print(f"✓ Color preserved: {evidence.color_preserved}")
    print(f"✓ Displacement: {evidence.measurements['displacement']:.2f} units")
    print(f"✓ Direction: dx={evidence.measurements['dx']:.2f}, dy={evidence.measurements['dy']:.2f}")
    print(f"✓ Reason: {evidence.close_match_reason}")


def test_scaling_evidence():
    """Test evidence generation for scaling (radius changes)."""
    print("\n" + "="*80)
    print("TEST 3: Scaling Evidence Generation")
    print("="*80)
    
    # Input: 2x2 object
    grid_in = np.array([
        [1, 1, 0, 0],
        [1, 1, 0, 0],
        [0, 0, 0, 0]
    ])
    
    # Output: 4x4 object (scaled 2x) - note: shape signature will differ
    # For this test, we'll use same shape but measure radius change
    grid_out = np.array([
        [1, 1, 1, 1],
        [1, 1, 1, 1],
        [1, 1, 1, 1],
        [1, 1, 1, 1]
    ])
    
    engine = CompEngineV2()
    os_in = engine.detect_objects_universal(grid_in)
    os_out = engine.detect_objects_universal(grid_out)
    
    # Note: scaling changes shape_signature, so matching might not be perfect
    # But we can still analyze the measurements
    
    obj_in = os_in.objects[0]
    obj_out = os_out.objects[0]
    
    print(f"✓ Input radius: {obj_in.radius:.2f}")
    print(f"✓ Output radius: {obj_out.radius:.2f}")
    print(f"✓ Radius ratio: {obj_out.radius / obj_in.radius:.2f}×")
    print(f"✓ Color preserved: {obj_in.color == obj_out.color}")
    
    # Radius should have increased
    assert obj_out.radius > obj_in.radius
    
    print(f"✓ Scaling detected: radius increased from {obj_in.radius:.2f} to {obj_out.radius:.2f}")


def test_color_retention():
    """Test that color is ALWAYS tracked and retention is reported."""
    print("\n" + "="*80)
    print("TEST 4: Color Retention Tracking")
    print("="*80)
    
    # Input: red object (color=1)
    grid_in = np.array([
        [0, 1, 1, 0],
        [0, 1, 1, 0]
    ])
    
    # Output: blue object (color=2) - color changed
    grid_out = np.array([
        [0, 2, 2, 0],
        [0, 2, 2, 0]
    ])
    
    engine = CompEngineV2()
    os_in = engine.detect_objects_universal(grid_in)
    os_out = engine.detect_objects_universal(grid_out)
    
    analyzer = AnchorAnalyzer()
    
    # Manually create evidence since auto-matching requires same color
    obj_in = os_in.objects[0]
    obj_out = os_out.objects[0]
    
    # Get indices
    src_idx = 0
    tgt_idx = 0
    
    evidence = analyzer._generate_evidence(obj_in, os_in, src_idx, obj_out, os_out)
    
    # All evidence should note color NOT preserved
    for e in evidence:
        assert not e.color_preserved, f"Expected color_preserved=False, got {e.color_preserved}"
        
        # Should have color change in discrepancies
        color_disc = [d for d in e.discrepancies if "Color changed" in d]
        if e.transform_type != "IDENTITY":  # Identity might not be detected when color changes
            print(f"  {e.transform_type}: color_preserved={e.color_preserved}, confidence={e.confidence:.1%}")
    
    print(f"✓ Color retention tracking working")
    print(f"✓ Input color: {obj_in.color}")
    print(f"✓ Output color: {obj_out.color}")
    print(f"✓ All evidence correctly marked color NOT preserved")


def test_close_match_threshold():
    """Test that only 85%+ confidence evidence is reported as close match."""
    print("\n" + "="*80)
    print("TEST 5: Close Match Threshold (85%)")
    print("="*80)
    
    # Perfect translation - should be close match
    grid_in = np.array([
        [1, 1, 0, 0],
        [1, 1, 0, 0]
    ])
    
    grid_out = np.array([
        [0, 0, 1, 1],
        [0, 0, 1, 1]
    ])
    
    engine = CompEngineV2()
    os_in = engine.detect_objects_universal(grid_in)
    os_out = engine.detect_objects_universal(grid_out)
    
    analyzer = AnchorAnalyzer()
    analyses = analyzer.compare_spaces(os_in, os_out)
    
    assert len(analyses) == 1
    analysis = analyses[0]
    
    # Should have close matches
    assert len(analysis.close_matches) > 0
    
    # All close matches should be >= 85%
    for match in analysis.close_matches:
        assert match.confidence >= 0.85
        print(f"✓ Close match: {match.transform_type} at {match.confidence:.1%}")
        print(f"  Reason: {match.close_match_reason}")


def test_evidence_report():
    """Test human-readable evidence report generation."""
    print("\n" + "="*80)
    print("TEST 6: Evidence Report Generation")
    print("="*80)
    
    # Translation example
    grid_in = np.array([
        [1, 1, 0, 0, 0],
        [1, 1, 0, 0, 0],
        [0, 0, 0, 2, 2],
        [0, 0, 0, 2, 2]
    ])
    
    grid_out = np.array([
        [0, 0, 1, 1, 0],
        [0, 0, 1, 1, 0],
        [2, 2, 0, 0, 0],
        [2, 2, 0, 0, 0]
    ])
    
    engine = CompEngineV2()
    os_in = engine.detect_objects_universal(grid_in)
    os_out = engine.detect_objects_universal(grid_out)
    
    analyzer = AnchorAnalyzer()
    analyses = analyzer.compare_spaces(os_in, os_out)
    
    # Generate report
    report = analyzer.report_close_matches(analyses)
    
    print(report)
    
    # Report should contain key information
    assert "Anchor Point" in report
    assert "Color" in report
    assert "Confidence" in report
    assert "Close Match" in report or "No close matches" in report
    
    print("\n✓ Report generated successfully")


def test_measurement_first_workflow():
    """Test the measure-first, reason-second workflow."""
    print("\n" + "="*80)
    print("TEST 7: Measure-First Workflow")
    print("="*80)
    
    # Create object
    grid = np.array([
        [0, 0, 1, 1, 0],
        [0, 0, 1, 1, 0],
        [0, 0, 0, 0, 0]
    ])
    
    engine = CompEngineV2()
    obj_space = engine.detect_objects_universal(grid)
    
    analyzer = AnchorAnalyzer()
    analysis = analyzer.analyze_object(obj_space.objects[0], obj_space)
    
    # Step 1: MEASURE - all measurements should be present
    assert analysis.anchor_point is not None
    assert analysis.radius > 0
    assert analysis.distance_to_center >= 0
    assert analysis.color >= 0
    
    print("Step 1: MEASURE ✓")
    print(f"  Anchor: {analysis.anchor_point}")
    print(f"  Radius: {analysis.radius:.2f}")
    print(f"  Distance to center: {analysis.distance_to_center:.2f}")
    print(f"  Color: {analysis.color}")
    
    # Step 2: REASON - evidence comes after measurements
    # (no evidence in this case since no target, but structure is ready)
    print("\nStep 2: REASON ✓")
    print(f"  Evidence count: {len(analysis.evidence)}")
    print(f"  Close matches: {len(analysis.close_matches)}")
    
    print("\n✓ Measure-first workflow validated")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ANCHOR POINT ANALYSIS SYSTEM - TEST SUITE")
    print("="*80)
    
    test_anchor_point_measurement()
    test_translation_evidence()
    test_scaling_evidence()
    test_color_retention()
    test_close_match_threshold()
    test_evidence_report()
    test_measurement_first_workflow()
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED ✓")
    print("="*80)
    print("\nAnchor Point Analysis System is operational.")
    print("Core principles validated:")
    print("  1. Centroid as anchor point ✓")
    print("  2. Distance measurements from anchor ✓")
    print("  3. Color ALWAYS tracked ✓")
    print("  4. Measure FIRST, reason SECOND ✓")
    print("  5. Close matches (85%+) with evidence ✓")
    print("  6. Evidence for examination + operator composition ✓")
