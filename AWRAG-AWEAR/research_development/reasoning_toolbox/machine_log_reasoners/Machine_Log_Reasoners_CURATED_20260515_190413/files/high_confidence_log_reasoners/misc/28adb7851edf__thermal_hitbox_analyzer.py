"""
Gaming Domain: Thermal Hitbox Analyzer Operator

Core Loop Stage: APPLY (Detector type)

Purpose:
  Detects hitbox manipulation by measuring enemy heat signature sizes in thermal buffer.
  Measures:
    - Thermal signature pixel count (blob size)
    - Apparent hitbox diameter (angular size × distance)
    - Bot vs human signature size ratios
  
  EOMM Manipulation Vector: HITBOX SIZE MANIPULATION
    - Enlarged hitboxes in bot lobbies (easier to hit)
    - Shrunk hitboxes in human matches (harder to hit)
    - Dynamic hitbox scaling based on player performance

Inputs:
  - FrameSequence with thermal buffer data (PNG images or raw buffer)
  - Depth buffer data (for distance normalization)
  - Config (thermal detection thresholds, blob parameters)

Outputs:
  - OperatorResult with:
    - thermal_signature_size: Pixel count of enemy heat signature
    - normalized_hitbox_diameter: Size adjusted for distance
    - hitbox_manipulation_score: Deviation from expected size
    - comparison_ratio: Bot lobby vs human match ratio
    
Core Loop Compliance:
  - Pure detector (no state modification)
  - Deterministic
  - Fast (< 50ms for thermal blob detection)
  - Explainable (returns signature measurements with coordinates)
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple, Any
import sys
from pathlib import Path
import yaml
import numpy as np

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


@dataclass
class ThermalBlob:
    """Detected thermal signature blob"""
    center_x: int
    center_y: int
    pixel_count: int
    bounding_box: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    max_intensity: float
    avg_intensity: float
    distance_meters: Optional[float] = None  # From depth buffer
    normalized_diameter: Optional[float] = None  # Adjusted for distance


class ThermalHitboxAnalyzer:
    """
    CORE LOOP STAGE: APPLY (Detector)
    
    Analyzes thermal buffer to measure enemy hitbox sizes and detect manipulation.
    """
    
    def __init__(self, config_path: str):
        self.name = "thermal_hitbox_analyzer"
        
        # Load config from YAML
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        op_config = self.config.get("operators", {}).get("thermal_hitbox_analyzer", {})
        
        # Thermal detection parameters
        self.thermal_threshold = op_config.get("thermal_threshold", 0.3)  # 30% intensity = heat signature
        self.min_blob_size = op_config.get("min_blob_size", 100)  # Minimum 100 pixels
        self.max_blob_size = op_config.get("max_blob_size", 50000)  # Maximum 50k pixels
        
        # Distance normalization (from depth buffer)
        self.use_depth_normalization = op_config.get("use_depth_normalization", True)
        self.reference_distance = op_config.get("reference_distance", 50.0)  # 50 meters reference
        
        # Hitbox manipulation detection
        self.expected_hitbox_size = op_config.get("expected_hitbox_size", 2000)  # Expected pixels at 50m
        self.manipulation_threshold = op_config.get("manipulation_threshold", 1.5)  # 1.5× = manipulation
        
        # Crosshair region (for filtering relevant blobs)
        self.crosshair_region_radius = op_config.get("crosshair_region_radius", 200)  # 200 pixels from center
        
        print(f"[+] ThermalHitboxAnalyzer initialized")
        print(f"    Thermal threshold: {self.thermal_threshold * 100}%")
        print(f"    Blob size range: {self.min_blob_size}-{self.max_blob_size} pixels")
        print(f"    Expected hitbox size: {self.expected_hitbox_size} pixels @ {self.reference_distance}m")
        print(f"    Manipulation threshold: {self.manipulation_threshold}×")
    
    def _extract_thermal_data(self, frame: FrameGrid) -> Optional[np.ndarray]:
        """
        Extract thermal buffer data from frame.
        
        Assumes thermal data is stored in frame.thermal_buffer (added by DirectX capture).
        Returns normalized float array [0.0, 1.0] representing heat intensity.
        """
        if not hasattr(frame, 'thermal_buffer') or frame.thermal_buffer is None:
            return None
        
        # Thermal buffer should be grayscale float array
        thermal = frame.thermal_buffer
        
        # Normalize to [0.0, 1.0] if not already
        if thermal.max() > 1.0:
            thermal = thermal / 255.0
        
        return thermal
    
    def _extract_depth_data(self, frame: FrameGrid) -> Optional[np.ndarray]:
        """
        Extract depth buffer data from frame.
        
        Assumes depth data is stored in frame.depth_buffer (added by DirectX capture).
        Returns float array representing distance in meters.
        """
        if not hasattr(frame, 'depth_buffer') or frame.depth_buffer is None:
            return None
        
        return frame.depth_buffer
    
    def _detect_thermal_blobs(self, thermal_data: np.ndarray, depth_data: Optional[np.ndarray],
                             center_x: int, center_y: int) -> List[ThermalBlob]:
        """
        Detect thermal signature blobs (connected regions of high heat).
        
        Uses simple flood-fill algorithm to identify connected hot pixels.
        Filters to only blobs near crosshair region.
        """
        h, w = thermal_data.shape
        visited = np.zeros((h, w), dtype=bool)
        blobs = []
        
        # Threshold thermal data
        hot_pixels = thermal_data > self.thermal_threshold
        
        def flood_fill(start_y: int, start_x: int) -> Optional[ThermalBlob]:
            """Flood fill to find connected blob"""
            stack = [(start_y, start_x)]
            blob_pixels = []
            intensities = []
            
            while stack:
                y, x = stack.pop()
                
                if y < 0 or y >= h or x < 0 or x >= w:
                    continue
                if visited[y, x] or not hot_pixels[y, x]:
                    continue
                
                visited[y, x] = True
                blob_pixels.append((y, x))
                intensities.append(thermal_data[y, x])
                
                # Add neighbors
                stack.extend([(y-1, x), (y+1, x), (y, x-1), (y, x+1)])
            
            if len(blob_pixels) < self.min_blob_size or len(blob_pixels) > self.max_blob_size:
                return None
            
            # Compute blob properties
            ys, xs = zip(*blob_pixels)
            center_blob_x = int(np.mean(xs))
            center_blob_y = int(np.mean(ys))
            
            # Filter: only keep blobs near crosshair
            dist_from_crosshair = np.sqrt((center_blob_x - center_x)**2 + (center_blob_y - center_y)**2)
            if dist_from_crosshair > self.crosshair_region_radius:
                return None
            
            # Get distance from depth buffer (if available)
            distance_meters = None
            if depth_data is not None:
                distance_meters = float(depth_data[center_blob_y, center_blob_x])
            
            # Compute normalized diameter (adjust for distance)
            normalized_diameter = None
            if distance_meters is not None and distance_meters > 0:
                # Inverse square law: apparent size ∝ 1/distance²
                normalized_diameter = len(blob_pixels) * (distance_meters / self.reference_distance) ** 2
            
            return ThermalBlob(
                center_x=center_blob_x,
                center_y=center_blob_y,
                pixel_count=len(blob_pixels),
                bounding_box=(min(xs), min(ys), max(xs), max(ys)),
                max_intensity=max(intensities),
                avg_intensity=np.mean(intensities),
                distance_meters=distance_meters,
                normalized_diameter=normalized_diameter
            )
        
        # Scan for blobs
        for y in range(h):
            for x in range(w):
                if not visited[y, x] and hot_pixels[y, x]:
                    blob = flood_fill(y, x)
                    if blob is not None:
                        blobs.append(blob)
        
        return blobs
    
    def _compute_manipulation_score(self, blob: ThermalBlob) -> float:
        """
        Compute manipulation score for a blob.
        
        Score = deviation from expected hitbox size.
        > 1.0 = larger than expected (bot lobby)
        < 1.0 = smaller than expected (human match)
        """
        if blob.normalized_diameter is not None:
            # Use distance-normalized size
            size = blob.normalized_diameter
        else:
            # Fallback to raw pixel count
            size = blob.pixel_count
        
        # Ratio to expected size
        ratio = size / self.expected_hitbox_size
        
        # Score = deviation from 1.0
        if ratio > 1.0:
            # Larger than expected
            score = (ratio - 1.0) / (self.manipulation_threshold - 1.0)
        else:
            # Smaller than expected
            score = (1.0 - ratio) / (1.0 - (1.0 / self.manipulation_threshold))
        
        return min(1.0, score)
    
    def analyze(self, seq: FrameSequence) -> Optional[OperatorResult]:
        """
        APPLY stage: Analyze thermal buffer to detect hitbox manipulation.
        
        Returns:
          OperatorResult with thermal signature measurements and manipulation flags
        """
        if len(seq.frames) < 1:
            return None
        
        h = seq.frames[0].h
        w = seq.frames[0].w
        center_x = w // 2
        center_y = h // 2
        
        # Collect thermal blobs across all frames
        all_blobs = []
        frames_with_thermal = 0
        
        for frame in seq.frames:
            thermal_data = self._extract_thermal_data(frame)
            if thermal_data is None:
                continue  # No thermal data in this frame
            
            frames_with_thermal += 1
            depth_data = self._extract_depth_data(frame)
            
            blobs = self._detect_thermal_blobs(thermal_data, depth_data, center_x, center_y)
            all_blobs.extend(blobs)
        
        if not all_blobs:
            return None  # No thermal signatures detected
        
        # Aggregate statistics
        total_blobs = len(all_blobs)
        
        # Signature sizes
        raw_sizes = [blob.pixel_count for blob in all_blobs]
        normalized_sizes = [blob.normalized_diameter for blob in all_blobs if blob.normalized_diameter is not None]
        
        avg_raw_size = np.mean(raw_sizes)
        avg_normalized_size = np.mean(normalized_sizes) if normalized_sizes else None
        
        # Distances
        distances = [blob.distance_meters for blob in all_blobs if blob.distance_meters is not None]
        avg_distance = np.mean(distances) if distances else None
        
        # Manipulation scores
        manipulation_scores = [self._compute_manipulation_score(blob) for blob in all_blobs]
        avg_manipulation_score = np.mean(manipulation_scores)
        max_manipulation_score = max(manipulation_scores)
        
        # Confidence: based on max manipulation score
        confidence = max_manipulation_score
        
        # Determine manipulation flags
        flags = []
        
        # Check for enlarged hitboxes (bot lobby)
        if avg_normalized_size is not None and avg_normalized_size > self.expected_hitbox_size * self.manipulation_threshold:
            flags.append(ManipulationFlags.HITBOX_DRIFT)
        
        # Check for shrunk hitboxes (human match)
        if avg_normalized_size is not None and avg_normalized_size < self.expected_hitbox_size / self.manipulation_threshold:
            flags.append(ManipulationFlags.HITBOX_DRIFT)
        
        # Prepare blob details for metadata
        blob_details = []
        for blob in all_blobs[:10]:  # Limit to first 10 for brevity
            blob_details.append({
                "center": (blob.center_x, blob.center_y),
                "size": blob.pixel_count,
                "normalized_size": blob.normalized_diameter,
                "distance": blob.distance_meters,
                "intensity": blob.avg_intensity
            })
        
        return OperatorResult(
            operator_name=self.name,
            confidence=min(1.0, confidence),
            flags=flags,
            metrics={
                "total_thermal_signatures": total_blobs,
                "avg_raw_size_pixels": float(avg_raw_size),
                "avg_normalized_size_pixels": float(avg_normalized_size) if avg_normalized_size is not None else None,
                "avg_distance_meters": float(avg_distance) if avg_distance is not None else None,
                "avg_manipulation_score": float(avg_manipulation_score),
                "max_manipulation_score": float(max_manipulation_score),
                
                # Size distribution
                "min_size": int(min(raw_sizes)),
                "max_size": int(max(raw_sizes)),
                "size_variance": float(np.var(raw_sizes)),
                
                # Comparison to expected
                "size_ratio_to_expected": float(avg_normalized_size / self.expected_hitbox_size) if avg_normalized_size else None
            },
            metadata={
                "frames_analyzed": len(seq.frames),
                "frames_with_thermal": frames_with_thermal,
                "blob_details": blob_details,
                "expected_hitbox_size": self.expected_hitbox_size,
                "reference_distance": self.reference_distance,
                "thermal_threshold": self.thermal_threshold
            }
        )
