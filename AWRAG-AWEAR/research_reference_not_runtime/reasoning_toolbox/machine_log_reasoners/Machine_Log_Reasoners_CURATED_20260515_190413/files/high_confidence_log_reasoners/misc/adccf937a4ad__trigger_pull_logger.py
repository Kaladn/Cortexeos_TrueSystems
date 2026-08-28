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
CompuCogLogger - Trigger Pull Detection Module
===============================================

Detects weapon firing using muzzle flash and screen shake.
Measures motor latency (crosshair on target → trigger pull).

Ground Truth: When weapon was fired.

Detection Methods:
1. Muzzle Flash: Sudden brightness increase in center-bottom
2. Screen Shake: Velocity spike from recoil

Schema:
- timestamp: ISO 8601 timestamp
- epoch: Unix epoch timestamp
- shot_detected: Boolean (shot fired)
- detection_method: "muzzle_flash", "screen_shake", or "both"
- confidence: 0.0-1.0 (detection confidence)
- flash_intensity: Brightness increase (0-255)
- shake_magnitude: Velocity spike magnitude

Output: logs/trigger_pull/trigger_pull_YYYYMMDD.jsonl
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
class ShotEvent:
    """Weapon firing event"""
    timestamp: float
    shot_detected: bool
    detection_method: str
    confidence: float
    flash_intensity: float
    shake_magnitude: float


