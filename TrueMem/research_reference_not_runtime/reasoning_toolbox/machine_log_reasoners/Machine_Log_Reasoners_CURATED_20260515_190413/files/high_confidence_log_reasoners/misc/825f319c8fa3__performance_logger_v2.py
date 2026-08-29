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
║     File automatically watermarked on: 2026-01-04 09:45:00                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""

"""
CompuCog Performance Logger V2 - Sensor Architecture
=====================================================

Modular sensors inside. Single CSV output outside.

Architecture:
- Sensors: Pure detection (no interpretation)
- Coordinator: Time alignment (no meaning)
- Engagement Builder: Interpretation (no detection)
- CSV Writer: Single source of truth

DeepSeek's philosophy: "Sensors only emit facts."
"""

import os
import csv
import time
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
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
# SENSORS (Pure Detection)
# ============================================================================

class CameraMovementSensor:
    """
    Detects camera movement from velocity buffer.
    
    Emits: CAMERA_MOVE event when significant movement detected.
    """
    
    def __init__(self, movement_threshold: float = 5.0):
        self.movement_threshold = movement_threshold
        self.previous_moving = False
    
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
        
        # Detect movement
        moving = speed > self.movement_threshold
        
        # Emit event on state change (stationary → moving)
        if moving and not self.previous_moving:
            # Compute direction
            avg_dx = np.mean(velocity_buffer[:, :, 0])
            avg_dy = np.mean(velocity_buffer[:, :, 1])
            direction = float(np.degrees(np.arctan2(avg_dy, avg_dx)))
            
            self.previous_moving = True
            
            return SensorEvent(
                event_type=EventType.CAMERA_MOVE,
                epoch=epoch,
                data={
                    "direction": direction,
                    "speed": speed
                }
            )
        
        elif not moving:
            self.previous_moving = False
        
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
            self.previous_ads_active = ads_active
            
            return SensorEvent(
                event_type=EventType.ADS_CHANGE,
                epoch=epoch,
                data={
                    "ads_active": ads_active,
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
# ENGAGEMENT BUILDER (Interpretation)
# ============================================================================

@dataclass
class Engagement:
    """Complete engagement with reaction times"""
    # Timestamps
    enemy_entry_time: Optional[float] = None
    camera_turn_time: Optional[float] = None
    ads_start_time: Optional[float] = None
    crosshair_on_target_time: Optional[float] = None
    trigger_pull_time: Optional[float] = None
    hit_marker_time: Optional[float] = None
    
    # Context
    enemy_location: Optional[str] = None
    enemy_distance: Optional[float] = None
    movement_state: Optional[str] = None
    stance: Optional[str] = None
    
    # Outcomes
    hit_confirmed: bool = False
    kill_confirmed: bool = False
    
    # Reaction times (calculated)
    perceptual_latency: Optional[float] = None
    decision_latency: Optional[float] = None
    motor_latency: Optional[float] = None
    total_reaction_time: Optional[float] = None


class EngagementBuilder:
    """
    Builds engagements from sensor events.
    
    Correlates events into causal chains and calculates reaction times.
    """
    
    def __init__(self):
        self.current_engagement = Engagement()
        self.engagement_active = False
    
    def on_event(self, event: SensorEvent):
        """
        Process sensor event and update engagement.
        
        Args:
            event: SensorEvent from sensor
        """
        if event.event_type == EventType.ENEMY_ENTRY:
            # Start new engagement
            self.current_engagement = Engagement()
            self.current_engagement.enemy_entry_time = event.epoch
            self.current_engagement.enemy_location = event.data.get("location")
            self.current_engagement.enemy_distance = event.data.get("distance")
            self.engagement_active = True
        
        elif event.event_type == EventType.CAMERA_MOVE:
            if self.engagement_active and self.current_engagement.camera_turn_time is None:
                self.current_engagement.camera_turn_time = event.epoch
        
        elif event.event_type == EventType.ADS_CHANGE:
            if event.data.get("ads_active") and self.engagement_active:
                if self.current_engagement.ads_start_time is None:
                    self.current_engagement.ads_start_time = event.epoch
        
        elif event.event_type == EventType.CROSSHAIR_LOCK:
            if self.engagement_active:
                self.current_engagement.crosshair_on_target_time = event.epoch
        
        elif event.event_type == EventType.TRIGGER_PULL:
            if self.engagement_active:
                self.current_engagement.trigger_pull_time = event.epoch
        
        elif event.event_type == EventType.HIT_MARKER:
            if self.engagement_active:
                self.current_engagement.hit_marker_time = event.epoch
                self.current_engagement.hit_confirmed = True
                
                if event.data.get("marker_type") == "red":
                    self.current_engagement.kill_confirmed = True
        
        elif event.event_type == EventType.MOVEMENT_STATE:
            self.current_engagement.movement_state = event.data.get("movement_state")
            self.current_engagement.stance = event.data.get("stance")
    
    def calculate_reaction_times(self):
        """Calculate reaction times from engagement timestamps"""
        e = self.current_engagement
        
        if e.enemy_entry_time:
            # Perceptual: enemy entry → camera turn
            if e.camera_turn_time and e.camera_turn_time > e.enemy_entry_time:
                e.perceptual_latency = e.camera_turn_time - e.enemy_entry_time
            
            # Decision: camera turn → ADS
            if e.camera_turn_time and e.ads_start_time and e.ads_start_time > e.camera_turn_time:
                e.decision_latency = e.ads_start_time - e.camera_turn_time
            
            # Motor: crosshair on target → trigger pull
            if e.crosshair_on_target_time and e.trigger_pull_time and e.trigger_pull_time > e.crosshair_on_target_time:
                e.motor_latency = e.trigger_pull_time - e.crosshair_on_target_time
            
            # Total: enemy entry → trigger pull
            if e.trigger_pull_time and e.trigger_pull_time > e.enemy_entry_time:
                e.total_reaction_time = e.trigger_pull_time - e.enemy_entry_time
    
    def get_engagement(self) -> Engagement:
        """Get current engagement with calculated reaction times"""
        self.calculate_reaction_times()
        return self.current_engagement


# ============================================================================
# PERFORMANCE LOGGER (Monolithic Deployment)
# ============================================================================

class PerformanceLogger:
    """
    Monolithic performance logger with internal sensor architecture.
    
    Sensors inside. Single CSV outside.
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
        
        # Initialize engagement builder
        self.engagement_builder = EngagementBuilder()
        
        # Frame counter
        self.frame_count = 0
        
        # CSV file handle
        self.csv_file = None
        self.csv_writer = None
        
        # Setup logging
        self._setup_logging()
        
        # Initialize CSV
        self._initialize_csv()
        
        logging.info(f"Performance Logger V2 Started (Sensor Architecture)")
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
                "timestamp", "frame_id",
                "enemy_entry_time", "enemy_location", "enemy_distance",
                "camera_turn_time", "ads_start_time", "crosshair_on_target_time",
                "trigger_pull_time", "hit_marker_time",
                "movement_state", "stance",
                "hit_confirmed", "kill_confirmed",
                "perceptual_latency", "decision_latency", "motor_latency", "total_reaction_time"
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
        self.frame_count += 1
        frame_id = f"{int(frame_epoch * 1000):016d}"
        
        # STEP 1: Run all sensors
        events = []
        
        # Camera movement
        camera_event = self.camera_sensor.observe(frame, velocity_buffer, frame_epoch)
        if camera_event:
            events.append(camera_event)
        
        # ADS state
        ads_event = self.ads_sensor.observe(frame, frame_epoch)
        if ads_event:
            events.append(ads_event)
        
        # Trigger pull
        trigger_event = self.trigger_sensor.observe(frame, frame_epoch)
        if trigger_event:
            events.append(trigger_event)
        
        # Hit marker
        hit_event = self.hit_marker_sensor.observe(frame, frame_epoch)
        if hit_event:
            events.append(hit_event)
        
        # Movement state
        movement_event = self.movement_sensor.observe(frame, velocity_buffer, frame_epoch)
        if movement_event:
            events.append(movement_event)
        
        # External events (from operators)
        if enemy_entry:
            events.append(SensorEvent(
                event_type=EventType.ENEMY_ENTRY,
                epoch=enemy_entry.get("timestamp", frame_epoch),
                data=enemy_entry
            ))
        
        if crosshair_on_target:
            events.append(SensorEvent(
                event_type=EventType.CROSSHAIR_LOCK,
                epoch=crosshair_on_target.get("timestamp", frame_epoch),
                data=crosshair_on_target
            ))
        
        # STEP 2: Feed events to engagement builder
        for event in events:
            self.engagement_builder.on_event(event)
        
        # STEP 3: Get current engagement
        engagement = self.engagement_builder.get_engagement()
        
        # STEP 4: Write to CSV
        self._write_csv_row(frame_epoch, frame_id, engagement)
        
        # Status update every 100 frames
        if self.frame_count % 100 == 0:
            logging.info(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"Frame {self.frame_count} | "
                f"Events: {len(events)} | "
                f"Engagement: {engagement.engagement_active if hasattr(engagement, 'engagement_active') else 'N/A'}"
            )
    
    def _write_csv_row(self, timestamp: float, frame_id: str, engagement: Engagement):
        """Write engagement data to CSV"""
        try:
            row = [
                timestamp,
                frame_id,
                engagement.enemy_entry_time,
                engagement.enemy_location,
                engagement.enemy_distance,
                engagement.camera_turn_time,
                engagement.ads_start_time,
                engagement.crosshair_on_target_time,
                engagement.trigger_pull_time,
                engagement.hit_marker_time,
                engagement.movement_state,
                engagement.stance,
                engagement.hit_confirmed,
                engagement.kill_confirmed,
                engagement.perceptual_latency,
                engagement.decision_latency,
                engagement.motor_latency,
                engagement.total_reaction_time
            ]
            
            self.csv_writer.writerow(row)
            self.csv_file.flush()
        
        except Exception as e:
            logging.error(f"Error writing CSV row: {e}")
    
    def close(self):
        """Close CSV file"""
        if self.csv_file:
            self.csv_file.close()
            logging.info(f"Closed CSV file ({self.frame_count} frames logged)")


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
