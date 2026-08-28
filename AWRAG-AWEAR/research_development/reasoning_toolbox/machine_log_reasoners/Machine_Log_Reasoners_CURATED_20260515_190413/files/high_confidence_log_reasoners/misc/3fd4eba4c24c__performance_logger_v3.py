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
║     File automatically watermarked on: 2026-01-04 12:00:00                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""

"""
CompuCog Performance Logger V3 - Row Contract Compliant
========================================================

DeepSeek's Row Contract:
- Rows = time snapshots, not stories
- One epoch_utc per row (Column A = truth anchor)
- Instantaneous fields (events) = happened at T, reset next row
- Latched fields (state) = value at T, persist until changed
- No multi-time semantics (no write_time, logger_time, etc.)

"Think of this as writing the spec comments you wish had existed in 1992 Excel."
"""

import os
import csv
import time
import logging
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


# ============================================================================
# EVENT TYPES
# ============================================================================

class EventType(Enum):
    """Event types emitted by sensors"""
    CAMERA_MOVE = "camera_move"
    ADS_CHANGE = "ads_change"
    TRIGGER_PULL = "trigger_pull"
    HIT_MARKER = "hit_marker"
    MOVEMENT_STATE = "movement_state"
    ENEMY_ENTRY = "enemy_entry"
    CROSSHAIR_LOCK = "crosshair_lock"


@dataclass
class SensorEvent:
    """Base event emitted by sensors"""
    event_type: EventType
    epoch: float
    data: Dict[str, Any]


# ============================================================================
# ROW SCHEMA (DeepSeek's Row Contract)
# ============================================================================

@dataclass
class PerformanceRow:
    """
    Single row representing one frame-time snapshot.
    
    ROW CONTRACT:
    - All fields describe the same moment T (epoch_utc)
    - Instantaneous fields (events) = happened at T, reset next row
    - Latched fields (state) = value at T, persist until changed
    - No multi-time semantics
    
    FORBIDDEN FIELDS (violate row contract):
    - write_time
    - detection_time
    - analysis_time
    - logger_time
    - Any additional time fields violate the row contract.
    """
    
    # ========================================================================
    # ROW ANCHOR (Column A = truth)
    # ========================================================================
    epoch_utc: float  # Authoritative time (seconds since epoch)
    timestamp_utc: str  # Human-readable (derived from epoch_utc)
    frame_index: int  # Monotonic counter (ordering proof)
    
    # ========================================================================
    # INSTANTANEOUS EVENTS (happened at T, reset next row)
    # ========================================================================
    trigger_pull_event: bool = False
    hit_marker_white_event: bool = False
    hit_marker_red_event: bool = False
    ads_enter_event: bool = False
    ads_exit_event: bool = False
    camera_snap_event: bool = False
    enemy_entry_event: bool = False
    crosshair_lock_event: bool = False
    
    # ========================================================================
    # EVENT CONFIDENCE (scoped to events, not rows)
    # ========================================================================
    trigger_pull_confidence: Optional[float] = None
    hit_marker_confidence: Optional[float] = None
    camera_snap_confidence: Optional[float] = None
    
    # ========================================================================
    # LATCHED STATE (value at T, persist until changed)
    # ========================================================================
    ads_active: bool = False
    movement_state: Optional[str] = None  # "stationary", "walking", "sprinting"
    stance: Optional[str] = None  # "standing", "crouching", "prone"
    camera_speed: Optional[float] = None
    crosshair_on_target: bool = False
    player_velocity: Optional[float] = None
    
    # ========================================================================
    # CONTEXT (latched, for correlation)
    # ========================================================================
    enemy_distance: Optional[float] = None
    enemy_location: Optional[str] = None  # "11_oclock", "3_oclock", etc.
    
    # ========================================================================
    # DERIVED METRICS (calculated from events, not stored in sensors)
    # ========================================================================
    # These are NOT part of the row contract, but calculated post-hoc
    # from event sequences. They belong in a separate analysis layer.
    # Included here for convenience, but marked as derived.
    # ========================================================================


