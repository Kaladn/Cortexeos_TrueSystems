"""
Stub engines - Minimal implementations to make ARC-CORE run.

These will be expanded into full engines later.
For now, they return empty hypothesis lists.
"""

from typing import List, Dict, Any
import numpy as np

from engines.base_engine import BaseEngine, Hypothesis, TaskView


class ColorEngine(BaseEngine):
    """
    Color transformation engine.
    
    Detects and applies color-based transformations:
    1. Direct mapping (color A → color B)
    2. Position-based recoloring (diagonal, edges, corners)
    3. Frequency-based recoloring (most/least common)
    4. Adjacency-based recoloring
    """
    def __init__(self):
        super().__init__(name="COLOR")
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        """Analyze task for color transformations."""
        hypotheses = []
        
        # Phase 1 - Simple patterns
        mapping_hyp = self._detect_color_mapping(task_view)
        if mapping_hyp:
            hypotheses.append(mapping_hyp)
        
        position_hyp = self._detect_position_recolor(task_view)
        if position_hyp:
            hypotheses.append(position_hyp)
        
        freq_hyp = self._detect_frequency_recolor(task_view)
        if freq_hyp:
            hypotheses.append(freq_hyp)
        
        # Phase 2 - Structural/positional patterns
        edge_hyp = self._detect_edge_recolor(task_view)
        if edge_hyp:
            hypotheses.append(edge_hyp)
        
        border_hyp = self._detect_border_frame_recolor(task_view)
        if border_hyp:
            hypotheses.append(border_hyp)
        
        checker_hyp = self._detect_checkerboard_recolor(task_view)
        if checker_hyp:
            hypotheses.append(checker_hyp)
        
        modular_hyp = self._detect_modular_recolor(task_view)
        if modular_hyp:
            hypotheses.append(modular_hyp)
        
        adjacency_hyp = self._detect_conditional_adjacency_recolor(task_view)
        if adjacency_hyp:
            hypotheses.append(adjacency_hyp)
        
        structural_hyp = self._detect_structural_recolor(task_view)
        if structural_hyp:
            hypotheses.append(structural_hyp)
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        return hypotheses
    
    def _detect_color_mapping(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is input with consistent color mapping."""
        # Build color mapping from first pair
        first_input, first_output = task_view.train_pairs[0]
        
        if first_input.shape != first_output.shape:
            return None
        
        # Extract all color mappings from first pair
        mapping = {}
        for i in range(first_input.shape[0]):
            for j in range(first_input.shape[1]):
                in_color = int(first_input[i, j])
                out_color = int(first_output[i, j])
                
                if in_color in mapping:
                    if mapping[in_color] != out_color:
                        # Inconsistent mapping in first pair
                        return None
                else:
                    mapping[in_color] = out_color
        
        # Check if mapping is identity (no change)
        if all(k == v for k, v in mapping.items()):
            return None
        
        # Verify mapping works on ALL training pairs
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
            
            for i in range(input_grid.shape[0]):
                for j in range(input_grid.shape[1]):
                    in_color = int(input_grid[i, j])
                    expected_out = mapping.get(in_color, in_color)
                    actual_out = int(output_grid[i, j])
                    
                    if expected_out != actual_out:
                        return None
        
        # Build DSL representation
        mapping_str = ",".join(f"{k}→{v}" for k, v in sorted(mapping.items()) if k != v)
        
        return Hypothesis(
            engine_name="COLOR",
            operation="MAPPING",
            params={"mapping": mapping},
            confidence=1.0,
            dsl_program=f"COLOR:MAPPING({mapping_str})",
            explanation=f"Map colors: {mapping_str}"
        )
    
    def _detect_position_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect position-based recoloring (e.g., diagonal, edges, corners)."""
        # Check for same shape
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Try diagonal pattern (main + anti-diagonal)
        all_match_diagonal = True
        target_color = None
        
        for input_grid, output_grid in task_view.train_pairs:
            h, w = input_grid.shape
            
            for i in range(h):
                for j in range(w):
                    on_diagonal = (i == j) or (i + j == h - 1)
                    
                    if on_diagonal:
                        # On diagonal - should be recolored
                        out_color = int(output_grid[i, j])
                        if target_color is None:
                            target_color = out_color
                        elif out_color != target_color:
                            all_match_diagonal = False
                    else:
                        # Off diagonal - should match input
                        if int(output_grid[i, j]) != int(input_grid[i, j]):
                            all_match_diagonal = False
        
        if all_match_diagonal and target_color is not None:
            return Hypothesis(
                engine_name="COLOR",
                operation="POSITION_RECOLOR",
                params={"pattern": "diagonal", "color": target_color},
                confidence=0.9,
                dsl_program=f"COLOR:DIAGONAL({target_color})",
                explanation=f"Recolor diagonals to {target_color}"
            )
        
        return None
    
    def _detect_frequency_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect frequency-based recoloring (most/least common color)."""
        from collections import Counter
        
        # Check if shape preserved
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Try: recolor most common to specific color
        all_match = True
        target_color = None
        
        for input_grid, output_grid in task_view.train_pairs:
            # Find most common non-zero color in input
            colors = input_grid.flatten()
            color_counts = Counter(int(c) for c in colors if c != 0)
            
            if not color_counts:
                continue
            
            most_common = color_counts.most_common(1)[0][0]
            
            # Check if most common color is changed consistently
            for i in range(input_grid.shape[0]):
                for j in range(input_grid.shape[1]):
                    if int(input_grid[i, j]) == most_common:
                        out_color = int(output_grid[i, j])
                        if target_color is None:
                            target_color = out_color
                        elif out_color != target_color:
                            all_match = False
                    else:
                        if int(output_grid[i, j]) != int(input_grid[i, j]):
                            all_match = False
    
    def _detect_edge_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect edge/border recoloring patterns."""
        # Check shape preservation
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Try outer edge pattern (1-pixel border)
        edge_color = None
        all_match = True
        
        for input_grid, output_grid in task_view.train_pairs:
            h, w = input_grid.shape
            
            for i in range(h):
                for j in range(w):
                    is_edge = (i == 0 or i == h-1 or j == 0 or j == w-1)
                    
                    if is_edge:
                        out_color = int(output_grid[i, j])
                        if edge_color is None:
                            edge_color = out_color
                        elif out_color != edge_color:
                            all_match = False
                    else:
                        # Interior - should preserve input
                        if int(output_grid[i, j]) != int(input_grid[i, j]):
                            all_match = False
        
        if all_match and edge_color is not None:
            return Hypothesis(
                engine_name="COLOR",
                operation="EDGE_RECOLOR",
                params={"color": edge_color, "thickness": 1},
                confidence=0.95,
                dsl_program=f"COLOR:EDGE({edge_color})",
                explanation=f"Recolor edge border to {edge_color}"
            )
        
        return None
    
    def _detect_border_frame_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect thicker border frame patterns (2+ pixel borders)."""
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Try thickness 2
        for thickness in [2, 3]:
            frame_color = None
            all_match = True
            
            for input_grid, output_grid in task_view.train_pairs:
                h, w = input_grid.shape
                
                if h <= 2*thickness or w <= 2*thickness:
                    all_match = False
                    break
                
                for i in range(h):
                    for j in range(w):
                        in_frame = (i < thickness or i >= h-thickness or 
                                   j < thickness or j >= w-thickness)
                        
                        if in_frame:
                            out_color = int(output_grid[i, j])
                            if frame_color is None:
                                frame_color = out_color
                            elif out_color != frame_color:
                                all_match = False
                        else:
                            if int(output_grid[i, j]) != int(input_grid[i, j]):
                                all_match = False
            
            if all_match and frame_color is not None:
                return Hypothesis(
                    engine_name="COLOR",
                    operation="BORDER_FRAME",
                    params={"color": frame_color, "thickness": thickness},
                    confidence=0.9,
                    dsl_program=f"COLOR:FRAME({frame_color},{thickness})",
                    explanation=f"Recolor {thickness}-pixel frame to {frame_color}"
                )
        
        return None
    
    def _detect_checkerboard_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect checkerboard alternating patterns."""
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Pattern: (row+col)%2 determines color
        colors = [None, None]  # [even, odd]
        all_match = True
        
        for input_grid, output_grid in task_view.train_pairs:
            h, w = input_grid.shape
            
            for i in range(h):
                for j in range(w):
                    parity = (i + j) % 2
                    out_color = int(output_grid[i, j])
                    
                    if colors[parity] is None:
                        colors[parity] = out_color
                    elif colors[parity] != out_color:
                        all_match = False
        
        if all_match and colors[0] is not None and colors[1] is not None and colors[0] != colors[1]:
            return Hypothesis(
                engine_name="COLOR",
                operation="CHECKERBOARD",
                params={"even_color": colors[0], "odd_color": colors[1]},
                confidence=0.95,
                dsl_program=f"COLOR:CHECKER({colors[0]},{colors[1]})",
                explanation=f"Checkerboard pattern: {colors[0]}/{colors[1]}"
            )
        
        return None
    
    def _detect_modular_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect modular arithmetic patterns (row%N, col%N)."""
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Try row%N and col%N for N in [2, 3, 4]
        for modulus in [2, 3, 4]:
            for axis in ['row', 'col']:
                colors = [None] * modulus
                all_match = True
                
                for input_grid, output_grid in task_view.train_pairs:
                    h, w = input_grid.shape
                    
                    for i in range(h):
                        for j in range(w):
                            mod_val = (i if axis == 'row' else j) % modulus
                            out_color = int(output_grid[i, j])
                            
                            if colors[mod_val] is None:
                                colors[mod_val] = out_color
                            elif colors[mod_val] != out_color:
                                all_match = False
                
                # Check if pattern is non-trivial (not all same color)
                if all_match and all(c is not None for c in colors) and len(set(colors)) > 1:
                    color_str = ",".join(str(c) for c in colors)
                    return Hypothesis(
                        engine_name="COLOR",
                        operation="MODULAR",
                        params={"axis": axis, "modulus": modulus, "colors": colors},
                        confidence=0.9,
                        dsl_program=f"COLOR:MOD_{axis.upper()}({modulus}:[{color_str}])",
                        explanation=f"Modular {axis}%{modulus} pattern: {color_str}"
                    )
        
        return None
    
    def _detect_conditional_adjacency_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect adjacency-based conditional recoloring."""
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Pattern: If adjacent to color X, recolor to Y
        # Try to find such X→Y mapping
        adjacency_rules = {}  # {adjacent_color: output_color}
        all_match = True
        
        for input_grid, output_grid in task_view.train_pairs:
            h, w = input_grid.shape
            
            for i in range(h):
                for j in range(w):
                    in_color = int(input_grid[i, j])
                    out_color = int(output_grid[i, j])
                    
                    if in_color != out_color:
                        # Find adjacent colors
                        adjacent = set()
                        for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
                            ni, nj = i+di, j+dj
                            if 0 <= ni < h and 0 <= nj < w:
                                adjacent.add(int(input_grid[ni, nj]))
                        
                        # Check if rule exists
                        for adj_color in adjacent:
                            if adj_color in adjacency_rules:
                                if adjacency_rules[adj_color] != out_color:
                                    all_match = False
                            else:
                                adjacency_rules[adj_color] = out_color
        
        if all_match and len(adjacency_rules) > 0:
            # Take the most common rule
            rule_items = list(adjacency_rules.items())
            if len(rule_items) == 1:
                adj_color, new_color = rule_items[0]
                return Hypothesis(
                    engine_name="COLOR",
                    operation="ADJACENCY",
                    params={"adjacent_to": adj_color, "recolor_to": new_color},
                    confidence=0.85,
                    dsl_program=f"COLOR:ADJACENT({adj_color}→{new_color})",
                    explanation=f"If adjacent to {adj_color}, recolor to {new_color}"
                )
        
        return None
    
    def _detect_structural_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect structural patterns (interior vs perimeter)."""
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Pattern: Interior pixels one color, perimeter pixels another
        interior_color = None
        perimeter_color = None
        all_match = True
        
        for input_grid, output_grid in task_view.train_pairs:
            h, w = input_grid.shape
            
            # Find non-zero regions
            mask = input_grid != 0
            
            for i in range(h):
                for j in range(w):
                    if not mask[i, j]:
                        # Background - preserve
                        if int(output_grid[i, j]) != 0:
                            all_match = False
                        continue
                    
                    # Check if perimeter (adjacent to background)
                    is_perimeter = False
                    for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
                        ni, nj = i+di, j+dj
                        if ni < 0 or ni >= h or nj < 0 or nj >= w or not mask[ni, nj]:
                            is_perimeter = True
                            break
                    
                    out_color = int(output_grid[i, j])
                    
                    if is_perimeter:
                        if perimeter_color is None:
                            perimeter_color = out_color
                        elif perimeter_color != out_color:
                            all_match = False
                    else:
                        if interior_color is None:
                            interior_color = out_color
                        elif interior_color != out_color:
                            all_match = False
        
        if all_match and interior_color is not None and perimeter_color is not None and interior_color != perimeter_color:
            return Hypothesis(
                engine_name="COLOR",
                operation="STRUCTURAL",
                params={"interior": interior_color, "perimeter": perimeter_color},
                confidence=0.85,
                dsl_program=f"COLOR:STRUCT(i:{interior_color},p:{perimeter_color})",
                explanation=f"Interior→{interior_color}, Perimeter→{perimeter_color}"
            )
        
        return None
        
        if all_match and target_color is not None:
            return Hypothesis(
                engine_name="COLOR",
                operation="FREQUENCY_RECOLOR",
                params={"mode": "most_common", "target": target_color},
                confidence=0.8,
                dsl_program=f"COLOR:MOST_COMMON→{target_color}",
                explanation=f"Recolor most common to {target_color}"
            )
        
        return None


class CompEngine(BaseEngine):
    """
    Component/blob detection engine.
    
    Detects connected components and applies transformations:
    1. Crop to bounding box (largest object, all objects)
    2. Object filtering (by size, color, position)
    3. Object extraction and placement
    4. Multi-object operations
    """
    def __init__(self):
        super().__init__(name="COMP")
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        """Analyze task for component-based transformations."""
        hypotheses = []
        
        # Check for bounding box crop
        bbox_hyp = self._detect_bbox_crop(task_view)
        if bbox_hyp:
            hypotheses.append(bbox_hyp)
        
        # Check for largest object extraction
        largest_hyp = self._detect_largest_object(task_view)
        if largest_hyp:
            hypotheses.append(largest_hyp)
        
        # Check for object count preservation
        count_hyp = self._detect_object_count(task_view)
        if count_hyp:
            hypotheses.append(count_hyp)
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        return hypotheses
    
    def _detect_bbox_crop(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is cropped to bounding box of non-zero pixels."""
        from scipy.ndimage import label
        
        for input_grid, output_grid in task_view.train_pairs:
            # Find bounding box of all non-zero pixels
            nonzero = np.argwhere(input_grid != 0)
            if len(nonzero) == 0:
                return None
            
            r_min, c_min = nonzero.min(axis=0)
            r_max, c_max = nonzero.max(axis=0)
            
            # Check if output matches this crop
            expected = input_grid[r_min:r_max+1, c_min:c_max+1]
            
            if not np.array_equal(expected, output_grid):
                return None
        
        return Hypothesis(
            engine_name="COMP",
            operation="BBOX_CROP",
            params={"target": "all_nonzero"},
            confidence=0.95,
            dsl_program="COMP:BBOX_CROP(all)",
            explanation="Crop to bounding box of all non-zero pixels"
        )
    
    def _detect_largest_object(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is the largest connected component."""
        from scipy.ndimage import label
        
        for input_grid, output_grid in task_view.train_pairs:
            # Find connected components
            labeled, num_features = label(input_grid != 0)
            
            if num_features == 0:
                return None
            
            # Find largest component
            largest_size = 0
            largest_label = 0
            
            for i in range(1, num_features + 1):
                size = np.sum(labeled == i)
                if size > largest_size:
                    largest_size = size
                    largest_label = i
            
            # Extract largest component
            largest_mask = (labeled == largest_label)
            
            # Get bounding box of largest
            coords = np.argwhere(largest_mask)
            if len(coords) == 0:
                return None
            
            r_min, c_min = coords.min(axis=0)
            r_max, c_max = coords.max(axis=0)
            
            expected = input_grid[r_min:r_max+1, c_min:c_max+1]
            
            if not np.array_equal(expected, output_grid):
                return None
        
        return Hypothesis(
            engine_name="COMP",
            operation="LARGEST_OBJECT",
            params={"extract": "largest"},
            confidence=0.9,
            dsl_program="COMP:LARGEST_OBJECT()",
            explanation="Extract largest connected component"
        )
    
    def _detect_object_count(self, task_view: TaskView) -> Hypothesis:
        """Detect if transformation preserves object count."""
        from scipy.ndimage import label
        
        # Check if all pairs have same object count in input and output
        for input_grid, output_grid in task_view.train_pairs:
            labeled_in, num_in = label(input_grid != 0)
            labeled_out, num_out = label(output_grid != 0)
            
            if num_in != num_out:
                return None
        
        # This is a weak hypothesis - just confirms objects are preserved
        return None  # Too generic to be useful


class PatternEngine(BaseEngine):
    """
    Pattern detection engine.
    
    Detects:
    1. Global tiling (input → tile repeated NxM times)
    2. Stripes (row/column periodicity)
    3. Fragment → tile (input is fragment, output is full tile)
    4. Symmetry completion
    """
    def __init__(self):
        super().__init__(name="PATTERN")
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        """Analyze task for pattern/tiling transformations."""
        hypotheses = []
        
        # Check for periodic recoloring (tiling pattern in output)
        periodic_hyp = self._detect_periodic_recolor(task_view)
        if periodic_hyp:
            hypotheses.append(periodic_hyp)
        
        # Check for global tiling
        tiling_hyp = self._detect_global_tiling(task_view)
        if tiling_hyp:
            hypotheses.append(tiling_hyp)
        
        # Check for stripe patterns
        stripe_hyp = self._detect_stripes(task_view)
        if stripe_hyp:
            hypotheses.append(stripe_hyp)
        
        # Check for fragment tiling
        fragment_hyp = self._detect_fragment_tiling(task_view)
        if fragment_hyp:
            hypotheses.append(fragment_hyp)
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        
        return hypotheses
    
    def _detect_periodic_recolor(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is periodic tiling derived from input fragment."""
        # Try periods from 1 to 4
        for period_h in [1, 2, 3, 4]:
            for period_w in [1, 2, 3, 4]:
                if period_h == 1 and period_w == 1:
                    continue
                
                all_pairs_match = True
                
                for input_grid, output_grid in task_view.train_pairs:
                    h_out, w_out = output_grid.shape
                    h_in, w_in = input_grid.shape
                    
                    # Check if output is periodic with this tile size
                    if h_out < period_h or w_out < period_w:
                        all_pairs_match = False
                        break
                    
                    # Check if input has the tile in top-left corner
                    if h_in < period_h or w_in < period_w:
                        all_pairs_match = False
                        break
                    
                    # Extract tile from input (top-left corner)
                    input_tile = input_grid[:period_h, :period_w].copy()
                    
                    # Check if input tile is non-zero
                    if np.all(input_tile == 0):
                        all_pairs_match = False
                        break
                    
                    # Verify output matches this tile tiled periodically
                    is_periodic = True
                    for i in range(h_out):
                        for j in range(w_out):
                            expected = input_tile[i % period_h, j % period_w]
                            if output_grid[i, j] != expected:
                                is_periodic = False
                                break
                        if not is_periodic:
                            break
                    
                    if not is_periodic:
                        all_pairs_match = False
                        break
                
                # If ALL pairs follow this pattern
                if all_pairs_match:
                    return Hypothesis(
                        engine_name="PATTERN",
                        operation="PERIODIC_RECOLOR",
                        params={
                            "period_h": period_h,
                            "period_w": period_w
                        },
                        confidence=0.95,
                        dsl_program=f"PATTERN:PERIODIC({period_h}x{period_w})",
                        explanation=f"Tile input fragment {period_h}×{period_w} periodically"
                    )
        
        return None
    
    def _detect_global_tiling(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is input tiled NxM times."""
        for input_grid, output_grid in task_view.train_pairs:
            h_in, w_in = input_grid.shape
            h_out, w_out = output_grid.shape
            
            # Check if output is multiple of input
            if h_out % h_in != 0 or w_out % w_in != 0:
                return None
            
            n_rows = h_out // h_in
            n_cols = w_out // w_in
            
            # Verify tiling
            for i in range(n_rows):
                for j in range(n_cols):
                    tile = output_grid[i*h_in:(i+1)*h_in, j*w_in:(j+1)*w_in]
                    if not np.array_equal(tile, input_grid):
                        return None
        
        # All pairs match - extract tile dimensions from first pair
        first_in, first_out = task_view.train_pairs[0]
        n_rows = first_out.shape[0] // first_in.shape[0]
        n_cols = first_out.shape[1] // first_in.shape[1]
        
        return Hypothesis(
            engine_name="PATTERN",
            operation="TILE",
            params={"n_rows": n_rows, "n_cols": n_cols},
            confidence=1.0,
            dsl_program=f"PATTERN:TILE({n_rows},{n_cols})",
            explanation=f"Tile input {n_rows}×{n_cols} times"
        )
    
    def _detect_stripes(self, task_view: TaskView) -> Hypothesis:
        """Detect stripe patterns (row/column periodicity)."""
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
        
        # Check for row stripes (every Nth row same color)
        for period in [2, 3, 4]:
            all_match = True
            stripe_color = None
            
            for input_grid, output_grid in task_view.train_pairs:
                h, w = output_grid.shape
                
                # Check if every period-th row is uniform
                for i in range(0, h, period):
                    row = output_grid[i, :]
                    if not np.all(row == row[0]):
                        all_match = False
                        break
                    
                    if stripe_color is None:
                        stripe_color = int(row[0])
                    elif int(row[0]) != stripe_color:
                        all_match = False
                        break
                
                if not all_match:
                    break
            
            if all_match and stripe_color is not None:
                return Hypothesis(
                    engine_name="PATTERN",
                    operation="ROW_STRIPE",
                    params={"period": period, "color": stripe_color},
                    confidence=0.85,
                    dsl_program=f"PATTERN:ROW_STRIPE({period},{stripe_color})",
                    explanation=f"Row stripes every {period} rows with color {stripe_color}"
                )
        
        return None
    
    def _detect_fragment_tiling(self, task_view: TaskView) -> Hypothesis:
        """Detect if input is fragment and output is tiled version."""
        # This is similar to global tiling but checks if input is partial
        for input_grid, output_grid in task_view.train_pairs:
            h_in, w_in = input_grid.shape
            h_out, w_out = output_grid.shape
            
            # Output should be larger
            if h_out <= h_in or w_out <= w_in:
                return None
            
            # Check if output contains input at top-left
            if not np.array_equal(output_grid[:h_in, :w_in], input_grid):
                return None
            
            # Check if output is periodic extension
            all_periodic = True
            for i in range(0, h_out, h_in):
                for j in range(0, w_out, w_in):
                    i_end = min(i + h_in, h_out)
                    j_end = min(j + w_in, w_out)
                    
                    expected_h = i_end - i
                    expected_w = j_end - j
                    
                    tile = output_grid[i:i_end, j:j_end]
                    fragment = input_grid[:expected_h, :expected_w]
                    
                    if not np.array_equal(tile, fragment):
                        all_periodic = False
                        break
                if not all_periodic:
                    break
            
            if not all_periodic:
                return None
        
        # Calculate tiling factor from first pair
        first_in, first_out = task_view.train_pairs[0]
        n_rows = (first_out.shape[0] + first_in.shape[0] - 1) // first_in.shape[0]
        n_cols = (first_out.shape[1] + first_in.shape[1] - 1) // first_in.shape[1]
        
        return Hypothesis(
            engine_name="PATTERN",
            operation="FRAGMENT_TILE",
            params={"n_rows": n_rows, "n_cols": n_cols},
            confidence=0.9,
            dsl_program=f"PATTERN:FRAGMENT_TILE({n_rows},{n_cols})",
            explanation=f"Fragment tiled {n_rows}×{n_cols}"
        )


class ShapeEngine(BaseEngine):
    """Stub: Shape/outline/morphology engine."""
    def __init__(self):
        super().__init__(name="SHAPE")
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        return []


class CountEngine(BaseEngine):
    """
    Counting/numeric reasoning engine.
    
    Detects:
    1. Most frequent color selection
    2. Object count → repetition
    3. Size-based selection
    """
    def __init__(self):
        super().__init__(name="COUNT")
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        """Analyze for count-based transformations."""
        hypotheses = []
        
        # Check for most frequent color
        freq_hyp = self._detect_most_frequent_color(task_view)
        if freq_hyp:
            hypotheses.append(freq_hyp)
        
        # Check for object count repetition
        count_hyp = self._detect_count_repetition(task_view)
        if count_hyp:
            hypotheses.append(count_hyp)
        
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        return hypotheses
    
    def _detect_most_frequent_color(self, task_view: TaskView) -> Hypothesis:
        """Detect if output is filled with most frequent color."""
        from collections import Counter
        
        for input_grid, output_grid in task_view.train_pairs:
            # Count colors in input (excluding 0)
            colors = input_grid.flatten()
            color_counts = Counter(int(c) for c in colors if c != 0)
            
            if not color_counts:
                return None
            
            most_common = color_counts.most_common(1)[0][0]
            
            # Check if output is uniformly this color
            if not np.all(output_grid == most_common):
                return None
        
        return Hypothesis(
            engine_name="COUNT",
            operation="MOST_FREQUENT_FILL",
            params={},
            confidence=0.85,
            dsl_program="COUNT:MOST_FREQUENT_FILL()",
            explanation="Fill with most frequent color"
        )
    
    def _detect_count_repetition(self, task_view: TaskView) -> Hypothesis:
        """Detect if repetition count matches object count."""
        from scipy.ndimage import label
        
        for input_grid, output_grid in task_view.train_pairs:
            # Count objects in input
            labeled, num_objects = label(input_grid != 0)
            
            if num_objects == 0:
                return None
            
            # Check if output is input tiled num_objects times
            h_in, w_in = input_grid.shape
            h_out, w_out = output_grid.shape
            
            # Simple case: tiled horizontally num_objects times
            if h_out != h_in or w_out != w_in * num_objects:
                return None
            
            # Verify tiling
            for i in range(num_objects):
                tile = output_grid[:, i*w_in:(i+1)*w_in]
                if not np.array_equal(tile, input_grid):
                    return None
        
        return Hypothesis(
            engine_name="COUNT",
            operation="COUNT_TILE",
            params={},
            confidence=0.8,
            dsl_program="COUNT:COUNT_TILE()",
            explanation="Tile input N times (N = object count)"
        )


class RelEngine(BaseEngine):
    """
    Spatial relation engine.
    
    Detects:
    1. Objects moved to corners
    2. Object alignment (same row/col)
    3. Relative positioning (next to, adjacent)
    """
    def __init__(self):
        super().__init__(name="REL")
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        """Analyze for spatial relations."""
        hypotheses = []
        
        # Check for corner placement
        corner_hyp = self._detect_corner_placement(task_view)
        if corner_hyp:
            hypotheses.append(corner_hyp)
        
        # Check for row/column alignment
        align_hyp = self._detect_alignment(task_view)
        if align_hyp:
            hypotheses.append(align_hyp)
        
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        return hypotheses
    
    def _detect_corner_placement(self, task_view: TaskView) -> Hypothesis:
        """Detect if objects move to corners."""
        from scipy.ndimage import label
        
        for input_grid, output_grid in task_view.train_pairs:
            if input_grid.shape != output_grid.shape:
                return None
            
            # Find objects in output
            labeled, num = label(output_grid != 0)
            if num == 0:
                return None
            
            # Check if all objects are in corners
            h, w = output_grid.shape
            corners = [(0, 0), (0, w-1), (h-1, 0), (h-1, w-1)]
            
            for obj_id in range(1, num + 1):
                coords = np.argwhere(labeled == obj_id)
                if len(coords) == 0:
                    continue
                
                # Check if any pixel is in a corner region (within 3x3 of corner)
                in_corner = False
                for r, c in coords:
                    for cr, cc in corners:
                        if abs(r - cr) <= 2 and abs(c - cc) <= 2:
                            in_corner = True
                            break
                    if in_corner:
                        break
                
                if not in_corner:
                    return None
        
        return Hypothesis(
            engine_name="REL",
            operation="TO_CORNERS",
            params={},
            confidence=0.8,
            dsl_program="REL:TO_CORNERS()",
            explanation="Move objects to corners"
        )
    
    def _detect_alignment(self, task_view: TaskView) -> Hypothesis:
        """Detect if objects align to same row/column."""
        # Stub for now - complex logic
        return None


class MetaCompEngine(BaseEngine):
    """Stub: Composition/meta-reasoning engine."""
    def __init__(self):
        super().__init__(name="META")
    
    def analyze(self, task_view: TaskView) -> List[Hypothesis]:
        return []
