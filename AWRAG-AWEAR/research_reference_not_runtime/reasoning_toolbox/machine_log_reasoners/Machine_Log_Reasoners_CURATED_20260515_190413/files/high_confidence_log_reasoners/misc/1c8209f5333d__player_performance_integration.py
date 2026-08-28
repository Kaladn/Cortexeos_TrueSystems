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
CompuCog Upgrade - Player Performance Integration
==================================================

Integrates all loggers with PlayerPerformance class.
Provides complete end-to-end pipeline from frame capture to performance analysis.

Pipeline:
1. MultiLoggerCoordinator processes frames → synchronized events
2. EngagementBuilder correlates events → complete engagements
3. PlayerPerformance analyzes engagements → performance metrics
4. Export results → JSONL + summary statistics

Usage:
    integrator = PlayerPerformanceIntegration()
    integrator.process_frame(frame, velocity_buffer, timestamp, h, w)
    summary = integrator.get_performance_summary()
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np

# Import all components
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from player_performance import PlayerPerformance
    from multi_logger_coordinator import MultiLoggerCoordinator
    from engagement_builder import EngagementBuilder
except ImportError as e:
    logging.error(f"Failed to import components: {e}")
    raise


class PlayerPerformanceIntegration:
    """
    Complete integration of all performance tracking components.
    
    Provides single interface for frame processing → performance analysis.
    """
    
    def __init__(self, logs_base_dir: Optional[Path] = None):
        """
        Initialize player performance integration.
        
        Args:
            logs_base_dir: Base directory for all logs (default: logs/)
        """
        # Setup base logging directory
        if logs_base_dir is None:
            script_dir = Path(__file__).parent
            logs_base_dir = script_dir / ".." / ".." / "logs"
        
        self.logs_base_dir = Path(logs_base_dir).resolve()
        self.logs_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.coordinator = MultiLoggerCoordinator(logs_base_dir=self.logs_base_dir)
        self.engagement_builder = EngagementBuilder()
        self.player_performance = PlayerPerformance()
        
        # Pending enemy entries (from operators)
        self.pending_enemy_entries: List[Dict[str, Any]] = []
        
        # Frame counter
        self.frame_count = 0
        
        # Setup logging
        self._setup_logging()
        
        logging.info(f"Player Performance Integration Started")
        logging.info(f"Base Log Directory: {self.logs_base_dir}")
        logging.info(f"Components: MultiLoggerCoordinator, EngagementBuilder, PlayerPerformance")
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
        frame_w: int,
        enemy_entry: Optional[Dict[str, Any]] = None,
        crosshair_on_target: Optional[Dict[str, Any]] = None,
        hit_confirmed: bool = False,
        kill_confirmed: bool = False
    ):
        """
        Process single frame through entire pipeline.
        
        Args:
            frame: RGB frame (height, width, 3)
            velocity_buffer: Motion vectors (height, width, 2) or None
            frame_timestamp: Frame timestamp in seconds
            frame_h: Frame height
            frame_w: Frame width
            enemy_entry: Enemy entry event from EdgeEntry operator (optional)
            crosshair_on_target: Crosshair lock event from CrosshairLock operator (optional)
            hit_confirmed: Whether hit was confirmed (from game state)
            kill_confirmed: Whether kill was confirmed (from game state)
        """
        self.frame_count += 1
        
        try:
            # STEP 1: Process frame through all loggers
            sync_frame = self.coordinator.process_frame(
                frame,
                velocity_buffer,
                frame_timestamp,
                frame_h,
                frame_w
            )
            
            # STEP 2: Track enemy entries
            if enemy_entry:
                self.pending_enemy_entries.append({
                    "timestamp": enemy_entry.get("timestamp", frame_timestamp),
                    "location": enemy_entry.get("location", "unknown"),
                    "distance": enemy_entry.get("distance"),
                    "frame_timestamp": frame_timestamp
                })
            
            # STEP 3: Build engagements when crosshair on target
            if crosshair_on_target and self.pending_enemy_entries:
                # Find matching enemy entry (within 5 seconds)
                crosshair_time = crosshair_on_target.get("timestamp", frame_timestamp)
                
                for enemy_entry_data in self.pending_enemy_entries:
                    if crosshair_time - enemy_entry_data["timestamp"] <= 5.0:
                        # Get synchronized events in time window
                        window_start = enemy_entry_data["timestamp"]
                        window_end = crosshair_time + 1.0
                        
                        window_frames = self.coordinator.get_events_in_time_window(
                            window_start,
                            window_end
                        )
                        
                        # Extract events by type
                        camera_movements = [
                            f.camera_movement for f in window_frames
                            if f.camera_movement
                        ]
                        ads_events = [
                            f.ads_event for f in window_frames
                            if f.ads_event
                        ]
                        shot_events = [
                            f.shot_event for f in window_frames
                            if f.shot_event
                        ]
                        movement_events = [
                            f.movement_event for f in window_frames
                            if f.movement_event
                        ]
                        
                        # Build engagement
                        engagement = self.engagement_builder.build_engagement(
                            enemy_entry_time=enemy_entry_data["timestamp"],
                            enemy_location=enemy_entry_data["location"],
                            enemy_distance=enemy_entry_data["distance"],
                            camera_movements=camera_movements,
                            ads_events=ads_events,
                            crosshair_on_target_time=crosshair_time,
                            shot_events=shot_events,
                            movement_events=movement_events,
                            hit_confirmed=hit_confirmed,
                            kill_confirmed=kill_confirmed
                        )
                        
                        # Add to player performance
                        if engagement:
                            self.player_performance.add_engagement(engagement)
                        
                        # Remove processed enemy entry
                        self.pending_enemy_entries.remove(enemy_entry_data)
                        break
            
            # STEP 4: Clean up old pending entries (> 10 seconds)
            current_time = frame_timestamp
            self.pending_enemy_entries = [
                entry for entry in self.pending_enemy_entries
                if current_time - entry["timestamp"] <= 10.0
            ]
            
            # Status update every 200 frames
            if self.frame_count % 200 == 0:
                stats = self.coordinator.get_statistics()
                engagements = len(self.player_performance.engagements)
                logging.info(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"Frame {self.frame_count} | "
                    f"Synchronized Events: {stats['total_frames']} | "
                    f"Engagements: {engagements} | "
                    f"Pending Enemies: {len(self.pending_enemy_entries)}"
                )
        
        except Exception as e:
            logging.error(f"Error processing frame {self.frame_count}: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get complete performance summary.
        
        Returns:
            Dict with all performance metrics
        """
        try:
            # Get player performance summary
            performance_summary = self.player_performance.get_summary()
            
            # Get coordinator statistics
            coordinator_stats = self.coordinator.get_statistics()
            
            # Get engagement builder statistics
            engagement_stats = self.engagement_builder.get_summary_statistics()
            
            # Combine all statistics
            return {
                "frames_processed": self.frame_count,
                "coordinator_stats": coordinator_stats,
                "engagement_stats": engagement_stats,
                "performance_summary": performance_summary
            }
        
        except Exception as e:
            logging.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}
    
    def export_all_logs(self):
        """Export all logs to files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Export synchronized events
            sync_file = self.logs_base_dir / "synchronized" / f"sync_{timestamp}.jsonl"
            self.coordinator.export_synchronized_log(sync_file)
            
            # Export engagements
            engagement_file = self.logs_base_dir / "engagements" / f"engagements_{timestamp}.jsonl"
            self.engagement_builder.export_engagements(engagement_file)
            
            # Export performance summary
            summary_file = self.logs_base_dir / "performance" / f"summary_{timestamp}.json"
            summary_file.parent.mkdir(parents=True, exist_ok=True)
            
            summary = self.get_performance_summary()
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
            
            logging.info(f"Exported all logs:")
            logging.info(f"  - Synchronized: {sync_file}")
            logging.info(f"  - Engagements: {engagement_file}")
            logging.info(f"  - Summary: {summary_file}")
        
        except Exception as e:
            logging.error(f"Error exporting logs: {e}")
    
    def cleanup_all(self):
        """Clean up all components"""
        self.coordinator.cleanup_all()
        logging.info("Cleaned up all components")


def main():
    """
    Example usage / testing
    """
    integrator = PlayerPerformanceIntegration()
    
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
            
            # Process frame
            integrator.process_frame(
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
            
            # Export every 1000 frames
            if frame_count % 1000 == 0:
                integrator.export_all_logs()
                
                # Print summary
                summary = integrator.get_performance_summary()
                logging.info(f"Performance Summary:\n{json.dumps(summary, indent=2)}")
                
                # Cleanup
                integrator.cleanup_all()
    
    except KeyboardInterrupt:
        # Final export
        integrator.export_all_logs()
        
        summary = integrator.get_performance_summary()
        logging.info(f"Final Performance Summary:\n{json.dumps(summary, indent=2)}")
        logging.info("Player performance integration stopped")


if __name__ == "__main__":
    main()
