Gaming Domain: Edge Entry Tracker Operator

Core Loop Stage: APPLY (Detector type)

Purpose:
  Detects spawn manipulation by tracking enemy entries at screen edges.
  Measures:
    - Spawn locations (front, side, rear)
    - Entry frequency and timing
    - Post-kill spawn pressure
  
  EOMM Manipulation Vector: SPAWN PRESSURE MANIPULATION
    - Rear-spawn flooding (enemies spawning behind player)
    - Immediate post-kill replacements
    - Spawn rate amplification during punishment matches

Inputs:
  - FrameSequence (1-second window of ARC grids)
  - Config (edge detection thresholds, enemy signatures)

Outputs:
  - VideoOpResult with:
    - total_entries: Number of new enemies entering screen
    - entry_locations: Distribution (front/side/rear)
    - entry_rate: Entries per second
    - rear_spawn_ratio: Percentage spawning behind player
    
Core Loop Compliance:
  - Pure detector (no state modification)
  - Deterministic
  - Fast (< 15ms for 30 frames)
  - Explainable (returns entry vectors with timestamps)
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))
from frame_to_grid import FrameGrid

# Import TrueVision unified schema
sys.path.insert(0, str(Path(__file__).parent.parent))
from truevision_schema import OperatorResult, ManipulationFlags


@dataclass
class FrameSequence:
    """Contiguous sequence of frames for temporal analysis"""
    frames: List[FrameGrid]
    t_start: float
    t_end: float
    src: str


class EdgeEntryOperator:
    """
    CORE LOOP STAGE: APPLY (Detector)
    
    Tracks enemy entries at screen edges to detect spawn manipulation.
    """
    
    def __init__(self, config_path: str):
        self.name = "edge_entry"
        
        # Load config from YAML
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        op_config = self.config.get("operators", {}).get("edge_entry", {})
        
        # Edge detection
        self.edge_width = op_config.get("edge_width", 0.15)  # 15% of screen
        
        # Enemy detection (palette signature)
        self.enemy_palette_min = op_config.get("enemy_palette_min", 5)
        self.enemy_palette_max = op_config.get("enemy_palette_max", 9)
        
        # Entry thresholds
        self.entry_threshold = op_config.get("entry_threshold", 0.05)  # 5% of edge region
        
        # Spawn pressure thresholds
        self.rear_spawn_threshold = op_config.get("rear_spawn_threshold", 0.4)  # 40% rear spawns = manipulation
        self.high_pressure_rate = op_config.get("high_pressure_rate", 3.0)  # 3 entries/sec = high pressure
        
        print(f"[+] EdgeEntryOperator initialized")
        print(f"    Edge width: {self.edge_width * 100}%")
        print(f"    Enemy palette range: {self.enemy_palette_min}-{self.enemy_palette_max}")
        print(f"    Rear spawn threshold: {self.rear_spawn_threshold * 100}%")
    
    def _get_edge_regions(self, h: int, w: int) -> Dict[str, List[tuple]]:
        """
        Get edge regions divided into directional zones.
        Front = bottom (where player typically looks)
        Rear = top (behind player view)
        Sides = left/right
        """
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
        """
        Detect new enemy entry in region.
        Entry = enemy pixels suddenly appear where there were none.
        """
        prev_enemy_pixels = self._count_enemy_pixels(prev_grid, region_cells)
        curr_enemy_pixels = self._count_enemy_pixels(curr_grid, region_cells)
        
        # Entry detected if enemy pixels increase significantly
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