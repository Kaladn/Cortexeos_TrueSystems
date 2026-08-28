"""
ARC-CORE - The Orchestrator

Coordinates all 8 reasoning engines to solve ARC tasks.

Philosophy:
- ARC-CORE never does math, only coordinates
- Each engine is a specialist, ARC-CORE is the conductor
- Try macros first (replay known solutions)
- Fallback to engine composition (1-step, 2-step, 3-step)
- Always return reasoning trace for debugging

Architecture:
    TaskView → ARC-CORE → Engines → Hypotheses → Execution → Output
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from engines.base_engine import TaskView, Hypothesis, BaseEngine
from engines.geo_engine import GeoEngine
from engines.shape_engine import ShapeEngine
from engines.rel_engine import RelEngine
from engines.color_engine import (
    ColorEngine,
    CompEngine,
    PatternEngine,
    CountEngine,
    MetaCompEngine
)


@dataclass
class SolutionTrace:
    """
    Complete trace of how a solution was found.
    
    Attributes:
        task_id: Task identifier
        success: Whether solution was found
        solution: Output grid (if success=True)
        method: How it was solved ("macro", "single-engine", "composition")
        hypotheses_tried: All hypotheses attempted
        winning_hypothesis: The hypothesis that worked
        execution_time: Time taken in seconds
        reasoning: Human-readable explanation
    """
    task_id: str
    success: bool
    solution: Optional[np.ndarray]
    method: str
    hypotheses_tried: List[Hypothesis]
    winning_hypothesis: Optional[Hypothesis]
    execution_time: float
    reasoning: str


class ArcCore:
    """
    The central reasoning engine coordinator.
    
    Responsibilities:
    1. Orchestrate 8 specialist engines
    2. Try macro-based solutions first (k-NN from training set)
    3. Fallback to single-engine solutions
    4. Fallback to 2-step compositions
    5. Fallback to 3-step compositions with beam search
    6. Return solution + complete reasoning trace
    
    The "we have all day" approach:
    - Try cheap solutions first (macros, single-ops)
    - Gradually increase search depth
    - Never give up until timeout
    """
    
    def __init__(self, 
                 operator_library: Optional[Dict] = None,
                 training_macros: Optional[Dict] = None,
                 timeout_per_task: float = 60.0):
        """
        Initialize ARC-CORE with engines and knowledge base.
        
        Args:
            operator_library: Pre-existing operators (for backward compatibility)
            training_macros: Pre-computed macro library from 1000 training tasks
            timeout_per_task: Maximum time per task (seconds)
        """
        # Initialize all 8 engines
        self.engines = {
            'geo': GeoEngine(),
            'color': ColorEngine(),
            'comp': CompEngine(),
            'pattern': PatternEngine(),
            'shape': ShapeEngine(),
            'count': CountEngine(),
            'rel': RelEngine(),
            'meta': MetaCompEngine(),
        }
        
        # Knowledge base
        self.operator_library = operator_library or {}
        self.training_macros = training_macros or {}
        self.timeout = timeout_per_task
        
        # Statistics
        self.stats = {
            'tasks_solved': 0,
            'macro_solves': 0,
            'single_engine_solves': 0,
            'composition_solves': 0,
            'total_time': 0.0,
        }
    
    def solve(self, task_data: Dict, task_id: str = "unknown") -> SolutionTrace:
        """
        Main solving loop.
        
        Args:
            task_data: Task with 'train' and 'test' keys
            task_id: Task identifier
            
        Returns:
            SolutionTrace with solution and reasoning
            
        Strategy:
        1. Parse task into TaskView
        2. Extract features (call all engines)
        3. Try macro solutions (k-NN from training set)
        4. Try single-engine solutions (each engine independently)
        5. Try 2-step compositions (pairwise engine combinations)
        6. Try 3-step compositions (beam search)
        7. Give up and return failure trace
        """
        start_time = time.time()
        
        # Step 1: Parse task
        task_view = self._parse_task(task_data, task_id)
        
        # Step 2: Extract features from all engines
        features = self._extract_features(task_view)
        task_view.metadata = features
        
        # Step 3: Try macros first (fastest)
        trace = self._try_macros(task_view)
        if trace.success:
            trace.execution_time = time.time() - start_time
            self.stats['macro_solves'] += 1
            self.stats['tasks_solved'] += 1
            return trace
        
        # Step 4: Try single-engine solutions
        trace = self._try_single_engines(task_view)
        if trace.success:
            trace.execution_time = time.time() - start_time
            self.stats['single_engine_solves'] += 1
            self.stats['tasks_solved'] += 1
            return trace
        
        # Step 5: Try 2-step compositions
        trace = self._try_compositions(task_view, max_depth=2)
        if trace.success:
            trace.execution_time = time.time() - start_time
            self.stats['composition_solves'] += 1
            self.stats['tasks_solved'] += 1
            return trace
        
        # Step 6: Try 3-step compositions (beam search)
        if (time.time() - start_time) < self.timeout:
            trace = self._try_compositions(task_view, max_depth=3)
            if trace.success:
                trace.execution_time = time.time() - start_time
                self.stats['composition_solves'] += 1
                self.stats['tasks_solved'] += 1
                return trace
        
        # Step 7: Give up
        elapsed = time.time() - start_time
        return SolutionTrace(
            task_id=task_id,
            success=False,
            solution=None,
            method="exhausted",
            hypotheses_tried=trace.hypotheses_tried,
            winning_hypothesis=None,
            execution_time=elapsed,
            reasoning=f"Exhausted all strategies in {elapsed:.2f}s. No solution found."
        )
    
    def _parse_task(self, task_data: Dict, task_id: str) -> TaskView:
        """Convert raw task data to TaskView."""
        train_pairs = []
        for example in task_data['train']:
            input_grid = np.array(example['input'])
            output_grid = np.array(example['output'])
            train_pairs.append((input_grid, output_grid))
        
        test_input = np.array(task_data['test'][0]['input'])
        
        return TaskView(
            train_pairs=train_pairs,
            test_input=test_input,
            task_id=task_id,
            metadata={}
        )
    
    def _extract_features(self, task_view: TaskView) -> Dict[str, Any]:
        """
        Call all engines to extract features.
        
        Returns:
            Combined feature dictionary with engine namespaces
        """
        features = {}
        for name, engine in self.engines.items():
            # Extract features from first training pair as proxy
            if task_view.train_pairs:
                input_grid = task_view.train_pairs[0][0]
                features[name] = engine.extract_features(input_grid)
        return features
    
    def _try_macros(self, task_view: TaskView) -> SolutionTrace:
        """
        Try macro-based solutions (replay known programs).
        
        TODO: Implement k-NN over training macro library
        """
        return SolutionTrace(
            task_id=task_view.task_id,
            success=False,
            solution=None,
            method="macro",
            hypotheses_tried=[],
            winning_hypothesis=None,
            execution_time=0.0,
            reasoning="Macro library not yet implemented"
        )
    
    def _try_single_engines(self, task_view: TaskView) -> SolutionTrace:
        """
        Try each engine independently.
        
        Strategy:
        - Ask each engine for hypotheses
        - Sort by confidence
        - Try top hypothesis from each engine
        - Return first that works on all training examples
        """
        all_hypotheses = []
        
        # Collect hypotheses from all engines
        for name, engine in self.engines.items():
            try:
                hypotheses = engine.analyze(task_view)
                all_hypotheses.extend(hypotheses)
            except Exception as e:
                # Engine failed, skip it
                continue
        
        # Sort by confidence
        all_hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        # Try each hypothesis
        for hyp in all_hypotheses:
            if self._test_hypothesis(hyp, task_view):
                return SolutionTrace(
                    task_id=task_view.task_id,
                    success=True,
                    solution=self._execute_hypothesis(hyp, task_view.test_input),
                    method="single-engine",
                    hypotheses_tried=all_hypotheses,
                    winning_hypothesis=hyp,
                    execution_time=0.0,
                    reasoning=f"Solved by {hyp.engine_name}: {hyp.explanation}"
                )
        
        return SolutionTrace(
            task_id=task_view.task_id,
            success=False,
            solution=None,
            method="single-engine",
            hypotheses_tried=all_hypotheses,
            winning_hypothesis=None,
            execution_time=0.0,
            reasoning=f"Tried {len(all_hypotheses)} single-engine hypotheses, none worked"
        )
    
    def _try_compositions(self, task_view: TaskView, max_depth: int = 2) -> SolutionTrace:
        """
        Try multi-step compositions.
        
        TODO: Implement composition search
        """
        return SolutionTrace(
            task_id=task_view.task_id,
            success=False,
            solution=None,
            method=f"composition-{max_depth}",
            hypotheses_tried=[],
            winning_hypothesis=None,
            execution_time=0.0,
            reasoning="Composition search not yet implemented"
        )
    
    def _test_hypothesis(self, hypothesis: Hypothesis, task_view: TaskView) -> bool:
        """
        Test if hypothesis works on all training examples.
        """
        for input_grid, expected_output in task_view.train_pairs:
            try:
                actual_output = self._execute_hypothesis(hypothesis, input_grid)
                if not np.array_equal(actual_output, expected_output):
                    return False
            except Exception:
                return False
        return True
    
    def _execute_hypothesis(self, hypothesis: Hypothesis, test_input: np.ndarray) -> np.ndarray:
        """
        Execute hypothesis on test input.
        
        Minimal DSL interpreter for GEO operations.
        """
        op = hypothesis.operation
        params = hypothesis.params
        
        # GEO operations
        if op == "ROTATE":
            k = params.get('k', 1)
            return np.rot90(test_input, k=k)
        
        elif op == "FLIP":
            axis = params.get('axis', 0)
            return np.flip(test_input, axis=axis)
        
        elif op == "TRANSLATE":
            dy = params.get('dy', 0)
            dx = params.get('dx', 0)
            return np.roll(test_input, shift=(dy, dx), axis=(0, 1))
        
        elif op == "CROP":
            # Extract crop coordinates from DSL: GEO:CROP(r1,c1,r2,c2)
            coords_str = dsl.split('(')[1].rstrip(')')
            coords = [int(x) for x in coords_str.split(',')]
            if len(coords) == 4:
                r1, c1, r2, c2 = coords
                return test_input[r1:r2, c1:c2]
            else:
                return test_input  # Fallback if coords not provided
        
        elif op == "SCALE":
            factor = params.get('factor', 1)
            return np.repeat(np.repeat(test_input, factor, axis=0), factor, axis=1)
        
        elif op == "TRANSPOSE":
            return test_input.T
        
        # COLOR operations
        elif op == "MAPPING":
            mapping = params.get('mapping', {})
            output = test_input.copy()
            for i in range(output.shape[0]):
                for j in range(output.shape[1]):
                    color = int(output[i, j])
                    output[i, j] = mapping.get(color, color)
            return output
        
        elif op == "POSITION_RECOLOR":
            pattern = params.get('pattern')
            color = params.get('color')
            output = test_input.copy()
            
            if pattern == "diagonal":
                h, w = output.shape
                for i in range(h):
                    for j in range(w):
                        if i == j or i + j == h - 1:
                            output[i, j] = color
            
            return output
        
        elif op == "FREQUENCY_RECOLOR":
            from collections import Counter
            mode = params.get('mode')
            target = params.get('target')
            
            # Find most/least common color
            colors = test_input.flatten()
            color_counts = Counter(int(c) for c in colors if c != 0)
            
            if not color_counts:
                return test_input
            
            if mode == "most_common":
                source_color = color_counts.most_common(1)[0][0]
            elif mode == "least_common":
                source_color = color_counts.most_common()[-1][0]
            else:
                return test_input
            
            # Recolor
            output = test_input.copy()
            output[output == source_color] = target
            return output
        
        # COLOR Phase 2 operations
        elif op == "EDGE_RECOLOR":
            color = params.get('color')
            thickness = params.get('thickness', 1)
            output = test_input.copy()
            h, w = output.shape
            
            for i in range(h):
                for j in range(w):
                    if i < thickness or i >= h-thickness or j < thickness or j >= w-thickness:
                        output[i, j] = color
            
            return output
        
        elif op == "BORDER_FRAME":
            color = params.get('color')
            thickness = params.get('thickness', 2)
            output = test_input.copy()
            h, w = output.shape
            
            for i in range(h):
                for j in range(w):
                    if i < thickness or i >= h-thickness or j < thickness or j >= w-thickness:
                        output[i, j] = color
            
            return output
        
        elif op == "CHECKERBOARD":
            even_color = params.get('even_color')
            odd_color = params.get('odd_color')
            output = np.zeros_like(test_input)
            h, w = output.shape
            
            for i in range(h):
                for j in range(w):
                    parity = (i + j) % 2
                    output[i, j] = even_color if parity == 0 else odd_color
            
            return output
        
        elif op == "MODULAR":
            axis = params.get('axis')
            modulus = params.get('modulus')
            colors = params.get('colors', [])
            output = np.zeros_like(test_input)
            h, w = output.shape
            
            for i in range(h):
                for j in range(w):
                    mod_val = (i if axis == 'row' else j) % modulus
                    output[i, j] = colors[mod_val] if mod_val < len(colors) else 0
            
            return output
        
        elif op == "ADJACENCY":
            adjacent_to = params.get('adjacent_to')
            recolor_to = params.get('recolor_to')
            output = test_input.copy()
            h, w = output.shape
            
            for i in range(h):
                for j in range(w):
                    # Check if adjacent to target color
                    is_adjacent = False
                    for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
                        ni, nj = i+di, j+dj
                        if 0 <= ni < h and 0 <= nj < w:
                            if int(test_input[ni, nj]) == adjacent_to:
                                is_adjacent = True
                                break
                    
                    if is_adjacent:
                        output[i, j] = recolor_to
            
            return output
        
        elif op == "STRUCTURAL":
            interior_color = params.get('interior')
            perimeter_color = params.get('perimeter')
            output = test_input.copy()
            h, w = output.shape
            
            # Find non-zero mask
            mask = test_input != 0
            
            for i in range(h):
                for j in range(w):
                    if not mask[i, j]:
                        continue
                    
                    # Check if perimeter
                    is_perimeter = False
                    for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
                        ni, nj = i+di, j+dj
                        if ni < 0 or ni >= h or nj < 0 or nj >= w or not mask[ni, nj]:
                            is_perimeter = True
                            break
                    
                    output[i, j] = perimeter_color if is_perimeter else interior_color
            
            return output
        
        # COMP operations
        elif op == "BBOX_CROP":
            # Crop to bounding box of non-zero pixels
            nonzero = np.argwhere(test_input != 0)
            if len(nonzero) == 0:
                return test_input
            
            r_min, c_min = nonzero.min(axis=0)
            r_max, c_max = nonzero.max(axis=0)
            
            return test_input[r_min:r_max+1, c_min:c_max+1]
        
        elif op == "LARGEST_OBJECT":
            from scipy.ndimage import label
            
            # Find largest connected component
            labeled, num_features = label(test_input != 0)
            
            if num_features == 0:
                return test_input
            
            # Find largest
            largest_size = 0
            largest_label = 0
            
            for i in range(1, num_features + 1):
                size = np.sum(labeled == i)
                if size > largest_size:
                    largest_size = size
                    largest_label = i
            
            # Extract largest
            largest_mask = (labeled == largest_label)
            coords = np.argwhere(largest_mask)
            
            if len(coords) == 0:
                return test_input
            
            r_min, c_min = coords.min(axis=0)
            r_max, c_max = coords.max(axis=0)
            
            return test_input[r_min:r_max+1, c_min:c_max+1]
        
        # PATTERN operations
        elif op == "TILE":
            n_rows = params.get('n_rows', 1)
            n_cols = params.get('n_cols', 1)
            return np.tile(test_input, (n_rows, n_cols))
        
        elif op == "PERIODIC_RECOLOR":
            period_h = params.get('period_h', 1)
            period_w = params.get('period_w', 1)
            
            # Extract tile from input (top-left corner)
            tile = test_input[:period_h, :period_w].copy()
            
            h, w = test_input.shape
            output = np.zeros((h, w), dtype=test_input.dtype)
            
            # Apply periodic tiling pattern
            for i in range(h):
                for j in range(w):
                    output[i, j] = tile[i % period_h, j % period_w]
            
            return output
        
        elif op == "ROW_STRIPE":
            period = params.get('period', 2)
            color = params.get('color', 0)
            output = test_input.copy()
            
            for i in range(0, output.shape[0], period):
                output[i, :] = color
            
            return output
        
        elif op == "FRAGMENT_TILE":
            n_rows = params.get('n_rows', 1)
            n_cols = params.get('n_cols', 1)
            return np.tile(test_input, (n_rows, n_cols))
        
        # REL operations
        elif op == "TO_CORNERS":
            # Stub - complex logic needed
            return test_input
        
        # COUNT operations
        elif op == "MOST_FREQUENT_FILL":
            from collections import Counter
            colors = test_input.flatten()
            color_counts = Counter(int(c) for c in colors if c != 0)
            
            if not color_counts:
                return test_input
            
            most_common = color_counts.most_common(1)[0][0]
            return np.full_like(test_input, most_common)
        
        elif op == "COUNT_TILE":
            from scipy.ndimage import label
            labeled, num_objects = label(test_input != 0)
            
            if num_objects == 0:
                return test_input
            
            # Tile horizontally num_objects times
            return np.tile(test_input, (1, num_objects))
        
        # SHAPE operations
        elif op == "SOLID_TO_OUTLINE":
            from scipy.ndimage import label
            output = test_input.copy()
            labeled, num_features = label(test_input != 0)
            
            for comp_id in range(1, num_features + 1):
                mask = (labeled == comp_id)
                coords = np.argwhere(mask)
                
                if len(coords) == 0:
                    continue
                
                y0, x0 = coords.min(axis=0)
                y1, x1 = coords.max(axis=0)
                
                # Check if it's a solid rectangle
                sub_mask = mask[y0:y1+1, x0:x1+1]
                h, w = sub_mask.shape
                
                if np.count_nonzero(sub_mask) == h * w and h > 1 and w > 1:
                    # Convert to outline
                    color = int(test_input[mask][0])
                    output[y0+1:y1, x0+1:x1] = 0
            
            return output
        
        elif op == "OUTLINE_TO_SOLID":
            from scipy.ndimage import label
            output = test_input.copy()
            labeled, num_features = label(test_input != 0)
            
            for comp_id in range(1, num_features + 1):
                mask = (labeled == comp_id)
                coords = np.argwhere(mask)
                
                if len(coords) == 0:
                    continue
                
                y0, x0 = coords.min(axis=0)
                y1, x1 = coords.max(axis=0)
                
                # Check if it's an outline rectangle
                sub_mask = mask[y0:y1+1, x0:x1+1]
                h, w = sub_mask.shape
                
                if h > 2 and w > 2:
                    border_mask = np.zeros_like(sub_mask, dtype=bool)
                    border_mask[0, :] = True
                    border_mask[-1, :] = True
                    border_mask[:, 0] = True
                    border_mask[:, -1] = True
                    interior_mask = ~border_mask
                    
                    if np.all(sub_mask[border_mask]) and np.count_nonzero(sub_mask[interior_mask]) == 0:
                        # Fill interior
                        color = int(test_input[mask][0])
                        output[y0:y1+1, x0:x1+1] = color
            
            return output
        
        elif op == "FRAME_INTERIOR":
            # Preserve frame, clear interior
            h, w = test_input.shape
            output = test_input.copy()
            
            if h > 2 and w > 2:
                output[1:h-1, 1:w-1] = 0
            
            return output
        
        elif op == "RECOLOR_LINES":
            # For now, just return input (needs more sophisticated detection)
            return test_input
        
        # REL operations
        elif op == "MOVE_TO_CORNER":
            from scipy.ndimage import label
            corner = params.get('corner', 'TL')
            
            # Find largest object
            labeled, num_features = label(test_input != 0)
            if num_features == 0:
                return test_input
            
            # Get largest object
            largest_size = 0
            largest_id = 0
            for obj_id in range(1, num_features + 1):
                size = np.sum(labeled == obj_id)
                if size > largest_size:
                    largest_size = size
                    largest_id = obj_id
            
            if largest_id == 0:
                return test_input
            
            # Extract object
            obj_mask = (labeled == largest_id)
            coords = np.argwhere(obj_mask)
            y0, x0 = coords.min(axis=0)
            y1, x1 = coords.max(axis=0)
            
            obj_h = y1 - y0 + 1
            obj_w = x1 - x0 + 1
            obj_data = test_input[y0:y1+1, x0:x1+1].copy()
            obj_mask_sub = obj_mask[y0:y1+1, x0:x1+1]
            
            # Determine target position
            h, w = test_input.shape
            if corner == 'TL':
                target_y, target_x = 0, 0
            elif corner == 'TR':
                target_y, target_x = 0, w - obj_w
            elif corner == 'BL':
                target_y, target_x = h - obj_h, 0
            elif corner == 'BR':
                target_y, target_x = h - obj_h, w - obj_w
            else:
                return test_input
            
            # Create output
            output = np.zeros_like(test_input)
            
            # Place object at target
            for i in range(obj_h):
                for j in range(obj_w):
                    if obj_mask_sub[i, j]:
                        if 0 <= target_y + i < h and 0 <= target_x + j < w:
                            output[target_y + i, target_x + j] = obj_data[i, j]
            
            return output
        
        elif op == "ALIGN_TO_OBJECT":
            from scipy.ndimage import label
            axis = params.get('axis', 'row')
            
            # Find objects
            labeled, num_features = label(test_input != 0)
            if num_features < 2:
                return test_input
            
            # Get largest (anchor) and second largest (target)
            sizes = [(i, np.sum(labeled == i)) for i in range(1, num_features + 1)]
            sizes.sort(key=lambda x: x[1], reverse=True)
            
            anchor_id = sizes[0][0]
            target_id = sizes[1][0]
            
            # Get anchor center
            anchor_coords = np.argwhere(labeled == anchor_id)
            anchor_cy = anchor_coords[:, 0].mean()
            anchor_cx = anchor_coords[:, 1].mean()
            
            # Get target object
            target_mask = (labeled == target_id)
            target_coords = np.argwhere(target_mask)
            target_cy = target_coords[:, 0].mean()
            target_cx = target_coords[:, 1].mean()
            
            y0, x0 = target_coords.min(axis=0)
            y1, x1 = target_coords.max(axis=0)
            target_h = y1 - y0 + 1
            target_w = x1 - x0 + 1
            
            # Calculate shift
            if axis == 'row':
                shift_y = int(anchor_cy - target_cy)
                shift_x = 0
            else:  # col
                shift_y = 0
                shift_x = int(anchor_cx - target_cx)
            
            # Create output (preserve anchor, move target)
            output = test_input.copy()
            
            # Clear old target position
            output[target_mask] = 0
            
            # Place target at new position
            new_y0 = y0 + shift_y
            new_x0 = x0 + shift_x
            
            h, w = test_input.shape
            for i in range(target_h):
                for j in range(target_w):
                    old_i = y0 + i
                    old_j = x0 + j
                    new_i = new_y0 + i
                    new_j = new_x0 + j
                    
                    if target_mask[old_i, old_j]:
                        if 0 <= new_i < h and 0 <= new_j < w:
                            output[new_i, new_j] = test_input[old_i, old_j]
            
            return output
        
        elif op == "MIRROR":
            from scipy.ndimage import label
            axis = params.get('axis', 'V')
            
            h, w = test_input.shape
            output = np.zeros_like(test_input)
            
            # Find objects
            labeled, num_features = label(test_input != 0)
            
            for obj_id in range(1, num_features + 1):
                obj_mask = (labeled == obj_id)
                coords = np.argwhere(obj_mask)
                
                # Get center
                cy = coords[:, 0].mean()
                cx = coords[:, 1].mean()
                
                # Calculate mirrored center
                if axis == 'V':
                    new_cy = cy
                    new_cx = w - 1 - cx
                elif axis == 'H':
                    new_cy = h - 1 - cy
                    new_cx = cx
                else:  # BOTH
                    new_cy = h - 1 - cy
                    new_cx = w - 1 - cx
                
                # Calculate shift
                shift_y = int(new_cy - cy)
                shift_x = int(new_cx - cx)
                
                # Place mirrored object
                for coord in coords:
                    old_y, old_x = coord
                    new_y = old_y + shift_y
                    new_x = old_x + shift_x
                    
                    if 0 <= new_y < h and 0 <= new_x < w:
                        output[new_y, new_x] = test_input[old_y, old_x]
            
            return output
        
        # Add more operations as engines are implemented
        
        # Unknown operation
        return test_input
    
    def get_statistics(self) -> Dict[str, Any]:
        """Return solving statistics."""
        return self.stats.copy()
    
    def __repr__(self):
        return f"<ArcCore engines={len(self.engines)} macros={len(self.training_macros)}>"
