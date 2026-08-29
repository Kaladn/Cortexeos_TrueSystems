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
CompuCogLogger - Movement State Tracking Module
================================================

Tracks player movement state (stationary, walking, sprinting, crouching, prone).
Provides context for engagement analysis.

Ground Truth: How player was moving during engagement.

Detection Methods:
1. Edge Velocity: Player movement creates edge-to-edge motion
2. Ground/Sky Ratio: Camera height changes with crouch/prone

Movement States:
- STATIONARY: < 5 pixels/frame
- WALKING: 5-20 pixels/frame
- SPRINTING: > 20 pixels/frame
- CROUCHING: Ground ratio > 0.6
- PRONE: Ground ratio > 0.75

Schema:
- timestamp: ISO 8601 timestamp
- epoch: Unix epoch timestamp
- movement_state: "stationary", "walking", "sprinting", "crouching", "prone"
- movement_speed: Pixels per frame
- ground_ratio: Proportion of frame showing ground (0.0-1.0)
- stance: "standing", "crouching", "prone"

Output: logs/movement_state/movement_state_YYYYMMDD.jsonl
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
from enum import Enum

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


class MovementState(Enum):
    """Player movement states"""
    STATIONARY = "stationary"
    WALKING = "walking"
    SPRINTING = "sprinting"


class Stance(Enum):
    """Player stance"""
    STANDING = "standing"
    CROUCHING = "crouching"
    PRONE = "prone"


@dataclass
class MovementEvent:
    """Movement state change event"""
    timestamp: float
    movement_state: str
    stance: str
    movement_speed: float
    ground_ratio: float


