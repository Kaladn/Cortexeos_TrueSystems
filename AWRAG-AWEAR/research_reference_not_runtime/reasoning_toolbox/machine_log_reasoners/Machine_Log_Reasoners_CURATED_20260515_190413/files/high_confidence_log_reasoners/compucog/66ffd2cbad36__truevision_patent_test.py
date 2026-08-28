"""
TrueVision Patent Detection Test Script

Standalone runner for testing V2 operators with patent detection.
NO Forge Memory dependency - pure operator testing.

Usage:
    python gaming/truevision_patent_test.py --duration 60

Output:
    - Console: Real-time patent matches
    - File: gaming/logs/patent_detections_{timestamp}.jsonl
"""

import sys
import time
import json
import argparse
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


def signal_handler(sig, frame):
    """Log signals but don't exit - user plays with controller, not keyboard"""
    sig_name = signal.Signals(sig).name if hasattr(signal, 'Signals') else str(sig)
    print(f"\n[DEBUG] Signal {sig_name} ({sig}) received - IGNORING (controller input not keyboard)")
    # Don't exit, just log for debugging

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "core"))
sys.path.insert(0, str(Path(__file__).parent / "operators"))
sys.path.insert(0, str(Path(__file__).parent / "gaming"))

from frame_to_grid import FrameCapture, FrameToGrid, FrameGrid
from hit_registration_v2 import HitRegistrationOperatorV2, FrameSequence
from edge_entry_v2 import EdgeEntryOperatorV2
from patent_matcher import PatentMatcher


