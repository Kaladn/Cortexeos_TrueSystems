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
CompuCog Performance Logger - Monolithic Spreadsheet Version
=============================================================

Single logger that captures ALL performance data and writes to CSV/Excel.

One file. One row per frame. All metrics in columns.

Columns:
- Timestamp, Frame ID
- Enemy Entry (time, location, distance)
- Camera Movement (direction, speed)
- ADS State (active, FOV ratio)
- Crosshair On Target (yes/no)
- Trigger Pull (shot detected, confidence)
- Movement State (state, stance, speed)
- Hit Confirmed, Kill Confirmed
- Reaction Times (perceptual, decision, motor, total)

Output: performance_log_YYYYMMDD.csv (append mode, one row per frame)
"""

import os
import csv
import time
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, fields
import statistics


@dataclass
class FramePerformanceData:
    """Complete performance data for single frame"""
    # Timestamp
    timestamp: float
    frame_id: str
    
    # Enemy Entry
    enemy_detected: bool
    enemy_entry_time: Optional[float]
    enemy_location: Optional[str]
    enemy_distance: Optional[float]
    
    # Camera Movement
    camera_moving: bool
    camera_direction: Optional[float]
    camera_speed: Optional[float]
    
    # ADS State
    ads_active: bool
    fov_ratio: Optional[float]
    scope_detected: bool
    
    # Crosshair
    crosshair_on_target: bool
    crosshair_on_target_time: Optional[float]
    
    # Trigger Pull
    shot_detected: bool
    shot_time: Optional[float]
    shot_confidence: Optional[float]
    muzzle_flash_intensity: Optional[float]
    
    # Movement State
    player_movement_state: Optional[str]
    player_stance: Optional[str]
    player_movement_speed: Optional[float]
    
    # Outcomes
    hit_confirmed: bool
    kill_confirmed: bool
    
    # Reaction Times (calculated)
    perceptual_latency: Optional[float]
    decision_latency: Optional[float]
    motor_latency: Optional[float]
    total_reaction_time: Optional[float]


class PerformanceLoggerMonolith:
    """
    Monolithic performance logger.
    
    Writes all data to single CSV file.
    """
    
    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialize monolithic logger.
        
        Args:
            logs_dir: Directory for CSV files (default: logs/)
        """
        # Setup logging directory
        if logs_dir is None:
            script_dir = Path(__file__).parent
            logs_dir = script_dir / "logs"
        
        self.logs_dir = Path(logs_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking for reaction time calculation
        self.last_enemy_entry: Optional[Dict[str, Any]] = None
        self.last_camera_turn: Optional[float] = None
        self.last_ads_start: Optional[float] = None
        self.last_crosshair_on_target: Optional[float] = None
        
        # Frame counter
        self.frame_count = 0
        
        # CSV file handle
        self.csv_file = None
        self.csv_writer = None
        
        # Setup logging
        self._setup_logging()
        
        # Initialize CSV
        self._initialize_csv()
        
        logging.info(f"Monolithic Performance Logger Started")
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
            # Get column names from dataclass
            column_names = [field.name for field in fields(FramePerformanceData)]
            self.csv_writer.writerow(column_names)
            self.csv_file.flush()
            logging.info(f"Created new CSV file: {csv_path}")
        else:
            logging.info(f"Appending to existing CSV file: {csv_path}")
    
    def analyze_frame(
        self,
        frame: np.ndarray,
        velocity_buffer: Optional[np.ndarray],
        frame_timestamp: float,
        frame_h: int,
        frame_w: int,
        enemy_entry: Optional[Dict[str, Any]] = None,
        crosshair_on_target: Optional[Dict[str, Any]] = None,
        hit_confirmed: bool = False,
        kill_confirmed: bool = False
    ) -> FramePerformanceData:
        """
        Analyze single frame and return complete performance data.
        
        Args:
            frame: RGB frame (height, width, 3)
            velocity_buffer: Motion vectors (height, width, 2) or None
            frame_timestamp: Frame timestamp in seconds
            frame_h: Frame height
            frame_w: Frame width
            enemy_entry: Enemy entry event (optional)
            crosshair_on_target: Crosshair lock event (optional)
            hit_confirmed: Whether hit was confirmed
            kill_confirmed: Whether kill was confirmed
        
        Returns:
            FramePerformanceData with all metrics
        """
        self.frame_count += 1
        frame_id = f"{int(frame_timestamp * 1000):016d}"
        
        # STEP 1: Detect camera movement
        camera_moving = False
        camera_direction = None
        camera_speed = None
        
        if velocity_buffer is not None:
            # Compute average velocity magnitude
            velocity_magnitude = np.sqrt(
                velocity_buffer[:, :, 0]**2 + velocity_buffer[:, :, 1]**2
            )
            camera_speed = float(np.mean(velocity_magnitude))
            
            if camera_speed > 5.0:  # Significant movement threshold
                camera_moving = True
                
                # Compute direction (average angle)
                avg_dx = np.mean(velocity_buffer[:, :, 0])
                avg_dy = np.mean(velocity_buffer[:, :, 1])
                camera_direction = float(np.degrees(np.arctan2(avg_dy, avg_dx)))
                
                # Track camera turn start
                if self.last_camera_turn is None:
                    self.last_camera_turn = frame_timestamp
        else:
            if self.last_camera_turn is not None and not camera_moving:
                self.last_camera_turn = None
        
        # STEP 2: Detect ADS state
        ads_active = False
        fov_ratio = None
        scope_detected = False
        
        # Method 1: FOV change detection
        center_region = frame[
            frame_h//4:3*frame_h//4,
            frame_w//4:3*frame_w//4,
            :
        ]
        edge_region = np.concatenate([
            frame[:frame_h//4, :, :].flatten(),
            frame[3*frame_h//4:, :, :].flatten(),
            frame[:, :frame_w//4, :].flatten(),
            frame[:, 3*frame_w//4:, :].flatten()
        ])
        
        center_variance = float(np.var(center_region))
        edge_variance = float(np.var(edge_region))
        
        if edge_variance > 0:
            fov_ratio = center_variance / edge_variance
            if fov_ratio > 1.5:  # FOV narrowed
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
        
        if black_pixel_ratio > 0.7:
            scope_detected = True
            ads_active = True
        
        # Track ADS start
        if ads_active and self.last_ads_start is None:
            self.last_ads_start = frame_timestamp
        elif not ads_active:
            self.last_ads_start = None
        
        # STEP 3: Enemy entry tracking
        enemy_detected = enemy_entry is not None
        enemy_entry_time = None
        enemy_location = None
        enemy_distance = None
        
        if enemy_entry:
            self.last_enemy_entry = {
                "time": enemy_entry.get("timestamp", frame_timestamp),
                "location": enemy_entry.get("location", "unknown"),
                "distance": enemy_entry.get("distance")
            }
            enemy_entry_time = self.last_enemy_entry["time"]
            enemy_location = self.last_enemy_entry["location"]
            enemy_distance = self.last_enemy_entry["distance"]
        
        # STEP 4: Crosshair on target
        crosshair_on_target_bool = crosshair_on_target is not None
        crosshair_on_target_time_val = None
        
        if crosshair_on_target:
            crosshair_on_target_time_val = crosshair_on_target.get("timestamp", frame_timestamp)
            self.last_crosshair_on_target = crosshair_on_target_time_val
        
        # STEP 5: Detect trigger pull (shot)
        shot_detected = False
        shot_time = None
        shot_confidence = None
        muzzle_flash_intensity = None
        
        # Detect muzzle flash (center region bright flash)
        center_brightness = float(np.mean(center_region))
        if center_brightness > 200:  # Bright flash threshold
            shot_detected = True
            shot_time = frame_timestamp
            muzzle_flash_intensity = center_brightness
            shot_confidence = min(1.0, (center_brightness - 200) / 55)
        
        # STEP 6: Detect movement state
        player_movement_state = None
        player_stance = None
        player_movement_speed = camera_speed
        
        if camera_speed is not None:
            if camera_speed < 5.0:
                player_movement_state = "stationary"
            elif camera_speed < 20.0:
                player_movement_state = "walking"
            else:
                player_movement_state = "sprinting"
        
        # Detect stance from ground ratio
        h_mid = frame_h // 2
        top_half = frame[:h_mid, :, :]
        bottom_half = frame[h_mid:, :, :]
        
        top_brightness = float(np.mean(top_half))
        bottom_brightness = float(np.mean(bottom_half))
        
        if top_brightness > 0:
            ground_ratio = 1.0 - (bottom_brightness / top_brightness)
            ground_ratio = np.clip(ground_ratio, 0.0, 1.0)
            
            if ground_ratio > 0.75:
                player_stance = "prone"
            elif ground_ratio > 0.6:
                player_stance = "crouching"
            else:
                player_stance = "standing"
        
        # STEP 7: Calculate reaction times
        perceptual_latency = None
        decision_latency = None
        motor_latency = None
        total_reaction_time = None
        
        if self.last_enemy_entry:
            enemy_time = self.last_enemy_entry["time"]
            
            # Perceptual: enemy entry → camera turn
            if self.last_camera_turn and self.last_camera_turn > enemy_time:
                perceptual_latency = self.last_camera_turn - enemy_time
            
            # Decision: camera turn → ADS
            if self.last_camera_turn and self.last_ads_start and self.last_ads_start > self.last_camera_turn:
                decision_latency = self.last_ads_start - self.last_camera_turn
            
            # Motor: crosshair on target → trigger pull
            if self.last_crosshair_on_target and shot_time and shot_time > self.last_crosshair_on_target:
                motor_latency = shot_time - self.last_crosshair_on_target
            
            # Total: enemy entry → trigger pull
            if shot_time and shot_time > enemy_time:
                total_reaction_time = shot_time - enemy_time
        
        # Build performance data
        perf_data = FramePerformanceData(
            timestamp=frame_timestamp,
            frame_id=frame_id,
            enemy_detected=enemy_detected,
            enemy_entry_time=enemy_entry_time,
            enemy_location=enemy_location,
            enemy_distance=enemy_distance,
            camera_moving=camera_moving,
            camera_direction=camera_direction,
            camera_speed=camera_speed,
            ads_active=ads_active,
            fov_ratio=fov_ratio,
            scope_detected=scope_detected,
            crosshair_on_target=crosshair_on_target_bool,
            crosshair_on_target_time=crosshair_on_target_time_val,
            shot_detected=shot_detected,
            shot_time=shot_time,
            shot_confidence=shot_confidence,
            muzzle_flash_intensity=muzzle_flash_intensity,
            player_movement_state=player_movement_state,
            player_stance=player_stance,
            player_movement_speed=player_movement_speed,
            hit_confirmed=hit_confirmed,
            kill_confirmed=kill_confirmed,
            perceptual_latency=perceptual_latency,
            decision_latency=decision_latency,
            motor_latency=motor_latency,
            total_reaction_time=total_reaction_time
        )
        
        return perf_data
    
    def log_frame(self, perf_data: FramePerformanceData):
        """
        Write performance data to CSV.
        
        Args:
            perf_data: FramePerformanceData
        """
        try:
            # Convert dataclass to row
            row = [getattr(perf_data, field.name) for field in fields(FramePerformanceData)]
            
            # Write to CSV
            self.csv_writer.writerow(row)
            self.csv_file.flush()
            
            # Status update every 100 frames
            if self.frame_count % 100 == 0:
                logging.info(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"Frame {self.frame_count} | "
                    f"Enemy: {perf_data.enemy_detected} | "
                    f"ADS: {perf_data.ads_active} | "
                    f"Crosshair: {perf_data.crosshair_on_target} | "
                    f"Shot: {perf_data.shot_detected}"
                )
        
        except Exception as e:
            logging.error(f"Error logging frame: {e}")
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Calculate summary statistics from CSV file.
        
        Returns:
            Dict with summary statistics
        """
        try:
            csv_path = self._get_csv_path()
            
            # Read CSV
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                return {"total_frames": 0}
            
            # Extract metrics
            perceptual_latencies = []
            decision_latencies = []
            motor_latencies = []
            total_reaction_times = []
            
            enemy_detections = 0
            crosshair_on_target_count = 0
            shots_fired = 0
            hits = 0
            kills = 0
            
            for row in rows:
                # Reaction times
                if row["perceptual_latency"]:
                    perceptual_latencies.append(float(row["perceptual_latency"]))
                if row["decision_latency"]:
                    decision_latencies.append(float(row["decision_latency"]))
                if row["motor_latency"]:
                    motor_latencies.append(float(row["motor_latency"]))
                if row["total_reaction_time"]:
                    total_reaction_times.append(float(row["total_reaction_time"]))
                
                # Counts
                if row["enemy_detected"] == "True":
                    enemy_detections += 1
                if row["crosshair_on_target"] == "True":
                    crosshair_on_target_count += 1
                if row["shot_detected"] == "True":
                    shots_fired += 1
                if row["hit_confirmed"] == "True":
                    hits += 1
                if row["kill_confirmed"] == "True":
                    kills += 1
            
            # Calculate statistics
            def calc_stats(values):
                if not values:
                    return {"mean": None, "median": None, "std": None, "count": 0}
                return {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                    "count": len(values)
                }
            
            return {
                "total_frames": len(rows),
                "reaction_times": {
                    "perceptual": calc_stats(perceptual_latencies),
                    "decision": calc_stats(decision_latencies),
                    "motor": calc_stats(motor_latencies),
                    "total": calc_stats(total_reaction_times)
                },
                "detections": {
                    "enemy_detections": enemy_detections,
                    "crosshair_on_target": crosshair_on_target_count,
                    "shots_fired": shots_fired,
                    "hits": hits,
                    "kills": kills
                },
                "rates": {
                    "hit_rate": hits / shots_fired if shots_fired > 0 else 0.0,
                    "kill_rate": kills / shots_fired if shots_fired > 0 else 0.0
                }
            }
        
        except Exception as e:
            logging.error(f"Error calculating summary statistics: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Close CSV file"""
        if self.csv_file:
            self.csv_file.close()
            logging.info(f"Closed CSV file ({self.frame_count} frames logged)")


def main():
    """
    Example usage / testing
    """
    logger = PerformanceLoggerMonolith()
    
    # Simulate frame processing
    try:
        frame_count = 0
        while True:
            time.sleep(0.033)  # ~30 FPS
            frame_count += 1
            
            # Create mock frame and velocity buffer (replace with real data)
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
            
            # Analyze frame
            perf_data = logger.analyze_frame(
                frame,
                velocity_buffer,
                frame_timestamp=time.time(),
                frame_h=2160,
                frame_w=3840,
                enemy_entry=enemy_entry,
                crosshair_on_target=crosshair_on_target,
                hit_confirmed=(frame_count % 150 == 0),
                kill_confirmed=(frame_count % 200 == 0)
            )
            
            # Log to CSV
            logger.log_frame(perf_data)
            
            # Print summary every 1000 frames
            if frame_count % 1000 == 0:
                summary = logger.get_summary_statistics()
                logging.info(f"Summary Statistics:\n{summary}")
    
    except KeyboardInterrupt:
        # Print final summary
        summary = logger.get_summary_statistics()
        logging.info(f"Final Summary:\n{summary}")
        logger.close()


if __name__ == "__main__":
    main()
