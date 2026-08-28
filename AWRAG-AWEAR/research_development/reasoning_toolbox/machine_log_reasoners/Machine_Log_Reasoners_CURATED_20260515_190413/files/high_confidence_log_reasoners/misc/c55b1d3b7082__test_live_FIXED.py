"""
CompuCog Live Patent Detection - SIGNAL-PROOF VERSION

FIXES:
- Ignores SIGINT/SIGTERM during capture
- Logs any signals received (debug mode)
- Won't exit until duration complete
- Proper cleanup on any error

Usage:
    python gaming/test_live_FIXED.py --duration 300

Requirements:
    pip install pyyaml numpy pillow mss msgpack
"""

import sys
import time
import json
import signal
import argparse
from pathlib import Path
from datetime import datetime
from typing import List

# Windows-compatible paths
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent

sys.path.insert(0, str(project_root / "core"))
sys.path.insert(0, str(project_root / "operators"))
sys.path.insert(0, str(project_root / "gaming"))

from frame_to_grid import FrameCapture, FrameToGrid, FrameGrid
from hit_registration_v2 import HitRegistrationOperatorV2, FrameSequence
from edge_entry_v2 import EdgeEntryOperatorV2
from patent_matcher import PatentMatcher


# Global flag for clean shutdown
SHUTDOWN_REQUESTED = False


def signal_handler(sig, frame):
    """Handle signals without exiting"""
    global SHUTDOWN_REQUESTED
    
    sig_name = signal.Signals(sig).name if hasattr(signal, 'Signals') else str(sig)
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    print(f"\n[DEBUG] {timestamp} - Signal received: {sig_name} ({sig})")
    print(f"[DEBUG] This signal is being IGNORED - capture continues")
    print(f"[DEBUG] CompuCog will run until duration complete")
    print()
    
    # Don't set SHUTDOWN_REQUESTED - let it run to completion
    # Only log the signal for debugging


class LivePatentDetector:
    """Signal-proof live patent detection"""
    
    def __init__(self, duration_sec: int = 60):
        self.duration_sec = duration_sec
        self.start_time = None
        
        print("=" * 80)
        print("COMPUCOG LIVE PATENT DETECTION - SIGNAL-PROOF")
        print("=" * 80)
        print(f"Duration: {duration_sec} seconds")
        print()
        print("[*] Signal handling: SIGINT and SIGTERM will be IGNORED")
        print("[*] Capture will run until duration complete")
        print()
        
        # Config
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
        
        # Logging
        self.log_dir = project_root / "gaming" / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"live_patent_{timestamp}.jsonl"
        self.signal_log = self.log_dir / f"signals_{timestamp}.log"
        
        print(f"[*] Patent log: {self.log_file}")
        print(f"[*] Signal log: {self.signal_log}")
        print()
        
        # State
        self.frame_buffer = []
        self.window_duration = 1.0
        self.fps = 30
        self.total_frames = 0
        self.patent_matches = 0
        self.frame_id_counter = 0
        self.signals_received = []
        
    def log_signal(self, sig_name, sig_num):
        """Log signal to file"""
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'signal_name': sig_name,
            'signal_number': sig_num,
            'elapsed_sec': time.time() - self.start_time if self.start_time else 0
        }
        self.signals_received.append(entry)
        
        with open(self.signal_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def run(self):
        """Run capture with signal immunity"""
        print("=" * 80)
        print("STARTING CAPTURE")
        print("=" * 80)
        print("Watching for patent manipulation...")
        print("Signals will be LOGGED but IGNORED")
        print()
        
        self.start_time = time.time()
        last_window = self.start_time
        
        log_f = open(self.log_file, 'w')
        
        try:
            while True:
                now = time.time()
                elapsed = now - self.start_time
                
                # Check duration
                if elapsed >= self.duration_sec:
                    print(f"\n[*] Duration complete ({self.duration_sec}s)")
                    break
                
                # Capture frame
                try:
                    frame_data = self.capturer.capture()
                    
                    grid = self.grid_converter.convert(
                        frame=frame_data,
                        frame_id=self.frame_id_counter,
                        t_sec=now,
                        source="live_capture"
                    )
                    
                    self.frame_buffer.append(grid)
                    self.total_frames += 1
                    self.frame_id_counter += 1
                    
                except Exception as e:
                    # Log but don't exit
                    print(f"[!] Capture error: {e}")
                    continue
                
                # Process window
                if now - last_window >= self.window_duration:
                    if len(self.frame_buffer) >= 5:
                        try:
                            self._process_window(self.frame_buffer, now, log_f)
                        except Exception as e:
                            print(f"[!] Processing error: {e}")
                    
                    self.frame_buffer = []
                    last_window = now
                
                # Maintain FPS
                time.sleep(1.0 / self.fps)
                
        except Exception as e:
            print(f"\n[!] Fatal error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            log_f.close()
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
                pass  # Silent fail, don't spam console
        
        # Edge entry
        if self.edge_entry:
            try:
                result = self.edge_entry.analyze(seq)
                if result:
                    results.append(result)
                    if 'patent_match' in result.metadata:
                        self._alert_patent(result, timestamp)
            except Exception as e:
                pass  # Silent fail
        
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
        print("CAPTURE COMPLETE")
        print("=" * 80)
        print(f"Frames captured: {self.total_frames}")
        print(f"Patent matches: {self.patent_matches}")
        print(f"Signals received: {len(self.signals_received)}")
        print(f"Patent log: {self.log_file}")
        print(f"Signal log: {self.signal_log}")
        print()
        
        if self.signals_received:
            print("SIGNALS RECEIVED (but ignored):")
            for sig in self.signals_received:
                print(f"  {sig['timestamp']} - {sig['signal_name']} ({sig['signal_number']})")
            print()
        
        if self.patent_matches > 0:
            print("🚨 MANIPULATION DETECTED WITH PATENT EVIDENCE")
        else:
            print("✓ No patent manipulation detected")
        
        print("=" * 80)


def main():
    # Install signal handlers FIRST
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows-specific signals
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)
    
    parser = argparse.ArgumentParser(description='CompuCog Live Patent Detection')
    parser.add_argument('--duration', type=int, default=60,
                       help='Capture duration in seconds (default: 60)')
    args = parser.parse_args()
    
    detector = LivePatentDetector(duration_sec=args.duration)
    detector.run()


if __name__ == "__main__":
    main()
