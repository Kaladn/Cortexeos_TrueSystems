"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     CompuCog — Sovereign Cognitive Defense System                           ║
║     Intellectual Property of Cortex Evolved / L.A. Mercey                   ║
║                                                                              ║
║     Copyright © 2025 Cortex Evolved. All Rights Reserved.                   ║
║                                                                              ║
║     "We use unconventional digital wisdom —                                  ║
║        because conventional digital wisdom doesn't protect anyone."         ║
║                                                                              ║
║     This software is proprietary and confidential.                           ║
║     Unauthorized access, copying, modification, or distribution             ║
║     is strictly prohibited and may violate applicable laws.                  ║
║                                                                              ║
║     File automatically watermarked on: 2025-12-06 00:00:00                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

EOMM Compositor V2 (Patent-Enhanced)

ENHANCEMENTS OVER V1:
  - Patent signature aggregation
  - Forensic evidence collection
  - Multi-patent citation tracking
  - Enhanced metadata with patent matches
"""

from typing import List, Dict, Any
import yaml
from pathlib import Path
import sys

# Import unified schema
sys.path.insert(0, str(Path(__file__).parent.parent))
from truevision_schema import OperatorResult, TelemetryWindow, ManipulationFlags
from session_baseline import SessionBaselineTracker


class EommCompositorV2:
    """
    EOMM Signature Compositor V2 - PATENT-ENHANCED
    
    Combines all operator results into unified TelemetryWindow.
    NOW WITH: Patent signature aggregation and forensic evidence collection.
    
    Responsibilities:
    - Aggregate confidence scores from all operators
    - Weight by operator reliability and detection quality
    - Generate composite EOMM manipulation score
    - Deduplicate flags across operators
    - **NEW: Aggregate patent matches from all operators**
    - **NEW: Provide forensic evidence citations**
    - Package results in TelemetryWindow format
    """
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        eomm_config = self.config.get("eomm_composite", {})
        self.operator_weights = eomm_config.get("operator_weights", {
            "crosshair_lock": 0.3,
            "hit_registration": 0.3,
            "hit_registration_v2": 0.3,  # Support v2 operators
            "death_event": 0.25,
            "edge_entry": 0.15,
            "edge_entry_v2": 0.15  # Support v2 operators
        })
        
        self.manipulation_threshold = eomm_config.get("manipulation_threshold", 0.5)
        self.high_confidence_threshold = eomm_config.get("high_confidence_threshold", 0.75)
        
        print(f"[+] EOMM Compositor V2 initialized (PATENT-ENHANCED)")
        print(f"    Operator weights: {self.operator_weights}")
        print(f"    Manipulation threshold: {self.manipulation_threshold}")
    
    def compose_window(
        self,
        operator_results: List[OperatorResult],
        window_start_epoch: float,
        window_end_epoch: float,
        session_id: str,
        frame_count: int,
        session_tracker: SessionBaselineTracker
    ) -> TelemetryWindow:
        """
        Compose TelemetryWindow from multiple operator results WITH PATENT AGGREGATION.
        
        Args:
            operator_results: List of results from all operators
            window_start_epoch: Window start timestamp (Unix epoch)
            window_end_epoch: Window end timestamp
            session_id: Unique session identifier
            frame_count: Number of frames analyzed
            session_tracker: Session baseline tracker for metadata
        
        Returns:
            TelemetryWindow with composite EOMM scoring AND patent citations
        """
        # Compute weighted average confidence score
        composite_score = self._compute_composite_score(operator_results)
        
        # Aggregate flags from all operators (deduplicated)
        all_flags = self._aggregate_flags(operator_results)
        
        # **NEW: Aggregate patent matches from all operators**
        patent_matches = self._aggregate_patent_matches(operator_results)
        
        # Build metadata with session baselines
        metadata = session_tracker.to_dict()
        metadata["manipulation_detected"] = composite_score >= self.manipulation_threshold
        metadata["high_confidence"] = composite_score >= self.high_confidence_threshold
        
        # **NEW: Add patent evidence to metadata**
        if patent_matches:
            metadata["patent_evidence"] = {
                "total_matches": len(patent_matches),
                "signatures": patent_matches,
                "evidence_type": "FORENSIC"
            }
        
        # Package into TelemetryWindow
        window = TelemetryWindow(
            window_start_epoch=window_start_epoch,
            window_end_epoch=window_end_epoch,
            session_id=session_id,
            frame_count=frame_count,
            composite_eomm_score=composite_score,
            operator_results=operator_results,
            manipulation_flags=all_flags,
            metadata=metadata
        )
        
        return window
    
    def _compute_composite_score(self, operator_results: List[OperatorResult]) -> float:
        """
        Compute weighted composite EOMM score.
        
        Uses operator weights from config. Operators not in results contribute 0.
        """
        weighted_sum = 0.0
        total_weight = 0.0
        
        for result in operator_results:
            op_name = result.operator_name
            weight = self.operator_weights.get(op_name, 0.0)
            
            if weight > 0:
                weighted_sum += result.confidence * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def _aggregate_flags(self, operator_results: List[OperatorResult]) -> List[ManipulationFlags]:
        """
        Aggregate and deduplicate manipulation flags from all operators.
        """
        flag_set = set()
        
        for result in operator_results:
            for flag in result.flags:
                flag_set.add(flag)
        
        return list(flag_set)
    
    def _aggregate_patent_matches(self, operator_results: List[OperatorResult]) -> List[Dict]:
        """
        **NEW: Aggregate patent matches from all operators**
        
        Collects all patent signature matches and returns deduplicated list
        with operator context.
        
        Returns:
            List of patent match dicts with:
            - signature_id
            - patent_number
            - operator_name (which operator detected it)
            - match_confidence
            - citation
        """
        patent_matches = []
        
        for result in operator_results:
            # Check if operator result has patent match in metadata
            if 'patent_match' in result.metadata:
                match = result.metadata['patent_match']
                
                # Add operator context
                match_with_context = {
                    'operator_name': result.operator_name,
                    'signature_id': match['signature_id'],
                    'patent_number': match['patent_number'],
                    'patent_paragraph': match.get('patent_paragraph', ''),
                    'manipulation_method': match['manipulation_method'],
                    'match_confidence': match['match_confidence'],
                    'citation': match['citation'],
                    'evidence_type': match.get('evidence_type', 'FORENSIC'),
                    'detection_pattern': match.get('detection_pattern', '')
                }
                
                patent_matches.append(match_with_context)
        
        return patent_matches
    
    def generate_report(self, window: TelemetryWindow) -> str:
        """
        **NEW: Generate human-readable report with patent citations**
        
        Returns formatted string with:
        - Composite EOMM score
        - Manipulation flags
        - Patent evidence (if any)
        - Operator-specific detections
        """
        lines = []
        lines.append("=" * 80)
        lines.append("COMPUCOG EOMM DETECTION REPORT (PATENT-ENHANCED)")
        lines.append("=" * 80)
        lines.append(f"Session ID: {window.session_id}")
        lines.append(f"Window: {window.window_start_epoch:.2f} - {window.window_end_epoch:.2f}")
        lines.append(f"Frames Analyzed: {window.frame_count}")
        lines.append("")
        
        lines.append(f"Composite EOMM Score: {window.composite_eomm_score:.3f}")
        lines.append(f"Manipulation Detected: {window.metadata.get('manipulation_detected', False)}")
        lines.append(f"High Confidence: {window.metadata.get('high_confidence', False)}")
        lines.append("")
        
        if window.manipulation_flags:
            lines.append("Manipulation Flags:")
            for flag in window.manipulation_flags:
                lines.append(f"  - {flag.name}")
            lines.append("")
        
        # **NEW: Patent evidence section**
        if 'patent_evidence' in window.metadata:
            evidence = window.metadata['patent_evidence']
            lines.append("=" * 80)
            lines.append("FORENSIC EVIDENCE (PATENT CITATIONS)")
            lines.append("=" * 80)
            lines.append(f"Total Patent Matches: {evidence['total_matches']}")
            lines.append("")
            
            for i, match in enumerate(evidence['signatures'], 1):
                lines.append(f"Patent Match #{i}:")
                lines.append(f"  Signature ID: {match['signature_id']}")
                lines.append(f"  Patent Number: {match['patent_number']}")
                lines.append(f"  Paragraph: {match['patent_paragraph']}")
                lines.append(f"  Detected By: {match['operator_name']}")
                lines.append(f"  Method: {match['manipulation_method']}")
                lines.append(f"  Confidence: {match['match_confidence']:.3f}")
                lines.append(f"  Citation:")
                lines.append(f"    {match['citation'][:200]}...")
                lines.append("")
        
        lines.append("=" * 80)
        lines.append("Operator Results:")
        lines.append("=" * 80)
        for result in window.operator_results:
            lines.append(f"{result.operator_name}: confidence={result.confidence:.3f}")
            if result.metrics:
                for key, val in result.metrics.items():
                    lines.append(f"  {key}: {val}")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
