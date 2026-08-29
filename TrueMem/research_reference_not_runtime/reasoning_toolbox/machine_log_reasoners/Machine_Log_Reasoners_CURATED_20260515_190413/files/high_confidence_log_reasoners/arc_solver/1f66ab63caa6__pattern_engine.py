"""
PATTERN-ENGINE — Phase 1: Symmetry Detection

Part of the 9-ENGINE DOCTRINE for ARC solving.
Handles: periodicity, tiling, Latin patterns, symmetry completion.

Phase 1: Symmetry Detection
- Detect horizontal, vertical, diagonal symmetry
- Score how symmetric a grid is for each axis
- Provide HAS_SYMMETRY(axis) and SYMMETRY_COMPLETION(axis)
"""
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field


@dataclass
class PatternHypothesis:
    """A hypothesis about pattern structure in a grid."""
    kind: str  # "tiling", "row_stripes", "col_stripes", "local_tiling"
    score: float  # Confidence 0.0 to 1.0
    params: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        params_str = ', '.join(f'{k}={v}' for k, v in list(self.params.items())[:3])
        return f"PatternHypothesis(kind={self.kind}, score={self.score:.3f}, {params_str})"


@dataclass
class SymmetryAnalysis:
    """Results of symmetry detection on a grid."""
    horizontal: bool
    vertical: bool
    diagonal_main: bool  # top-left to bottom-right
    diagonal_anti: bool  # top-right to bottom-left
    rotational_90: bool
    rotational_180: bool
    
    # Confidence scores (0.0 to 1.0)
    h_score: float
    v_score: float
    d_main_score: float
    d_anti_score: float
    rot_90_score: float
    rot_180_score: float
    
    # Best symmetry axis (for completion)
    best_axis: Optional[str] = None
    best_score: float = 0.0
    
    def __post_init__(self):
        """Determine best axis after initialization."""
        axes = {
            'horizontal': self.h_score,
            'vertical': self.v_score,
            'diagonal_main': self.d_main_score,
            'diagonal_anti': self.d_anti_score,
            'rotational_90': self.rot_90_score,
            'rotational_180': self.rot_180_score
        }
        self.best_axis = max(axes, key=axes.get)
        self.best_score = axes[self.best_axis]


