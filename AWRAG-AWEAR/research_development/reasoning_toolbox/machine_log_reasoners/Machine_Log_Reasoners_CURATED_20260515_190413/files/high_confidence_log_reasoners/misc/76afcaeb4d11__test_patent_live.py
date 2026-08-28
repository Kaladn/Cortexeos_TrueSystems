"""
TrueVision Patent Detection - Live Test (Windows Compatible)

Standalone runner for testing V2 operators with patent detection.
NO Forge Memory dependency.

Usage:
    python gaming/test_patent_live.py --duration 60
"""

import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Windows-compatible path setup
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent

# Add to path
sys.path.insert(0, str(project_root / "core"))
sys.path.insert(0, str(project_root / "operators"))
sys.path.insert(0, str(project_root / "gaming"))

# Now import modules
from frame_to_grid import FrameCapture, FrameToGrid, FrameGrid
from hit_registration_v2 import HitRegistrationOperatorV2, FrameSequence
from edge_entry_v2 import EdgeEntryOperatorV2
from patent_matcher import PatentMatcher


class LivePatentTest:
    """Live patent detection test runner"""
    
    def __init__(self, duration_sec: int = 60):
        self.duration_sec = duration_sec
        
        print("=" * 80)
        print("TRUEVISION PATENT DETECTION - LIVE TEST")
        print("=" * 80)
        print(f"Duration: {duration_sec} seconds")
        print()
        
        # Minimal config
        self.config = {
            "capture": {"monitor": 1, "fps": 30},
            "grid": {"height": 32, "width": 32, "palette_size": 10}
        }
        
        # Initialize capture
        print("[*] Initializing frame capture...")
        self.capturer = FrameCapture(self.config)
        self.grid_converter = FrameToGrid(self.config)
        
        # Initialize V2 operators
        print("[*] Initializing V2 operators...")
        op_config_dir = project_root / "gaming" / "config" / "operators"
        
        self.hit_reg = None
        self.edge_entry = None
        
        try:
            self.hit_reg = HitRegistrationOperatorV2(str(op_config_dir / "hit_registration.yaml"))
            print("    ✓ HitRegistrationOperatorV2")
        except Exception as e:
            print(f"    ✗ HitRegistrationOperatorV2: {e}")
        
        try:
            self.edge_entry = EdgeEntryOperatorV2(str(op_config_dir / "edge_entry.yaml"))
            print("    ✓ EdgeEntryOperatorV2")
        except Exception as e:
            print(f"    ✗ EdgeEntryOperatorV2: {e}")
        
        # Setup logging
        self.log_dir = project_root / "gaming" / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"patent_live_{timestamp}.jsonl"
        
        print(f"[*] Logging to: {self.log_file}")
        print()
        
        # State
        self.frame_buffer = []
        self.window_duration = 1.0
        self.fps = 30
        self.total_frames = 0
        self.patent_matches = 0
        
    def run(self):
        """Run live capture with patent detection"""
        print("=" * 80)
        print("STARTING LIVE CAPTURE")
        print("=" * 80)
        print("Watching for patent manipulation...")
        print("Press Ctrl+C to stop early")
        print()
        
        start_time = time.time()
        last_window = start_time
        
        with open(self.log_file, 'w') as log_f:
            try:
                while True:
                    now = time.time()
                    elapsed = now - start_time
                    
                    if elapsed >= self.duration_sec:
                        break
                    
                    # Capture frame
                    try:
                        frame_data = self.capturer.capture()
                        grid = self.grid_converter.convert(frame_data)
                        self.frame_buffer.append(grid)
                        self.total_frames += 1
                    except Exception as e:
                        print(f"[!] Capture error: {e}")
                        continue
                    
                    # Process window every second
                    if now - last_window >= self.window_duration:
                        if len(self.frame_buffer) >= 5:
                            self._process_window(self.frame_buffer, now, log_f)
                        
                        self.frame_buffer = []
                        last_window = now
                    
                    # Maintain FPS
                    time.sleep(1.0 / self.fps)
                    
            except KeyboardInterrupt:
                print("\n[!] Stopped by user")
        
        self._print_summary()
    
    def _process_window(self, frames, timestamp, log_file):
        """Process frame window"""
        seq = FrameSequence(
            frames=frames,
            t_start=timestamp - self.window_duration,
            t_end=timestamp,
            src="live"
        )
        
        results = []
        
        # Hit registration
        if self.hit_reg:
            try:
                result = self.hit_reg.analyze(seq)
                if result:
                    results.append(result)
                    if 'patent_match' in result.metadata:
                        self._alert_patent(result, timestamp)
            except Exception as e:
                print(f"[!] HitReg error: {e}")
        
        # Edge entry
        if self.edge_entry:
            try:
                result = self.edge_entry.analyze(seq)
                if result:
                    results.append(result)
                    if 'patent_match' in result.metadata:
                        self._alert_patent(result, timestamp)
            except Exception as e:
                print(f"[!] EdgeEntry error: {e}")
        
        # Log
        if results:
            entry = {
                'timestamp': timestamp,
                'frames': len(frames),
                'results': [self._to_dict(r) for r in results]
            }
            log_file.write(json.dumps(entry) + '\n')
            log_file.flush()
    
    def _alert_patent(self, result, timestamp):
        """Alert on patent match"""
        match = result.metadata['patent_match']
        self.patent_matches += 1
        
        print("\n" + "=" * 80)
        print(f"🚨 PATENT MATCH #{self.patent_matches}")
        print("=" * 80)
        print(f"Time: {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")
        print(f"Operator: {result.operator_name}")
        print(f"Signature: {match['signature_id']}")
        print(f"Patent: {match['patent_number']}")
        print(f"Confidence: {match['match_confidence']:.3f}")
        print()
        print(f"Citation: {match['citation'][:150]}...")
        print("=" * 80 + "\n")
    
    def _to_dict(self, result):
        """Serialize result"""
        return {
            'operator': result.operator_name,
            'confidence': result.confidence,
            'flags': [f.name for f in result.flags],
            'metrics': result.metrics,
            'metadata': result.metadata
        }
    
    def _print_summary(self):
        """Print summary"""
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print(f"Frames captured: {self.total_frames}")
        print(f"Patent matches: {self.patent_matches}")
        print(f"Log file: {self.log_file}")
        print()
        
        if self.patent_matches > 0:
            print("🚨 MANIPULATION DETECTED WITH PATENT EVIDENCE")
        else:
            print("✓ No patent manipulation detected")
        
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=60,
                       help='Duration in seconds (default: 60)')
    args = parser.parse_args()
    
    try:
        test = LivePatentTest(duration_sec=args.duration)
        test.run()
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
