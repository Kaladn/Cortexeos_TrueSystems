"""
YOLO Detector Module
CompuCog Multimodal Game Intelligence Engine

YOLOv8 object detection for game elements:
- Player positions
- UI elements  
- Weapon detection
- Motion tracking

Built: November 25, 2025
"""

import numpy as np
import torch
import cv2
from typing import List, Dict, Optional, Tuple
from pathlib import Path

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[WARNING] ultralytics not installed. YOLO detection disabled.")


class YOLODetector:
    """
    Real-time YOLO object detection for game analysis.
    
    Detects and tracks objects in screen frames for 616 fusion.
    """
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence: float = 0.5,
        iou: float = 0.45,
        device: str = "cuda",
        classes: Optional[List[int]] = None,
        skip_frames: int = 1,
        input_resolution: Optional[Tuple[int, int]] = None
    ):
        """
        Args:
            model_path: Path to YOLO model weights
            confidence: Detection confidence threshold
            iou: IoU threshold for NMS
            device: 'cuda' or 'cpu'
            classes: List of class IDs to detect (None = all)
            skip_frames: Run YOLO every Nth frame (1 = every frame)
            input_resolution: Optional (width, height) to resize before YOLO
        """
        if not YOLO_AVAILABLE:
            raise ImportError("ultralytics not installed. Run: pip install ultralytics")
        
        self.model_path = model_path
        self.confidence = confidence
        self.iou = iou
        self.device = device
        self.classes = classes
        self.skip_frames = skip_frames
        self.input_resolution = input_resolution
        self.frame_counter = 0
        self.last_detections = []  # Cache for skipped frames
        
        # Check if model exists, download if needed
        if not Path(model_path).exists() and not model_path.startswith("yolov8"):
            print(f"[WARNING] Model not found: {model_path}")
            print(f"[INFO] Using default YOLOv8n model")
            model_path = "yolov8n.pt"
        
        # Load model
        print(f"[616 YOLO Detector]")
        print(f"  Model: {model_path}")
        print(f"  Device: {device}")
        print(f"  Confidence: {confidence}")
        print(f"  IoU: {iou}")
        
        self.model = YOLO(model_path)
        self.model.to(device)
        
        # Statistics
        self.frames_processed = 0
        self.total_inference_time = 0.0
        
        # Previous detections for tracking
        self.prev_detections = []
        
        print(f"  ✓ Model loaded: {self.model.names}")
    
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Run detection on frame.
        
        Args:
            frame: RGB image (H, W, 3)
        
        Returns:
            List of detections, each dict with:
                - 'bbox': [x1, y1, x2, y2]
                - 'confidence': float
                - 'class_id': int
                - 'class_name': str
                - 'center': [x, y]
                - 'area': float
        """
        self.frame_counter += 1
        
        # Skip frames (reuse cached detections)
        if self.frame_counter % self.skip_frames != 0:
            return self.last_detections
        
        # Downscale frame for YOLO if specified
        if self.input_resolution is not None:
            frame = cv2.resize(frame, self.input_resolution, interpolation=cv2.INTER_AREA)
        import time
        start_time = time.perf_counter()
        
        # Run inference
        results = self.model.predict(
            frame,
            conf=self.confidence,
            iou=self.iou,
            classes=self.classes,
            verbose=False,
            device=self.device
        )
        
        # Parse results
        detections = []
        for result in results:
            boxes = result.boxes
            
            for i in range(len(boxes)):
                bbox = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]
                conf = float(boxes.conf[i].cpu().numpy())
                cls_id = int(boxes.cls[i].cpu().numpy())
                cls_name = self.model.names[cls_id]
                
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                area = (x2 - x1) * (y2 - y1)
                
                detections.append({
                    'bbox': bbox.tolist(),
                    'confidence': conf,
                    'class_id': cls_id,
                    'class_name': cls_name,
                    'center': [center_x, center_y],
                    'area': area
                })
        
        # Update statistics
        inference_time = time.perf_counter() - start_time
        self.frames_processed += 1
        self.total_inference_time += inference_time
        
        # Store for tracking
        self.prev_detections = detections
        
        # Cache for skip frames
        self.last_detections = detections
        
        return detections
    
    def extract_features(self, detections: List[Dict], frame_shape: Tuple[int, int]) -> Dict[str, np.ndarray]:
        """
        Extract feature vector from detections.
        
        Args:
            detections: List of detection dicts from detect()
            frame_shape: (height, width) of frame
        
        Returns:
            Dict with:
                - 'count': Number of detections
                - 'class_histogram': Class count histogram (80 bins for COCO)
                - 'spatial_histogram': 2D spatial histogram (10×10 bins)
                - 'area_stats': [mean, std, max, min] area
                - 'confidence_stats': [mean, std, max, min] confidence
                - 'center_mass': [x, y] center of mass
                - 'feature_vector': Flattened feature vector
        """
        height, width = frame_shape
        
        # Initialize features
        count = len(detections)
        class_histogram = np.zeros(80, dtype=np.float32)  # COCO has 80 classes
        spatial_histogram = np.zeros((10, 10), dtype=np.float32)
        
        if count == 0:
            return {
                'count': 0,
                'class_histogram': class_histogram,
                'spatial_histogram': spatial_histogram,
                'area_stats': np.zeros(4, dtype=np.float32),
                'confidence_stats': np.zeros(4, dtype=np.float32),
                'center_mass': np.array([width / 2, height / 2], dtype=np.float32),
                'feature_vector': np.concatenate([
                    [0],  # count
                    class_histogram,  # 80
                    spatial_histogram.flatten(),  # 100
                    np.zeros(4),  # area_stats
                    np.zeros(4),  # confidence_stats
                    [width / 2, height / 2]  # center_mass
                ])  # Total: 191 features
            }
        
        # Compute features
        areas = []
        confidences = []
        centers_x = []
        centers_y = []
        
        for det in detections:
            # Class histogram
            class_histogram[det['class_id']] += 1
            
            # Spatial histogram (10×10 grid)
            cx, cy = det['center']
            grid_x = int((cx / width) * 10)
            grid_y = int((cy / height) * 10)
            grid_x = min(grid_x, 9)
            grid_y = min(grid_y, 9)
            spatial_histogram[grid_y, grid_x] += 1
            
            # Statistics
            areas.append(det['area'])
            confidences.append(det['confidence'])
            centers_x.append(cx)
            centers_y.append(cy)
        
        # Compute stats
        area_stats = np.array([
            np.mean(areas),
            np.std(areas),
            np.max(areas),
            np.min(areas)
        ], dtype=np.float32)
        
        confidence_stats = np.array([
            np.mean(confidences),
            np.std(confidences),
            np.max(confidences),
            np.min(confidences)
        ], dtype=np.float32)
        
        center_mass = np.array([
            np.mean(centers_x),
            np.mean(centers_y)
        ], dtype=np.float32)
        
        # Flatten to feature vector
        feature_vector = np.concatenate([
            [count],  # 1
            class_histogram,  # 80
            spatial_histogram.flatten(),  # 100
            area_stats,  # 4
            confidence_stats,  # 4
            center_mass  # 2
        ])  # Total: 191 features
        
        return {
            'count': count,
            'class_histogram': class_histogram,
            'spatial_histogram': spatial_histogram,
            'area_stats': area_stats,
            'confidence_stats': confidence_stats,
            'center_mass': center_mass,
            'feature_vector': feature_vector
        }
    
    def visualize_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Draw bounding boxes on frame.
        
        Args:
            frame: RGB image (H, W, 3)
            detections: List of detection dicts
        
        Returns:
            np.ndarray: Frame with bounding boxes
        """
        vis_frame = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det['bbox']]
            conf = det['confidence']
            cls_name = det['class_name']
            
            # Draw box
            color = (0, 255, 0)
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{cls_name} {conf:.2f}"
            cv2.putText(vis_frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return vis_frame
    
    def get_statistics(self) -> Dict[str, float]:
        """
        Get inference statistics.
        
        Returns:
            Dict with frame count, average FPS, average inference time
        """
        if self.frames_processed == 0:
            return {
                'frames_processed': 0,
                'avg_fps': 0.0,
                'avg_inference_time_ms': 0.0
            }
        
        avg_inference_time = self.total_inference_time / self.frames_processed
        avg_fps = 1.0 / avg_inference_time if avg_inference_time > 0 else 0.0
        
        return {
            'frames_processed': self.frames_processed,
            'avg_fps': avg_fps,
            'avg_inference_time_ms': avg_inference_time * 1000
        }


if __name__ == "__main__":
    """Test YOLO detector."""
    
    if not YOLO_AVAILABLE:
        print("ultralytics not installed. Exiting.")
        exit(1)
    
    print("Testing 616 YOLO Detector...")
    print("Capturing webcam (press 'q' to quit)\n")
    
    # Initialize detector
    detector = YOLODetector(
        model_path="yolov8n.pt",
        confidence=0.5,
        device="cuda" if torch.cuda.is_available() else "cpu"
    )
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect
            detections = detector.detect(frame_rgb)
            
            # Extract features
            features = detector.extract_features(detections, frame_rgb.shape[:2])
            
            # Visualize
            vis_frame = detector.visualize_detections(frame_rgb, detections)
            vis_frame = cv2.cvtColor(vis_frame, cv2.COLOR_RGB2BGR)
            
            # Print stats
            if detector.frames_processed % 30 == 0:
                stats = detector.get_statistics()
                print(f"[Frame {stats['frames_processed']:>5}] "
                      f"FPS: {stats['avg_fps']:>6.1f} | "
                      f"Inference: {stats['avg_inference_time_ms']:>5.2f}ms | "
                      f"Detections: {features['count']}")
            
            # Show
            cv2.imshow('616 YOLO Detector', vis_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    
    finally:
        stats = detector.get_statistics()
        print(f"\n[Final Stats]")
        print(f"  Frames processed: {stats['frames_processed']}")
        print(f"  Average FPS: {stats['avg_fps']:.1f}")
        print(f"  Average inference time: {stats['avg_inference_time_ms']:.2f}ms")
        
        cap.release()
        cv2.destroyAllWindows()
