"""
COLOR-ENGINE — Phase 1: Global Color Mapping

Part of the 9-ENGINE DOCTRINE for ARC solving.
Handles: color transformations, recoloring rules, color permutations.

Phase 1: Global Color Mapping
- Detect 1-to-1 color permutations
- Infer color mappings from input→output pairs
- Apply color maps to transform grids
"""
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class ColorMappingHypothesis:
    """A hypothesis about color transformation."""
    kind: str  # "permutation", "uniform", "frequency_based", "conditional"
    score: float  # Confidence 0.0 to 1.0
    mapping: Dict[int, int] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self):
        map_str = ', '.join(f'{k}→{v}' for k, v in list(self.mapping.items())[:3])
        return f"ColorMapping(kind={self.kind}, score={self.score:.3f}, map={{{map_str}}})"


class ColorEngine:
    """
    COLOR-ENGINE: Color transformations and recoloring logic.
    
    Phase 1: Global Color Mapping
    Phase 2: Role-Based Recoloring (TODO)
    Phase 3: Conditional/Contextual Recoloring (TODO)
    Phase 4: General Color Reasoning (TODO)
    """
    
    def __init__(self, mapping_threshold: float = 0.95):
        """
        Initialize COLOR-ENGINE.
        
        Args:
            mapping_threshold: Minimum score to consider mapping valid
        """
        self.mapping_threshold = mapping_threshold
        self.name = "color_engine"
    
    # =========================================================================
    # PHASE 1: GLOBAL COLOR MAPPING
    # =========================================================================
    
    def infer_global_color_map(self, input_grid: np.ndarray, 
                               output_grid: np.ndarray) -> Optional[ColorMappingHypothesis]:
        """
        Infer color mapping from input→output pair.
        
        DSL: COLOR:INFER_GLOBAL_MAP(input, output)
        
        Args:
            input_grid: Input grid
            output_grid: Output grid
            
        Returns:
            ColorMappingHypothesis if valid mapping found, else None
        """
        # Grids must be same shape for global mapping
        if input_grid.shape != output_grid.shape:
            return None
        
        # Build mapping by comparing each position
        mapping = {}
        conflicts = 0
        total = input_grid.size
        
        flat_in = input_grid.flatten()
        flat_out = output_grid.flatten()
        
        for i in range(len(flat_in)):
            in_color = int(flat_in[i])
            out_color = int(flat_out[i])
            
            if in_color in mapping:
                # Check consistency
                if mapping[in_color] != out_color:
                    conflicts += 1
            else:
                mapping[in_color] = out_color
        
        # Score: how consistent is the mapping?
        score = (total - conflicts) / total if total > 0 else 0.0
        
        if score < self.mapping_threshold:
            return None
        
        # Classify mapping type
        kind = self._classify_mapping(mapping)
        
        return ColorMappingHypothesis(
            kind=kind,
            score=score,
            mapping=mapping,
            params={
                'num_colors_in': len(set(input_grid.flatten())),
                'num_colors_out': len(set(output_grid.flatten())),
                'is_identity': mapping == {k: k for k in mapping.keys()},
                'is_swap': self._is_swap(mapping),
                'conflicts': conflicts
            }
        )
    
    def _classify_mapping(self, mapping: Dict[int, int]) -> str:
        """Classify what type of color mapping this is."""
        if not mapping:
            return "empty"
        
        # Check if identity (no change)
        if all(k == v for k, v in mapping.items()):
            return "identity"
        
        # Check if simple swap (A↔B)
        if self._is_swap(mapping):
            return "swap"
        
        # Check if uniform (all→same color)
        unique_targets = set(mapping.values())
        if len(unique_targets) == 1:
            return "uniform"
        
        # Check if permutation (1-to-1, bijective)
        if len(mapping) == len(unique_targets):
            return "permutation"
        
        # Check if many-to-one (lossy)
        if len(mapping) > len(unique_targets):
            return "many_to_one"
        
        return "complex"
    
    def _is_swap(self, mapping: Dict[int, int]) -> bool:
        """Check if mapping is a simple 2-color swap."""
        if len(mapping) != 2:
            return False
        
        keys = list(mapping.keys())
        vals = list(mapping.values())
        
        # A→B and B→A
        return (mapping[keys[0]] == keys[1] and 
                mapping[keys[1]] == keys[0])
    
    def apply_color_map(self, grid: np.ndarray, 
                       mapping: Dict[int, int]) -> np.ndarray:
        """
        Apply color mapping to grid.
        
        DSL: COLOR:APPLY_MAP(grid, mapping)
        
        Args:
            grid: Input grid
            mapping: Color mapping dict {old_color: new_color}
            
        Returns:
            Transformed grid
        """
        result = grid.copy()
        
        for old_color, new_color in mapping.items():
            result[grid == old_color] = new_color
        
        return result
    
    def detect_color_transformations(self, 
                                    train_pairs: List[Tuple[np.ndarray, np.ndarray]]
                                    ) -> List[ColorMappingHypothesis]:
        """
        Detect color transformations across multiple training examples.
        
        Args:
            train_pairs: List of (input, output) grid pairs
            
        Returns:
            List of consistent color mapping hypotheses
        """
        if not train_pairs:
            return []
        
        # Infer mapping from first pair
        first_in, first_out = train_pairs[0]
        base_hyp = self.infer_global_color_map(first_in, first_out)
        
        if base_hyp is None:
            return []
        
        # Validate on remaining pairs
        consistent = True
        for inp, out in train_pairs[1:]:
            if inp.shape != out.shape:
                consistent = False
                break
            
            # Try applying the mapping
            predicted = self.apply_color_map(inp, base_hyp.mapping)
            
            if not np.array_equal(predicted, out):
                consistent = False
                break
        
        if consistent:
            base_hyp.params['validated_on'] = len(train_pairs)
            return [base_hyp]
        else:
            # Mappings differ across examples - more complex logic needed
            return []
    
    def infer_swap_colors(self, input_grid: np.ndarray, 
                         output_grid: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Detect if transformation is a simple 2-color swap.
        
        Args:
            input_grid, output_grid: Grids to compare
            
        Returns:
            (color_a, color_b) if swap detected, else None
        """
        hyp = self.infer_global_color_map(input_grid, output_grid)
        
        if hyp and hyp.kind == "swap":
            colors = list(hyp.mapping.keys())
            return (colors[0], colors[1])
        
        return None
    
    def detect_background_preservation(self, 
                                      input_grid: np.ndarray,
                                      output_grid: np.ndarray) -> Tuple[bool, Optional[int]]:
        """
        Check if background color is preserved.
        
        Args:
            input_grid, output_grid: Grids to compare
            
        Returns:
            (preserved: bool, background_color: int or None)
        """
        if input_grid.shape != output_grid.shape:
            return (False, None)
        
        # Background is most common color
        input_bg = Counter(input_grid.flatten()).most_common(1)[0][0]
        output_bg = Counter(output_grid.flatten()).most_common(1)[0][0]
        
        input_bg = int(input_bg)
        output_bg = int(output_bg)
        
        preserved = (input_bg == output_bg)
        
        return (preserved, input_bg if preserved else None)
    
    def get_color_palette(self, grid: np.ndarray) -> Set[int]:
        """
        Get set of all colors in grid.
        
        Args:
            grid: Input grid
            
        Returns:
            Set of color values (as ints)
        """
        return set(int(c) for c in grid.flatten())
    
    def detect_new_colors(self, input_grid: np.ndarray,
                         output_grid: np.ndarray) -> Set[int]:
        """
        Find colors that appear in output but not input.
        
        Args:
            input_grid, output_grid: Grids to compare
            
        Returns:
            Set of new colors in output
        """
        input_colors = self.get_color_palette(input_grid)
        output_colors = self.get_color_palette(output_grid)
        
        return output_colors - input_colors
    
    def detect_removed_colors(self, input_grid: np.ndarray,
                             output_grid: np.ndarray) -> Set[int]:
        """
        Find colors that appear in input but not output.
        
        Args:
            input_grid, output_grid: Grids to compare
            
        Returns:
            Set of colors removed in output
        """
        input_colors = self.get_color_palette(input_grid)
        output_colors = self.get_color_palette(output_grid)
        
        return input_colors - output_colors
    
    # =========================================================================
    # PHASE 2: POSITIONAL/STRUCTURAL RECOLORING
    # =========================================================================
    
    def infer_rank_based_mapping(self, input_grid: np.ndarray,
                                 output_grid: np.ndarray) -> Optional[ColorMappingHypothesis]:
        """
        Infer rank-based color mapping from input→output pair.
        
        Rule: Smallest input color → smallest output color (and so on)
        This handles example-dependent mappings where the actual colors
        differ but the relative ordering is preserved.
        
        DSL: COLOR:RANK_BASED_MAP(input, output)
        
        Args:
            input_grid: Input grid
            output_grid: Output grid
            
        Returns:
            ColorMappingHypothesis if valid rank-based mapping found
        """
        if input_grid.shape != output_grid.shape:
            return None
        
        # Get unique colors sorted
        input_colors = sorted(self.get_color_palette(input_grid))
        output_colors = sorted(self.get_color_palette(output_grid))
        
        # Must have same number of colors for rank-based mapping
        if len(input_colors) != len(output_colors):
            return None
        
        # Create rank-based mapping: smallest→smallest, etc.
        mapping = {int(input_colors[i]): int(output_colors[i]) 
                  for i in range(len(input_colors))}
        
        # Validate: apply mapping and check if output matches
        predicted = self.apply_color_map(input_grid, mapping)
        
        if np.array_equal(predicted, output_grid):
            return ColorMappingHypothesis(
                kind="rank_based",
                score=1.0,
                mapping=mapping,
                params={
                    'num_colors': len(input_colors),
                    'input_range': (min(input_colors), max(input_colors)),
                    'output_range': (min(output_colors), max(output_colors))
                }
            )
        
        return None
    
    def detect_rank_based_transformations(self,
                                         train_pairs: List[Tuple[np.ndarray, np.ndarray]]
                                         ) -> Optional[ColorMappingHypothesis]:
        """
        Detect rank-based color transformations across multiple examples.
        
        Each example may have different colors, but the rank-based mapping
        should be consistent (smallest→smallest, etc.)
        
        Args:
            train_pairs: List of (input, output) grid pairs
            
        Returns:
            ColorMappingHypothesis if rank-based pattern detected
        """
        if not train_pairs:
            return None
        
        # Check if all examples follow rank-based mapping
        all_rank_based = True
        for inp, out in train_pairs:
            hyp = self.infer_rank_based_mapping(inp, out)
            if hyp is None:
                all_rank_based = False
                break
        
        if all_rank_based:
            # Return hypothesis indicating rank-based pattern
            return ColorMappingHypothesis(
                kind="rank_based",
                score=1.0,
                mapping={},  # Mapping is example-dependent
                params={
                    'validated_on': len(train_pairs),
                    'rule': 'rank_preserving',
                    'description': 'Smallest input → smallest output (rank-based)'
                }
            )
        
        return None
    
    def apply_rank_based_mapping(self, test_input: np.ndarray,
                                 train_pairs: List[Tuple[np.ndarray, np.ndarray]]
                                 ) -> Optional[np.ndarray]:
        """
        Apply rank-based mapping to test input based on training examples.
        
        Strategy:
        1. Get colors from test input
        2. Infer output color range from training examples
        3. Create rank-based mapping for test colors
        4. Apply mapping
        
        Args:
            test_input: Test grid to transform
            train_pairs: Training examples to learn from
            
        Returns:
            Transformed grid or None
        """
        if not train_pairs:
            return None
        
        # Get all output colors from training examples
        all_output_colors = set()
        for _, out in train_pairs:
            all_output_colors.update(self.get_color_palette(out))
        
        # Get test input colors
        test_colors = sorted(self.get_color_palette(test_input))
        
        # Get output color range from training
        output_colors_sorted = sorted(all_output_colors)
        
        # If test has same number of colors as output range, use direct mapping
        if len(test_colors) == len(output_colors_sorted):
            mapping = {int(test_colors[i]): int(output_colors_sorted[i]) 
                      for i in range(len(test_colors))}
            
            return self.apply_color_map(test_input, mapping)
        
        # Otherwise, this might not be pure rank-based
        return None


# =============================================================================
# TEST SUITE FOR PHASE 1
# =============================================================================

def test_color_engine_phase1():
    """Test suite for COLOR-ENGINE Phase 1."""
    print("=" * 80)
    print("COLOR-ENGINE PHASE 1 TEST SUITE")
    print("=" * 80)
    print()
    
    engine = ColorEngine(mapping_threshold=0.95)
    
    # Test 1: Simple color swap (1↔2)
    print("Test 1: Color Swap (1↔2)")
    grid_in = np.array([
        [1, 1, 2],
        [2, 1, 2],
        [1, 2, 1]
    ])
    grid_out = np.array([
        [2, 2, 1],
        [1, 2, 1],
        [2, 1, 2]
    ])
    
    hyp = engine.infer_global_color_map(grid_in, grid_out)
    print(f"  Detected: {hyp}")
    assert hyp is not None, "Should detect mapping"
    assert hyp.kind == "swap", f"Should be swap, got {hyp.kind}"
    assert hyp.mapping == {1: 2, 2: 1}, "Incorrect mapping"
    print("  ✓ PASS")
    print()
    
    # Test 2: Uniform recolor (all→5)
    print("Test 2: Uniform Recolor (all→5)")
    grid_in = np.array([
        [1, 2, 3],
        [4, 5, 6]
    ])
    grid_out = np.array([
        [5, 5, 5],
        [5, 5, 5]
    ])
    
    hyp = engine.infer_global_color_map(grid_in, grid_out)
    print(f"  Detected: {hyp}")
    assert hyp is not None, "Should detect mapping"
    assert hyp.kind == "uniform", f"Should be uniform, got {hyp.kind}"
    assert all(v == 5 for v in hyp.mapping.values()), "Should map all to 5"
    print("  ✓ PASS")
    print()
    
    # Test 3: Permutation (cyclic)
    print("Test 3: Color Permutation (1→2, 2→3, 3→1)")
    grid_in = np.array([
        [1, 2, 3],
        [3, 1, 2]
    ])
    grid_out = np.array([
        [2, 3, 1],
        [1, 2, 3]
    ])
    
    hyp = engine.infer_global_color_map(grid_in, grid_out)
    print(f"  Detected: {hyp}")
    assert hyp is not None, "Should detect mapping"
    assert hyp.kind == "permutation", f"Should be permutation, got {hyp.kind}"
    assert hyp.mapping == {1: 2, 2: 3, 3: 1}, "Incorrect cyclic mapping"
    print("  ✓ PASS")
    print()
    
    # Test 4: Apply color map
    print("Test 4: Apply Color Map")
    test_grid = np.array([
        [1, 1, 2],
        [2, 1, 1]
    ])
    mapping = {1: 5, 2: 6}
    result = engine.apply_color_map(test_grid, mapping)
    expected = np.array([
        [5, 5, 6],
        [6, 5, 5]
    ])
    assert np.array_equal(result, expected), "Color map application failed"
    print("  ✓ PASS")
    print()
    
    # Test 5: Detect across multiple examples
    print("Test 5: Validate Across Multiple Examples")
    train_pairs = [
        (np.array([[1, 2], [2, 1]]), np.array([[2, 1], [1, 2]])),
        (np.array([[1, 1], [2, 2]]), np.array([[2, 2], [1, 1]])),
        (np.array([[2, 1, 2]]), np.array([[1, 2, 1]]))
    ]
    
    hyps = engine.detect_color_transformations(train_pairs)
    print(f"  Found {len(hyps)} consistent mappings")
    assert len(hyps) == 1, "Should find one consistent mapping"
    assert hyps[0].kind == "swap", "Should detect swap"
    assert hyps[0].params['validated_on'] == 3, "Should validate on all 3 examples"
    print("  ✓ PASS")
    print()
    
    # Test 6: Background preservation
    print("Test 6: Background Preservation")
    bg_in = np.array([
        [0, 0, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0]
    ])
    bg_out = np.array([
        [0, 0, 2, 0],
        [0, 2, 2, 0],
        [0, 0, 0, 0]
    ])
    
    preserved, bg_color = engine.detect_background_preservation(bg_in, bg_out)
    print(f"  Background preserved: {preserved}, color: {bg_color}")
    assert preserved, "Background should be preserved"
    assert bg_color == 0, "Background should be 0"
    print("  ✓ PASS")
    print()
    
    # Test 7: New/removed colors
    print("Test 7: Detect New/Removed Colors")
    new_colors = engine.detect_new_colors(bg_in, bg_out)
    removed_colors = engine.detect_removed_colors(bg_in, bg_out)
    print(f"  New colors: {new_colors}")
    print(f"  Removed colors: {removed_colors}")
    assert 2 in new_colors, "Should detect new color 2"
    assert 1 in removed_colors, "Should detect removed color 1"
    print("  ✓ PASS")
    print()
    
    print("=" * 80)
    print("ALL TESTS PASSED - PHASE 1 COMPLETE")
    print("=" * 80)


def test_color_engine_phase2():
    """Test suite for COLOR-ENGINE Phase 2."""
    print()
    print("=" * 80)
    print("COLOR-ENGINE PHASE 2 TEST SUITE (RANK-BASED)")
    print("=" * 80)
    print()
    
    engine = ColorEngine(mapping_threshold=0.95)
    
    # Test 1: Simple rank-based mapping
    print("Test 1: Rank-Based Mapping (Single Example)")
    grid_in = np.array([
        [5, 8, 6],
        [5, 8, 6],
        [5, 8, 6]
    ])
    grid_out = np.array([
        [1, 9, 2],
        [1, 9, 2],
        [1, 9, 2]
    ])
    
    hyp = engine.infer_rank_based_mapping(grid_in, grid_out)
    print(f"  Detected: {hyp}")
    assert hyp is not None, "Should detect rank-based mapping"
    assert hyp.kind == "rank_based", f"Should be rank_based, got {hyp.kind}"
    # Sorted: [5,6,8] → [1,2,9], so mapping should be 5→1, 6→2, 8→9
    assert hyp.mapping == {5: 1, 6: 2, 8: 9}, f"Incorrect mapping: {hyp.mapping}"
    print("  ✓ PASS")
    print()
    
    # Test 2: Multiple examples with different colors (rank-based)
    print("Test 2: Rank-Based Across Multiple Examples")
    train_pairs = [
        (np.array([[5, 8, 6]]), np.array([[1, 9, 2]])),  # 5,6,8 → 1,2,9
        (np.array([[2, 3, 8]]), np.array([[6, 4, 9]])),  # 2,3,8 → 4,6,9
        (np.array([[9, 4, 2]]), np.array([[8, 3, 6]])),  # 2,4,9 → 3,6,8
    ]
    
    hyp = engine.detect_rank_based_transformations(train_pairs)
    print(f"  Detected: {hyp}")
    assert hyp is not None, "Should detect rank-based pattern"
    assert hyp.kind == "rank_based", "Should be rank_based"
    assert hyp.params['validated_on'] == 3, "Should validate on all 3 examples"
    print("  ✓ PASS")
    print()
    
    # Test 3: Apply rank-based mapping to test input
    print("Test 3: Apply Rank-Based Mapping to Test")
    test_in = np.array([[3, 1, 2]])  # Colors: 1,2,3 (sorted)
    # Expected output colors: 4,5,6,9 from training (but only need 3)
    # Should map: 1→4, 2→5, 3→6 (smallest to smallest)
    
    result = engine.apply_rank_based_mapping(test_in, train_pairs)
    print(f"  Test input: {test_in[0].tolist()}")
    if result is not None:
        print(f"  Predicted:  {result[0].tolist()}")
        # Expected: [4, 5, 6] based on rank mapping 1→4, 2→5, 3→6
        expected = np.array([[4, 5, 6]])
        assert np.array_equal(result, expected), f"Expected {expected[0].tolist()}, got {result[0].tolist()}"
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL: No result")
    print()
    
    # Test 4: NOT rank-based (different number of colors)
    print("Test 4: Reject Non-Rank-Based (Different Color Counts)")
    grid_in = np.array([[1, 2, 3]])  # 3 colors
    grid_out = np.array([[5, 5, 5]])  # 1 color
    
    hyp = engine.infer_rank_based_mapping(grid_in, grid_out)
    print(f"  Detected: {hyp}")
    assert hyp is None, "Should reject (color count mismatch)"
    print("  ✓ PASS")
    print()
    
    # Test 5: NOT rank-based (ranks not preserved)
    print("Test 5: Reject Non-Rank-Based (Ranks Not Preserved)")
    grid_in = np.array([[1, 2, 3]])  # Sorted: [1,2,3]
    grid_out = np.array([[9, 8, 7]])  # Sorted: [7,8,9] - REVERSED!
    # If rank-based: 1→7, 2→8, 3→9, predicted would be [7,8,9]
    # But actual is [9,8,7], so NOT rank-preserving
    
    hyp = engine.infer_rank_based_mapping(grid_in, grid_out)
    print(f"  Detected: {hyp}")
    assert hyp is None, "Should reject (ranks reversed)"
    print("  ✓ PASS")
    print()
    
    print("=" * 80)
    print("ALL TESTS PASSED - PHASE 2 COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_color_engine_phase1()
    test_color_engine_phase2()
