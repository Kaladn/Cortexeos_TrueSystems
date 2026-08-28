"""
Player Performance Analysis Class

Purpose:
  Measure human reaction chains under real conditions:
  Perception → Decision → Action → Outcome
  
Core Principle:
  Ground truth only. No interpretation, no claims, just measurements.
  
Metrics Categories:
  1. Perceptual Latency - Enemy enters view → first camera correction
  2. Decision Latency - Awareness → ADS / movement change
  3. Motor Latency - Crosshair alignment → trigger pull
  4. Execution Consistency - Variance over time, fatigue, tilt
  5. Contextual Performance - Distance, movement state, weapon class
  6. Outcome Correlation - Deaths from rear, cover usage, engagement choices
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np
from pathlib import Path
import json


class EngagementOutcome(Enum):
    """Possible outcomes of an engagement"""
    KILL = "kill"
    DEATH = "death"
    DISENGAGE = "disengage"
    ONGOING = "ongoing"


class MovementState(Enum):
    """Player movement state during engagement"""
    STATIONARY = "stationary"
    WALKING = "walking"
    SPRINTING = "sprinting"
    CROUCHING = "crouching"
    PRONE = "prone"


class CoverState(Enum):
    """Player cover state"""
    IN_COVER = "in_cover"
    EXPOSED = "exposed"
    PARTIAL_COVER = "partial_cover"


@dataclass
class EnemyEntry:
    """
    Ground truth: Enemy entered field of view
    
    Measured from: EdgeEntry operator
    """
    timestamp: float  # Seconds since match start
    screen_location: str  # "11_oclock", "3_oclock", etc.
    distance_meters: Optional[float] = None  # From depth buffer
    entry_type: str = "edge"  # "edge", "spawn", "corner"


@dataclass
class PlayerResponse:
    """
    Ground truth: Player's physical response to stimulus
    
    Measured from: Velocity buffer, input telemetry
    """
    camera_turn_start: Optional[float] = None  # First camera movement toward threat
    ads_start: Optional[float] = None  # Aim-down-sights initiated
    crosshair_on_target: Optional[float] = None  # Crosshair intersects enemy
    trigger_pull: Optional[float] = None  # First shot fired
    
    # Movement response
    movement_change: Optional[float] = None  # Changed movement direction/speed
    cover_seek: Optional[float] = None  # Moved toward cover


@dataclass
class EngagementContext:
    """
    Ground truth: Environmental conditions during engagement
    
    Measured from: All buffers
    """
    enemy_distance: Optional[float] = None  # Meters (from depth buffer)
    player_movement_state: MovementState = MovementState.STATIONARY
    player_cover_state: CoverState = CoverState.EXPOSED
    weapon_class: Optional[str] = None  # "AR", "SMG", "Sniper", etc.
    match_time_seconds: float = 0.0  # Time since match start
    player_health: Optional[float] = None  # 0.0-1.0 (if detectable)


@dataclass
class EngagementOutcomeData:
    """
    Ground truth: What actually happened
    
    Measured from: Kill feed, death detection, player state
    """
    outcome: EngagementOutcome
    outcome_timestamp: float
    shots_fired: int = 0
    shots_hit: int = 0
    damage_dealt: Optional[float] = None
    damage_received: Optional[float] = None


@dataclass
class Engagement:
    """
    Complete engagement record: Stimulus → Response → Outcome
    
    Ground truth only. No interpretation.
    """
    engagement_id: str
    enemy_entry: EnemyEntry
    player_response: PlayerResponse
    context: EngagementContext
    outcome: EngagementOutcomeData
    
    # Derived metrics (computed from ground truth)
    perceptual_latency: Optional[float] = None  # Entry → camera turn
    decision_latency: Optional[float] = None  # Camera turn → ADS
    motor_latency: Optional[float] = None  # Crosshair on target → trigger pull
    total_reaction_time: Optional[float] = None  # Entry → trigger pull
    
    def compute_derived_metrics(self):
        """
        Compute derived metrics from ground truth timestamps.
        
        Only computes if ground truth data exists.
        """
        entry_time = self.enemy_entry.timestamp
        response = self.player_response
        
        # Perceptual latency: How long to detect threat
        if response.camera_turn_start is not None:
            self.perceptual_latency = response.camera_turn_start - entry_time
        
        # Decision latency: How long to decide to engage
        if response.camera_turn_start is not None and response.ads_start is not None:
            self.decision_latency = response.ads_start - response.camera_turn_start
        
        # Motor latency: How long to execute shot
        if response.crosshair_on_target is not None and response.trigger_pull is not None:
            self.motor_latency = response.trigger_pull - response.crosshair_on_target
        
        # Total reaction time: Full chain
        if response.trigger_pull is not None:
            self.total_reaction_time = response.trigger_pull - entry_time


class PlayerPerformance:
    """
    Player performance analysis system.
    
    Measures human reaction chains under real conditions.
    No claims. No interpretation. Just measurements.
    """
    
    def __init__(self):
        self.engagements: List[Engagement] = []
        self.match_duration: float = 0.0
        self.player_id: Optional[str] = None
        self.session_id: Optional[str] = None
    
    def add_engagement(self, engagement: Engagement):
        """
        Add an engagement to the performance record.
        
        Automatically computes derived metrics.
        """
        engagement.compute_derived_metrics()
        self.engagements.append(engagement)
    
    # ===== GROUND TRUTH AGGREGATIONS =====
    # These functions aggregate measured data, no interpretation
    
    def get_perceptual_latencies(self) -> List[float]:
        """
        Return all measured perceptual latencies (enemy entry → camera turn).
        
        Ground truth: How long it takes to detect threats.
        """
        return [e.perceptual_latency for e in self.engagements 
                if e.perceptual_latency is not None]
    
    def get_decision_latencies(self) -> List[float]:
        """
        Return all measured decision latencies (camera turn → ADS).
        
        Ground truth: How long it takes to decide to engage.
        """
        return [e.decision_latency for e in self.engagements 
                if e.decision_latency is not None]
    
    def get_motor_latencies(self) -> List[float]:
        """
        Return all measured motor latencies (crosshair on target → trigger pull).
        
        Ground truth: How long it takes to execute shot.
        """
        return [e.motor_latency for e in self.engagements 
                if e.motor_latency is not None]
    
    def get_total_reaction_times(self) -> List[float]:
        """
        Return all measured total reaction times (enemy entry → trigger pull).
        
        Ground truth: Full reaction chain duration.
        """
        return [e.total_reaction_time for e in self.engagements 
                if e.total_reaction_time is not None]
    
    # ===== CONTEXTUAL FILTERING =====
    # Filter engagements by measured conditions
    
    def filter_by_distance(self, min_dist: float, max_dist: float) -> List[Engagement]:
        """
        Return engagements within distance range.
        
        Ground truth: Performance at specific ranges.
        """
        return [e for e in self.engagements 
                if e.context.enemy_distance is not None 
                and min_dist <= e.context.enemy_distance <= max_dist]
    
    def filter_by_movement_state(self, state: MovementState) -> List[Engagement]:
        """
        Return engagements during specific movement state.
        
        Ground truth: Performance while moving vs stationary.
        """
        return [e for e in self.engagements 
                if e.context.player_movement_state == state]
    
    def filter_by_match_time(self, min_time: float, max_time: float) -> List[Engagement]:
        """
        Return engagements within match time range.
        
        Ground truth: Performance over time (fatigue detection).
        """
        return [e for e in self.engagements 
                if min_time <= e.context.match_time_seconds <= max_time]
    
    def filter_by_screen_location(self, location: str) -> List[Engagement]:
        """
        Return engagements from specific screen location.
        
        Ground truth: Performance by threat direction.
        """
        return [e for e in self.engagements 
                if e.enemy_entry.screen_location == location]
    
    # ===== ACCURACY METRICS =====
    # Measured outcomes, no interpretation
    
    def get_accuracy_by_distance(self, distance_bins: List[Tuple[float, float]]) -> Dict[str, float]:
        """
        Return hit rate by distance bins.
        
        Ground truth: Accuracy at different ranges.
        
        Args:
            distance_bins: List of (min, max) distance tuples
        
        Returns:
            Dict mapping distance range to hit rate (0.0-1.0)
        """
        accuracy = {}
        
        for min_dist, max_dist in distance_bins:
            engagements = self.filter_by_distance(min_dist, max_dist)
            
            if not engagements:
                accuracy[f"{min_dist}-{max_dist}m"] = None
                continue
            
            total_shots = sum(e.outcome.shots_fired for e in engagements)
            total_hits = sum(e.outcome.shots_hit for e in engagements)
            
            if total_shots > 0:
                accuracy[f"{min_dist}-{max_dist}m"] = total_hits / total_shots
            else:
                accuracy[f"{min_dist}-{max_dist}m"] = None
        
        return accuracy
    
    def get_accuracy_by_movement(self) -> Dict[str, float]:
        """
        Return hit rate by movement state.
        
        Ground truth: Accuracy while moving vs stationary.
        """
        accuracy = {}
        
        for state in MovementState:
            engagements = self.filter_by_movement_state(state)
            
            if not engagements:
                accuracy[state.value] = None
                continue
            
            total_shots = sum(e.outcome.shots_fired for e in engagements)
            total_hits = sum(e.outcome.shots_hit for e in engagements)
            
            if total_shots > 0:
                accuracy[state.value] = total_hits / total_shots
            else:
                accuracy[state.value] = None
        
        return accuracy
    
    def get_first_shot_accuracy(self) -> float:
        """
        Return first shot hit rate.
        
        Ground truth: % of first shots that hit.
        """
        first_shot_hits = 0
        total_engagements = 0
        
        for e in self.engagements:
            if e.outcome.shots_fired > 0:
                total_engagements += 1
                if e.outcome.shots_hit > 0:
                    first_shot_hits += 1
        
        if total_engagements > 0:
            return first_shot_hits / total_engagements
        return 0.0
    
    # ===== CONSISTENCY METRICS =====
    # Variance and distribution analysis
    
    def get_reaction_time_variance(self) -> Dict[str, float]:
        """
        Return variance in reaction times.
        
        Ground truth: Consistency of performance.
        """
        perceptual = self.get_perceptual_latencies()
        decision = self.get_decision_latencies()
        motor = self.get_motor_latencies()
        total = self.get_total_reaction_times()
        
        return {
            "perceptual_variance": float(np.var(perceptual)) if perceptual else None,
            "decision_variance": float(np.var(decision)) if decision else None,
            "motor_variance": float(np.var(motor)) if motor else None,
            "total_variance": float(np.var(total)) if total else None
        }
    
    def get_performance_over_time(self, time_bins: List[Tuple[float, float]]) -> Dict[str, Dict]:
        """
        Return performance metrics by match time bins.
        
        Ground truth: Fatigue detection, warm-up curve.
        
        Args:
            time_bins: List of (min, max) time tuples in seconds
        
        Returns:
            Dict mapping time range to performance metrics
        """
        performance = {}
        
        for min_time, max_time in time_bins:
            engagements = self.filter_by_match_time(min_time, max_time)
            
            if not engagements:
                performance[f"{min_time}-{max_time}s"] = None
                continue
            
            # Compute metrics for this time bin
            total_shots = sum(e.outcome.shots_fired for e in engagements)
            total_hits = sum(e.outcome.shots_hit for e in engagements)
            accuracy = total_hits / total_shots if total_shots > 0 else 0.0
            
            reaction_times = [e.total_reaction_time for e in engagements 
                            if e.total_reaction_time is not None]
            avg_reaction = float(np.mean(reaction_times)) if reaction_times else None
            
            performance[f"{min_time}-{max_time}s"] = {
                "accuracy": accuracy,
                "avg_reaction_time": avg_reaction,
                "engagement_count": len(engagements)
            }
        
        return performance
    
    # ===== DECISION-MAKING METRICS =====
    # Measured choices, no interpretation
    
    def get_engagement_decisions(self) -> Dict[str, Dict[str, float]]:
        """
        Return engagement vs disengage rates by context.
        
        Ground truth: When player chooses to fight vs retreat.
        """
        # Group by cover state
        decisions = {}
        
        for cover_state in CoverState:
            engagements = [e for e in self.engagements 
                          if e.context.player_cover_state == cover_state]
            
            if not engagements:
                decisions[cover_state.value] = None
                continue
            
            engaged = sum(1 for e in engagements 
                         if e.outcome.outcome in [EngagementOutcome.KILL, EngagementOutcome.DEATH])
            disengaged = sum(1 for e in engagements 
                           if e.outcome.outcome == EngagementOutcome.DISENGAGE)
            
            total = len(engagements)
            
            decisions[cover_state.value] = {
                "engage_rate": engaged / total,
                "disengage_rate": disengaged / total,
                "sample_size": total
            }
        
        return decisions
    
    def get_death_analysis(self) -> Dict[str, any]:
        """
        Return death analysis metrics.
        
        Ground truth: How and where player dies.
        """
        deaths = [e for e in self.engagements 
                 if e.outcome.outcome == EngagementOutcome.DEATH]
        
        if not deaths:
            return {"total_deaths": 0}
        
        # Analyze death locations
        rear_deaths = sum(1 for d in deaths 
                         if "12_oclock" in d.enemy_entry.screen_location or 
                            "11_oclock" in d.enemy_entry.screen_location or
                            "1_oclock" in d.enemy_entry.screen_location)
        
        # Analyze death contexts
        exposed_deaths = sum(1 for d in deaths 
                           if d.context.player_cover_state == CoverState.EXPOSED)
        
        moving_deaths = sum(1 for d in deaths 
                          if d.context.player_movement_state in [MovementState.SPRINTING, MovementState.WALKING])
        
        return {
            "total_deaths": len(deaths),
            "rear_death_ratio": rear_deaths / len(deaths),
            "exposed_death_ratio": exposed_deaths / len(deaths),
            "moving_death_ratio": moving_deaths / len(deaths)
        }
    
    # ===== SUMMARY REPORT =====
    # Aggregate all ground truth measurements
    
    def generate_summary(self) -> Dict:
        """
        Generate complete performance summary.
        
        Ground truth: All measured metrics, no interpretation.
        """
        perceptual = self.get_perceptual_latencies()
        decision = self.get_decision_latencies()
        motor = self.get_motor_latencies()
        total = self.get_total_reaction_times()
        
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "match_duration": self.match_duration,
            "total_engagements": len(self.engagements),
            
            # Reaction time metrics
            "reaction_times": {
                "perceptual": {
                    "mean": float(np.mean(perceptual)) if perceptual else None,
                    "median": float(np.median(perceptual)) if perceptual else None,
                    "std": float(np.std(perceptual)) if perceptual else None,
                    "min": float(np.min(perceptual)) if perceptual else None,
                    "max": float(np.max(perceptual)) if perceptual else None
                },
                "decision": {
                    "mean": float(np.mean(decision)) if decision else None,
                    "median": float(np.median(decision)) if decision else None,
                    "std": float(np.std(decision)) if decision else None
                },
                "motor": {
                    "mean": float(np.mean(motor)) if motor else None,
                    "median": float(np.median(motor)) if motor else None,
                    "std": float(np.std(motor)) if motor else None
                },
                "total": {
                    "mean": float(np.mean(total)) if total else None,
                    "median": float(np.median(total)) if total else None,
                    "std": float(np.std(total)) if total else None
                }
            },
            
            # Accuracy metrics
            "accuracy": {
                "by_distance": self.get_accuracy_by_distance([(0, 30), (30, 50), (50, 70), (70, 100)]),
                "by_movement": self.get_accuracy_by_movement(),
                "first_shot": self.get_first_shot_accuracy()
            },
            
            # Consistency metrics
            "consistency": self.get_reaction_time_variance(),
            
            # Performance over time
            "performance_over_time": self.get_performance_over_time([
                (0, 300), (300, 600), (600, 900), (900, 1200)
            ]),
            
            # Decision-making
            "decisions": self.get_engagement_decisions(),
            
            # Death analysis
            "death_analysis": self.get_death_analysis()
        }
    
    def export_to_json(self, filepath: Path):
        """
        Export performance summary to JSON file.
        
        Ground truth: All measurements in structured format.
        """
        summary = self.generate_summary()
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def export_engagements_to_jsonl(self, filepath: Path):
        """
        Export individual engagements to JSONL file.
        
        Ground truth: Raw engagement records for analysis.
        """
        with open(filepath, 'w') as f:
            for engagement in self.engagements:
                # Convert to dict (simplified for JSON serialization)
                record = {
                    "engagement_id": engagement.engagement_id,
                    "enemy_entry_time": engagement.enemy_entry.timestamp,
                    "enemy_entry_location": engagement.enemy_entry.screen_location,
                    "enemy_distance": engagement.context.enemy_distance,
                    "perceptual_latency": engagement.perceptual_latency,
                    "decision_latency": engagement.decision_latency,
                    "motor_latency": engagement.motor_latency,
                    "total_reaction_time": engagement.total_reaction_time,
                    "outcome": engagement.outcome.outcome.value,
                    "shots_fired": engagement.outcome.shots_fired,
                    "shots_hit": engagement.outcome.shots_hit,
                    "match_time": engagement.context.match_time_seconds,
                    "movement_state": engagement.context.player_movement_state.value,
                    "cover_state": engagement.context.player_cover_state.value
                }
                
                f.write(json.dumps(record) + '\n')


# ===== EXAMPLE USAGE =====

if __name__ == "__main__":
    # Create performance tracker
    perf = PlayerPerformance()
    perf.session_id = "match_20260104_001"
    perf.player_id = "player_001"
    perf.match_duration = 900.0  # 15 minutes
    
    # Example engagement 1: Enemy from 11 o'clock, player responds, gets kill
    engagement1 = Engagement(
        engagement_id="eng_001",
        enemy_entry=EnemyEntry(
            timestamp=45.2,
            screen_location="11_oclock",
            distance_meters=48.5
        ),
        player_response=PlayerResponse(
            camera_turn_start=45.42,  # 220ms detection
            ads_start=45.65,           # 230ms decision
            crosshair_on_target=45.89, # 240ms target acquisition
            trigger_pull=45.97         # 80ms trigger pull
        ),
        context=EngagementContext(
            enemy_distance=48.5,
            player_movement_state=MovementState.WALKING,
            player_cover_state=CoverState.EXPOSED,
            weapon_class="AR",
            match_time_seconds=45.2
        ),
        outcome=EngagementOutcomeData(
            outcome=EngagementOutcome.KILL,
            outcome_timestamp=46.1,
            shots_fired=5,
            shots_hit=3
        )
    )
    
    perf.add_engagement(engagement1)
    
    # Generate summary
    summary = perf.generate_summary()
    print(json.dumps(summary, indent=2))
    
    # Export
    perf.export_to_json(Path("performance_summary.json"))
    perf.export_engagements_to_jsonl(Path("engagements.jsonl"))
