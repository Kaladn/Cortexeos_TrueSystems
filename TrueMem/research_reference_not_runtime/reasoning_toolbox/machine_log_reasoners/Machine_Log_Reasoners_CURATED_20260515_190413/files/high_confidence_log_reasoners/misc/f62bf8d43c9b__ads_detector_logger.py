#!/usr/bin/env python3

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
║     File automatically watermarked on: 2026-01-04 09:30:00                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""

"""
CompuCogLogger - ADS (Aim Down Sights) Detection Module
========================================================

Detects when player aims down sights using screen analysis.
Measures decision latency (camera turn → ADS).

Ground Truth: When FOV narrowed or scope overlay appeared.

Detection Methods:
1. FOV Change: Edge/center variance ratio changes when ADS
2. Scope Overlay: Black pixels in corners (scope vignette)

Schema:
- timestamp: ISO 8601 timestamp
- epoch: Unix epoch timestamp
- ads_active: Boolean (ADS detected)
- detection_method: "fov_change" or "scope_overlay"
- confidence: 0.0-1.0 (detection confidence)
- fov_ratio: Edge/center variance ratio
- scope_pixels: Number of black pixels in corners

Output: logs/ads_detection/ads_detection_YYYYMMDD.jsonl
"""

import os
import json
import time
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

# Import common utilities
try:
    from logger_common import get_timestamp, write_safe, cleanup_old_logs
except ImportError:
    def get_timestamp():
        now = datetime.now()
        return {
            "timestamp": now.isoformat(),
            "epoch": time.time(),
            "date": now.strftime("%Y%m%d")
        }
    
    def write_safe(log_file, data, max_retries=3):
        for attempt in range(max_retries):
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
                    f.flush()
                return True
            except Exception:
                time.sleep(0.05 * (attempt + 1))
        return False
    
    def cleanup_old_logs(logs_dir, max_age_days=1):
        return 0


@dataclass
class ADSEvent:
    """ADS state change event"""
    timestamp: float
    ads_active: bool
    detection_method: str
    confidence: float
    fov_ratio: float
    scope_pixels: int