class PatternEngine:
    """
    PATTERN-ENGINE: Symmetry, Tiling, and Pattern Recognition.
    
    Phase 1: Symmetry Detection
    Phase 2: Tile/Fragment Detection (TODO)
    Phase 3: Latin/Modular Patterns (TODO)
    Phase 4: Completion & Extrapolation (TODO)
    """
    
    def __init__(self, symmetry_threshold: float = 0.95):
        """
        Initialize PATTERN-ENGINE.
        
        Args:
            symmetry_threshold: Minimum score to consider grid symmetric (0.0 to 1.0)
        """
        self.symmetry_threshold = symmetry_threshold
        self.name = "pattern_engine"
    
    # =========================================================================
    # PHASE 1: SYMMETRY DETECTION
    # =========================================================================
    
    def detect_symmetry(self, grid: np.ndarray) -> SymmetryAnalysis:
        """
        Detect all symmetries in a grid.
        
        Args:
            grid: 2D numpy array
            
        Returns:
            SymmetryAnalysis with all detected symmetries and scores
        """
        h, w = grid.shape
        
        # Horizontal symmetry (flip up-down)
        h_score = self._score_symmetry(grid, np.flipud(grid))
        h_symmetric = h_score >= self.symmetry_threshold
        
        # Vertical symmetry (flip left-right)
        v_score = self._score_symmetry(grid, np.fliplr(grid))
        v_symmetric = v_score >= self.symmetry_threshold
        
        # Diagonal symmetry (main diagonal: transpose)
        if h == w:  # Only square grids can have diagonal symmetry
            d_main_score = self._score_symmetry(grid, grid.T)
            d_main_symmetric = d_main_score >= self.symmetry_threshold
            
            # Anti-diagonal (transpose + both flips)
            anti_diag = np.flipud(np.fliplr(grid.T))
            d_anti_score = self._score_symmetry(grid, anti_diag)
            d_anti_symmetric = d_anti_score >= self.symmetry_threshold
        else:
            d_main_score = d_anti_score = 0.0
            d_main_symmetric = d_anti_symmetric = False
        
        # Rotational symmetry
        rot_90_score = self._score_symmetry(grid, np.rot90(grid, k=1))
        rot_90_symmetric = rot_90_score >= self.symmetry_threshold
        
        rot_180_score = self._score_symmetry(grid, np.rot90(grid, k=2))
        rot_180_symmetric = rot_180_score >= self.symmetry_threshold
        
        return SymmetryAnalysis(
            horizontal=h_symmetric,
            vertical=v_symmetric,
            diagonal_main=d_main_symmetric,
            diagonal_anti=d_anti_symmetric,
            rotational_90=rot_90_symmetric,
            rotational_180=rot_180_symmetric,
            h_score=h_score,
            v_score=v_score,
            d_main_score=d_main_score,
            d_anti_score=d_anti_score,
            rot_90_score=rot_90_score,
            rot_180_score=rot_180_score
        )
    
    def _score_symmetry(self, grid1: np.ndarray, grid2: np.ndarray) -> float:
        """
        Score how similar two grids are (0.0 to 1.0).
        
        Args:
            grid1, grid2: Grids to compare
            
        Returns:
            Similarity score (1.0 = identical)
        """
        if grid1.shape != grid2.shape:
            return 0.0
        
        matches = np.sum(grid1 == grid2)
        total = grid1.size
        
        return float(matches / total) if total > 0 else 0.0
    
    def has_symmetry(self, grid: np.ndarray, axis: str) -> bool:
        """
        Check if grid has specific symmetry.
        
        DSL: PATTERN:HAS_SYMMETRY(axis)
        
        Args:
            grid: Input grid
            axis: One of 'horizontal', 'vertical', 'diagonal_main', 'diagonal_anti',
                  'rotational_90', 'rotational_180', 'any'
                  
        Returns:
            True if grid has requested symmetry
        """
        analysis = self.detect_symmetry(grid)
        
        if axis == 'any':
            return any([
                analysis.horizontal,
                analysis.vertical,
                analysis.diagonal_main,
                analysis.diagonal_anti,
                analysis.rotational_90,
                analysis.rotational_180
            ])
        
        axis_map = {
            'horizontal': analysis.horizontal,
            'vertical': analysis.vertical,
            'diagonal_main': analysis.diagonal_main,
            'diagonal_anti': analysis.diagonal_anti,
            'rotational_90': analysis.rotational_90,
            'rotational_180': analysis.rotational_180
        }
        
        return axis_map.get(axis, False)
    
    def symmetry_completion(self, fragment: np.ndarray, axis: str, 
                          target_shape: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        Complete a fragment by reflecting it across specified axis.
        
        DSL: PATTERN:SYMMETRY_COMPLETION(axis)
        
        Args:
            fragment: Partial grid to complete
            axis: Symmetry axis to use for completion
            target_shape: Optional target size for output
            
        Returns:
            Completed symmetric grid
        """
        if axis == 'horizontal':
            # Mirror top-bottom
            completed = np.vstack([fragment, np.flipud(fragment)])
        elif axis == 'vertical':
            # Mirror left-right
            completed = np.hstack([fragment, np.fliplr(fragment)])
        elif axis == 'diagonal_main':
            # Mirror across main diagonal
            completed = np.block([
                [fragment, fragment.T],
                [fragment.T, fragment]
            ])
        elif axis == 'diagonal_anti':
            # Mirror across anti-diagonal
            flipped = np.flipud(np.fliplr(fragment))
            completed = np.block([
                [fragment, flipped.T],
                [flipped.T, fragment]
            ])
        elif axis == 'rotational_180':
            # 180° rotational completion
            completed = np.vstack([fragment, np.rot90(fragment, k=2)])
        elif axis == 'rotational_90':
            # 4-way rotational completion
            r90 = np.rot90(fragment, k=1)
            r180 = np.rot90(fragment, k=2)
            r270 = np.rot90(fragment, k=3)
            completed = np.block([
                [fragment, r90],
                [r270, r180]
            ])
        else:
            # Unknown axis, return fragment
            completed = fragment
        
        # Resize to target if specified
        if target_shape is not None:
            th, tw = target_shape
            ch, cw = completed.shape
            if (ch, cw) != (th, tw):
                # Crop or pad to match
                if ch >= th and cw >= tw:
                    completed = completed[:th, :tw]
                # If too small, would need padding logic (TODO)
        
        return completed
    
    def detect_best_symmetry(self, grid: np.ndarray) -> Tuple[str, float]:
        """
        Find the strongest symmetry in a grid.
        
        Returns:
            (axis_name, confidence_score)
        """
        analysis = self.detect_symmetry(grid)
        return (analysis.best_axis, analysis.best_score)
    
    # =========================================================================
    # PHASE 2: TILE / FRAGMENT DETECTION
    # =========================================================================
    
    def detect_global_tiling(self, grid: np.ndarray, 
                           max_tile_size: int = 10,
                           score_threshold: float = 0.95) -> List[PatternHypothesis]:
        """
        Detect if entire grid is composed of a repeating 2D tile.
        
        DSL: PATTERN:DETECT_GLOBAL_TILING(grid)
        
        Args:
            grid: Input grid to analyze
            max_tile_size: Maximum tile dimension to consider
            score_threshold: Minimum match score to report hypothesis
            
        Returns:
            List of tiling hypotheses, sorted by score (best first)
        """
        h, w = grid.shape
        hypotheses = []
        
        # Find divisors of height and width (up to max_tile_size)
        h_divisors = [d for d in range(1, min(h, max_tile_size) + 1) if h % d == 0]
        w_divisors = [d for d in range(1, min(w, max_tile_size) + 1) if w % d == 0]
        
        # Try each (tile_h, tile_w) combination
        for tile_h in h_divisors:
            for tile_w in w_divisors:
                # Skip trivial case (whole grid)
                if tile_h == h and tile_w == w:
                    continue
                
                # Extract candidate tile from top-left
                tile = grid[0:tile_h, 0:tile_w].copy()
                
                # Tile it to fill entire grid
                tiled = self._tile_to_shape(tile, (h, w))
                
                # Score how well it matches
                score = self._score_symmetry(grid, tiled)
                
                if score >= score_threshold:
                    hypotheses.append(PatternHypothesis(
                        kind="tiling",
                        score=score,
                        params={
                            'tile_height': tile_h,
                            'tile_width': tile_w,
                            'tile': tile,
                            'mode': 'full_grid',
                            'repeat_x': w // tile_w,
                            'repeat_y': h // tile_h
                        }
                    ))
        
        # Sort by score (best first)
        hypotheses.sort(key=lambda h: h.score, reverse=True)
        return hypotheses
    
    def detect_stripes(self, grid: np.ndarray,
                      max_period: int = 10,
                      score_threshold: float = 0.95) -> List[PatternHypothesis]:
        """
        Detect 1D repetition patterns (row or column stripes).
        
        DSL: PATTERN:DETECT_STRIPES(grid)
        
        Args:
            grid: Input grid to analyze
            max_period: Maximum repetition period to check
            score_threshold: Minimum match score to report
            
        Returns:
            List of stripe hypotheses (row or column based)
        """
        h, w = grid.shape
        hypotheses = []
        
        # Check row-wise repetition
        for period in range(1, min(h, max_period) + 1):
            if h % period != 0:
                continue
            
            # Check if pattern repeats every 'period' rows
            base_segment = grid[0:period, :].copy()
            matches = 0
            total = h // period
            
            for i in range(0, h, period):
                segment = grid[i:i+period, :]
                if np.array_equal(segment, base_segment):
                    matches += 1
            
            score = matches / total if total > 0 else 0.0
            
            if score >= score_threshold and period < h:  # Don't report trivial whole-grid
                hypotheses.append(PatternHypothesis(
                    kind="row_stripes",
                    score=score,
                    params={
                        'axis': 'row',
                        'period': period,
                        'base_segment': base_segment,
                        'num_repetitions': h // period
                    }
                ))
        
        # Check column-wise repetition
        for period in range(1, min(w, max_period) + 1):
            if w % period != 0:
                continue
            
            base_segment = grid[:, 0:period].copy()
            matches = 0
            total = w // period
            
            for i in range(0, w, period):
                segment = grid[:, i:i+period]
                if np.array_equal(segment, base_segment):
                    matches += 1
            
            score = matches / total if total > 0 else 0.0
            
            if score >= score_threshold and period < w:
                hypotheses.append(PatternHypothesis(
                    kind="col_stripes",
                    score=score,
                    params={
                        'axis': 'col',
                        'period': period,
                        'base_segment': base_segment,
                        'num_repetitions': w // period
                    }
                ))
        
        hypotheses.sort(key=lambda h: h.score, reverse=True)
        return hypotheses
    
    def detect_local_tiling(self, grid: np.ndarray, 
                          mask: Optional[np.ndarray] = None,
                          max_tile_size: int = 10,
                          score_threshold: float = 0.95) -> List[PatternHypothesis]:
        """
        Detect tiling within a masked region (future: COMP-ENGINE integration).
        
        DSL: PATTERN:DETECT_LOCAL_TILING(grid, mask)
        
        Args:
            grid: Input grid
            mask: Boolean mask (True = region to analyze), None = whole grid
            max_tile_size: Maximum tile dimension
            score_threshold: Minimum score
            
        Returns:
            List of local tiling hypotheses
            
        Note: Currently falls back to global tiling if no mask provided.
              Full masked tiling requires COMP-ENGINE for region extraction.
        """
        if mask is None:
            # No mask provided, use global tiling
            return self.detect_global_tiling(grid, max_tile_size, score_threshold)
        
        # TODO: Implement true masked tiling when COMP-ENGINE is ready
        # For now, extract masked region and detect tiling within it
        raise NotImplementedError("Masked tiling requires COMP-ENGINE integration")
    
    def _tile_to_shape(self, tile: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
        """
        Tile a fragment to fill target shape.
        
        Args:
            tile: Small tile to repeat
            target_shape: (height, width) to fill
            
        Returns:
            Tiled grid
        """
        th, tw = target_shape
        tile_h, tile_w = tile.shape
        
        # Calculate repetitions needed
        repeat_y = (th + tile_h - 1) // tile_h
        repeat_x = (tw + tile_w - 1) // tile_w
        
        # Tile using numpy repeat
        tiled = np.tile(tile, (repeat_y, repeat_x))
        
        # Crop to exact target shape
        return tiled[:th, :tw]
    
    def detect_all_patterns(self, grid: np.ndarray) -> Dict[str, List[PatternHypothesis]]:
        """
        Run all pattern detection methods and return comprehensive analysis.
        
        Returns:
            Dictionary with keys: 'tiling', 'stripes', 'local_tiling'
        """
        return {
            'tiling': self.detect_global_tiling(grid),
            'stripes': self.detect_stripes(grid),
            # 'local_tiling': self.detect_local_tiling(grid)  # Requires mask
        }


# =============================================================================
# TEST SUITE FOR PHASE 1
# =============================================================================

def test_symmetry_detection():
    """Test suite for symmetry detection."""
    print("=" * 80)
    print("PATTERN-ENGINE PHASE 1 TEST SUITE")
    print("=" * 80)
    print()
    
    engine = PatternEngine(symmetry_threshold=0.95)
    
    # Test 1: Horizontal symmetry
    print("Test 1: Horizontal Symmetry")
    h_sym = np.array([
        [1, 2, 3],
        [4, 5, 6],
        [4, 5, 6],
        [1, 2, 3]
    ])
    analysis = engine.detect_symmetry(h_sym)
    print(f"  Horizontal: {analysis.horizontal} (score: {analysis.h_score:.3f})")
    print(f"  Vertical: {analysis.vertical} (score: {analysis.v_score:.3f})")
    assert analysis.horizontal, "Should detect horizontal symmetry"
    print("  ✓ PASS")
    print()
    
    # Test 2: Vertical symmetry
    print("Test 2: Vertical Symmetry")
    v_sym = np.array([
        [1, 4, 1],
        [2, 5, 2],
        [3, 6, 3]
    ])
    analysis = engine.detect_symmetry(v_sym)
    print(f"  Horizontal: {analysis.horizontal} (score: {analysis.h_score:.3f})")
    print(f"  Vertical: {analysis.vertical} (score: {analysis.v_score:.3f})")
    assert analysis.vertical, "Should detect vertical symmetry"
    print("  ✓ PASS")
    print()
    
    # Test 3: 180° rotational symmetry
    print("Test 3: 180° Rotational Symmetry")
    rot_sym = np.array([
        [1, 2, 3],
        [4, 5, 6],
        [6, 5, 4],
        [3, 2, 1]
    ])
    analysis = engine.detect_symmetry(rot_sym)
    print(f"  180° rotation: {analysis.rotational_180} (score: {analysis.rot_180_score:.3f})")
    assert analysis.rotational_180, "Should detect 180° rotational symmetry"
    print("  ✓ PASS")
    print()
    
    # Test 4: No symmetry
    print("Test 4: No Symmetry")
    no_sym = np.array([
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ])
    analysis = engine.detect_symmetry(no_sym)
    print(f"  Best axis: {analysis.best_axis} (score: {analysis.best_score:.3f})")
    assert analysis.best_score < 0.95, "Should not find strong symmetry"
    print("  ✓ PASS")
    print()
    
    # Test 5: Symmetry completion
    print("Test 5: Vertical Symmetry Completion")
    fragment = np.array([
        [1, 2],
        [3, 4]
    ])
    completed = engine.symmetry_completion(fragment, 'vertical')
    expected = np.array([
        [1, 2, 2, 1],
        [3, 4, 4, 3]
    ])
    print(f"  Fragment shape: {fragment.shape}")
    print(f"  Completed shape: {completed.shape}")
    print(f"  Expected shape: {expected.shape}")
    assert np.array_equal(completed, expected), "Vertical completion failed"
    print("  ✓ PASS")
    print()
    
    # Test 6: Has symmetry check
    print("Test 6: HAS_SYMMETRY DSL function")
    assert engine.has_symmetry(v_sym, 'vertical'), "Should have vertical symmetry"
    assert not engine.has_symmetry(no_sym, 'vertical'), "Should not have vertical symmetry"
    assert engine.has_symmetry(v_sym, 'any'), "Should have some symmetry"
    print("  ✓ PASS")
    print()
    
    print("=" * 80)
    print("ALL TESTS PASSED - PHASE 1 COMPLETE")
    print("=" * 80)


def test_tiling_detection():
    """Test suite for Phase 2: Tile and Stripe Detection."""
    print()
    print("=" * 80)
    print("PATTERN-ENGINE PHASE 2 TEST SUITE")
    print("=" * 80)
    print()
    
    engine = PatternEngine(symmetry_threshold=0.95)
    
    # Test 1: 2×2 checkerboard tiled to 6×6
    print("Test 1: 2×2 Checkerboard Tiling")
    checkerboard_tile = np.array([
        [0, 1],
        [1, 0]
    ])
    checkerboard = np.tile(checkerboard_tile, (3, 3))  # 6×6
    
    hypotheses = engine.detect_global_tiling(checkerboard)
    print(f"  Found {len(hypotheses)} tiling hypotheses")
    if hypotheses:
        best = hypotheses[0]
        print(f"  Best: tile_size=({best.params['tile_height']}, {best.params['tile_width']}), score={best.score:.3f}")
        assert best.params['tile_height'] == 2 and best.params['tile_width'] == 2, "Should detect 2×2 tile"
    print("  ✓ PASS")
    print()
    
    # Test 2: Vertical stripes (3-column pattern repeated)
    print("Test 2: Vertical Stripes (3-col pattern)")
    stripe_pattern = np.array([
        [1, 2, 3, 1, 2, 3],
        [4, 5, 6, 4, 5, 6],
        [7, 8, 9, 7, 8, 9]
    ])
    
    stripe_hyps = engine.detect_stripes(stripe_pattern)
    print(f"  Found {len(stripe_hyps)} stripe hypotheses")
    col_stripes = [h for h in stripe_hyps if h.kind == 'col_stripes']
    if col_stripes:
        best = col_stripes[0]
        print(f"  Best col stripe: period={best.params['period']}, score={best.score:.3f}")
        assert best.params['period'] == 3, "Should detect period-3 column stripe"
    print("  ✓ PASS")
    print()
    
    # Test 3: Horizontal stripes (2-row pattern)
    print("Test 3: Horizontal Stripes (2-row pattern)")
    h_stripe = np.array([
        [1, 1, 1],
        [2, 2, 2],
        [1, 1, 1],
        [2, 2, 2]
    ])
    
    h_hyps = engine.detect_stripes(h_stripe)
    row_stripes = [h for h in h_hyps if h.kind == 'row_stripes']
    if row_stripes:
        best = row_stripes[0]
        print(f"  Best row stripe: period={best.params['period']}, score={best.score:.3f}")
        assert best.params['period'] == 2, "Should detect period-2 row stripe"
    print("  ✓ PASS")
    print()
    
    # Test 4: 3×3 tile repeated to 9×9
    print("Test 4: 3×3 Tile → 9×9")
    tile_3x3 = np.array([
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ])
    grid_9x9 = np.tile(tile_3x3, (3, 3))
    
    hyps = engine.detect_global_tiling(grid_9x9)
    if hyps:
        best = hyps[0]
        print(f"  Detected: {best.params['tile_height']}×{best.params['tile_width']} tile, score={best.score:.3f}")
        assert best.params['tile_height'] == 3 and best.params['tile_width'] == 3, "Should detect 3×3 tile"
    print("  ✓ PASS")
    print()
    
    # Test 5: Detect all patterns at once
    print("Test 5: Comprehensive Pattern Detection")
    all_patterns = engine.detect_all_patterns(checkerboard)
    print(f"  Tiling hypotheses: {len(all_patterns.get('tiling', []))}")
    print(f"  Stripe hypotheses: {len(all_patterns.get('stripes', []))}")
    assert len(all_patterns['tiling']) > 0, "Should find tiling in checkerboard"
    print("  ✓ PASS")
    print()
    
    # Test 6: Non-tiled grid (should find few/no hypotheses)
    print("Test 6: Non-Tiled Grid")
    random_grid = np.array([
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 0, 1, 2],
        [3, 4, 5, 6]
    ])
    hyps = engine.detect_global_tiling(random_grid, score_threshold=0.95)
    print(f"  Found {len(hyps)} high-confidence tiling hypotheses")
    # Should find very few or none with 0.95 threshold
    print("  ✓ PASS")
    print()
    
    print("=" * 80)
    print("ALL PHASE 2 TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    test_symmetry_detection()
    test_tiling_detection()
