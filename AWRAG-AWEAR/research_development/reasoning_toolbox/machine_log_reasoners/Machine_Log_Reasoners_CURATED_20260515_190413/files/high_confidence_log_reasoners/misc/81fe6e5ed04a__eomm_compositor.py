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
║     File automatically watermarked on: 2025-11-29 00:00:00                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import List, Dict, Any
import yaml
from pathlib import Path
import sys

# Import unified schema
sys.path.insert(0, str(Path(__file__).parent.parent))
from truevision_schema import OperatorResult, TelemetryWindow, ManipulationFlags
from session_baseline import SessionBaselineTracker


class EommCompositor:
    """
    EOMM Signature Compositor - combines all operator results into unified TelemetryWindow.
    
    Responsibilities:
    - Aggregate confidence scores from all operators
    - Weight by operator reliability and detection quality
    - Generate composite EOMM manipulation score
    - Deduplicate flags across operators
    - Package results in TelemetryWindow format
    """
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        eomm_config = self.config.get("eomm_composite", {})
        self.operator_weights = eomm_config.get("operator_weights", {
            "crosshair_lock": 0.3,
            "hit_registration": 0.3,
            "death_event": 0.25,
            "edge_entry": 0.15
        })
        
        self.manipulation_threshold = eomm_config.get("manipulation_threshold", 0.5)
        self.high_confidence_threshold = eomm_config.get("high_confidence_threshold", 0.75)
        
        print(f"[+] EOMM Compositor initialized")
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
        Compose TelemetryWindow from multiple operator results.
        
        Args:
            operator_results: List of results from all operators
            window_start_epoch: Window start timestamp (Unix epoch)
            window_end_epoch: Window end timestamp
            session_id: Unique session identifier
            frame_count: Number of frames analyzed
            session_tracker: Session baseline tracker for metadata
        
        Returns:
            TelemetryWindow with composite EOMM scoring
        """
        # Compute weighted average confidence score
        composite_score = self._compute_composite_score(operator_results)
        
        # Aggregate flags from all operators (deduplicated)
        all_flags = self._aggregate_flags(operator_results)
        
        # Build metadata with session baselines
        metadata = session_tracker.to_dict()
        metadata["manipulation_detected"] = composite_score >= self.manipulation_threshold
        metadata["high_confidence"] = composite_score >= self.high_confidence_threshold
        
        # Package into TelemetryWindow
        window = TelemetryWindow(
            window_start_epoch=window_start_epoch,
            window_end_epoch=window_end_epoch,