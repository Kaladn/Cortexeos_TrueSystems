"""
Gaming Domain: Crosshair Lock Operator - SIMPLIFIED

Core Loop Stage: APPLY (Detector type)

Purpose:
  Detects aim manipulation by tracking crosshair-to-enemy intersection physics.
  SIMPLIFIED VERSION: Uses center 20×20 pixel region only.
  
  EOMM Manipulation Vector: AIM SUPPRESSION
    - Hitbox shrinking (crosshair on target, no hit)
    - Aim drag/resistance (slowdown without magnetism)
    - Variable aim assist strength

Inputs:
  - FrameSequence (1-second window of ARC grids)
  - Config (crosshair region, enemy palette signatures)

Outputs:
  - OperatorResult with:
    - on_target_frames: How many frames had enemy in center 20×20
    - hit_marker_frames: How many frames showed hit marker flash
    - intersection_ratio: on_target / total_frames
    - hit_efficiency: hit_markers / on_target_frames
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any
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


class CrosshairLockOperator:
    """
    CORE LOOP STAGE: APPLY (Detector)
    
    Tracks crosshair-to-enemy physics to detect aim manipulation.
    SIMPLIFIED: Uses center 20×20 pixel region only.
    """
    
    def __init__(self, config_path: str):
        self.name = "crosshair_lock"
        
        # Load config from YAML
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        op_config = self.config.get("operators", {}).get("crosshair_lock", {})
        
        # CENTER 20×20 PIXEL REGION
        self.center_region_size = 20  # 20×20 pixels at exact screen center
        
        # Palette signature config
        self.enemy_palette_min = op_config.get("enemy_palette_min", 7)
        self.enemy_palette_max = op_config.get("enemy_palette_max", 9)
        self.environment_palette_min = op_config.get("environment_palette_min", 5)
        self.environment_palette_max = op_config.get("environment_palette_max", 6)
        self.hit_marker_palette = op_config.get("hit_marker_palette", 9)
        
        # SIMPLE THRESHOLD: Any enemy pixels in 20×20 = detected
        self.enemy_threshold = op_config.get("enemy_threshold", 0.05)  # 5% of 400 pixels = 20 pixels
        
        print(f"[+] CrosshairLockOperator initialized (SIMPLIFIED)")
        print(f"    Center region: {self.center_region_size}×{self.center_region_size} pixels")
        print(f"    Enemy palette: {self.enemy_palette_min}-{self.enemy_palette_max}")
        print(f"    Enemy threshold: {self.enemy_threshold * 100}% ({int(self.enemy_threshold * 400)} pixels)")
    
    def _get_center_20x20_pixels(self, h: int, w: int) -> List[tuple]:
        """
        Get pixel coordinates for center 20×20 region.
        
        Returns list of (y, x) tuples for all pixels in the 20×20 center.
        """
        center_y = h // 2
        center_x = w // 2
        
        half_size = self.center_region_size // 2  # 10 pixels
        
        pixels = []
        for y in range(center_y - half_size, center_y + half_size):
            for x in range(center_x - half_size, center_x + half_size):
                if 0 <= y < h and 0 <= x < w:  # Bounds check
                    pixels.append((y, x))
        
        return pixels
    
    def _detect_enemy_in_center(self, grid: List[List[int]], center_pixels: List[tuple]) -> tuple:
        """
        Check if enemy palette (7-9) is in center 20×20 pixels.
        
        Returns (bool, ratio):
          - bool: True if enemy detected (>5% of pixels)
          - ratio: Percentage of center pixels that are enemy
        """
        enemy_count = 0
        total_pixels = len(center_pixels)
        
        for y, x in center_pixels:
            palette = grid[y][x]
            if self.enemy_palette_min <= palette <= self.enemy_palette_max:
                enemy_count += 1
        
        ratio = enemy_count / total_pixels if total_pixels > 0 else 0.0
        detected = ratio >= self.enemy_threshold
        
        return detected, ratio
    
    def _detect_environment_in_center(self, grid: List[List[int]], center_pixels: List[tuple]) -> tuple:
        """
        Check if environment palette (5-6) is in center 20×20 pixels.
        
        Returns (bool, ratio):
          - bool: True if environment detected
          - ratio: Percentage of center pixels that are environment
        """
        env_count = 0
        total_pixels = len(center_pixels)
        
        for y, x in center_pixels:
            palette = grid[y][x]
            if self.environment_palette_min <= palette <= self.environment_palette_max:
                env_count += 1
        
        ratio = env_count / total_pixels if total_pixels > 0 else 0.0
        detected = ratio >= 0.10  # 10% threshold for environment
        
        return detected, ratio
    
    def _detect_hit_marker(self, grid: List[List[int]], center_pixels: List[tuple]) -> bool:
        """
        Check if hit marker flash (palette 9) is visible in center 20×20.
        
        Returns True if >10% of center pixels are hit marker.
        """
        hit_count = 0
        total_pixels = len(center_pixels)
        
        for y, x in center_pixels:
            if grid[y][x] == self.hit_marker_palette:
                hit_count += 1
        
        ratio = hit_count / total_pixels if total_pixels > 0 else 0.0
        return ratio >= 0.10  # 10% threshold (40 pixels out of 400)
    
    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        """
        APPLY stage: Simple center 20×20 aim manipulation detection.
        
        Returns:
          OperatorResult with metrics and flags, or None if no frames
        """
        print(f"🔥 CROSSHAIR_LOCK.ANALYZE() CALLED - FRAMES: {len(seq.frames)}")
        
        if len(seq.frames) < 1:
            print(f"  ❌ RETURNING NONE: No frames in sequence")
            return None
        
        h = seq.frames[0].h
        w = seq.frames[0].w
        
        print(f"  ✓ Frame dimensions: {h}×{w}")
        
        # Get center 20×20 pixel coordinates
        center_pixels = self._get_center_20x20_pixels(h, w)
        total_pixels = len(center_pixels)
        
        print(f"  ✓ Center region: {total_pixels} pixels ({self.center_region_size}×{self.center_region_size})")
        
        # Analyze each frame
        on_target_frames = []
        hit_marker_frames = []
        enemy_ratios = []
        environment_ratios = []
        
        for i, frame in enumerate(seq.frames):
            # Enemy detection
            enemy_detected, enemy_ratio = self._detect_enemy_in_center(frame.grid, center_pixels)
            on_target_frames.append(enemy_detected)
            enemy_ratios.append(enemy_ratio)
            
            # Environment detection
            env_detected, env_ratio = self._detect_environment_in_center(frame.grid, center_pixels)
            environment_ratios.append(env_ratio)
            
            # Hit marker detection
            hit_detected = self._detect_hit_marker(frame.grid, center_pixels)
            hit_marker_frames.append(hit_detected)
            
            if enemy_detected:
                print(f"    Frame {i}: ENEMY DETECTED ({enemy_ratio*100:.1f}% of center)")
        
        # Aggregate statistics
        total_frames = len(seq.frames)
        on_target_count = sum(on_target_frames)
        hit_marker_count = sum(hit_marker_frames)
        
        print(f"  ✓ On-target frames: {on_target_count}/{total_frames}")
        print(f"  ✓ Hit marker frames: {hit_marker_count}/{total_frames}")
        
        intersection_ratio = on_target_count / total_frames if total_frames > 0 else 0.0
        hit_efficiency = hit_marker_count / on_target_count if on_target_count > 0 else 0.0
        
        # Detect anomalies
        hit_efficiency_anomaly = 0.0
        if on_target_count >= 3:  # Need at least 3 frames
            if hit_efficiency < 0.2:
                hit_efficiency_anomaly = (0.2 - hit_efficiency) / 0.2
            elif hit_efficiency > 0.6:
                hit_efficiency_anomaly = (hit_efficiency - 0.6) / 0.4
        
        # Confidence: based on hit efficiency anomaly
        confidence = min(1.0, hit_efficiency_anomaly)
        
        # Flags
        flags = []
        if hit_efficiency_anomaly > 0.5:
            flags.append(ManipulationFlags.HITBOX_DRIFT)
        
        print(f"  ✓ Confidence: {confidence:.3f}")
        print(f"  ✓ Flags: {flags}")
        
        # ALWAYS RETURN RESULT (even if confidence=0)
        result = OperatorResult(
            operator_name=self.name,
            confidence=confidence,
            flags=flags,
            metrics={
                "on_target_frames": on_target_count,
                "hit_marker_frames": hit_marker_count,
                "intersection_ratio": intersection_ratio,
                "hit_efficiency": hit_efficiency,
                "hit_efficiency_anomaly": hit_efficiency_anomaly,
                
                # Per-frame ratios
                "avg_enemy_ratio": sum(enemy_ratios) / len(enemy_ratios) if enemy_ratios else 0.0,
                "max_enemy_ratio": max(enemy_ratios) if enemy_ratios else 0.0,
                "avg_environment_ratio": sum(environment_ratios) / len(environment_ratios) if environment_ratios else 0.0,
                "max_environment_ratio": max(environment_ratios) if environment_ratios else 0.0,
                
                # Center region info
                "center_region_size": self.center_region_size,
                "center_pixel_count": total_pixels
            },
            metadata={
                "frames_analyzed": total_frames,
                "enemy_threshold": self.enemy_threshold,
                "center_region": f"{self.center_region_size}×{self.center_region_size}"
            }
        )
        
        print(f"  ✅ RETURNING RESULT (confidence={confidence:.3f})")
        return result


# Test harness
if __name__ == "__main__":
    print("CrosshairLockOperator - Simplified Version")
    print("Uses center 20×20 pixel region for detection")
    print("\nTo use: Replace operators/crosshair_lock.py with this file")