class TrueVisionPatentTest:
    """
    Standalone TrueVision runner for patent detection testing.
    """
    
    def __init__(self, duration_sec: int = 60):
        self.duration_sec = duration_sec
        
        print("=" * 80)
        print("TRUEVISION PATENT DETECTION TEST")
        print("=" * 80)
        print(f"Duration: {duration_sec} seconds")
        print()
        
        # Initialize frame capture
        print("[*] Initializing frame capture...")
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        
        # Minimal config for testing
        self.config = {
            "capture": {
                "monitor": 1,
                "fps": 30
            },
            "grid": {
                "height": 32,
                "width": 32,
                "palette_size": 10
            }
        }
        
        self.capturer = FrameCapture(self.config)
        self.grid_converter = FrameToGrid(self.config)
        
        # Initialize V2 operators
        print("[*] Initializing V2 operators...")
        op_config_path = Path(__file__).parent / "gaming" / "config" / "operators"
        
        try:
            self.hit_reg = HitRegistrationOperatorV2(
                str(op_config_path / "hit_registration.yaml")
            )
            print("    ✓ HitRegistrationOperatorV2 loaded")
        except Exception as e:
            print(f"    ✗ HitRegistrationOperatorV2 failed: {e}")
            self.hit_reg = None
        
        try:
            self.edge_entry = EdgeEntryOperatorV2(
                str(op_config_path / "edge_entry.yaml")
            )
            print("    ✓ EdgeEntryOperatorV2 loaded")
        except Exception as e:
            print(f"    ✗ EdgeEntryOperatorV2 failed: {e}")
            self.edge_entry = None
        
        # Setup logging
        self.log_dir = Path(__file__).parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"patent_detections_{timestamp}.jsonl"
        
        print(f"[*] Logging to: {self.log_file}")
        print()
        
        # Frame buffer
        self.frame_buffer: List[FrameGrid] = []
        self.window_duration = 1.0  # 1 second windows
        self.fps = 30
        
        # Stats
        self.total_frames = 0
        self.patent_matches = 0
        
    def run(self):
        """Run patent detection test"""
        print("=" * 80)
        print("STARTING CAPTURE")
        print("=" * 80)
        print("Watching for patent-documented manipulation...")
        print()
        
        start_time = time.time()
        last_window_time = start_time
        last_status = start_time
        
        try:
            with open(self.log_file, 'w') as log_f:
                while True:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # Status update every 30 seconds
                    if current_time - last_status >= 30:
                        print(f"[{int(elapsed)}s] Frames: {self.total_frames} | Matches: {self.patent_matches}")
                        last_status = current_time
                    
                    # Check duration
                    if elapsed >= self.duration_sec:
                        print(f"\n[+] Duration complete: {int(elapsed)} seconds")
                        break
                    
                    # Capture frame
                    try:
                        frame_data = self.capturer.capture()
                        grid = self.grid_converter.convert(
                            frame_data, 
                            frame_id=self.total_frames,
                            t_sec=current_time,
                            source="live_capture"
                        )
                        
                        self.frame_buffer.append(grid)
                        self.total_frames += 1
                        
                    except Exception as e:
                        print(f"[!] Capture error: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                    
                    # Process window every second
                    if current_time - last_window_time >= self.window_duration:
                        if len(self.frame_buffer) >= 5:  # Minimum frames
                            try:
                                self._process_window(self.frame_buffer, current_time, log_f)
                            except Exception as e:
                                print(f"[!] Window processing error: {e}")
                                import traceback
                                traceback.print_exc()
                        
                        # Clear buffer
                        self.frame_buffer = []
                        last_window_time = current_time
                    
                    # Sleep to maintain FPS
                    time.sleep(1.0 / self.fps)
        
        except Exception as e:
            print(f"\n\n[!] FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Final summary
            self._print_summary()
    
    def _process_window(self, frames: List[FrameGrid], timestamp: float, log_file):
        """Process frame window with V2 operators"""
        
        seq = FrameSequence(
            frames=frames,
            t_start=timestamp - self.window_duration,
            t_end=timestamp,
            src="live_capture"
        )
        
        results = []
        
        # Run hit registration
        if self.hit_reg:
            try:
                result = self.hit_reg.analyze(seq)
                if result:
                    results.append(result)
                    
                    # Check for patent match
                    if 'patent_match' in result.metadata:
                        self._handle_patent_match(result, timestamp)
                        
            except Exception as e:
                print(f"[!] HitReg error: {e}")
        
        # Run edge entry
        if self.edge_entry:
            try:
                result = self.edge_entry.analyze(seq)
                if result:
                    results.append(result)
                    
                    # Check for patent match
                    if 'patent_match' in result.metadata:
                        self._handle_patent_match(result, timestamp)
                        
            except Exception as e:
                print(f"[!] EdgeEntry error: {e}")
        
        # Log results
        if results:
            log_entry = {
                'timestamp': timestamp,
                'frames_analyzed': len(frames),
                'results': [self._serialize_result(r) for r in results]
            }
            log_file.write(json.dumps(log_entry) + '\n')
            log_file.flush()
    
    def _handle_patent_match(self, result, timestamp):
        """Handle patent match detection"""
        match = result.metadata['patent_match']
        
        self.patent_matches += 1
        
        print("=" * 80)
        print(f"🚨 PATENT MATCH DETECTED #{self.patent_matches}")
        print("=" * 80)
        print(f"Time: {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")
        print(f"Operator: {result.operator_name}")
        print(f"Signature: {match['signature_id']}")
        print(f"Patent: {match['patent_number']} {match.get('patent_paragraph', '')}")
        print(f"Method: {match['manipulation_method']}")
        print(f"Confidence: {match['match_confidence']:.3f}")
        print()
        print(f"Citation:")
        print(f"  {match['citation']}")
        print("=" * 80)
        print()
    
    def _serialize_result(self, result) -> Dict:
        """Serialize OperatorResult to dict"""
        return {
            'operator_name': result.operator_name,
            'confidence': result.confidence,
            'flags': [f.name if hasattr(f, 'name') else str(f) for f in result.flags],
            'metrics': result.metrics,
            'metadata': result.metadata
        }
    
    def _print_summary(self):
        """Print final summary"""
        print()
        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print(f"Total frames captured: {self.total_frames}")
        print(f"Patent matches detected: {self.patent_matches}")
        print(f"Log file: {self.log_file}")
        print()
        
        if self.patent_matches > 0:
            print("🚨 MANIPULATION DETECTED WITH PATENT EVIDENCE")
            print("Review log file for detailed citations.")
        else:
            print("✓ No patent-documented manipulation detected")
            print("(Either no manipulation present, or thresholds not met)")
        
        print("=" * 80)


def main():
    # Install signal handlers FIRST - ignore signals, don't exit
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)
    
    parser = argparse.ArgumentParser(description='TrueVision Patent Detection Test')
    parser.add_argument('--duration', type=int, default=60,
                       help='Test duration in seconds (default: 60)')
    
    args = parser.parse_args()
    
    try:
        test = TrueVisionPatentTest(duration_sec=args.duration)
        test.run()
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()