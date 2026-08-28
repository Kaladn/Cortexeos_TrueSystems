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
CompuCog Upgrade - Multi-Logger Coordinator
============================================

Coordinates all performance loggers and synchronizes their output.
Manages frame distribution, timestamp synchronization, and data correlation.

Loggers Coordinated:
1. CameraMovementLogger - Perceptual latency
2. ADSDetectorLogger - Decision latency
3. TriggerPullLogger - Motor latency
4. MovementStateLogger - Context tracking

Output: Synchronized events across all loggers with correlation IDs.
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
from threading import Lock
import uuid

# Import loggers
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from camera_movement_logger import CameraMovementLogger, CameraMovement
    from ads_detector_logger import ADSDetectorLogger, ADSEvent
    from trigger_pull_logger import TriggerPullLogger, ShotEvent
    from movement_state_logger import MovementStateLogger, MovementEvent
except ImportError as e:
    logging.error(f"Failed to import loggers: {e}")
    logging.error("Ensure all logger files are in parent directory")
    raise


@dataclass
class SynchronizedFrame:
    """Frame data with all logger outputs"""
    frame_id: str
    timestamp: float
    frame: np.ndarray
    velocity_buffer: Optional[np.ndarray]
    camera_movement: Optional[CameraMovement]
    ads_event: Optional[ADSEvent]
    shot_event: Optional[ShotEvent]
    movement_event: Optional[MovementEvent]


class MultiLoggerCoordinator:
    """
    Coordinates all performance loggers.
    
    Ensures synchronized analysis and correlation across loggers.
    """
    
    def __init__(self, logs_base_dir: Optional[Path] = None):
        """
        Initialize multi-logger coordinator.
        
        Args:
            logs_base_dir: Base directory for all logs (default: logs/)
        """
        # Setup base logging directory
        if logs_base_dir is None:
            script_dir = Path(__file__).parent
            logs_base_dir = script_dir / ".." / ".." / "logs"
        
        self.logs_base_dir = Path(logs_base_dir).resolve()
        self.logs_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all loggers
        self.camera_logger = CameraMovementLogger(
            logs_dir=self.logs_base_dir / "camera_movement"
        )
        self.ads_logger = ADSDetectorLogger(
            logs_dir=self.logs_base_dir / "ads_detection"
        )
        self.trigger_logger = TriggerPullLogger(
            logs_dir=self.logs_base_dir / "trigger_pull"
        )
        self.movement_logger = MovementStateLogger(
            logs_dir=self.logs_base_dir / "movement_state"
        )
        
        # Synchronized events storage
        self.synchronized_events: List[SynchronizedFrame] = []
        self.events_lock = Lock()
        
        # Frame counter
        self.frame_count = 0
        
        # Setup logging
        self._setup_logging()
        
        logging.info(f"Multi-Logger Coordinator Started")
        logging.info(f"Base Log Directory: {self.logs_base_dir}")
        logging.info(f"Loggers Initialized: 4")
        logging.info("")
    
    def _setup_logging(self):
        """Configure logging output"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def process_frame(
        self,
        frame: np.ndarray,
        velocity_buffer: Optional[np.ndarray],
        frame_timestamp: float,
        frame_h: int,
        frame_w: int
    ) -> SynchronizedFrame:
        """
        Process single frame through all loggers.
        
        Args:
            frame: RGB frame (height, width, 3)
            velocity_buffer: Motion vectors (height, width, 2) or None
            frame_timestamp: Frame timestamp in seconds
            frame_h: Frame height
            frame_w: Frame width
        
        Returns:
            SynchronizedFrame with all logger outputs
        """
        self.frame_count += 1
        frame_id = f"{int(frame_timestamp * 1000):016d}_{uuid.uuid4().hex[:8]}"
        
        # Run all loggers in parallel
        camera_movement = None
        ads_event = None
        shot_event = None
        movement_event = None
        
        try:
            # Camera movement detection
            if velocity_buffer is not None:
                camera_movement = self.camera_logger.analyze_frame(
                    velocity_buffer,
                    frame_timestamp,
                    frame_h,
                    frame_w
                )
                if camera_movement:
                    self.camera_logger.log_movement(camera_movement)
            
            # ADS detection
            ads_event = self.ads_logger.analyze_frame(frame, frame_timestamp)
            if ads_event:
                self.ads_logger.log_event(ads_event)
            
            # Trigger pull detection
            shot_event = self.trigger_logger.analyze_frame(
                frame,
                velocity_buffer,
                frame_timestamp
            )
            if shot_event:
                self.trigger_logger.log_event(shot_event)
            
            # Movement state tracking
            if velocity_buffer is not None:
                movement_event = self.movement_logger.analyze_frame(
                    frame,
                    velocity_buffer,
                    frame_timestamp
                )
                if movement_event:
                    self.movement_logger.log_event(movement_event)
        
        except Exception as e:
            logging.error(f"Error processing frame {frame_id}: {e}")
        
        # Create synchronized frame
        sync_frame = SynchronizedFrame(
            frame_id=frame_id,
            timestamp=frame_timestamp,
            frame=frame,
            velocity_buffer=velocity_buffer,
            camera_movement=camera_movement,
            ads_event=ads_event,
            shot_event=shot_event,
            movement_event=movement_event
        )
        
        # Store synchronized event
        with self.events_lock:
            self.synchronized_events.append(sync_frame)
            
            # Keep only last 1000 frames in memory
            if len(self.synchronized_events) > 1000:
                self.synchronized_events = self.synchronized_events[-1000:]
        
        # Status update every 100 frames
        if self.frame_count % 100 == 0:
            active_loggers = sum([
                camera_movement is not None,
                ads_event is not None,
                shot_event is not None,
                movement_event is not None
            ])
            logging.info(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"Frame {self.frame_count} | "
                f"Active Loggers: {active_loggers}/4 | "
                f"Buffered Events: {len(self.synchronized_events)}"
            )
        
        return sync_frame
    
    def get_events_in_time_window(
        self,
        start_time: float,
        end_time: float
    ) -> List[SynchronizedFrame]:
        """
        Get all synchronized events in time window.
        
        Args:
            start_time: Window start (seconds)
            end_time: Window end (seconds)
        
        Returns:
            List of SynchronizedFrame in window
        """
        with self.events_lock:
            return [
                frame for frame in self.synchronized_events
                if start_time <= frame.timestamp <= end_time
            ]
    
    def export_synchronized_log(self, output_file: Path):
        """
        Export all synchronized events to single JSONL file.
        
        Args:
            output_file: Output file path
        """
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with self.events_lock:
                with open(output_file, "w", encoding="utf-8") as f:
                    for frame in self.synchronized_events:
                        log_entry = {
                            "frame_id": frame.frame_id,
                            "timestamp": frame.timestamp,
                            "camera_movement": asdict(frame.camera_movement) if frame.camera_movement else None,
                            "ads_event": asdict(frame.ads_event) if frame.ads_event else None,
                            "shot_event": asdict(frame.shot_event) if frame.shot_event else None,
                            "movement_event": asdict(frame.movement_event) if frame.movement_event else None
                        }
                        f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + "\n")
            
            logging.info(f"Exported {len(self.synchronized_events)} synchronized events to {output_file}")
        
        except Exception as e:
            logging.error(f"Error exporting synchronized log: {e}")
    
    def cleanup_all(self):
        """Clean up all logger files"""
        self.camera_logger.cleanup()
        self.ads_logger.cleanup()
        self.trigger_logger.cleanup()
        self.movement_logger.cleanup()
        logging.info("Cleaned up all loggers")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics across all loggers.
        
        Returns:
            Dict with logger statistics
        """
        with self.events_lock:
            total_frames = len(self.synchronized_events)
            
            camera_events = sum(1 for f in self.synchronized_events if f.camera_movement)
            ads_events = sum(1 for f in self.synchronized_events if f.ads_event)
            shot_events = sum(1 for f in self.synchronized_events if f.shot_event)
            movement_events = sum(1 for f in self.synchronized_events if f.movement_event)
            
            return {
                "total_frames": total_frames,
                "camera_movement_events": camera_events,
                "ads_events": ads_events,
                "shot_events": shot_events,
                "movement_events": movement_events,
                "camera_logger_samples": self.camera_logger.sample_count,
                "ads_logger_samples": self.ads_logger.sample_count,
                "trigger_logger_samples": self.trigger_logger.sample_count,
                "movement_logger_samples": self.movement_logger.sample_count
            }


