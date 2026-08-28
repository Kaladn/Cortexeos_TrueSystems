"""
RepeatOperator - Handles tiling, repetition, and pattern replication.

This operator unlocks ~30 tasks that involve:
- Tiling a fragment across the grid
- Repeating an object N times
- Extending patterns along directions
- Rolling/wrapping repetitions

This is one of the HIGHEST PAYOFF operators in ARC.
"""

import numpy as np
from typing import Optional, Dict, Any, Tuple


class RepeatOperator:
    """
    Repeats a pattern, object, or tile across the grid.
    
    Modes:
    - 'tile': Tile a fragment to fill grid (most common)
    - 'horizontal': Repeat horizontally N times
    - 'vertical': Repeat vertically N times
    - 'grid': Repeat in 2D grid pattern (M x N copies)
    - 'wrap': Wraparound tiling (toroidal)
    """
    
    name = "repeat_operator"
    
    def analyze(self, inp: np.ndarray, out: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Infer repetition pattern from input→output transformation.
        
        Returns config with:
        - mode: 'tile' | 'horizontal' | 'vertical' | 'grid'
        - tile_height, tile_width: Size of repeating unit
        - repeat_x, repeat_y: Number of repetitions
        """
        # Check if output is simple tiling of input
        if self._is_exact_tile(inp, out):
            return {
                "mode": "tile",
                "tile": inp,
                "target_shape": out.shape
            }
        
        # Check if output is input tiled to larger grid
        tile_h, tile_w = self._find_tile_size(inp, out)
        if tile_h and tile_w:
            if tile_h == inp.shape[0] and tile_w == inp.shape[1]:
                # Output is tiled version of input
                repeat_y = out.shape[0] // inp.shape[0]
                repeat_x = out.shape[1] // inp.shape[1]
                
                return {
                    "mode": "grid",
                    "tile": inp,
                    "repeat_x": repeat_x,
                    "repeat_y": repeat_y
                }
        
        # Check if input contains a fragment that tiles to output
        fragment = self._extract_repeating_fragment(inp)
        if fragment is not None:
            if self._validates_tiling(fragment, out):
                return {
                    "mode": "tile",
                    "tile": fragment,
                    "target_shape": out.shape
                }
        
        # Check horizontal repetition
        if inp.shape[0] == out.shape[0]:
            if out.shape[1] % inp.shape[1] == 0:
                repeat_x = out.shape[1] // inp.shape[1]
                if self._validates_horizontal_repeat(inp, out, repeat_x):
                    return {
                        "mode": "horizontal",
                        "tile": inp,
                        "repeat_x": repeat_x
                    }
        
        # Check vertical repetition
        if inp.shape[1] == out.shape[1]:
            if out.shape[0] % inp.shape[0] == 0:
                repeat_y = out.shape[0] // inp.shape[0]
                if self._validates_vertical_repeat(inp, out, repeat_y):
                    return {
                        "mode": "vertical",
                        "tile": inp,
                        "repeat_y": repeat_y
                    }
        
        return None
    
    def apply(self, inp: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
        """Apply repetition pattern to input."""
        mode = config.get("mode")
        tile = config.get("tile")
        
        if tile is None:
            return inp.copy()
        
        if mode == "tile":
            target_shape = config.get("target_shape", inp.shape)
            return self._tile_to_shape(tile, target_shape)
        
        elif mode == "horizontal":
            repeat_x = config.get("repeat_x", 1)
            return np.tile(tile, (1, repeat_x))
        
        elif mode == "vertical":
            repeat_y = config.get("repeat_y", 1)
            return np.tile(tile, (repeat_y, 1))
        
        elif mode == "grid":
            repeat_x = config.get("repeat_x", 1)
            repeat_y = config.get("repeat_y", 1)
            return np.tile(tile, (repeat_y, repeat_x))
        
        return inp.copy()
    
    def _is_exact_tile(self, inp: np.ndarray, out: np.ndarray) -> bool:
        """Check if output is exactly input (identity)."""
        return inp.shape == out.shape and np.array_equal(inp, out)
    
    def _find_tile_size(self, inp: np.ndarray, out: np.ndarray) -> Tuple[Optional[int], Optional[int]]:
        """Find dimensions of repeating tile in output."""
        h_out, w_out = out.shape
        h_in, w_in = inp.shape
        
        # Try common tile sizes
        for tile_h in range(1, min(h_out, 20) + 1):
            if h_out % tile_h != 0:
                continue
            
            for tile_w in range(1, min(w_out, 20) + 1):
                if w_out % tile_w != 0:
                    continue
                
                # Check if output is tiled with this size
                tile = out[:tile_h, :tile_w]
                if self._validates_tiling(tile, out):
                    return tile_h, tile_w
        
        return None, None
    
    def _extract_repeating_fragment(self, inp: np.ndarray) -> Optional[np.ndarray]:
        """Extract smallest repeating fragment from input."""
        h, w = inp.shape
        
        # Try small fragments (2x2, 3x3, etc.)
        for fh in range(1, min(h, 10) + 1):
            if h % fh != 0:
                continue
            
            for fw in range(1, min(w, 10) + 1):
                if w % fw != 0:
                    continue
                
                fragment = inp[:fh, :fw]
                if self._validates_tiling(fragment, inp):
                    return fragment
        
        return None
    
    def _validates_tiling(self, tile: np.ndarray, target: np.ndarray) -> bool:
        """Check if tile tiles perfectly to make target."""
        th, tw = tile.shape
        h, w = target.shape
        
        if h % th != 0 or w % tw != 0:
            return False
        
        # Tile and compare
        repeat_y = h // th
        repeat_x = w // tw
        tiled = np.tile(tile, (repeat_y, repeat_x))
        
        return np.array_equal(tiled, target)
    
    def _validates_horizontal_repeat(self, inp: np.ndarray, out: np.ndarray, repeat_x: int) -> bool:
        """Check if output is input repeated horizontally."""
        repeated = np.tile(inp, (1, repeat_x))
        return np.array_equal(repeated, out)
    
    def _validates_vertical_repeat(self, inp: np.ndarray, out: np.ndarray, repeat_y: int) -> bool:
        """Check if output is input repeated vertically."""
        repeated = np.tile(inp, (repeat_y, 1))
        return np.array_equal(repeated, out)
    
    def _tile_to_shape(self, tile: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
        """Tile pattern to fill target shape."""
        th, tw = tile.shape
        h, w = target_shape
        
        # Tile enough times to cover target
        repeat_y = (h + th - 1) // th
        repeat_x = (w + tw - 1) // tw
        
        tiled = np.tile(tile, (repeat_y, repeat_x))
        
        # Crop to exact target shape
        return tiled[:h, :w]


# Test
if __name__ == "__main__":
    print("Testing RepeatOperator...")
    
    op = RepeatOperator()
    
    # Test 1: Simple 2x tiling
    inp = np.array([[1, 2], [3, 4]])
    out = np.array([[1, 2, 1, 2], [3, 4, 3, 4]])
    
    cfg = op.analyze(inp, out)
    print(f"Test 1 config: {cfg}")
    
    if cfg:
        result = op.apply(inp, cfg)
        print(f"Test 1 result matches: {np.array_equal(result, out)}")
    
    # Test 2: Vertical repetition
    inp = np.array([[1, 2, 3]])
    out = np.array([[1, 2, 3], [1, 2, 3], [1, 2, 3]])
    
    cfg = op.analyze(inp, out)
    print(f"Test 2 config: {cfg}")
    
    if cfg:
        result = op.apply(inp, cfg)
        print(f"Test 2 result matches: {np.array_equal(result, out)}")
    
    # Test 3: Fragment extraction and tiling
    inp = np.array([[1, 2, 1, 2], [3, 4, 3, 4]])
    out = np.array([[1, 2, 1, 2, 1, 2], 
                    [3, 4, 3, 4, 3, 4],
                    [1, 2, 1, 2, 1, 2], 
                    [3, 4, 3, 4, 3, 4]])
    
    cfg = op.analyze(inp, out)
    print(f"Test 3 config: {cfg}")
    
    if cfg:
        result = op.apply(inp, cfg)
        print(f"Test 3 result matches: {np.array_equal(result, out)}")