class ADSDetectorLogger:
    """
    Detects ADS (Aim Down Sights) using screen analysis.
    
    Ground truth: When FOV narrowed or scope appeared.
    """
    
    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialize ADS detector logger.
        
        Args:
            logs_dir: Directory for log files (default: logs/ads_detection)
        """
        # Setup logging directory
        if logs_dir is None:
            script_dir = Path(__file__).parent
            logs_dir = script_dir / ".." / "logs" / "ads_detection"
        
        self.logs_dir = Path(logs_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.baseline_fov_ratio = None
        self.current_ads_state = False
        self.last_ads_timestamp = None
        
        # Detection thresholds
        self.fov_threshold = 0.15  # 15% change in FOV ratio
        self.scope_pixel_threshold = 1000  # Min black pixels for scope
        
        # Sample counter
        self.sample_count = 0
        
        # Setup logging
        self._setup_logging()
        
        logging.info(f"ADS Detector Logger Started")
        logging.info(f"Log Directory: {self.logs_dir}")
        logging.info(f"FOV Threshold: {self.fov_threshold * 100}%")
        logging.info(f"Scope Pixel Threshold: {self.scope_pixel_threshold}")
        logging.info("")
    
    def _setup_logging(self):
        """Configure logging output"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _get_log_file_path(self) -> Path:
        """Get today's log file path"""
        today = datetime.now().strftime("%Y%m%d")
        return self.logs_dir / f"ads_detection_{today}.jsonl"
    
    def _detect_fov_change(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Detect FOV change (Method 1).
        
        When ADS, FOV narrows → edge variance decreases relative to center.
        
        Args:
            frame: RGB frame (height, width, 3)
        
        Returns:
            Tuple of (ads_detected, fov_ratio)
        """
        try:
            h, w = frame.shape[:2]
            
            # Extract edge region (outer 10%)
            edge_thickness = int(min(h, w) * 0.1)
            edge_top = frame[:edge_thickness, :, :]
            edge_bottom = frame[-edge_thickness:, :, :]
            edge_left = frame[:, :edge_thickness, :]
            edge_right = frame[:, -edge_thickness:, :]
            edge_region = np.concatenate([
                edge_top.reshape(-1, 3),
                edge_bottom.reshape(-1, 3),
                edge_left.reshape(-1, 3),
                edge_right.reshape(-1, 3)
            ])
            
            # Extract center region (middle 50%)
            center_h_start = h // 4
            center_h_end = 3 * h // 4
            center_w_start = w // 4
            center_w_end = 3 * w // 4
            center_region = frame[center_h_start:center_h_end, center_w_start:center_w_end, :]
            
            # Compute variance
            edge_variance = np.var(edge_region)
            center_variance = np.var(center_region)
            
            # FOV ratio (edge/center)
            fov_ratio = edge_variance / (center_variance + 1e-6)
            
            # Establish baseline on first frame
            if self.baseline_fov_ratio is None:
                self.baseline_fov_ratio = fov_ratio
                return False, fov_ratio
            
            # Detect ADS (FOV ratio drops)
            ratio_change = abs(fov_ratio - self.baseline_fov_ratio) / self.baseline_fov_ratio
            ads_detected = ratio_change > self.fov_threshold and fov_ratio < self.baseline_fov_ratio
            
            return ads_detected, float(fov_ratio)
        
        except Exception as e:
            logging.error(f"Error detecting FOV change: {e}")
            return False, 0.0
    
    def _detect_scope_overlay(self, frame: np.ndarray) -> Tuple[bool, int]:
        """
        Detect scope overlay (Method 2).
        
        Scopes have black vignette in corners.
        
        Args:
            frame: RGB frame (height, width, 3)
        
        Returns:
            Tuple of (ads_detected, scope_pixels)
        """
        try:
            h, w = frame.shape[:2]
            
            # Extract corners (10% of frame size)
            corner_size = int(min(h, w) * 0.1)
            
            corners = [
                frame[:corner_size, :corner_size, :],  # Top-left
                frame[:corner_size, -corner_size:, :],  # Top-right
                frame[-corner_size:, :corner_size, :],  # Bottom-left
                frame[-corner_size:, -corner_size:, :]  # Bottom-right
            ]
            
            # Count black pixels (RGB < 30)
            scope_pixels = 0
            for corner in corners:
                black_mask = np.all(corner < 30, axis=2)
                scope_pixels += np.sum(black_mask)
            
            # Detect ADS (enough black pixels)
            ads_detected = scope_pixels > self.scope_pixel_threshold
            
            return ads_detected, int(scope_pixels)
        
        except Exception as e:
            logging.error(f"Error detecting scope overlay: {e}")
            return False, 0
    
    def analyze_frame(
        self,
        frame: np.ndarray,
        frame_timestamp: float
    ) -> Optional[ADSEvent]:
        """
        Analyze single frame for ADS state.
        
        Args:
            frame: RGB frame (height, width, 3)
            frame_timestamp: Frame timestamp in seconds
        
        Returns:
            ADSEvent if state changed, None otherwise
        """
        try:
            # Method 1: FOV change
            fov_detected, fov_ratio = self._detect_fov_change(frame)
            
            # Method 2: Scope overlay
            scope_detected, scope_pixels = self._detect_scope_overlay(frame)
            
            # Combine detections
            ads_active = fov_detected or scope_detected
            
            # Determine detection method and confidence
            if fov_detected and scope_detected:
                detection_method = "both"
                confidence = 1.0
            elif fov_detected:
                detection_method = "fov_change"
                confidence = 0.7
            elif scope_detected:
                detection_method = "scope_overlay"
                confidence = 0.8
            else:
                detection_method = "none"
                confidence = 0.0
            
            # Check for state change
            state_changed = ads_active != self.current_ads_state
            self.current_ads_state = ads_active
            
            if state_changed:
                self.last_ads_timestamp = frame_timestamp
            
            # Create event (log state changes or every 30th frame)
            if state_changed or self.sample_count % 30 == 0:
                event = ADSEvent(
                    timestamp=frame_timestamp,
                    ads_active=ads_active,
                    detection_method=detection_method,
                    confidence=confidence,
                    fov_ratio=fov_ratio,
                    scope_pixels=scope_pixels
                )
                return event
            
            return None
        
        except Exception as e:
            logging.error(f"Error analyzing frame: {e}")
            return None
    
    def log_event(self, event: ADSEvent, correlation_data: Optional[Dict] = None):
        """
        Log ADS event to JSONL.
        
        Args:
            event: ADSEvent
            correlation_data: Optional correlation with enemy entry
        """
        try:
            self.sample_count += 1
            
            # Get log file
            log_file = self._get_log_file_path()
            
            # Build log entry
            ts = get_timestamp()
            log_entry = {
                **ts,
                "ads_active": event.ads_active,
                "detection_method": event.detection_method,
                "confidence": event.confidence,
                "fov_ratio": event.fov_ratio,
                "scope_pixels": event.scope_pixels,
                "frame_timestamp": event.timestamp
            }
            
            # Add correlation data if provided
            if correlation_data:
                log_entry["correlation"] = correlation_data
            
            # Write to JSONL
            write_safe(log_file, log_entry)
            
            # Status update every 20 samples
            if self.sample_count % 20 == 0:
                status = "ADS" if event.ads_active else "HIP"
                logging.info(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"{self.sample_count} events | {status} | "
                    f"Method: {event.detection_method} | "
                    f"Confidence: {event.confidence:.2f}"
                )
        
        except Exception as e:
            logging.error(f"Error logging event: {e}")
    
    def get_ads_start_after_enemy_entry(
        self,
        enemy_entry_time: float,
        events: List[ADSEvent],
        time_window: float = 2.0
    ) -> Optional[Tuple[float, Dict]]:
        """
        Find first ADS activation after enemy entry.
        
        Args:
            enemy_entry_time: When enemy entered screen
            events: List of ADS events
            time_window: Max time after entry to look (seconds)
        
        Returns:
            Tuple of (timestamp, correlation_data) or None
        """
        for event in events:
            if enemy_entry_time <= event.timestamp <= enemy_entry_time + time_window:
                if event.ads_active:
                    correlation_data = {
                        "enemy_entry_time": enemy_entry_time,
                        "ads_start_time": event.timestamp,
                        "decision_latency": event.timestamp - enemy_entry_time,
                        "detection_method": event.detection_method,
                        "confidence": event.confidence
                    }
                    return event.timestamp, correlation_data
        
        return None
    
    def cleanup(self):
        """Clean up old log files"""
        deleted = cleanup_old_logs(self.logs_dir, max_age_days=1)
        if deleted > 0:
            logging.info(f"Cleaned up {deleted} old log files")


def main():
    """
    Example usage / testing
    """
    logger = ADSDetectorLogger()
    
    # Simulate frame analysis
    try:
        frame_count = 0
        while True:
            time.sleep(0.033)  # ~30 FPS
            frame_count += 1
            
            # Create mock frame (replace with real data)
            frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
            
            # Analyze frame
            event = logger.analyze_frame(frame, frame_timestamp=time.time())
            
            # Log if event detected
            if event:
                logger.log_event(event)
            
            # Cleanup every 1000 frames
            if frame_count % 1000 == 0:
                logger.cleanup()
    
    except KeyboardInterrupt:
        logging.info(f"ADS detector stopped ({logger.sample_count} events)")


if __name__ == "__main__":
    main()