def main():
    """
    Example usage / testing
    """
    coordinator = MultiLoggerCoordinator()
    
    # Simulate frame processing
    try:
        frame_count = 0
        while True:
            time.sleep(0.033)  # ~30 FPS
            frame_count += 1
            
            # Create mock frame and velocity buffer (replace with real data)
            frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)
            velocity_buffer = np.random.randn(2160, 3840, 2) * 10
            
            # Process frame through all loggers
            sync_frame = coordinator.process_frame(
                frame,
                velocity_buffer,
                frame_timestamp=time.time(),
                frame_h=2160,
                frame_w=3840
            )
            
            # Export every 1000 frames
            if frame_count % 1000 == 0:
                output_file = coordinator.logs_base_dir / "synchronized" / f"sync_{frame_count}.jsonl"
                coordinator.export_synchronized_log(output_file)
                
                # Print statistics
                stats = coordinator.get_statistics()
                logging.info(f"Statistics: {json.dumps(stats, indent=2)}")
                
                # Cleanup
                coordinator.cleanup_all()
    
    except KeyboardInterrupt:
        # Final export
        output_file = coordinator.logs_base_dir / "synchronized" / "sync_final.jsonl"
        coordinator.export_synchronized_log(output_file)
        
        stats = coordinator.get_statistics()
        logging.info(f"Final Statistics: {json.dumps(stats, indent=2)}")
        logging.info("Multi-logger coordinator stopped")


if __name__ == "__main__":
    main()
