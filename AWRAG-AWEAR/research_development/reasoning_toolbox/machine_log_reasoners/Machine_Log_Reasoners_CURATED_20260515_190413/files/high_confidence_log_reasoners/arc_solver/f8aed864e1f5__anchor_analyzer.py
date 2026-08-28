#!/usr/bin/env python3
"""
Anchor Point Analysis System
Measure-first reasoning with centroid as anchor point.

Core Principles:
1. Centroid is the anchor point - measure ALL distances from there
2. Color is ALWAYS retained unless rules explicitly override
3. Measure FIRST, reason SECOND
4. Report close matches with evidence (threshold: 85%+ similarity)
5. Return partial matches for human examination + other operators
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Any
import numpy as np

from engines.object_geometry import DetectedObject, ObjectSpace


@dataclass
class TransformationEvidence:
    """Evidence for a potential transformation."""
    transform_type: str
    confidence: float  # 0.0 to 1.0
    measurements: Dict[str, float]  # Raw distance/angle measurements
    color_preserved: bool
    close_match_reason: str  # Why this is a close match
    discrepancies: List[str]  # What doesn't match perfectly


@dataclass
class AnchorAnalysis:
    """
    Analysis results from anchor-point measurement system.
    
    Includes:
    - Distance measurements from centroid
    - Color retention status
    - Close matches (85%+ confidence)
    - Evidence for human + operator examination
    """
    object_id: int
    anchor_point: Tuple[float, float]  # (cy, cx) - the centroid
    color: int  # Always tracked
    
    # Distance measurements from anchor
    radius: float  # Max distance to any pixel
    distance_to_center: float  # Distance to grid center
    distances_to_others: Dict[int, float]  # object_id -> distance
    angles_to_others: Dict[int, float]  # object_id -> angle (radians)
    
    # Transformation evidence
    evidence: List[TransformationEvidence]
    
    # Close matches for examination
    close_matches: List[TransformationEvidence]  # 85%+ confidence


class AnchorAnalyzer:
    """
    Anchor-point-based object analyzer.
    
    Workflow:
    1. Set centroid as anchor point
    2. Measure all distances FROM anchor (radius, d_center, pairwise)
    3. Measure angles between objects
    4. Track color (always retained unless rule overrides)
    5. Reason about transformations based on measurements
    6. Report close matches (85%+) with full evidence
    7. Return for examination + operator composition
    """
    
    # Evidence thresholds
    CLOSE_MATCH_THRESHOLD = 0.85  # 85% confidence = close match
    PERFECT_MATCH_THRESHOLD = 0.95  # 95% = very confident
    
    # Distance tolerance (as fraction of grid size)
    DISTANCE_TOLERANCE = 0.05  # 5% of grid diagonal
    ANGLE_TOLERANCE = np.pi / 36  # 5 degrees
    
    def __init__(self):
        pass
    
    def analyze_object(
        self, 
        obj: DetectedObject, 
        obj_space: ObjectSpace,
        target_obj: Optional[DetectedObject] = None,
        target_space: Optional[ObjectSpace] = None
    ) -> AnchorAnalysis:
        """
        Analyze single object using anchor-point measurement.
        
        Args:
            obj: Source object to analyze
            obj_space: Source ObjectSpace (for geometry)
            target_obj: Target object (if comparing input->output)
            target_space: Target ObjectSpace (if comparing input->output)
        
        Returns:
            Full anchor analysis with measurements and evidence
        """
        # Anchor point is the centroid
        anchor = obj.centroid
        
        # Get object index in space
        obj_idx = None
        for i, o in enumerate(obj_space.objects):
            if o.object_id == obj.object_id:
                obj_idx = i
                break
        
        if obj_idx is None:
            # Object not in space, return minimal analysis
            return AnchorAnalysis(
                object_id=obj.object_id,
                anchor_point=anchor,
                color=obj.color,
                radius=obj.radius,
                distance_to_center=0.0,
                distances_to_others={},
                angles_to_others={},
                evidence=[],
                close_matches=[]
            )
        
        # Measure distances from anchor to other objects
        distances_to_others = {}
        angles_to_others = {}
        
        for i, other_obj in enumerate(obj_space.objects):
            if i == obj_idx:
                continue
            
            distances_to_others[other_obj.object_id] = obj_space.D[obj_idx, i]
            angles_to_others[other_obj.object_id] = obj_space.Theta[obj_idx, i]
        
        # Distance to grid center
        distance_to_center = obj_space.d_center[obj_idx]
        
        # If target provided, generate transformation evidence
        evidence = []
        close_matches = []
        
        if target_obj is not None and target_space is not None:
            evidence = self._generate_evidence(
                obj, obj_space, obj_idx,
                target_obj, target_space
            )
            
            # Filter close matches
            close_matches = [
                e for e in evidence 
                if e.confidence >= self.CLOSE_MATCH_THRESHOLD
            ]
        
        return AnchorAnalysis(
            object_id=obj.object_id,
            anchor_point=anchor,
            color=obj.color,
            radius=obj.radius,
            distance_to_center=distance_to_center,
            distances_to_others=distances_to_others,
            angles_to_others=angles_to_others,
            evidence=evidence,
            close_matches=close_matches
        )
    
    def _generate_evidence(
        self,
        src_obj: DetectedObject,
        src_space: ObjectSpace,
        src_idx: int,
        tgt_obj: DetectedObject,
        tgt_space: ObjectSpace
    ) -> List[TransformationEvidence]:
        """
        Generate transformation evidence by comparing measurements.
        
        Measures:
        - Centroid displacement (translation)
        - Radius change (scaling)
        - Shape signature match (identity preservation)
        - Color preservation
        - Angle changes (rotation)
        """
        evidence = []
        
        # Get target index
        tgt_idx = None
        for i, o in enumerate(tgt_space.objects):
            if o.color == tgt_obj.color and o.shape_signature == tgt_obj.shape_signature:
                tgt_idx = i
                break
        
        if tgt_idx is None:
            # Can't find matching target
            return evidence
        
        # Measurement 1: Color preservation (ALWAYS track this)
        color_preserved = (src_obj.color == tgt_obj.color)
        
        # Measurement 2: Centroid displacement
        src_cy, src_cx = src_obj.centroid
        tgt_cy, tgt_cx = tgt_obj.centroid
        
        dy = tgt_cy - src_cy
        dx = tgt_cx - src_cx
        displacement = np.sqrt(dy**2 + dx**2)
        
        # Measurement 3: Radius change (scaling indicator)
        radius_ratio = tgt_obj.radius / src_obj.radius if src_obj.radius > 0 else 1.0
        radius_change = abs(radius_ratio - 1.0)
        
        # Measurement 4: Shape signature match
        shape_match = (src_obj.shape_signature == tgt_obj.shape_signature)
        
        # Measurement 5: Distance to center change
        d_center_change = abs(tgt_space.d_center[tgt_idx] - src_space.d_center[src_idx])
        
        # Grid diagonal for normalization
        grid_diag = np.sqrt(src_space.H**2 + src_space.W**2)
        
        # Evidence 1: TRANSLATION (centroid moved, shape/radius preserved)
        if displacement > 0 and shape_match and radius_change < 0.1:
            # Measure confidence based on how clean the translation is
            confidence = 1.0
            discrepancies = []
            
            # Color preservation check
            if not color_preserved:
                confidence *= 0.7
                discrepancies.append(f"Color changed: {src_obj.color} -> {tgt_obj.color}")
            
            # Radius should be stable
            if radius_change > 0.01:
                confidence *= 0.95
                discrepancies.append(f"Radius changed slightly: {src_obj.radius:.2f} -> {tgt_obj.radius:.2f}")
            
            evidence.append(TransformationEvidence(
                transform_type="TRANSLATION",
                confidence=confidence,
                measurements={
                    "displacement": displacement,
                    "dy": dy,
                    "dx": dx,
                    "radius_ratio": radius_ratio,
                    "displacement_normalized": displacement / grid_diag
                },
                color_preserved=color_preserved,
                close_match_reason=f"Centroid moved {displacement:.2f} units, shape/size preserved",
                discrepancies=discrepancies
            ))
        
        # Evidence 2: SCALING (radius changed, shape preserved, centroid stable)
        if radius_change > 0.1 and shape_match and displacement < grid_diag * 0.05:
            confidence = 1.0
            discrepancies = []
            
            if not color_preserved:
                confidence *= 0.7
                discrepancies.append(f"Color changed: {src_obj.color} -> {tgt_obj.color}")
            
            if displacement > 0:
                confidence *= 0.95
                discrepancies.append(f"Centroid drifted {displacement:.2f} units")
            
            evidence.append(TransformationEvidence(
                transform_type="SCALING",
                confidence=confidence,
                measurements={
                    "radius_ratio": radius_ratio,
                    "src_radius": src_obj.radius,
                    "tgt_radius": tgt_obj.radius,
                    "displacement": displacement
                },
                color_preserved=color_preserved,
                close_match_reason=f"Radius scaled by {radius_ratio:.2f}×, shape preserved",
                discrepancies=discrepancies
            ))
        
        # Evidence 3: MOVE_TO_CENTER (centroid approaches grid center)
        if d_center_change > grid_diag * 0.1:
            # Check if moving toward or away from center
            toward_center = tgt_space.d_center[tgt_idx] < src_space.d_center[src_idx]
            
            confidence = 0.90
            discrepancies = []
            
            if not color_preserved:
                confidence *= 0.7
                discrepancies.append(f"Color changed: {src_obj.color} -> {tgt_obj.color}")
            
            if not shape_match:
                confidence *= 0.8
                discrepancies.append("Shape signature changed")
            
            direction = "toward" if toward_center else "away from"
            
            evidence.append(TransformationEvidence(
                transform_type="MOVE_TO_CENTER" if toward_center else "MOVE_FROM_CENTER",
                confidence=confidence,
                measurements={
                    "src_d_center": src_space.d_center[src_idx],
                    "tgt_d_center": tgt_space.d_center[tgt_idx],
                    "d_center_change": d_center_change,
                    "displacement": displacement
                },
                color_preserved=color_preserved,
                close_match_reason=f"Moved {d_center_change:.2f} units {direction} center",
                discrepancies=discrepancies
            ))
        
        # Evidence 4: IDENTITY (everything preserved)
        if displacement < grid_diag * 0.01 and radius_change < 0.01 and shape_match:
            confidence = 1.0
            discrepancies = []
            
            if not color_preserved:
                confidence = 0.5  # Identity should preserve color
                discrepancies.append(f"Color changed: {src_obj.color} -> {tgt_obj.color}")
            
            evidence.append(TransformationEvidence(
                transform_type="IDENTITY",
                confidence=confidence,
                measurements={
                    "displacement": displacement,
                    "radius_ratio": radius_ratio,
                    "shape_match": shape_match
                },
                color_preserved=color_preserved,
                close_match_reason="Object unchanged (identity transform)",
                discrepancies=discrepancies
            ))
        
        return evidence
    
    def compare_spaces(
        self, 
        src_space: ObjectSpace, 
        tgt_space: ObjectSpace
    ) -> Dict[int, AnchorAnalysis]:
        """
        Compare two ObjectSpaces and generate anchor analyses.
        
        Returns:
            Dict mapping source object_id -> AnchorAnalysis with evidence
        """
        analyses = {}
        
        # Try to match objects by shape_signature + color
        matched_pairs = []
        used_target_ids = set()
        
        for src_obj in src_space.objects:
            best_match = None
            best_score = 0.0
            
            for tgt_obj in tgt_space.objects:
                if tgt_obj.object_id in used_target_ids:
                    continue
                
                # Matching score
                score = 0.0
                
                # Shape signature match
                if src_obj.shape_signature == tgt_obj.shape_signature:
                    score += 0.6
                
                # Color match
                if src_obj.color == tgt_obj.color:
                    score += 0.4
                
                if score > best_score:
                    best_score = score
                    best_match = tgt_obj
            
            if best_match and best_score >= 0.5:  # At least half the criteria
                matched_pairs.append((src_obj, best_match))
                used_target_ids.add(best_match.object_id)
        
        # Generate analyses for matched pairs
        for src_obj, tgt_obj in matched_pairs:
            analysis = self.analyze_object(src_obj, src_space, tgt_obj, tgt_space)
            analyses[src_obj.object_id] = analysis
        
        # Generate analyses for unmatched source objects (no target)
        matched_src_ids = {src.object_id for src, _ in matched_pairs}
        for src_obj in src_space.objects:
            if src_obj.object_id not in matched_src_ids:
                analysis = self.analyze_object(src_obj, src_space)
                analyses[src_obj.object_id] = analysis
        
        return analyses
    
    def report_close_matches(self, analyses: Dict[int, AnchorAnalysis]) -> str:
        """
        Generate human-readable report of close matches (85%+ confidence).
        
        Format:
        - Object ID
        - Anchor point (centroid)
        - Color (always shown)
        - Close match transformations with evidence
        - Measurements supporting each match
        - Discrepancies to consider
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ANCHOR POINT ANALYSIS - CLOSE MATCHES (85%+ Confidence)")
        lines.append("=" * 80)
        lines.append("")
        
        total_close_matches = 0
        
        for obj_id, analysis in sorted(analyses.items()):
            if not analysis.close_matches:
                continue
            
            total_close_matches += len(analysis.close_matches)
            
            lines.append(f"Object #{obj_id}")
            lines.append(f"  Anchor Point (Centroid): ({analysis.anchor_point[0]:.2f}, {analysis.anchor_point[1]:.2f})")
            lines.append(f"  Color: {analysis.color} {'[RETAINED]' if any(e.color_preserved for e in analysis.close_matches) else '[CHANGED]'}")
            lines.append(f"  Radius: {analysis.radius:.2f}")
            lines.append(f"  Distance to Center: {analysis.distance_to_center:.2f}")
            lines.append("")
            
            for i, evidence in enumerate(analysis.close_matches, 1):
                lines.append(f"  Close Match #{i}: {evidence.transform_type}")
                lines.append(f"    Confidence: {evidence.confidence:.1%}")
                lines.append(f"    Color Preserved: {'YES' if evidence.color_preserved else 'NO'}")
                lines.append(f"    Reason: {evidence.close_match_reason}")
                lines.append(f"    Measurements:")
                for key, value in evidence.measurements.items():
                    lines.append(f"      - {key}: {value:.4f}")
                
                if evidence.discrepancies:
                    lines.append(f"    Discrepancies:")
                    for disc in evidence.discrepancies:
                        lines.append(f"      ⚠ {disc}")
                
                lines.append("")
        
        if total_close_matches == 0:
            lines.append("No close matches found (threshold: 85% confidence)")
            lines.append("")
        else:
            lines.append(f"Total Close Matches: {total_close_matches}")
            lines.append("Recommendation: Examine evidence and compose with other operators")
            lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
