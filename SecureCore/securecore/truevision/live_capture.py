"""TrueVision SC Edition live capture.

The capture backend is expected to provide GPU pre-render RGB state. This module
derives an aspect-preserving grid and emits only a compact state-change record.
"""

from __future__ import annotations

from typing import Callable, Sequence

from securecore.collectors.screen import DEFAULT_ARC_PALETTE, _nearest_palette_index
from securecore.time import utc_now
from securecore.truevision.contracts import build_state_change, grid_hash, validate_state_change


class TrueVisionSCLiveCapture:
    """Small live state-change capture lane."""

    def __init__(
        self,
        *,
        source_id: str,
        session_id: str,
        grid_size: int = 32,
        capture_backend: Callable[[], object | None] | None = None,
        glyph_summary_provider: Callable[[], dict | None] | None = None,
        clock: Callable[[], str] = utc_now,
    ):
        self.source_id = source_id
        self.session_id = session_id
        self.grid_size = max(1, int(grid_size))
        self.capture_backend = capture_backend
        self.glyph_summary_provider = glyph_summary_provider
        self.clock = clock
        self._previous_grid_hash = "GENESIS"
        self._previous_grid: list[list[int]] | None = None
        self._sequence = 0

    def capture_state_change(self, *, change_id: str | None = None) -> dict:
        pixels = self._capture_pixels()
        grid, letterbox_cells = aspect_preserving_grid(pixels, grid_size=self.grid_size)
        current_hash = grid_hash(grid)
        changed_cells = _changed_cell_count(self._previous_grid, grid)
        total_cells = max(1, len(grid) * (len(grid[0]) if grid else self.grid_size))
        self._sequence += 1
        record = build_state_change(
            change_id=change_id or f"{self.session_id}-{self._sequence}",
            source_id=self.source_id,
            session_id=self.session_id,
            observed_at_utc=self.clock(),
            native_geometry=_native_geometry(pixels),
            grid_shape=[len(grid), len(grid[0]) if grid else self.grid_size],
            current_grid_hash=current_hash,
            previous_grid_hash=self._previous_grid_hash,
            changed_cell_count=changed_cells,
            total_cell_count=total_cells,
            letterbox_cell_count=letterbox_cells,
            glyph_summary=self._glyph_summary(),
        )
        self._previous_grid = [list(row) for row in grid]
        self._previous_grid_hash = current_hash
        return validate_state_change(record)

    def _glyph_summary(self) -> dict | None:
        if self.glyph_summary_provider is None:
            return None
        return self.glyph_summary_provider()

    def _capture_pixels(self) -> object:
        if self.capture_backend is None:
            raise RuntimeError("TrueVision SC Edition capture backend is not configured")
        pixels = self.capture_backend()
        if pixels is None:
            return []
        return pixels


def aspect_preserving_grid(frame_pixels: object, *, grid_size: int = 32) -> tuple[list[list[int]], int]:
    grid_size = max(1, int(grid_size))
    pixels = _normalize_pixels(frame_pixels)
    if not pixels:
        return [[0] * grid_size for _ in range(grid_size)], grid_size * grid_size
    src_h = len(pixels)
    src_w = len(pixels[0]) if pixels[0] else 0
    if src_w == 0:
        return [[0] * grid_size for _ in range(grid_size)], grid_size * grid_size

    scale = min(grid_size / src_w, grid_size / src_h)
    out_w = max(1, min(grid_size, int(src_w * scale)))
    out_h = max(1, min(grid_size, int(src_h * scale)))
    x_pad = (grid_size - out_w) // 2
    y_pad = (grid_size - out_h) // 2
    grid = [[0] * grid_size for _ in range(grid_size)]

    for y in range(out_h):
        src_y = min(src_h - 1, (y * src_h) // out_h)
        for x in range(out_w):
            src_x = min(src_w - 1, (x * src_w) // out_w)
            grid[y + y_pad][x + x_pad] = _nearest_palette_index(pixels[src_y][src_x], DEFAULT_ARC_PALETTE)

    return grid, (grid_size * grid_size) - (out_w * out_h)


def _changed_cell_count(previous: list[list[int]] | None, current: list[list[int]]) -> int:
    if previous is None:
        return 0
    count = 0
    for y, row in enumerate(current):
        for x, cell in enumerate(row):
            old = previous[y][x] if y < len(previous) and x < len(previous[y]) else None
            if old != cell:
                count += 1
    return count


def _native_geometry(pixels: object) -> dict[str, int]:
    rows = _as_rows(pixels)
    return {"height": len(rows), "width": len(rows[0]) if rows else 0}


def _as_rows(pixels: object) -> Sequence:
    if hasattr(pixels, "tolist"):
        pixels = pixels.tolist()
    return pixels if isinstance(pixels, list) else []


def _normalize_pixels(frame_pixels: object) -> list[list[tuple[int, int, int]]]:
    rows = _as_rows(frame_pixels)
    normalized = []
    for row in rows:
        normalized_row = []
        for pixel in row:
            normalized_row.append((int(pixel[0]), int(pixel[1]), int(pixel[2])))
        if normalized_row:
            normalized.append(normalized_row)
    return normalized
