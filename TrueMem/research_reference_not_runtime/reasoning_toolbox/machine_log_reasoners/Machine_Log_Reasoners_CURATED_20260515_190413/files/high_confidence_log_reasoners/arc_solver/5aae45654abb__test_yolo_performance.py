"""
Test YOLO performance at different resolutions to determine optimal settings.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

import numpy as np
import time
from modules.yolo_detector import YOLODetector

def test_resolution(width, height, num_runs=10):
    """Test YOLO at specific resolution."""
    print(f"\n{'='*60}")
    print(f"Testing: {width}×{height}")
    print(f"{'='*60}")
    
    # Create detector
    detector = YOLODetector(device='cuda', confidence=0.5)
    
    # Generate random test frame
    frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    # Warmup run (first inference is always slower)
    print("Warmup run...")
    detector.detect(frame)
    
    # Timed runs
    times = []
    detection_counts = []
    
    print(f"Running {num_runs} inference tests...")
    for i in range(num_runs):
        t0 = time.time()
        detections = detector.detect(frame)
        t1 = time.time()
        
        elapsed_ms = (t1 - t0) * 1000
        times.append(elapsed_ms)
        detection_counts.append(len(detections))
        
        if (i + 1) % 5 == 0:
            print(f"  Run {i+1}/{num_runs}: {elapsed_ms:.1f}ms, {len(detections)} detections")
    
    # Statistics
    avg_time = np.mean(times)
    std_time = np.std(times)
    min_time = np.min(times)
    max_time = np.max(times)
    fps = 1000 / avg_time
    
    print(f"\nResults:")
    print(f"  Average: {avg_time:.1f}ms ± {std_time:.1f}ms")
    print(f"  Range: {min_time:.1f}ms - {max_time:.1f}ms")
    print(f"  FPS: {fps:.1f}")
    print(f"  Avg detections: {np.mean(detection_counts):.1f}")
    
    return {
        'resolution': f'{width}×{height}',
        'avg_ms': avg_time,
        'std_ms': std_time,
        'fps': fps,
        'min_ms': min_time,
        'max_ms': max_time
    }

if __name__ == "__main__":
    print("="*60)
    print("YOLO Performance Test - RTX 4080")
    print("="*60)
    
    # Test different resolutions
    resolutions = [
        (640, 360),    # Low (Play Nice - every 4th frame)
        (960, 540),    # Medium (Forensic - every 2nd frame)
        (1280, 720),   # High (occasional use)
        (1920, 1080),  # Native (reference)
    ]
    
    results = []
    for width, height in resolutions:
        result = test_resolution(width, height, num_runs=10)
        results.append(result)
    
    # Summary table
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Resolution':<15} {'Avg Time':<12} {'FPS':<8} {'Range':<20}")
    print("-"*60)
    
    for r in results:
        print(f"{r['resolution']:<15} {r['avg_ms']:>6.1f}ms     {r['fps']:>5.1f}    "
              f"{r['min_ms']:.1f}-{r['max_ms']:.1f}ms")
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    # Find optimal resolutions
    for r in results:
        if r['avg_ms'] < 10:
            print(f"✅ {r['resolution']}: EXCELLENT - {r['fps']:.0f} FPS (every frame)")
        elif r['avg_ms'] < 20:
            print(f"✅ {r['resolution']}: GOOD - {r['fps']:.0f} FPS (every 2nd frame = {r['fps']/2:.0f} effective FPS)")
        elif r['avg_ms'] < 40:
            print(f"⚠️  {r['resolution']}: ACCEPTABLE - {r['fps']:.0f} FPS (every 4th frame = {r['fps']/4:.0f} effective FPS)")
        else:
            print(f"❌ {r['resolution']}: TOO SLOW - {r['fps']:.0f} FPS (not recommended)")
    
    print("\n" + "="*60)
    print("PROFILE RECOMMENDATIONS")
    print("="*60)
    print("Play Nice Profile:")
    print("  - YOLO input: 640×360")
    print("  - Skip frames: 4")
    print(f"  - Effective YOLO FPS: ~{results[0]['fps']/4:.1f} (if capture is 20 FPS)")
    print()
    print("Forensic Profile:")
    print("  - YOLO input: 960×540")
    print("  - Skip frames: 2")
    print(f"  - Effective YOLO FPS: ~{results[1]['fps']/2:.1f} (if capture is 15 FPS)")