class MovementStateLogger:
    """
    Tracks player movement state and stance.
    
    Ground truth: How player was moving.
    """
    
    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialize movement state logger.
        
        Args:
            logs_dir: Directory for log files (default: logs/movement_state)
        """
        # Setup logging directory
        if logs_dir is None:
            script_dir = Path(__file__).parent
            logs_dir = script_dir / ".." / "logs" / "movement_state"
        
        self.logs_dir = Path(logs_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.current_movement_state = MovementState.STATIONARY
        self.current_stance = Stance.STANDING
        self.last_state_change = None
        
        # Detection thresholds
        self.walking_threshold = 5.0  # pixels/frame
        self.sprinting_threshold = 20.0  # pixels/frame
        self.crouch_ground_ratio = 0.6
        self.prone_ground_ratio = 0.75
        
        # Sample counter
        self.sample_count = 0
        
        # Setup logging
        self._setup_logging()
        
        logging.info(f"Movement State Logger Started")
        logging.info(f"Log Directory: {self.logs_dir}")
        logging.info(f"Walking Threshold: {self.walking_threshold} px/frame")
        logging.info(f"Sprinting Threshold: {self.sprinting_threshold} px/frame")
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
        return self.logs_dir / f"movement_state_{today}.jsonl"
    
    def _detect_movement_speed(self, velocity_buffer: np.ndarray) -> float:
        """
        Detect player movement speed from velocity buffer.
        
        Player movement creates edge-to-edge motion (entire frame moves).
        
        Args:
            velocity_buffer: Motion vectors (height, width, 2) - (dx, dy)
        
        Returns:
            Movement speed in pixels/frame
        """
        try:
            # Extract edge regions (player movement affects edges)
            h, w = velocity_buffer.shape[:2]
            edge_thickness = int(min(h, w) * 0.05)
            
            edges = [
                velocity_buffer[:edge_thickness, :, :],  # Top
                velocity_buffer[-edge_thickness:, :, :],  # Bottom
                velocity_buffer[:, :edge_thickness, :],  # Left
                velocity_buffer[:, -edge_thickness:, :]  # Right
            ]
            
            # Compute average velocity magnitude at edges
            edge_velocities = []
            for edge in edges:
                velocity_magnitude = np.sqrt(edge[:, :, 0]**2 + edge[:, :, 1]**2)
                edge_velocities.append(np.mean(velocity_magnitude))
            
            # Average across all edges
            movement_speed = np.mean(edge_velocities)
            
            return float(movement_speed)
        
        except Exception as e:
            logging.error(f"Error detecting movement speed: {e}")
            return 0.0
    
    def _detect_ground_ratio(self, frame: np.ndarray) -> float:
        """
        Detect ground/sky ratio from frame.
        
        Camera height changes with crouch/prone → ground ratio increases.
        
        Args:
            frame: RGB frame (height, width, 3)
        
        Returns:
            Ground ratio (0.0-1.0)
        """
        try:
            h, w = frame.shape[:2]
            
            # Split frame into top half (sky) and bottom half (ground)
            top_half = frame[:h//2, :, :]
            bottom_half = frame[h//2:, :, :]
            
            # Compute average brightness
            top_brightness = np.mean(top_half)
            bottom_brightness = np.mean(bottom_half)
            
            # Ground is typically darker than sky
            # Ground ratio = how much darker bottom is
            if top_brightness > 0:
                ground_ratio = 1.0 - (bottom_brightness / top_brightness)
                ground_ratio = np.clip(ground_ratio, 0.0, 1.0)
            else:
                ground_ratio = 0.5
            
            return float(ground_ratio)
        
        except Exception as e:
            logging.error(f"Error detecting ground ratio: {e}")
            return 0.5
    
    def analyze_frame(
        self,
        frame: np.ndarray,
        velocity_buffer: np.ndarray,
        frame_timestamp: float
    ) -> Optional[MovementEvent]:
        """
        Analyze single frame for movement state.
        
        Args:
            frame: RGB frame (height, width, 3)
            velocity_buffer: Motion vectors (height, width, 2)
            frame_timestamp: Frame timestamp in seconds
        
        Returns:
            MovementEvent if state changed, None otherwise
        """
        try:
            # Detect movement speed
            movement_speed = self._detect_movement_speed(velocity_buffer)
            
            # Classify movement state
            if movement_speed < self.walking_threshold:
                movement_state = MovementState.STATIONARY
            elif movement_speed < self.sprinting_threshold:
                movement_state = MovementState.WALKING
            else:
                movement_state = MovementState.SPRINTING
            
            # Detect ground ratio
            ground_ratio = self._detect_ground_ratio(frame)
            
            # Classify stance
            if ground_ratio > self.prone_ground_ratio:
                stance = Stance.PRONE
            elif ground_ratio > self.crouch_ground_ratio:
                stance = Stance.CROUCHING
            else:
                stance = Stance.STANDING
            
            # Check for state change
            state_changed = (
                movement_state != self.current_movement_state or
                stance != self.current_stance
            )
            
            self.current_movement_state = movement_state
            self.current_stance = stance
            
            if state_changed:
                self.last_state_change = frame_timestamp
            
            # Create event (log state changes or every 30th frame)
            if state_changed or self.sample_count % 30 == 0:
                event = MovementEvent(
                    timestamp=frame_timestamp,
                    movement_state=movement_state.value,
                    stance=stance.value,
                    movement_speed=movement_speed,
                    ground_ratio=ground_ratio
                )
                return event
            
            return None
        
        except Exception as e:
            logging.error(f"Error analyzing frame: {e}")
            return None
    
    def log_event(self, event: MovementEvent):
        """
        Log movement event to JSONL.
        
        Args:
            event: MovementEvent
        """
        try:
            self.sample_count += 1
            
            # Get log file
            log_file = self._get_log_file_path()
            
            # Build log entry
            ts = get_timestamp()
            log_entry = {
                **ts,
                "movement_state": event.movement_state,
                "stance": event.stance,
                "movement_speed": event.movement_speed,
                "ground_ratio": event.ground_ratio,
                "frame_timestamp": event.timestamp
            }
            
            # Write to JSONL
            write_safe(log_file, log_entry)
            
            # Status update every 20 samples
            if self.sample_count % 20 == 0:
                logging.info(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"{self.sample_count} events | "
                    f"{event.movement_state.upper()} | "
                    f"{event.stance.upper()} | "
                    f"Speed: {event.movement_speed:.1f}"
                )
        
        except Exception as e:
            logging.error(f"Error logging event: {e}")
    
    def get_state_at_time(
        self,
        target_time: float,
        events: List[MovementEvent]
    ) -> Optional[MovementEvent]:
        """
        Get movement state at specific time.
        
        Args:
            target_time: Time to query
            events: List of movement events
        
        Returns:
            MovementEvent closest to target_time
        """
        if not events:
            return None
        
        # Find event closest to target time (before or at)
        closest_event = None
        min_diff = float('inf')
        
        for event in events:
            if event.timestamp <= target_time:
                diff = target_time - event.timestamp
                if diff < min_diff:
                    min_diff = diff
                    closest_event = event
        
        return closest_event
    
    def cleanup(self):
        """Clean up old log files"""
        deleted = cleanup_old_logs(self.logs_dir, max_age_days=1)
        if deleted > 0:
            logging.info(f"Cleaned up {deleted} old log files")


def main():
    """
    Example usage / testing
    """
    logger = MovementStateLogger()
    
    # Simulate frame analysis
    try:
        frame_count = 0
        while True:
            time.sleep(0.033)  # ~30 FPS
            frame_count += 1
            
            # Create mock frame and velocity buffer (replace with real data)
            frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
            velocity_buffer = np.random.randn(2160, 3840, 2) * 10
            
            # Analyze frame
            event = logger.analyze_frame(
                frame,
                velocity_buffer,
                frame_timestamp=time.time()
            )
            
            # Log if event detected
            if event:
                logger.log_event(event)
            
            # Cleanup every 1000 frames
            if frame_count % 1000 == 0:
                logger.cleanup()
    
    except KeyboardInterrupt:
        logging.info(f"Movement state logger stopped ({logger.sample_count} events)")


if __name__ == "__main__":
    main()
