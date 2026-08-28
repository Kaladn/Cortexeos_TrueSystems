"""
GEO-ENGINE - Geometry & Spatial Transformations

Handles:
- Translations (shift up/down/left/right)
- Rotations (90°, 180°, 270°)
- Flips/Mirrors (horizontal, vertical, diagonal)
- Scaling (upsample, downsample)
- Cropping (bounding box, largest component)
- Padding (add border, center in canvas)

Philosophy:
- Detect "where things are" and "how they moved"
- Generate hypotheses for ALL consistent geometric transforms
- Return confidence based on exact match vs approximate
"""

import numpy as np
from typing import List, Dict, Any
from scipy import ndimage

from engines.base_engine import BaseEngine, Hypothesis, TaskView


class GeoEngine(BaseEngine):
    """
    Geometry reasoning engine.
    
    Detects spatial transformations between input and output grids.
    """
    
    def __init__(self):
        super().__init__(name="GEO")
        self.engine_name = "GEO"  # For ARC-CORE v3 dispatch
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        """
        Analyze task for geometric transformations.
        
        Strategy:
        1. For each training pair, detect geometric relationship
        2. Find transforms that work on ALL pairs
        3. Return hypotheses sorted by confidence
        """
        hypotheses = []
        
        # Check for rotation
        rotation_hyp = self._detect_rotation(task_view)
        if rotation_hyp:
            hypotheses.append(rotation_hyp)
        
        # Check for flip/mirror
        flip_hyp = self._detect_flip(task_view)
        if flip_hyp:
            hypotheses.append(flip_hyp)
        
        # Check for translation
        translation_hyp = self._detect_translation(task_view)
        if translation_hyp:
            hypotheses.append(translation_hyp)
        
        # Check for crop
        crop_hyp = self._detect_crop(task_view)
        if crop_hyp:
            hypotheses.append(crop_hyp)
        
        # Check for scale
        scale_hyp = self._detect_scale(task_view)
        if scale_hyp:
            hypotheses.append(scale_hyp)
        
        # Check for transpose
        transpose_hyp = self._detect_transpose(task_view)
        if transpose_hyp:
            hypotheses.append(transpose_hyp)
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        return hypotheses
    
    def _detect_rotation(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is rotated version of input."""
        # Try 90°, 180°, 270° rotations
        for k in [1, 2, 3]:  # rot90(k)
            matches = 0
            for input_grid, output_grid in task_view.train_pairs:
                rotated = np.rot90(input_grid, k=k)
                if np.array_equal(rotated, output_grid):
                    matches += 1
            
            if matches == len(task_view.train_pairs):
                # All pairs match this rotation
                angle = k * 90
                return Hypothesis(
                    engine_name="GEO",
                    operation="ROTATE",
                    params={"angle": angle, "k": k},
                    confidence=1.0,
                    dsl_program=f"GEO:ROTATE({angle})",
                    explanation=f"Rotate {angle}° clockwise"
                )
        
        return None
    
    def _detect_flip(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is flipped version of input."""
        # Try horizontal and vertical flips
        for axis, name in [(0, "vertical"), (1, "horizontal")]:
            matches = 0
            for input_grid, output_grid in task_view.train_pairs:
                flipped = np.flip(input_grid, axis=axis)
                if np.array_equal(flipped, output_grid):
                    matches += 1
            
            if matches == len(task_view.train_pairs):
                return Hypothesis(
                    engine_name="GEO",
                    operation="FLIP",
                    params={"axis": axis, "direction": name},
                    confidence=1.0,
                    dsl_program=f"GEO:FLIP({name.upper()})",
                    explanation=f"Flip {name}"
                )
        
        return None
    
    def _detect_translation(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is translated version of input."""
        # Try different shift amounts
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                if dy == 0 and dx == 0:
                    continue
                
                matches = 0
                for input_grid, output_grid in task_view.train_pairs:
                    # Check if shapes match
                    if input_grid.shape != output_grid.shape:
                        break
                    
                    # Roll with wraparound
                    shifted = np.roll(input_grid, shift=(dy, dx), axis=(0, 1))
                    if np.array_equal(shifted, output_grid):
                        matches += 1
                
                if matches == len(task_view.train_pairs):
                    return Hypothesis(
                        engine_name="GEO",
                        operation="TRANSLATE",
                        params={"dy": dy, "dx": dx},
                        confidence=1.0,
                        dsl_program=f"GEO:TRANSLATE({dy},{dx})",
                        explanation=f"Shift by ({dy}, {dx})"
                    )
        
        return None
    
    def _detect_crop(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is cropped version of input."""
        # Check if output is always a crop of input at the SAME position
        all_crop = True
        crop_coords = None  # (row_start, col_start, row_end, col_end)
        
        for input_grid, output_grid in task_view.train_pairs:
            h_in, w_in = input_grid.shape
            h_out, w_out = output_grid.shape
            
            # Output must be smaller
            if h_out >= h_in or w_out >= w_in:
                all_crop = False
                break
            
            # Check if output appears somewhere in input
            found = False
            for i in range(h_in - h_out + 1):
                for j in range(w_in - w_out + 1):
                    if np.array_equal(input_grid[i:i+h_out, j:j+w_out], output_grid):
                        found = True
                        current_coords = (i, j, i+h_out, j+w_out)
                        
                        # First pair sets the crop position
                        if crop_coords is None:
                            crop_coords = current_coords
                        # All pairs must crop from SAME position
                        elif crop_coords != current_coords:
                            all_crop = False
                        break
                if found:
                    break
            
            if not found:
                all_crop = False
                break
        
        if all_crop and crop_coords:
            r1, c1, r2, c2 = crop_coords
            
            # Classify crop type
            if r1 == 0 and c1 == 0:
                crop_type = "top_left"
            elif r2 == h_in and c2 == w_in:
                crop_type = "bottom_right"
            else:
                crop_type = "region"
            
            return Hypothesis(
                engine_name="GEO",
                operation="CROP",
                params={"type": crop_type, "coords": crop_coords},
                confidence=0.9,
                dsl_program=f"GEO:CROP({r1},{c1},{r2},{c2})",
                explanation=f"Crop to [{r1}:{r2}, {c1}:{c2}]"
            )
        
        return None
    
    def _detect_scale(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is scaled version of input."""
        # Check for integer upscaling (each pixel becomes k×k block)
        for k in [2, 3, 4]:
            matches = 0
            for input_grid, output_grid in task_view.train_pairs:
                h_in, w_in = input_grid.shape
                h_out, w_out = output_grid.shape
                
                # Check if dimensions match scaling
                if h_out != h_in * k or w_out != w_in * k:
                    break
                
                # Check if each pixel is replicated k×k times
                scaled = np.repeat(np.repeat(input_grid, k, axis=0), k, axis=1)
                if np.array_equal(scaled, output_grid):
                    matches += 1
            
            if matches == len(task_view.train_pairs):
                return Hypothesis(
                    engine_name="GEO",
                    operation="SCALE",
                    params={"factor": k},
                    confidence=1.0,
                    dsl_program=f"GEO:SCALE({k})",
                    explanation=f"Upscale by {k}× (each pixel → {k}×{k} block)"
                )
        
        return None
    
    def _detect_transpose(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is transposed version of input."""
        matches = 0
        for input_grid, output_grid in task_view.train_pairs:
            if np.array_equal(input_grid.T, output_grid):
                matches += 1
        
        if matches == len(task_view.train_pairs):
            return Hypothesis(
                engine_name="GEO",
                operation="TRANSPOSE",
                params={},
                confidence=1.0,
                dsl_program="GEO:TRANSPOSE()",
                explanation="Transpose (swap rows and columns)"
            )
        
        return None
    
    def extract_features(self, grid: np.ndarray) -> Dict[str, Any]:
        """Extract geometric features from grid."""
        h, w = grid.shape
        
        # Check symmetries
        has_h_symmetry = np.array_equal(grid, np.flip(grid, axis=1))
        has_v_symmetry = np.array_equal(grid, np.flip(grid, axis=0))
        has_diag_symmetry = np.array_equal(grid, grid.T) if h == w else False
        
        return {
            'shape': (h, w),
            'has_horizontal_symmetry': has_h_symmetry,
            'has_vertical_symmetry': has_v_symmetry,
            'has_diagonal_symmetry': has_diag_symmetry,
        }
    
    # ========================================================================
    # ARC-CORE V3 COMPATIBILITY METHODS
    # ========================================================================
    
    def analyze_pair(self, grid_pair) -> List:
        """
        ARC-CORE v3 interface: Analyze single train pair for geometric transforms.
        
        Args:
            grid_pair: GridPair with input_grid, output_grid
        
        Returns:
            List of EngineHypothesis instances (created as dict for compatibility)
        """
        # Create hypothesis as dict to avoid circular import
        def make_hypothesis(engine, op_name, params, cost, confidence):
            # Return dict that matches EngineHypothesis fields
            class Hyp:
                pass
            h = Hyp()
            h.engine = engine
            h.op_name = op_name
            h.params = params
            h.cost = cost
            h.confidence = confidence
            h.supports_multi_input = True
            return h
        
        hypotheses = []
        input_grid = grid_pair.input_grid
        output_grid = grid_pair.output_grid
        
        # Check ROTATE (90°, 180°, 270°)
        for k in [1, 2, 3]:
            rotated = np.rot90(input_grid, k=k)
            if np.array_equal(rotated, output_grid):
                hypotheses.append(make_hypothesis(
                    engine="GEO",
                    op_name="ROTATE",
                    params={"angle": k * 90, "k": k},
                    cost=1.0,
                    confidence=1.0
                ))
                break  # Only one rotation matches
        
        # Check MIRROR (horizontal and vertical)
        if np.array_equal(np.flip(input_grid, axis=1), output_grid):
            hypotheses.append(make_hypothesis(
                engine="GEO",
                op_name="MIRROR_H",
                params={"axis": 1},
                cost=1.0,
                confidence=1.0
            ))
        
        if np.array_equal(np.flip(input_grid, axis=0), output_grid):
            hypotheses.append(make_hypothesis(
                engine="GEO",
                op_name="MIRROR_V",
                params={"axis": 0},
                cost=1.0,
                confidence=1.0
            ))
        
        # Check TRANSPOSE
        if np.array_equal(input_grid.T, output_grid):
            hypotheses.append(make_hypothesis(
                engine="GEO",
                op_name="TRANSPOSE",
                params={},
                cost=1.0,
                confidence=1.0
            ))
        
        # Check SCALE (upscaling by 2x, 3x, 4x)
        h_in, w_in = input_grid.shape
        h_out, w_out = output_grid.shape
        
        for k in [2, 3, 4]:
            if h_out == h_in * k and w_out == w_in * k:
                scaled = np.repeat(np.repeat(input_grid, k, axis=0), k, axis=1)
                if np.array_equal(scaled, output_grid):
                    hypotheses.append(make_hypothesis(
                        engine="GEO",
                        op_name="SCALE",
                        params={"factor": k},
                        cost=1.5,
                        confidence=1.0
                    ))
                    break
        
        return hypotheses
    
    def execute_op(self, grid: np.ndarray, op_name: str, params: Dict[str, Any]) -> np.ndarray:
        """
        ARC-CORE v3 interface: Execute geometric operation on grid.
        
        Args:
            grid: Input grid
            op_name: Operation name (ROTATE, MIRROR_H, MIRROR_V, TRANSPOSE, SCALE, etc.)
            params: Operation parameters
        
        Returns:
            Transformed grid
        """
        if op_name == "ROTATE":
            k = params.get("k", 1)
            return np.rot90(grid, k=k)
        
        elif op_name == "MIRROR_H":
            return np.flip(grid, axis=1)
        
        elif op_name == "MIRROR_V":
            return np.flip(grid, axis=0)
        
        elif op_name == "TRANSPOSE":
            return grid.T
        
        elif op_name == "SCALE":
            factor = params.get("factor", 2)
            return np.repeat(np.repeat(grid, factor, axis=0), factor, axis=1)
        
        elif op_name == "CROP":
            coords = params.get("coords")
            if coords:
                r1, c1, r2, c2 = coords
                return grid[r1:r2, c1:c2]
            return grid
        
        else:
            return grid
