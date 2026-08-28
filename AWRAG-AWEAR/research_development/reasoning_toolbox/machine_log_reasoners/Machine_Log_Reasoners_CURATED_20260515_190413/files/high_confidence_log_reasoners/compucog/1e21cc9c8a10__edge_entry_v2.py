"""
Gaming Domain: Edge Entry Tracker Operator V2 (Patent-Enhanced)

Core Loop Stage: APPLY (Detector type)

ENHANCEMENTS OVER V1:
  - Patent signature matching (US20190091581A1, US10322351B2)
  - Spawn bias analysis (proximity to player)
  - Targeting likelihood detection
  - Forensic evidence citations

Purpose:
  Detects spawn manipulation by tracking enemy entries at screen edges.
  NOW WITH: Patent-documented spawn bias detection.
  
  EOMM Manipulation Vector: SPAWN PRESSURE MANIPULATION
    - Rear-spawn flooding (enemies spawning behind player)
    - Immediate post-kill replacements
    - Spawn rate amplification during punishment matches
    
  PATENT DETECTION:
    - US20190091581A1 [0083]: Enemy targeting likelihood modification
    - US10322351B2: Soft reservation spawn manipulation

Inputs:
  - FrameSequence (1-second window of ARC grids)
  - Config (edge detection thresholds, enemy signatures)
  - Patent signatures (loaded from activision_patents.jsonl)

Outputs:
  - OperatorResult with:
    - total_entries: Number of new enemies entering screen
    - entry_locations: Distribution (front/side/rear)
    - spawn_bias_score: Proximity bias metric
    - patent_match: Patent signature match (if detected)
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from frame_to_grid import FrameGrid

# Import TrueVision unified schema
sys.path.insert(0, str(Path(__file__).parent.parent))
from truevision_schema import OperatorResult, ManipulationFlags

# Import patent matcher
sys.path.insert(0, str(Path(__file__).parent.parent / "gaming"))
from patent_matcher import PatentMatcher


@dataclass
class FrameSequence:
    """Contiguous sequence of frames for temporal analysis"""
    frames: List[FrameGrid]
    t_start: float
    t_end: float
    src: str


class EdgeEntryOperatorV2:
    """
    CORE LOOP STAGE: APPLY (Detector) - PATENT-ENHANCED
    
    Tracks enemy entries at screen edges to detect spawn manipulation.
    NOW WITH: Spawn bias analysis and patent signature matching.
    """
    
    def __init__(self, config_path: str, signature_path: Optional[str] = None):
        self.name = "edge_entry_v2"
        
        # Load config from YAML
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        op_config = self.config.get("operators", {}).get("edge_entry", {})
        
        # Edge detection
        self.edge_width = op_config.get("edge_width", 0.15)
        
        # Enemy detection
        self.enemy_palette_min = op_config.get("enemy_palette_min", 5)
        self.enemy_palette_max = op_config.get("enemy_palette_max", 9)
        
        # Entry thresholds
        self.entry_threshold = op_config.get("entry_threshold", 0.05)
        
        # Spawn pressure thresholds
        self.rear_spawn_threshold = op_config.get("rear_spawn_threshold", 0.4)
        self.high_pressure_rate = op_config.get("high_pressure_rate", 3.0)
        
        # Patent signature matcher
        if signature_path is None:
            signature_path = Path(__file__).parent.parent / "gaming" / "signatures" / "activision_patents.jsonl"
        
        self.patent_matcher = PatentMatcher(str(signature_path))
        
        print(f"[+] EdgeEntryOperatorV2 initialized (PATENT-ENHANCED)")
        print(f"    Edge width: {self.edge_width * 100}%")
        print(f"    Enemy palette range: {self.enemy_palette_min}-{self.enemy_palette_max}")
        print(f"    Rear spawn threshold: {self.rear_spawn_threshold * 100}%")
        print(f"    Patent signatures loaded: {len(self.patent_matcher.signatures)}")
    
    def _get_edge_regions(self, h: int, w: int) -> Dict[str, List[tuple]]:
        """Get edge regions divided into directional zones"""
        edge_h = int(h * self.edge_width)
        edge_w = int(w * self.edge_width)
        
        regions = {
            "rear": [(y, x) for y in range(edge_h) for x in range(w)],
            "front": [(y, x) for y in range(h - edge_h, h) for x in range(w)],
            "left": [(y, x) for y in range(edge_h, h - edge_h) for x in range(edge_w)],
            "right": [(y, x) for y in range(edge_h, h - edge_h) for x in range(w - edge_w, w)]
        }
        
        return regions
    
    def _count_enemy_pixels(self, grid: List[List[int]], cells: List[tuple]) -> int:
        """Count pixels in enemy palette range"""
        enemy_pixels = 0
        
        for y, x in cells:
            val = grid[y][x]
            if self.enemy_palette_min <= val <= self.enemy_palette_max:
                enemy_pixels += 1
        
        return enemy_pixels
    
    def _detect_new_entry(self, prev_grid: List[List[int]], curr_grid: List[List[int]], 
                         region_cells: List[tuple], region_name: str) -> Optional[Dict]:
        """Detect new enemy entry in region"""
        prev_enemy_pixels = self._count_enemy_pixels(prev_grid, region_cells)
        curr_enemy_pixels = self._count_enemy_pixels(curr_grid, region_cells)
        
        pixel_increase = curr_enemy_pixels - prev_enemy_pixels
        total_region_pixels = len(region_cells)
        
        increase_ratio = pixel_increase / total_region_pixels if total_region_pixels > 0 else 0
        
        if increase_ratio > self.entry_threshold:
            return {
                "region": region_name,
                "increase_ratio": increase_ratio,
                "enemy_pixels": curr_enemy_pixels
            }
        
        return None
    
    def _classify_direction(self, region_name: str) -> str:
        """Classify region as front, side, or rear"""
        if region_name == "front":
            return "front"
        elif region_name == "rear":
            return "rear"
        else:
            return "side"
    
    def _calculate_spawn_bias_score(self, entries: List[Dict]) -> float:
        """
        **NEW: Calculate spawn bias score**
        
        Measures how biased spawns are toward rear/side (player-proximate) vs front.
        Higher score = more manipulation likely.
        
        Patent: US20190091581A1 [0083] - "likelihood of being targeted by enemy"
        """
        if not entries:
            return 0.0
        
        rear_count = sum(1 for e in entries if e['region'] == 'rear')
        side_count = sum(1 for e in entries if e['region'] in ['left', 'right'])
        front_count = sum(1 for e in entries if e['region'] == 'front')
        total = len(entries)
        
        # Bias score: weighted by proximity to player
        # Rear spawns = highest bias (behind player)
        # Side spawns = medium bias
        # Front spawns = expected (low bias)
        
        rear_weight = 1.0
        side_weight = 0.5
        front_weight = 0.0
        
        weighted_bias = (
            (rear_count * rear_weight) +
            (side_count * side_weight) +
            (front_count * front_weight)
        ) / total if total > 0 else 0.0
        
        return weighted_bias
    
    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        """
        APPLY stage: Detect spawn manipulation WITH PATENT MATCHING.
        
        Returns:
          OperatorResult with spawn metrics, manipulation flags,
          AND patent signature match if detected.
        """
        if len(seq.frames) < 2:
            return None
        
        h = seq.frames[0].h
        w = seq.frames[0].w
        regions = self._get_edge_regions(h, w)
        
        # Track entries across frames
        all_entries = []
        
        for i in range(1, len(seq.frames)):
            prev_frame = seq.frames[i - 1]
            curr_frame = seq.frames[i]
            
            for region_name, region_cells in regions.items():
                entry = self._detect_new_entry(
                    prev_frame.grid, curr_frame.grid, region_cells, region_name
                )
                if entry:
                    entry['frame_idx'] = i
                    entry['direction'] = self._classify_direction(region_name)
                    all_entries.append(entry)
        
        if not all_entries:
            return None
        
        # Compute metrics
        total_entries = len(all_entries)
        rear_entries = sum(1 for e in all_entries if e['direction'] == 'rear')
        side_entries = sum(1 for e in all_entries if e['direction'] == 'side')
        front_entries = sum(1 for e in all_entries if e['direction'] == 'front')
        
        rear_spawn_ratio = rear_entries / total_entries if total_entries > 0 else 0
        
        # Entry rate (entries per second)
        duration = seq.t_end - seq.t_start
        entry_rate = total_entries / duration if duration > 0 else 0
        
        # **NEW: Spawn bias score**
        spawn_bias_score = self._calculate_spawn_bias_score(all_entries)
        
        # Confidence
        confidence = 0.0
        if rear_spawn_ratio > self.rear_spawn_threshold:
            confidence = min(1.0, (rear_spawn_ratio - self.rear_spawn_threshold) / (1.0 - self.rear_spawn_threshold))
        
        if entry_rate > self.high_pressure_rate:
            confidence = max(confidence, min(1.0, (entry_rate - self.high_pressure_rate) / 5.0))
        
        # Spawn bias adds to confidence
        if spawn_bias_score > 0.5:
            confidence = max(confidence, spawn_bias_score)
        
        # Determine manipulation flags
        flags = []
        if rear_spawn_ratio > self.rear_spawn_threshold:
            flags.append(ManipulationFlags.REAR_SPAWNS)
        if entry_rate > self.high_pressure_rate:
            flags.append(ManipulationFlags.SPAWN_PRESSURE)
        if spawn_bias_score > 0.6:
            flags.append(ManipulationFlags.SPAWN_BIAS)
        
        # **NEW: Patent signature matching**
        detection_data = {
            'spawn_bias_score': spawn_bias_score,
            'rear_spawn_ratio': rear_spawn_ratio,
            'entry_rate': entry_rate,
            'total_entries': total_entries
        }
        
        patent_match = self.patent_matcher.match_signature("edge_entry", detection_data)
        
        # Build result
        result = OperatorResult(
            operator_name=self.name,
            confidence=min(1.0, confidence),
            flags=flags,
            metrics={
                "total_entries": total_entries,
                "rear_entries": rear_entries,
                "side_entries": side_entries,
                "front_entries": front_entries,
                "rear_spawn_ratio": rear_spawn_ratio,
                "entry_rate": entry_rate,
                "spawn_bias_score": spawn_bias_score  # NEW
            },
            metadata={
                "frames_analyzed": len(seq.frames),
                "duration_sec": duration
            }
        )
        
        # **NEW: Add patent match to metadata if found**
        if patent_match:
            result.metadata['patent_match'] = patent_match
            print(f"[!] PATENT MATCH: {patent_match['signature_id']}")
            print(f"    Confidence: {patent_match['match_confidence']:.2f}")
            print(f"    Citation: {patent_match['citation'][:100]}...")
        
        return result
