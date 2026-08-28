Gaming Domain: Sensor Orchestrator

CORE LOOP: Full 6-stage unified reasoning cycle
  PERCEIVE → REPRESENT → SELECT → APPLY → EVALUATE → UPDATE

Purpose:
  Main daemon that coordinates all gaming operators.
  Captures screen frames, runs detectors, builds fingerprints, logs results.

Components:
  - Frame capture (mss)
  - Grid conversion (32×32 ARC)
  - Operator orchestration (all 5 detectors)
  - Fingerprint construction
  - JSONL logging

Output:
  gaming/logs/gaming_fingerprint_{date}.jsonl
  One record per second with 6 feature scores + metadata

Usage:
  python gaming_sensor.py [--duration SECONDS] [--smoke]
"""

import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import yaml

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from frame_to_grid import FrameCapture, FrameToGrid, FrameGrid

# Import all operators
sys.path.insert(0, str(Path(__file__).parent / "operators"))
from flicker_detector import FlickerDetector, FrameSequence
from hud_stability import HUDStabilityDetector
from crosshair_motion import CrosshairMotionAnalyzer
from peripheral_flash import PeripheralFlashDetector
from color_shift import ColorShiftDetector


class GamingSensor:
    """
    CORE LOOP orchestrator for gaming domain visual reasoning.
    """
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        
        # Load master config
        with open(self.config_path, 'r') as f:
            self.master_config = yaml.safe_load(f)
        
        # Load gaming domain config
        gaming_config_path = Path(__file__).parent / "config.yaml"
        with open(gaming_config_path, 'r') as f:
            self.gaming_config = yaml.safe_load(f)
        
        # Check if gaming domain enabled
        if not self.master_config.get("domains", {}).get("gaming", {}).get("enabled", False):
            raise RuntimeError("Gaming domain is disabled in master config")
        
        # PERCEIVE stage: Frame capture
        self.capturer = FrameCapture(self.master_config)
        self.grid_converter = FrameToGrid(self.master_config)
        
        # APPLY stage: Initialize all operators
        print("[*] Initializing gaming operators...")
        self.operators = {
            "flicker": FlickerDetector(self.gaming_config),
            "hud_stability": HUDStabilityDetector(self.gaming_config),
            "crosshair_motion": CrosshairMotionAnalyzer(self.gaming_config),
            "peripheral_flash": PeripheralFlashDetector(self.gaming_config),
            "color_shift": ColorShiftDetector(self.gaming_config)
        }
        
        # Output configuration
        output_config = self.gaming_config.get("output", {})
        self.fingerprint_interval = output_config.get("fingerprint_interval_sec", 1.0)
        self.log_dir = Path(__file__).parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Frame buffer for windowing
        self.frame_buffer: List[FrameGrid] = []
        self.buffer_duration = self.fingerprint_interval
        
        print(f"[+] GamingSensor initialized")
        print(f"    Fingerprint interval: {self.fingerprint_interval}s")
        print(f"    Log directory: {self.log_dir}")
    
    def _build_fingerprint(self, seq: FrameSequence) -> Dict:
        """
        APPLY + EVALUATE stages: Run all operators and build feature vector.
        