class TriggerPullLogger:
    """
    Detects weapon firing using muzzle flash and screen shake.
    
    Ground truth: When weapon was fired.
    """
    
    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialize trigger pull logger.
        
        Args:
            logs_dir: Directory for log files (default: logs/trigger_pull)
        """
        # Setup logging directory
        if logs_dir is None:
            script_dir = Path(__file__).parent
            logs_dir = script_dir / ".." / "logs" / "trigger_pull"
        
        self.logs_dir = Path(logs_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.baseline_brightness = None
        self.baseline_shake = None
        self.last_shot_timestamp = None
        self.min_shot_interval = 0.05  # 50ms minimum between shots
        
        # Detection thresholds
        self.flash_threshold = 50  # Brightness increase
        self.shake_threshold = 20  # Velocity spike
        
        # Sample counter
        self.sample_count = 0
        
        # Setup logging
        self._setup_logging()
        
        logging.info(f"Trigger Pull Logger Started")
        logging.info(f"Log Directory: {self.logs_dir}")
        logging.info(f"Flash Threshold: {self.flash_threshold}")
        logging.info(f"Shake Threshold: {self.shake_threshold}")
        logging.info(f"Min Shot Interval: {self.min_shot_interval}s")
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
        return self.logs_dir / f"trigger_pull_{today}.jsonl"
    
    def _detect_muzzle_flash(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Detect muzzle flash (Method 1).
        
        Muzzle flash = sudden brightness increase in center-bottom region.
        
        Args:
            frame: RGB frame (height, width, 3)
        
        Returns:
            Tuple of (flash_detected, flash_intensity)
        """
        try:
            h, w = frame.shape[:2]
            
            # Extract center-bottom region (where weapon is)
            region_h = int(h * 0.2)  # Bottom 20%
            region_w = int(w * 0.3)  # Center 30%
            
            h_start = int(h * 0.8)
            h_end = h
            w_start = int(w * 0.35)
            w_end = int(w * 0.65)
            
            muzzle_region = frame[h_start:h_end, w_start:w_end, :]
            
            # Compute average brightness
            brightness = np.mean(muzzle_region)
            
            # Establish baseline on first frame
            if self.baseline_brightness is None:
                self.baseline_brightness = brightness
                return False, 0.0
            
            # Detect flash (brightness spike)
            flash_intensity = brightness - self.baseline_brightness
            flash_detected = flash_intensity > self.flash_threshold
            
            # Update baseline (exponential moving average)
            self.baseline_brightness = 0.9 * self.baseline_brightness + 0.1 * brightness
            
            return flash_detected, float(flash_intensity)
        
        except Exception as e:
            logging.error(f"Error detecting muzzle flash: {e}")
            return False, 0.0
    
    def _detect_screen_shake(self, velocity_buffer: np.ndarray) -> Tuple[bool, float]:
        """
        Detect screen shake from recoil (Method 2).
        
        Recoil = sudden velocity spike across entire frame.
        
        Args:
            velocity_buffer: Motion vectors (height, width, 2) - (dx, dy)
        
        Returns:
            Tuple of (shake_detected, shake_magnitude)
        """
        try:
            # Compute average velocity magnitude
            velocity_magnitude = np.sqrt(
                velocity_buffer[:, :, 0]**2 + velocity_buffer[:, :, 1]**2
            )
            shake_magnitude = np.mean(velocity_magnitude)
            
            # Establish baseline on first frame
            if self.baseline_shake is None:
                self.baseline_shake = shake_magnitude
                return False, 0.0
            
            # Detect shake (velocity spike)
            shake_increase = shake_magnitude - self.baseline_shake
            shake_detected = shake_increase > self.shake_threshold
            
            # Update baseline (exponential moving average)
            self.baseline_shake = 0.9 * self.baseline_shake + 0.1 * shake_magnitude
            
            return shake_detected, float(shake_increase)
        
        except Exception as e:
            logging.error(f"Error detecting screen shake: {e}")
            return False, 0.0
    
    def analyze_frame(
        self,
        frame: np.ndarray,
        velocity_buffer: Optional[np.ndarray],
        frame_timestamp: float
    ) -> Optional[ShotEvent]:
        """
        Analyze single frame for weapon firing.
        
        Args:
            frame: RGB frame (height, width, 3)
            velocity_buffer: Motion vectors (height, width, 2) or None
            frame_timestamp: Frame timestamp in seconds
        
        Returns:
            ShotEvent if shot detected, None otherwise
        """
        try:
            # Prevent double-counting (min interval between shots)
            if self.last_shot_timestamp is not None:
                if frame_timestamp - self.last_shot_timestamp < self.min_shot_interval:
                    return None
            
            # Method 1: Muzzle flash
            flash_detected, flash_intensity = self._detect_muzzle_flash(frame)
            
            # Method 2: Screen shake (if velocity buffer available)
            shake_detected = False
            shake_magnitude = 0.0
            if velocity_buffer is not None:
                shake_detected, shake_magnitude = self._detect_screen_shake(velocity_buffer)
            
            # Combine detections
            shot_detected = flash_detected or shake_detected
            
            # Determine detection method and confidence
            if flash_detected and shake_detected:
                detection_method = "both"
                confidence = 1.0
            elif flash_detected:
                detection_method = "muzzle_flash"
                confidence = 0.8
            elif shake_detected:
                detection_method = "screen_shake"
                confidence = 0.7
            else:
                detection_method = "none"
                confidence = 0.0
            
            # Update last shot timestamp
            if shot_detected:
                self.last_shot_timestamp = frame_timestamp
            
            # Create event (log shots only)
            if shot_detected:
                event = ShotEvent(
                    timestamp=frame_timestamp,
                    shot_detected=shot_detected,
                    detection_method=detection_method,
                    confidence=confidence,
                    flash_intensity=flash_intensity,
                    shake_magnitude=shake_magnitude
                )
                return event
            
            return None
        
        except Exception as e:
            logging.error(f"Error analyzing frame: {e}")
            return None
    
    def log_event(self, event: ShotEvent, correlation_data: Optional[Dict] = None):
        """
        Log shot event to JSONL.
        
        Args:
            event: ShotEvent
            correlation_data: Optional correlation with crosshair on target
        """
        try:
            self.sample_count += 1
            
            # Get log file
            log_file = self._get_log_file_path()
            
            # Build log entry
            ts = get_timestamp()
            log_entry = {
                **ts,
                "shot_detected": event.shot_detected,
                "detection_method": event.detection_method,
                "confidence": event.confidence,
                "flash_intensity": event.flash_intensity,
                "shake_magnitude": event.shake_magnitude,
                "frame_timestamp": event.timestamp
            }
            
            # Add correlation data if provided
            if correlation_data:
                log_entry["correlation"] = correlation_data
            
            # Write to JSONL
            write_safe(log_file, log_entry)
            
            # Status update every shot
            logging.info(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"SHOT #{self.sample_count} | "
                f"Method: {event.detection_method} | "
                f"Confidence: {event.confidence:.2f} | "
                f"Flash: {event.flash_intensity:.1f}"
            )
        
        except Exception as e:
            logging.error(f"Error logging event: {e}")
    
    def get_first_shot_after_crosshair_on_target(
        self,
        crosshair_on_target_time: float,
        events: List[ShotEvent],
        time_window: float = 0.5
    ) -> Optional[Tuple[float, Dict]]:
        """
        Find first shot after crosshair on target.
        
        Args:
            crosshair_on_target_time: When crosshair first on target
            events: List of shot events
            time_window: Max time after crosshair to look (seconds)
        
        Returns:
            Tuple of (timestamp, correlation_data) or None
        """
        for event in events:
            if crosshair_on_target_time <= event.timestamp <= crosshair_on_target_time + time_window:
                if event.shot_detected:
                    correlation_data = {
                        "crosshair_on_target_time": crosshair_on_target_time,
                        "trigger_pull_time": event.timestamp,
                        "motor_latency": event.timestamp - crosshair_on_target_time,
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
    logger = TriggerPullLogger()
    
    # Simulate frame analysis
    try:
        frame_count = 0
        while True:
            time.sleep(0.033)  # ~30 FPS
            frame_count += 1
            
            # Create mock frame (replace with real data)
            frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
            velocity_buffer = np.random.randn(2160, 3840, 2) * 5
            
            # Analyze frame
            event = logger.analyze_frame(
                frame,
                velocity_buffer,
                frame_timestamp=time.time()
            )
            
            # Log if shot detected
            if event:
                logger.log_event(event)
            
            # Cleanup every 1000 frames
            if frame_count % 1000 == 0:
                logger.cleanup()
    
    except KeyboardInterrupt:
        logging.info(f"Trigger pull logger stopped ({logger.sample_count} shots)")


if __name__ == "__main__":
    main()
