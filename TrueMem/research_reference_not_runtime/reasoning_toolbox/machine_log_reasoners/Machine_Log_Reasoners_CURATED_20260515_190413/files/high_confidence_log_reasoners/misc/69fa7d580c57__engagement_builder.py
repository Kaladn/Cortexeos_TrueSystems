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
CompuCog Upgrade - Engagement Builder
======================================

Builds complete Engagement objects from synchronized logger data.
Correlates enemy entry → camera turn → ADS → crosshair on target → trigger pull.

Input: Synchronized events from MultiLoggerCoordinator
Output: Complete Engagement objects with all timestamps populated

Engagement Chain:
1. Enemy enters screen (EdgeEntry operator)
2. Player turns camera toward enemy (CameraMovementLogger)
3. Player aims down sights (ADSDetectorLogger)
4. Crosshair on target (CrosshairLock operator)
5. Player fires weapon (TriggerPullLogger)

Context: Player movement state (MovementStateLogger)
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

# Import PlayerPerformance classes
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from player_performance import (
        Engagement,
        EnemyEntry,
        PlayerResponse,
        EngagementContext,
        EngagementOutcome
    )
except ImportError:
    # Define minimal versions if player_performance not available
    @dataclass
    class EnemyEntry:
        timestamp: float
        screen_location: str
        distance: Optional[float] = None
    
    @dataclass
    class PlayerResponse:
        camera_turn_start: Optional[float] = None
        ads_start: Optional[float] = None
        crosshair_on_target: Optional[float] = None
        trigger_pull: Optional[float] = None
    
    @dataclass
    class EngagementContext:
        player_movement_state: Optional[str] = None
        player_cover_state: Optional[str] = None
        weapon_class: Optional[str] = None
        match_time: Optional[float] = None
        enemy_distance: Optional[float] = None
    
    @dataclass
    class EngagementOutcome:
        hit_confirmed: bool = False
        kill_confirmed: bool = False
        shots_fired: int = 0
        time_to_kill: Optional[float] = None
    
    @dataclass
    class Engagement:
        enemy_entry: EnemyEntry
        player_response: PlayerResponse
        context: EngagementContext
        outcome: EngagementOutcome