# ============================================================================
# SENSORS (Pure Detection)
# ============================================================================

class CameraMovementSensor:
    """
    Detects camera movement from velocity buffer.
    
    Emits: CAMERA_MOVE event when significant movement detected.
    """
    
    def __init__(self, movement_threshold: float = 5.0, snap_threshold: float = 50.0):
        self.movement_threshold = movement_threshold
        self.snap_threshold = snap_threshold
        self.previous_speed = 0.0
    
    def observe(self, frame: np.ndarray, velocity_buffer: Optional[np.ndarray], epoch: float) -> Optional[SensorEvent]:
        """
        Observe frame and detect camera movement.
        
        Returns:
            SensorEvent if movement detected, None otherwise
        """
        if velocity_buffer is None:
            return None
        
        # Compute velocity magnitude
        velocity_magnitude = np.sqrt(
            velocity_buffer[:, :, 0]**2 + velocity_buffer[:, :, 1]**2
        )
        speed = float(np.mean(velocity_magnitude))
        
        # Detect camera snap (sudden large movement)
        speed_delta = abs(speed - self.previous_speed)
        is_snap = speed_delta > self.snap_threshold
        
        self.previous_speed = speed
        
        # Emit event if significant movement
        if speed > self.movement_threshold:
            # Compute direction
            avg_dx = np.mean(velocity_buffer[:, :, 0])
            avg_dy = np.mean(velocity_buffer[:, :, 1])
            direction = float(np.degrees(np.arctan2(avg_dy, avg_dx)))
            
            return SensorEvent(
                event_type=EventType.CAMERA_MOVE,
                epoch=epoch,
                data={
                    "direction": direction,
                    "speed": speed,
                    "is_snap": is_snap,
                    "snap_confidence": min(1.0, speed_delta / 100.0) if is_snap else 0.0
                }
            )
        
        return None


