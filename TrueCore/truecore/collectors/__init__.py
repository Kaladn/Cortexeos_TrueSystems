"""Collector adapters for TrueCore sensor inputs.

Collectors gather local sensor metadata and write structured records into
substrates through permission-gated writers. They do not interpret signals.
"""

from truecore.collectors.desktop import DesktopCollector, DesktopSnapshot
from truecore.collectors.keyboard_mouse import (
    KeyboardActivitySample,
    KeyboardMouseCollector,
    MouseActivitySample,
)
from truecore.collectors.screen import ScreenCaptureSample, ScreenCollector

__all__ = [
    "DesktopCollector",
    "DesktopSnapshot",
    "KeyboardActivitySample",
    "KeyboardMouseCollector",
    "MouseActivitySample",
    "ScreenCaptureSample",
    "ScreenCollector",
]
