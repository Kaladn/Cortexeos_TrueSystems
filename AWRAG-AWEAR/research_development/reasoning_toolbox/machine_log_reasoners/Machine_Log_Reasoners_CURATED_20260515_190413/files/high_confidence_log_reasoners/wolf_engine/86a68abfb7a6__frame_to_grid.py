"""ARC Frame Grid — frame-to-grid conversion for symbolic reasoning.

Ported from unzipped_cleanup/frame_to_grid.py.
Screen capture requires mss + pillow (optional).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from wolf_engine.modules.base import WolfModule
from wolf_engine.modules.truevision import FrameGrid

try:
    import numpy as np
except ImportError:
    np = None

try:
    import mss
except ImportError:
    mss = None

try:
    from PIL import Image
except ImportError:
    Image = None


# Default ARC-style 10-color palette (RGB)
_DEFAULT_PALETTE = [
    (0, 0, 0),       # 0 = black
    (0, 116, 217),   # 1 = blue
    (255, 65, 54),   # 2 = red
    (46, 204, 64),   # 3 = green
    (255, 220, 0),   # 4 = yellow
    (170, 170, 170), # 5 = grey
    (240, 18, 190),  # 6 = magenta
    (255, 133, 27),  # 7 = orange
    (127, 219, 255), # 8 = cyan
    (135, 12, 37),   # 9 = dark red
]


def quantize_frame(frame_array, grid_size: int = 32, palette=None) -> List[List[int]]:
    """Downsample RGB frame to grid_size x grid_size and quantize to palette indices."""
    if np is None or Image is None:
        return [[0] * grid_size for _ in range(grid_size)]

    palette = palette or _DEFAULT_PALETTE

    img = Image.fromarray(frame_array).resize((grid_size, grid_size), Image.NEAREST)
    arr = np.array(img)

    grid = []
    for y in range(grid_size):
        row = []
        for x in range(grid_size):
            pixel = arr[y, x, :3]
            # Find nearest palette color (L2 distance)
            dists = [sum((int(pixel[c]) - int(p[c])) ** 2 for c in range(3)) for p in palette]
            row.append(int(min(range(len(dists)), key=lambda i: dists[i])))
        grid.append(row)
    return grid


def capture_screen(region: Optional[Tuple[int, int, int, int]] = None,
                   grid_size: int = 32) -> Optional[FrameGrid]:
    """Capture screen region and convert to FrameGrid."""
    if mss is None or np is None or Image is None:
        return None

    import time
    with mss.mss() as sct:
        monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}
        if region:
            monitor = {"left": region[0], "top": region[1],
                       "width": region[2], "height": region[3]}
        shot = sct.grab(monitor)
        frame_array = np.array(shot)[:, :, :3]  # Drop alpha

    grid = quantize_frame(frame_array, grid_size)
    return FrameGrid(
        frame_id=0,
        t_sec=time.time(),
        grid=grid,
        source="screen_capture",
        capture_region=str(monitor),
        h=grid_size,
        w=grid_size,
    )


class ArcModule(WolfModule):
    """WolfModule wrapper for ARC Frame Grid reasoning."""

    key = "rsn_arc"
    name = "ARC Frame Grid"
    category = "reasoning"
    description = "Frame to 32x32 quantized grid (ARC reasoning)"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._grid_size = self._config.get("arc_grid_size", 32)

    def capture(self, region=None) -> Optional[FrameGrid]:
        """Capture screen and return FrameGrid."""
        return capture_screen(region, self._grid_size)

    def quantize(self, frame_array) -> List[List[int]]:
        """Convert RGB frame to quantized grid."""
        return quantize_frame(frame_array, self._grid_size)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "grid_size": self._grid_size,
            "mss_available": mss is not None,
            "pillow_available": Image is not None,
            "numpy_available": np is not None,
        }
