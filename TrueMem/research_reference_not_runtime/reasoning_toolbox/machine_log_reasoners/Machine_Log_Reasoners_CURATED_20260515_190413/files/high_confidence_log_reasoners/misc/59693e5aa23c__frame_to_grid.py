╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     CompuCog — Sovereign Cognitive Defense System                           ║
║     Intellectual Property of Cortex Evolved / L.A. Mercey                   ║
║                                                                              ║
║     Copyright © 2025 Cortex Evolved. All Rights Reserved.                   ║
║                                                                              ║
║     "We use unconventional digital wisdom —                                  ║
║        because conventional digital wisdom doesn't protect anyone."         ║
║                                                                              ║
║     This software is proprietary and confidential.                           ║
║     Unauthorized access, copying, modification, or distribution             ║
║     is strictly prohibited and may violate applicable laws.                  ║
║                                                                              ║
║     File automatically watermarked on: 2025-11-29 19:21:12                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""

"""
CompuCog Visual Sensor — Frame-Grid Converter (Module 1)

Purpose:
  Convert raw frames into ARC-style grids for symbolic reasoning.

Responsibilities:
  1. Capture frames from screen or game window
  2. Downsample to small grid (32×32 default)
  3. Quantize colors to palette (0-9 like ARC)
  4. Output FrameGrid objects with metadata
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime
import numpy as np

try:
    import mss
except ImportError:
    print("[ERROR] mss not installed. Run: pip install mss")
    raise

try:
    from PIL import Image
except ImportError:
    print("[ERROR] PIL not installed. Run: pip install pillow")
    raise


@dataclass
class FrameGrid:
    """ARC-style grid representation of a captured frame"""
    frame_id: int
    t_sec: float
    grid: List[List[int]]  # H×W, values 0-9 (or configured palette size)
    source: str
    capture_region: str