class EngagementBuilder:
    """
    Builds complete Engagement objects from synchronized logger data.
    
    Correlates all timestamps to create full reaction chains.
    """
    
    def __init__(self):
        """Initialize engagement builder"""
        self.engagements: List[Engagement] = []
        self.engagement_count = 0
        
        # Setup logging
        self._setup_logging()
        
        logging.info(f"Engagement Builder Started")
        logging.info("")
    
    def _setup_logging(self):
        """Configure logging output"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def build_engagement(
        self,
        enemy_entry_time: float,
        enemy_location: str,
        enemy_distance: Optional[float],
        camera_movements: List[Any],
        ads_events: List[Any],
        crosshair_on_target_time: Optional[float],
        shot_events: List[Any],
        movement_events: List[Any],
        hit_confirmed: bool = False,
        kill_confirmed: bool = False
    ) -> Optional[Engagement]:
        """
        Build complete engagement from synchronized events.
        
        Args:
            enemy_entry_time: When enemy entered screen
            enemy_location: Screen location (e.g., "11_oclock")
            enemy_distance: Distance to enemy (meters)
            camera_movements: List of camera movement events
            ads_events: List of ADS events
            crosshair_on_target_time: When crosshair first on target
            shot_events: List of shot events
            movement_events: List of movement state events
            hit_confirmed: Whether hit was confirmed
            kill_confirmed: Whether kill was confirmed
        
        Returns:
            Complete Engagement object or None if insufficient data
        """
        try:
            # STEP 1: Find camera turn toward enemy
            camera_turn_start = None
            for movement in camera_movements:
                if enemy_entry_time <= movement.timestamp <= enemy_entry_time + 1.0:
                    # Check if movement is toward enemy (simplified - use actual correlation)
                    camera_turn_start = movement.timestamp
                    break
            
            # STEP 2: Find ADS start after camera turn
            ads_start = None
            search_start = camera_turn_start if camera_turn_start else enemy_entry_time
            for ads_event in ads_events:
                if search_start <= ads_event.timestamp <= search_start + 2.0:
                    if ads_event.ads_active:
                        ads_start = ads_event.timestamp
                        break
            
            # STEP 3: Crosshair on target (provided)
            # crosshair_on_target_time already provided
            
            # STEP 4: Find trigger pull after crosshair on target
            trigger_pull = None
            shots_fired = 0
            if crosshair_on_target_time:
                for shot_event in shot_events:
                    if crosshair_on_target_time <= shot_event.timestamp <= crosshair_on_target_time + 0.5:
                        if shot_event.shot_detected:
                            if trigger_pull is None:
                                trigger_pull = shot_event.timestamp
                            shots_fired += 1
            
            # STEP 5: Get player movement state at engagement time
            player_movement_state = None
            for movement_event in movement_events:
                if movement_event.timestamp <= enemy_entry_time:
                    player_movement_state = movement_event.movement_state
                else:
                    break
            
            # Build engagement object
            enemy_entry = EnemyEntry(
                timestamp=enemy_entry_time,
                screen_location=enemy_location,
                distance=enemy_distance
            )
            
            player_response = PlayerResponse(
                camera_turn_start=camera_turn_start,
                ads_start=ads_start,
                crosshair_on_target=crosshair_on_target_time,
                trigger_pull=trigger_pull
            )
            
            context = EngagementContext(
                player_movement_state=player_movement_state,
                player_cover_state=None,  # Not detected yet
                weapon_class=None,  # Not detected yet
                match_time=enemy_entry_time,
                enemy_distance=enemy_distance
            )
            
            # Calculate time to kill
            time_to_kill = None
            if kill_confirmed and trigger_pull:
                time_to_kill = trigger_pull - enemy_entry_time
            
            outcome = EngagementOutcome(
                hit_confirmed=hit_confirmed,
                kill_confirmed=kill_confirmed,
                shots_fired=shots_fired,
                time_to_kill=time_to_kill
            )
            
            engagement = Engagement(
                enemy_entry=enemy_entry,
                player_response=player_response,
                context=context,
                outcome=outcome
            )
            
            self.engagements.append(engagement)
            self.engagement_count += 1
            
            # Log engagement summary
            logging.info(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"Engagement #{self.engagement_count} | "
                f"Location: {enemy_location} | "
                f"Camera: {camera_turn_start is not None} | "
                f"ADS: {ads_start is not None} | "
                f"Crosshair: {crosshair_on_target_time is not None} | "
                f"Trigger: {trigger_pull is not None} | "
                f"Kill: {kill_confirmed}"
            )
            
            return engagement
        
        except Exception as e:
            logging.error(f"Error building engagement: {e}")
            return None
    
    def calculate_reaction_times(self, engagement: Engagement) -> Dict[str, Optional[float]]:
        """
        Calculate all reaction time metrics for engagement.
        
        Args:
            engagement: Engagement object
        
        Returns:
            Dict with perceptual, decision, motor, and total reaction times
        """
        try:
            enemy_entry_time = engagement.enemy_entry.timestamp
            response = engagement.player_response
            
            # Perceptual latency (enemy entry → camera turn)
            perceptual = None
            if response.camera_turn_start:
                perceptual = response.camera_turn_start - enemy_entry_time
            
            # Decision latency (camera turn → ADS)
            decision = None
            if response.camera_turn_start and response.ads_start:
                decision = response.ads_start - response.camera_turn_start
            
            # Motor latency (crosshair on target → trigger pull)
            motor = None
            if response.crosshair_on_target and response.trigger_pull:
                motor = response.trigger_pull - response.crosshair_on_target
            
            # Total reaction time (enemy entry → trigger pull)
            total = None
            if response.trigger_pull:
                total = response.trigger_pull - enemy_entry_time
            
            return {
                "perceptual_latency": perceptual,
                "decision_latency": decision,
                "motor_latency": motor,
                "total_reaction_time": total
            }
        
        except Exception as e:
            logging.error(f"Error calculating reaction times: {e}")
            return {
                "perceptual_latency": None,
                "decision_latency": None,
                "motor_latency": None,
                "total_reaction_time": None
            }
    
    def export_engagements(self, output_file: Path):
        """
        Export all engagements to JSONL file.
        
        Args:
            output_file: Output file path
        """
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                for engagement in self.engagements:
                    # Calculate reaction times
                    reaction_times = self.calculate_reaction_times(engagement)
                    
                    # Build log entry
                    log_entry = {
                        "enemy_entry": asdict(engagement.enemy_entry),
                        "player_response": asdict(engagement.player_response),
                        "context": asdict(engagement.context),
                        "outcome": asdict(engagement.outcome),
                        "reaction_times": reaction_times
                    }
                    
                    f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + "\n")
            
            logging.info(f"Exported {len(self.engagements)} engagements to {output_file}")
        
        except Exception as e:
            logging.error(f"Error exporting engagements: {e}")
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics across all engagements.
        
        Returns:
            Dict with summary statistics
        """
        if not self.engagements:
            return {"total_engagements": 0}
        
        try:
            # Calculate reaction times for all engagements
            perceptual_times = []
            decision_times = []
            motor_times = []
            total_times = []
            
            for engagement in self.engagements:
                reaction_times = self.calculate_reaction_times(engagement)
                
                if reaction_times["perceptual_latency"]:
                    perceptual_times.append(reaction_times["perceptual_latency"])
                if reaction_times["decision_latency"]:
                    decision_times.append(reaction_times["decision_latency"])
                if reaction_times["motor_latency"]:
                    motor_times.append(reaction_times["motor_latency"])
                if reaction_times["total_reaction_time"]:
                    total_times.append(reaction_times["total_reaction_time"])
            
            # Calculate statistics
            import statistics
            
            def calc_stats(values):
                if not values:
                    return {"mean": None, "median": None, "std": None, "count": 0}
                return {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                    "count": len(values)
                }
            
            # Count outcomes
            hits = sum(1 for e in self.engagements if e.outcome.hit_confirmed)
            kills = sum(1 for e in self.engagements if e.outcome.kill_confirmed)
            total_shots = sum(e.outcome.shots_fired for e in self.engagements)
            
            return {
                "total_engagements": len(self.engagements),
                "reaction_times": {
                    "perceptual": calc_stats(perceptual_times),
                    "decision": calc_stats(decision_times),
                    "motor": calc_stats(motor_times),
                    "total": calc_stats(total_times)
                },
                "outcomes": {
                    "hits": hits,
                    "kills": kills,
                    "total_shots": total_shots,
                    "hit_rate": hits / len(self.engagements) if self.engagements else 0.0,
                    "kill_rate": kills / len(self.engagements) if self.engagements else 0.0
                }
            }
        
        except Exception as e:
            logging.error(f"Error calculating summary statistics: {e}")
            return {"total_engagements": len(self.engagements), "error": str(e)}


def main():
    """
    Example usage / testing
    """
    builder = EngagementBuilder()
    
    # Simulate building engagements
    try:
        # Mock data (replace with real synchronized events)
        for i in range(10):
            engagement = builder.build_engagement(
                enemy_entry_time=time.time() + i * 5.0,
                enemy_location="11_oclock",
                enemy_distance=45.0,
                camera_movements=[],  # Mock camera movements
                ads_events=[],  # Mock ADS events
                crosshair_on_target_time=time.time() + i * 5.0 + 0.5,
                shot_events=[],  # Mock shot events
                movement_events=[],  # Mock movement events
                hit_confirmed=True,
                kill_confirmed=True
            )
            
            if engagement:
                reaction_times = builder.calculate_reaction_times(engagement)
                logging.info(f"Reaction times: {json.dumps(reaction_times, indent=2)}")
        
        # Export engagements
        output_file = Path("logs/engagements/engagements_test.jsonl")
        builder.export_engagements(output_file)
        
        # Print summary statistics
        stats = builder.get_summary_statistics()
        logging.info(f"Summary Statistics:\n{json.dumps(stats, indent=2)}")
    
    except KeyboardInterrupt:
        logging.info("Engagement builder stopped")


if __name__ == "__main__":
    main()
