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
CompuCogLogger - Camera Movement Detection Module
==================================================

Detects camera movement toward threats using velocity buffer analysis.
Measures perceptual latency (enemy entry → camera turn).

Ground Truth: When player physically moved camera toward threat.

Schema:
- timestamp: ISO 8601 timestamp
- epoch: Unix epoch timestamp
- camera_angle: Camera direction in degrees (0-360)
- camera_speed: Velocity magnitude (pixels/frame)
- angle_change: Degrees turned from previous frame
- movement_detected: Boolean (significant movement)
- correlation_data: {enemy_entry_time, enemy_location, matched}

Output: logs/camera_movement/camera_movement_YYYYMMDD.jsonl
"""

import os
import json
import time
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

# Import common utilities
try:
    from logger_common import get_timestamp, write_safe, cleanup_old_logs
except ImportError:
    # Fallback if logger_common not available
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
class CameraMovement:
    """Camera movement event"""
    timestamp: float
    angle_change: float
    camera_speed: float
    direction: float  # 0-360 degrees
    movement_detected: bool


class CameraMovementLogger:
    """
    Detects camera movement toward threats using velocity buffer.
    
    Ground truth: When camera starts moving toward enemy location.
    """
    
    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialize camera movement logger.
        
        Args:
            logs_dir: Directory for log files (default: logs/camera_movement)
        """
        # Setup logging directory
        if logs_dir is None:
            script_dir = Path(__file__).parent
            logs_dir = script_dir / ".." / "logs" / "camera_movement"
        
        self.logs_dir = Path(logs_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.previous_camera_direction = None
        self.movement_threshold = 5.0  # degrees per frame
        self.last_movement_timestamp = None
        
        # Sample counter
        self.sample_count = 0
        
        # Setup logging
        self._setup_logging()
        
        logging.info(f"Camera Movement Logger Started")
        logging.info(f"Log Directory: {self.logs_dir}")
        logging.info(f"Movement Threshold: {self.movement_threshold} degrees")
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
        return self.logs_dir / f"camera_movement_{today}.jsonl"
    
    def analyze_frame(
        self, 
        velocity_buffer: np.ndarray, 
        frame_timestamp: float,
        frame_h: int,
        frame_w: int
    ) -> Optional[CameraMovement]:
        """
        Analyze single frame for camera movement.
        
        Args:
            velocity_buffer: Motion vectors (height, width, 2) - (dx, dy)
            frame_timestamp: Frame timestamp in seconds
            frame_h: Frame height
            frame_w: Frame width
        
        Returns:
            CameraMovement if significant movement detected, None otherwise
        """
        try:
            # STEP 1: Extract center region (camera movement dominates)
            center_h = frame_h // 2
            center_w = frame_w // 2
            region_size = 200  # pixels
            
            h_start = max(0, center_h - region_size)
            h_end = min(frame_h, center_h + region_size)
            w_start = max(0, center_w - region_size)
            w_end = min(frame_w, center_w + region_size)
            
            center_region = velocity_buffer[h_start:h_end, w_start:w_end, :]
            
            # STEP 2: Compute average motion vector
            avg_dx = np.mean(center_region[:, :, 0])
            avg_dy = np.mean(center_region[:, :, 1])
            
            # Convert to angle (0-360 degrees)
            camera_angle = np.arctan2(avg_dy, avg_dx) * 180 / np.pi
            if camera_angle < 0:
                camera_angle += 360
            
            camera_speed = np.sqrt(avg_dx**2 + avg_dy**2)
            
            # STEP 3: Detect significant camera movement
            movement_detected = False
            angle_change = 0.0
            
            if self.previous_camera_direction is not None:
                angle_change = abs(camera_angle - self.previous_camera_direction)
                
                # Normalize to 0-180 range
                if angle_change > 180:
                    angle_change = 360 - angle_change
                
                # Check if movement exceeds threshold
                if angle_change > self.movement_threshold:
                    movement_detected = True
                    self.last_movement_timestamp = frame_timestamp
            
            self.previous_camera_direction = camera_angle
            
            # Create movement event
            if movement_detected or self.sample_count % 10 == 0:  # Log every 10th frame or on movement
                movement = CameraMovement(
                    timestamp=frame_timestamp,
                    angle_change=angle_change,
                    camera_speed=float(camera_speed),
                    direction=float(camera_angle),
                    movement_detected=movement_detected
                )
                return movement
            
            return None
            
        except Exception as e:
            logging.error(f"Error analyzing frame: {e}")
            return None
    
    def log_movement(self, movement: CameraMovement, correlation_data: Optional[Dict] = None):
        """
        Log camera movement event to JSONL.
        
        Args:
            movement: CameraMovement event
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
                "camera_angle": movement.direction,
                "camera_speed": movement.camera_speed,
                "angle_change": movement.angle_change,
                "movement_detected": movement.movement_detected,
                "frame_timestamp": movement.timestamp
            }
            
            # Add correlation data if provided
            if correlation_data:
                log_entry["correlation"] = correlation_data
            
            # Write to JSONL
            write_safe(log_file, log_entry)
            
            # Status update every 20 samples
            if self.sample_count % 20 == 0:
                status = "MOVING" if movement.movement_detected else "STABLE"
                logging.info(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"{self.sample_count} events | {status} | "
                    f"Angle: {movement.direction:.1f}° | "
                    f"Speed: {movement.camera_speed:.2f}"
                )
        
        except Exception as e:
            logging.error(f"Error logging movement: {e}")
    
    def correlate_with_enemy_entry(
        self,
        enemy_entry_time: float,
        enemy_entry_location: str,
        movements: List[CameraMovement],
        time_window: float = 1.0
    ) -> Optional[Tuple[float, Dict]]:
        """
        Find first camera movement toward enemy after entry.
        
        Args:
            enemy_entry_time: When enemy entered screen
            enemy_entry_location: Screen location (e.g., "11_oclock")
            movements: List of camera movements
            time_window: Max time after entry to look (seconds)
        
        Returns:
            Tuple of (timestamp, correlation_data) or None
        """
        # Convert screen location to expected camera angle
        expected_angles = {
            "12_oclock": 90,   # Up
            "1_oclock": 60,
            "2_oclock": 30,
            "3_oclock": 0,     # Right
            "4_oclock": 330,
            "5_oclock": 300,
            "6_oclock": 270,   # Down
            "7_oclock": 240,
            "8_oclock": 210,
            "9_oclock": 180,   # Left
            "10_oclock": 150,
            "11_oclock": 120
        }
        
        expected_angle = expected_angles.get(enemy_entry_location, None)
        if expected_angle is None:
            return None
        
        # Find first movement toward expected angle within time window
        for movement in movements:
            if enemy_entry_time <= movement.timestamp <= enemy_entry_time + time_window:
                # Check if movement is toward enemy
                angle_diff = abs(movement.direction - expected_angle)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                
                if angle_diff < 45:  # Within 45 degrees of expected
                    correlation_data = {
                        "enemy_entry_time": enemy_entry_time,
                        "enemy_location": enemy_entry_location,
                        "expected_angle": expected_angle,
                        "actual_angle": movement.direction,
                        "angle_diff": angle_diff,
                        "matched": True,
                        "perceptual_latency": movement.timestamp - enemy_entry_time
                    }
                    return movement.timestamp, correlation_data
        
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
    logger = CameraMovementLogger()
    
    # Simulate frame analysis
    try:
        frame_count = 0
        while True:
            time.sleep(0.033)  # ~30 FPS
            frame_count += 1
            
            # Create mock velocity buffer (replace with real data)
            velocity_buffer = np.random.randn(2160, 3840, 2) * 10
            
            # Analyze frame
            movement = logger.analyze_frame(
                velocity_buffer,
                frame_timestamp=time.time(),
                frame_h=2160,
                frame_w=3840
            )
            
            # Log if movement detected
            if movement:
                logger.log_movement(movement)
            
            # Cleanup every 1000 frames
            if frame_count % 1000 == 0:
                logger.cleanup()
    
    except KeyboardInterrupt:
        logging.info(f"Camera movement logger stopped ({logger.sample_count} events)")


if __name__ == "__main__":
    main()
