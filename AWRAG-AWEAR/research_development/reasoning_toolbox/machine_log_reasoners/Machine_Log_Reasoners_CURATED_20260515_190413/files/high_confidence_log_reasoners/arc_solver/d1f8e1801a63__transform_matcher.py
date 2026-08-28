"""
Enhanced transform matching with anchor point reasoning and close match reporting.

Measures transformations from object centroids (anchor points) and reports
near-misses with evidence for manual examination.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from arc_organ.object_space import DetectedObject, ObjectSpace, build_object_space


@dataclass
class TransformMeasurement:
    """Measurement of transformation from anchor point (centroid)."""
    object_id: int
    color: int
    anchor_in: Tuple[float, float]  # Input centroid (cy, cx)
    anchor_out: Tuple[float, float]  # Output centroid (cy, cx)
    
    # Vector measurements from anchor point
    delta_y: float
    delta_x: float
    distance: float  # Euclidean distance of transformation
    angle: float  # Angle of transformation (radians)
    
    # Shape measurements
    shape_preserved: bool
    size_preserved: bool
    color_preserved: bool
    
    # Area measurements
    pixel_count_in: int
    pixel_count_out: int
    radius_in: float
    radius_out: float


@dataclass
class MatchEvidence:
    """Evidence for why a transform is close but not exact."""
    transform_name: str
    confidence: float  # 0.0 to 1.0
    measurements: List[TransformMeasurement]
    
    # What matches
    matches: List[str]
    
    # What doesn't match (with tolerance info)
    mismatches: List[str]
    
    # Statistics
    avg_distance: float
    max_distance: float
    distance_std: float
    uniform_translation: bool
    color_preserved: bool


def measure_object_transformations(
    objects_in: List[DetectedObject],
    objects_out: List[DetectedObject],
    tolerance: float = 0.01
) -> List[TransformMeasurement]:
    """
    Measure transformations for each object pair using anchor points.
    
    Colors are preserved by default unless stated otherwise.
    Measurements are from centroid (anchor point) to transformed position.
    """
    measurements = []
    
    # Match objects by color first (preserve color by default)
    matched_pairs = []
    used_out = set()
    
    for obj_in in objects_in:
        # Find matching color in output
        for i, obj_out in enumerate(objects_out):
            if i not in used_out and obj_out.color == obj_in.color:
                matched_pairs.append((obj_in, obj_out))
                used_out.add(i)
                break
    
    # Measure each matched pair
    for obj_in, obj_out in matched_pairs:
        cy_in, cx_in = obj_in.centroid
        cy_out, cx_out = obj_out.centroid
        
        delta_y = cy_out - cy_in
        delta_x = cx_out - cx_in
        distance = np.sqrt(delta_y**2 + delta_x**2)
        angle = np.arctan2(delta_y, delta_x)
        
        # Check preservation
        shape_preserved = obj_in.shape_signature == obj_out.shape_signature
        size_preserved = abs(obj_in.pixel_count - obj_out.pixel_count) <= tolerance
        color_preserved = obj_in.color == obj_out.color
        
        measurements.append(TransformMeasurement(
            object_id=obj_in.object_id,
            color=obj_in.color,
            anchor_in=(cy_in, cx_in),
            anchor_out=(cy_out, cx_out),
            delta_y=delta_y,
            delta_x=delta_x,
            distance=distance,
            angle=angle,
            shape_preserved=shape_preserved,
            size_preserved=size_preserved,
            color_preserved=color_preserved,
            pixel_count_in=obj_in.pixel_count,
            pixel_count_out=obj_out.pixel_count,
            radius_in=obj_in.radius,
            radius_out=obj_out.radius
        ))
    
    return measurements


def analyze_translation_pattern(
    measurements: List[TransformMeasurement],
    tolerance: float = 0.1
) -> MatchEvidence:
    """
    Analyze if measurements show translation pattern.
    
    Reports confidence and evidence for close matches.
    """
    if not measurements:
        return MatchEvidence(
            transform_name="TRANSLATE",
            confidence=0.0,
            measurements=[],
            matches=[],
            mismatches=["No measurements available"],
            avg_distance=0.0,
            max_distance=0.0,
            distance_std=0.0,
            uniform_translation=False,
            color_preserved=False
        )
    
    # Measure translation vectors
    deltas_y = [m.delta_y for m in measurements]
    deltas_x = [m.delta_x for m in measurements]
    
    avg_dy = np.mean(deltas_y)
    avg_dx = np.mean(deltas_x)
    std_dy = np.std(deltas_y)
    std_dx = np.std(deltas_x)
    
    distances = [m.distance for m in measurements]
    avg_distance = np.mean(distances)
    max_distance = np.max(distances)
    distance_std = np.std(distances)
    
    # Check uniformity
    uniform = (std_dy <= tolerance and std_dx <= tolerance)
    
    # Check color preservation
    all_colors_preserved = all(m.color_preserved for m in measurements)
    
    # Build evidence
    matches = []
    mismatches = []
    
    if all_colors_preserved:
        matches.append("✓ All colors preserved")
    else:
        mismatches.append(f"✗ {sum(not m.color_preserved for m in measurements)} objects changed color")
    
    if uniform:
        matches.append(f"✓ Uniform translation: dy={avg_dy:.2f}, dx={avg_dx:.2f}")
    else:
        mismatches.append(f"✗ Non-uniform translation: std_dy={std_dy:.2f}, std_dx={std_dx:.2f}")
        # Report individual translations
        for m in measurements:
            mismatches.append(f"  Object {m.object_id} (color {m.color}): dy={m.delta_y:.2f}, dx={m.delta_x:.2f}")
    
    # Shape/size preservation
    shapes_preserved = sum(m.shape_preserved for m in measurements)
    sizes_preserved = sum(m.size_preserved for m in measurements)
    
    if shapes_preserved == len(measurements):
        matches.append(f"✓ All {len(measurements)} shapes preserved")
    else:
        mismatches.append(f"✗ {len(measurements) - shapes_preserved} shapes changed")
    
    if sizes_preserved == len(measurements):
        matches.append(f"✓ All {len(measurements)} sizes preserved")
    else:
        mismatches.append(f"✗ {len(measurements) - sizes_preserved} sizes changed")
    
    # Calculate confidence
    confidence = 0.0
    if uniform:
        confidence += 0.5
    else:
        # Partial credit for near-uniform
        confidence += 0.5 * (1.0 - min(1.0, (std_dy + std_dx) / 2.0))
    
    if all_colors_preserved:
        confidence += 0.25
    
    if shapes_preserved == len(measurements):
        confidence += 0.25
    
    return MatchEvidence(
        transform_name="TRANSLATE",
        confidence=confidence,
        measurements=measurements,
        matches=matches,
        mismatches=mismatches,
        avg_distance=avg_distance,
        max_distance=max_distance,
        distance_std=distance_std,
        uniform_translation=uniform,
        color_preserved=all_colors_preserved
    )


def analyze_mirror_pattern(
    measurements: List[TransformMeasurement],
    grid_width: int,
    grid_height: int,
    tolerance: float = 0.5
) -> Tuple[MatchEvidence, MatchEvidence]:
    """
    Analyze if measurements show vertical or horizontal mirror pattern.
    
    Returns evidence for both vertical and horizontal mirrors.
    """
    if not measurements:
        empty = MatchEvidence(
            transform_name="MIRROR",
            confidence=0.0,
            measurements=[],
            matches=[],
            mismatches=["No measurements available"],
            avg_distance=0.0,
            max_distance=0.0,
            distance_std=0.0,
            uniform_translation=False,
            color_preserved=False
        )
        return empty, empty
    
    # Check vertical mirror (flip across vertical axis)
    v_matches = []
    v_mismatches = []
    v_errors = []
    
    for m in measurements:
        cy_in, cx_in = m.anchor_in
        cy_out, cx_out = m.anchor_out
        
        expected_cx = (grid_width - 1) - cx_in
        error = abs(cx_out - expected_cx)
        v_errors.append(error)
        
        if error <= tolerance:
            v_matches.append(f"✓ Object {m.object_id}: cx {cx_in:.1f} → {cx_out:.1f} (expected {expected_cx:.1f})")
        else:
            v_mismatches.append(f"✗ Object {m.object_id}: cx {cx_in:.1f} → {cx_out:.1f} (expected {expected_cx:.1f}, error={error:.2f})")
    
    # Check horizontal mirror (flip across horizontal axis)
    h_matches = []
    h_mismatches = []
    h_errors = []
    
    for m in measurements:
        cy_in, cx_in = m.anchor_in
        cy_out, cx_out = m.anchor_out
        
        expected_cy = (grid_height - 1) - cy_in
        error = abs(cy_out - expected_cy)
        h_errors.append(error)
        
        if error <= tolerance:
            h_matches.append(f"✓ Object {m.object_id}: cy {cy_in:.1f} → {cy_out:.1f} (expected {expected_cy:.1f})")
        else:
            h_mismatches.append(f"✗ Object {m.object_id}: cy {cy_in:.1f} → {cy_out:.1f} (expected {expected_cy:.1f}, error={error:.2f})")
    
    all_colors_preserved = all(m.color_preserved for m in measurements)
    
    # Vertical mirror evidence
    v_confidence = len(v_matches) / len(measurements) if measurements else 0.0
    if all_colors_preserved:
        v_confidence *= 1.0
    else:
        v_confidence *= 0.5
    
    v_evidence = MatchEvidence(
        transform_name="MIRROR_VERTICAL",
        confidence=v_confidence,
        measurements=measurements,
        matches=v_matches + (["✓ All colors preserved"] if all_colors_preserved else []),
        mismatches=v_mismatches + ([] if all_colors_preserved else ["✗ Some colors changed"]),
        avg_distance=np.mean([m.distance for m in measurements]),
        max_distance=np.max([m.distance for m in measurements]),
        distance_std=np.std([m.distance for m in measurements]),
        uniform_translation=False,
        color_preserved=all_colors_preserved
    )
    
    # Horizontal mirror evidence
    h_confidence = len(h_matches) / len(measurements) if measurements else 0.0
    if all_colors_preserved:
        h_confidence *= 1.0
    else:
        h_confidence *= 0.5
    
    h_evidence = MatchEvidence(
        transform_name="MIRROR_HORIZONTAL",
        confidence=h_confidence,
        measurements=measurements,
        matches=h_matches + (["✓ All colors preserved"] if all_colors_preserved else []),
        mismatches=h_mismatches + ([] if all_colors_preserved else ["✗ Some colors changed"]),
        avg_distance=np.mean([m.distance for m in measurements]),
        max_distance=np.max([m.distance for m in measurements]),
        distance_std=np.std([m.distance for m in measurements]),
        uniform_translation=False,
        color_preserved=all_colors_preserved
    )
    
    return v_evidence, h_evidence


def find_close_matches(
    grid_in: np.ndarray,
    grid_out: np.ndarray,
    min_confidence: float = 0.3
) -> List[MatchEvidence]:
    """
    Find all close transform matches with evidence.
    
    Uses anchor point (centroid) measurements and reports matches above threshold.
    Always preserves color unless rules state otherwise.
    """
    # Detect objects
    from arc_organ.object_space import detect_objects
    
    objects_in = detect_objects(grid_in)
    objects_out = detect_objects(grid_out)
    
    if not objects_in or not objects_out:
        return []
    
    # Measure transformations from anchor points
    measurements = measure_object_transformations(objects_in, objects_out)
    
    if not measurements:
        return []
    
    close_matches = []
    
    # Analyze translation
    trans_evidence = analyze_translation_pattern(measurements)
    if trans_evidence.confidence >= min_confidence:
        close_matches.append(trans_evidence)
    
    # Analyze mirrors
    v_mirror, h_mirror = analyze_mirror_pattern(
        measurements, 
        grid_in.shape[1], 
        grid_in.shape[0]
    )
    
    if v_mirror.confidence >= min_confidence:
        close_matches.append(v_mirror)
    
    if h_mirror.confidence >= min_confidence:
        close_matches.append(h_mirror)
    
    # Sort by confidence
    close_matches.sort(key=lambda x: x.confidence, reverse=True)
    
    return close_matches


def report_close_matches(task_id: str, grid_in: np.ndarray, grid_out: np.ndarray):
    """
    Report close matches with evidence for manual examination.
    """
    print(f"\n{'='*80}")
    print(f"TASK {task_id}: Close Match Analysis")
    print(f"{'='*80}")
    
    print(f"\nGrid shapes: {grid_in.shape} → {grid_out.shape}")
    
    matches = find_close_matches(grid_in, grid_out, min_confidence=0.3)
    
    if not matches:
        print("❌ No close matches found (confidence < 0.3)")
        return
    
    print(f"\n✓ Found {len(matches)} close match(es):\n")
    
    for i, evidence in enumerate(matches, 1):
        print(f"{i}. {evidence.transform_name} (confidence: {evidence.confidence:.2f})")
        print(f"   Objects measured: {len(evidence.measurements)}")
        print(f"   Avg distance: {evidence.avg_distance:.2f}, Max: {evidence.max_distance:.2f}, Std: {evidence.distance_std:.2f}")
        
        print(f"\n   ✓ MATCHES:")
        for match in evidence.matches[:5]:  # Show first 5
            print(f"      {match}")
        if len(evidence.matches) > 5:
            print(f"      ... and {len(evidence.matches) - 5} more")
        
        if evidence.mismatches:
            print(f"\n   ✗ MISMATCHES:")
            for mismatch in evidence.mismatches[:5]:  # Show first 5
                print(f"      {mismatch}")
            if len(evidence.mismatches) > 5:
                print(f"      ... and {len(evidence.mismatches) - 5} more")
        
        print()


# Test function
def test_close_match_detection():
    """Test close match detection with anchor point measurements."""
    print("\n" + "="*80)
    print("TEST: Close Match Detection with Anchor Points")
    print("="*80)
    
    # Test 1: Perfect translation
    grid_in = np.array([[1, 0, 0], [0, 0, 0], [0, 0, 2]])
    grid_out = np.array([[0, 1, 0], [0, 0, 0], [0, 0, 0], [2, 0, 0]])
    
    print("\nTest 1: Perfect uniform translation")
    report_close_matches("test_1", grid_in, grid_out)
    
    # Test 2: Non-uniform translation (different shifts per object)
    grid_in = np.array([[1, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 2, 0, 0]])
    grid_out = np.array([[0, 1, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 2]])
    
    print("\nTest 2: Non-uniform translation (different per object)")
    report_close_matches("test_2", grid_in, grid_out)
    
    print("\n✓ Close match detection tests complete")


if __name__ == "__main__":
    test_close_match_detection()