class ADSSensor:
    """
    Detects ADS (Aim Down Sights) state from FOV changes.
    
    Emits: ADS_CHANGE event when ADS state changes.
    """
    
    def __init__(self, ads_fov_ratio: float = 1.5, scope_black_threshold: float = 0.7):
        self.ads_fov_ratio = ads_fov_ratio
        self.scope_black_threshold = scope_black_threshold
        self.previous_ads_active = False
    
    def observe(self, frame: np.ndarray, epoch: float) -> Optional[SensorEvent]:
        """
        Observe frame and detect ADS state.
        
        Returns:
            SensorEvent if ADS state changed, None otherwise
        """
        h, w = frame.shape[:2]
        
        # Method 1: FOV change detection
        center_region = frame[h//4:3*h//4, w//4:3*w//4, :]
        edge_region = np.concatenate([
            frame[:h//4, :, :].flatten(),
            frame[3*h//4:, :, :].flatten(),
            frame[:, :w//4, :].flatten(),
            frame[:, 3*w//4:, :].flatten()
        ])
        
        center_variance = float(np.var(center_region))
        edge_variance = float(np.var(edge_region))
        
        fov_ratio = None
        ads_active = False
        
        if edge_variance > 0:
            fov_ratio = center_variance / edge_variance
            if fov_ratio > self.ads_fov_ratio:
                ads_active = True
        
        # Method 2: Scope overlay detection (black corners)
        corners = [
            frame[:50, :50, :],
            frame[:50, -50:, :],
            frame[-50:, :50, :],
            frame[-50:, -50:, :]
        ]
        black_pixel_ratio = sum(
            np.mean(corner < 30) for corner in corners
        ) / 4
        
        scope_detected = black_pixel_ratio > self.scope_black_threshold
        
        if scope_detected:
            ads_active = True
        
        # Emit event on state change
        if ads_active != self.previous_ads_active:
            event_type = "enter" if ads_active else "exit"
            self.previous_ads_active = ads_active
            
            return SensorEvent(
                event_type=EventType.ADS_CHANGE,
                epoch=epoch,
                data={
                    "ads_active": ads_active,
                    "event_type": event_type,
                    "fov_ratio": fov_ratio,
                    "scope_detected": scope_detected
                }
            )
        
        return None


class TriggerPullSensor:
    """
    Detects trigger pull from muzzle flash.
    
    Emits: TRIGGER_PULL event when shot detected.
    """
    
    def __init__(self, flash_threshold: float = 200.0):
        self.flash_threshold = flash_threshold
    
    def observe(self, frame: np.ndarray, epoch: float) -> Optional[SensorEvent]:
        """
        Observe frame and detect trigger pull.
        
        Returns:
            SensorEvent if shot detected, None otherwise
        """
        h, w = frame.shape[:2]
        
        # Detect muzzle flash (center region bright flash)
        center_region = frame[h//4:3*h//4, w//4:3*w//4, :]
        center_brightness = float(np.mean(center_region))
        
        if center_brightness > self.flash_threshold:
            confidence = min(1.0, (center_brightness - self.flash_threshold) / 55)
            
            return SensorEvent(
                event_type=EventType.TRIGGER_PULL,
                epoch=epoch,
                data={
                    "confidence": confidence,
                    "muzzle_flash_intensity": center_brightness
                }
            )
        
        return None


class HitMarkerSensor:
    """
    Detects hit marker (white X) from screen center.
    
    Emits: HIT_MARKER event when hit marker detected.
    """
    
    def __init__(self, white_threshold: int = 200, red_threshold: int = 150):
        self.white_threshold = white_threshold
        self.red_threshold = red_threshold
    
    def observe(self, frame: np.ndarray, epoch: float) -> Optional[SensorEvent]:
        """
        Observe frame and detect hit marker.
        
        Returns:
            SensorEvent if hit marker detected, None otherwise
        """
        h, w = frame.shape[:2]
        
        # Sample center and diagonals
        center_y, center_x = h // 2, w // 2
        samples = [
            frame[center_y, center_x, :],  # Center
            frame[center_y - 10, center_x - 10, :],  # Top-left
            frame[center_y - 10, center_x + 10, :],  # Top-right
            frame[center_y + 10, center_x - 10, :],  # Bottom-left
            frame[center_y + 10, center_x + 10, :],  # Bottom-right
        ]
        
        # Check for white X (hit marker)
        white_count = sum(1 for sample in samples if np.all(sample > self.white_threshold))
        
        if white_count >= 3:  # At least 3 samples are white
            return SensorEvent(
                event_type=EventType.HIT_MARKER,
                epoch=epoch,
                data={
                    "marker_type": "white",
                    "confidence": white_count / len(samples)
                }
            )
        
        # Check for red X (kill marker)
        red_count = sum(1 for sample in samples if sample[0] > self.red_threshold and sample[1] < 100 and sample[2] < 100)
        
        if red_count >= 3:
            return SensorEvent(
                event_type=EventType.HIT_MARKER,
                epoch=epoch,
                data={
                    "marker_type": "red",
                    "confidence": red_count / len(samples)
                }
            )
        
        return None


class MovementStateSensor:
    """
    Detects player movement state from velocity and ground ratio.
    
    Emits: MOVEMENT_STATE event when state changes.
    """
    
    def __init__(self):
        self.previous_state = None
        self.previous_stance = None
    
    def observe(self, frame: np.ndarray, velocity_buffer: Optional[np.ndarray], epoch: float) -> Optional[SensorEvent]:
        """
        Observe frame and detect movement state.
        
        Returns:
            SensorEvent if state changed, None otherwise
        """
        h, w = frame.shape[:2]
        
        # Detect movement state from velocity
        movement_state = None
        movement_speed = None
        
        if velocity_buffer is not None:
            velocity_magnitude = np.sqrt(
                velocity_buffer[:, :, 0]**2 + velocity_buffer[:, :, 1]**2
            )
            movement_speed = float(np.mean(velocity_magnitude))
            
            if movement_speed < 5.0:
                movement_state = "stationary"
            elif movement_speed < 20.0:
                movement_state = "walking"
            else:
                movement_state = "sprinting"
        
        # Detect stance from ground ratio
        h_mid = h // 2
        top_half = frame[:h_mid, :, :]
        bottom_half = frame[h_mid:, :, :]
        
        top_brightness = float(np.mean(top_half))
        bottom_brightness = float(np.mean(bottom_half))
        
        stance = None
        if top_brightness > 0:
            ground_ratio = 1.0 - (bottom_brightness / top_brightness)
            ground_ratio = np.clip(ground_ratio, 0.0, 1.0)
            
            if ground_ratio > 0.75:
                stance = "prone"
            elif ground_ratio > 0.6:
                stance = "crouching"
            else:
                stance = "standing"
        
        # Emit event on state change
        if movement_state != self.previous_state or stance != self.previous_stance:
            self.previous_state = movement_state
            self.previous_stance = stance
            
            return SensorEvent(
                event_type=EventType.MOVEMENT_STATE,
                epoch=epoch,
                data={
                    "movement_state": movement_state,
                    "stance": stance,
                    "movement_speed": movement_speed
                }
            )
        
        return None


# ============================================================================
# PERFORMANCE LOGGER (Row Contract Compliant)
# ============================================================================

class PerformanceLogger:
    """
    Performance logger compliant with DeepSeek's row contract.
    
    ROW CONTRACT:
    - Rows = time snapshots, not stories
    - One epoch_utc per row (Column A = truth anchor)
    - Instantaneous fields (events) reset every row
    - Latched fields (state) persist until changed
    - No multi-time semantics
    """
    
    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialize performance logger.
        
        Args:
            logs_dir: Directory for CSV files (default: logs/)
        """
        # Setup logging directory
        if logs_dir is None:
            script_dir = Path(__file__).parent
            logs_dir = script_dir / "logs"
        
        self.logs_dir = Path(logs_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sensors
        self.camera_sensor = CameraMovementSensor()
        self.ads_sensor = ADSSensor()
        self.trigger_sensor = TriggerPullSensor()
        self.hit_marker_sensor = HitMarkerSensor()
        self.movement_sensor = MovementStateSensor()
        
        # Frame counter (monotonic)
        self.frame_index = 0
        
        # Latched state (persists across rows)
        self.latched_state = {
            "ads_active": False,
            "movement_state": None,
            "stance": None,
            "camera_speed": None,
            "crosshair_on_target": False,
            "player_velocity": None,
            "enemy_distance": None,
            "enemy_location": None
        }
        
        # CSV file handle
        self.csv_file = None
        self.csv_writer = None
        
        # Setup logging
        self._setup_logging()
        
        # Initialize CSV
        self._initialize_csv()
        
        logging.info(f"Performance Logger V3 Started (Row Contract Compliant)")
        logging.info(f"Log Directory: {self.logs_dir}")
        logging.info(f"CSV File: {self._get_csv_path()}")
        logging.info("")
    
    def _setup_logging(self):
        """Configure logging output"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _get_csv_path(self) -> Path:
        """Get today's CSV file path"""
        today = datetime.now().strftime("%Y%m%d")
        return self.logs_dir / f"performance_log_{today}.csv"
    
    def _initialize_csv(self):
        """Initialize CSV file with headers"""
        csv_path = self._get_csv_path()
        
        # Check if file exists
        file_exists = csv_path.exists()
        
        # Open in append mode
        self.csv_file = open(csv_path, "a", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        
        # Write header if new file
        if not file_exists:
            headers = [
                # ROW ANCHOR
                "epoch_utc", "timestamp_utc", "frame_index",
                
                # INSTANTANEOUS EVENTS
                "trigger_pull_event", "hit_marker_white_event", "hit_marker_red_event",
                "ads_enter_event", "ads_exit_event", "camera_snap_event",
                "enemy_entry_event", "crosshair_lock_event",
                
                # EVENT CONFIDENCE
                "trigger_pull_confidence", "hit_marker_confidence", "camera_snap_confidence",
                
                # LATCHED STATE
                "ads_active", "movement_state", "stance",
                "camera_speed", "crosshair_on_target", "player_velocity",
                
                # CONTEXT
                "enemy_distance", "enemy_location"
            ]
            self.csv_writer.writerow(headers)
            self.csv_file.flush()
            logging.info(f"Created new CSV file: {csv_path}")
        else:
            logging.info(f"Appending to existing CSV file: {csv_path}")
    
    def process_frame(
        self,
        frame: np.ndarray,
        velocity_buffer: Optional[np.ndarray],
        frame_epoch: float,
        frame_h: int,
        frame_w: int,
        enemy_entry: Optional[Dict[str, Any]] = None,
        crosshair_on_target: Optional[Dict[str, Any]] = None
    ):
        """
        Process single frame through sensor pipeline.
        
        Args:
            frame: RGB frame (height, width, 3)
            velocity_buffer: Motion vectors (height, width, 2) or None
            frame_epoch: Frame timestamp (epoch seconds)
            frame_h: Frame height
            frame_w: Frame width
            enemy_entry: Enemy entry event (optional)
            crosshair_on_target: Crosshair lock event (optional)
        """
        self.frame_index += 1
        
        # All instantaneous events reset per row by construction
        # (PerformanceRow dataclass defaults all *_event fields to False)
        row = PerformanceRow(
            epoch_utc=frame_epoch,
            timestamp_utc=datetime.fromtimestamp(frame_epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
            frame_index=self.frame_index
        )
        
        # STEP 1: Run all sensors
        events = []
        
        # Camera movement
        camera_event = self.camera_sensor.observe(frame, velocity_buffer, frame_epoch)
        if camera_event:
            events.append(camera_event)
            row.camera_snap_event = camera_event.data.get("is_snap", False)
            row.camera_snap_confidence = camera_event.data.get("snap_confidence")
            self.latched_state["camera_speed"] = camera_event.data.get("speed")
        
        # ADS state
        ads_event = self.ads_sensor.observe(frame, frame_epoch)
        if ads_event:
            events.append(ads_event)
            if ads_event.data.get("event_type") == "enter":
                row.ads_enter_event = True
            else:
                row.ads_exit_event = True
            self.latched_state["ads_active"] = ads_event.data.get("ads_active")
        
        # Trigger pull
        trigger_event = self.trigger_sensor.observe(frame, frame_epoch)
        if trigger_event:
            events.append(trigger_event)
            row.trigger_pull_event = True
            row.trigger_pull_confidence = trigger_event.data.get("confidence")
        
        # Hit marker
        hit_event = self.hit_marker_sensor.observe(frame, frame_epoch)
        if hit_event:
            events.append(hit_event)
            if hit_event.data.get("marker_type") == "white":
                row.hit_marker_white_event = True
            else:
                row.hit_marker_red_event = True
            row.hit_marker_confidence = hit_event.data.get("confidence")
        
        # Movement state
        movement_event = self.movement_sensor.observe(frame, velocity_buffer, frame_epoch)
        if movement_event:
            events.append(movement_event)
            self.latched_state["movement_state"] = movement_event.data.get("movement_state")
            self.latched_state["stance"] = movement_event.data.get("stance")
            self.latched_state["player_velocity"] = movement_event.data.get("movement_speed")
        
        # External events (from operators)
        # WARNING: Any timestamps in enemy_entry are IGNORED by row contract
        if enemy_entry:
            row.enemy_entry_event = True
            self.latched_state["enemy_distance"] = enemy_entry.get("distance")
            self.latched_state["enemy_location"] = enemy_entry.get("location")
        
        # WARNING: Any timestamps in crosshair_on_target are IGNORED by row contract
        if crosshair_on_target:
            row.crosshair_lock_event = True
            self.latched_state["crosshair_on_target"] = True
        # Note: crosshair_on_target is level-triggered (not truly latched)
        # It resets to False when input is absent
        else:
            self.latched_state["crosshair_on_target"] = False
        
        # STEP 2: Apply latched state to row
        row.ads_active = self.latched_state["ads_active"]
        row.movement_state = self.latched_state["movement_state"]
        row.stance = self.latched_state["stance"]
        row.camera_speed = self.latched_state["camera_speed"]
        row.crosshair_on_target = self.latched_state["crosshair_on_target"]
        row.player_velocity = self.latched_state["player_velocity"]
        row.enemy_distance = self.latched_state["enemy_distance"]
        row.enemy_location = self.latched_state["enemy_location"]
        
        # STEP 3: Write to CSV
        self._write_csv_row(row)
        
        # Status update every 100 frames
        if self.frame_index % 100 == 0:
            logging.info(
                f"[{row.timestamp_utc}] "
                f"Frame {self.frame_index} | "
                f"Events: {len(events)}"
            )
    
    def _write_csv_row(self, row: PerformanceRow):
        """Write row to CSV"""
        try:
            csv_row = [
                # ROW ANCHOR
                row.epoch_utc, row.timestamp_utc, row.frame_index,
                
                # INSTANTANEOUS EVENTS
                int(row.trigger_pull_event), int(row.hit_marker_white_event), int(row.hit_marker_red_event),
                int(row.ads_enter_event), int(row.ads_exit_event), int(row.camera_snap_event),
                int(row.enemy_entry_event), int(row.crosshair_lock_event),
                
                # EVENT CONFIDENCE
                row.trigger_pull_confidence, row.hit_marker_confidence, row.camera_snap_confidence,
                
                # LATCHED STATE
                int(row.ads_active), row.movement_state, row.stance,
                row.camera_speed, int(row.crosshair_on_target), row.player_velocity,
                
                # CONTEXT
                row.enemy_distance, row.enemy_location
            ]
            
            self.csv_writer.writerow(csv_row)
            self.csv_file.flush()
        
        except Exception as e:
            logging.error(f"Error writing CSV row: {e}")
    
    def close(self):
        """Close CSV file"""
        if self.csv_file:
            self.csv_file.close()
            logging.info(f"Closed CSV file ({self.frame_index} frames logged)")


def main():
    """Example usage"""
    logger = PerformanceLogger()
    
    try:
        frame_count = 0
        while True:
            time.sleep(0.033)  # ~30 FPS
            frame_count += 1
            
            # Create mock frame and velocity buffer
            frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
            velocity_buffer = np.random.randn(2160, 3840, 2) * 10
            
            # Mock enemy entry every 100 frames
            enemy_entry = None
            if frame_count % 100 == 0:
                enemy_entry = {
                    "timestamp": time.time(),
                    "location": "11_oclock",
                    "distance": 45.0
                }
            
            # Mock crosshair on target every 120 frames
            crosshair_on_target = None
            if frame_count % 120 == 0:
                crosshair_on_target = {
                    "timestamp": time.time()
                }
            
            # Process frame
            logger.process_frame(
                frame,
                velocity_buffer,
                frame_epoch=time.time(),
                frame_h=2160,
                frame_w=3840,
                enemy_entry=enemy_entry,
                crosshair_on_target=crosshair_on_target
            )
    
    except KeyboardInterrupt:
        logger.close()


if __name__ == "__main__":
    main()
