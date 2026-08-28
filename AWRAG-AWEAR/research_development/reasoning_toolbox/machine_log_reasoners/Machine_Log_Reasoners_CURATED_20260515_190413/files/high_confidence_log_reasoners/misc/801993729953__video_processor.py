import cv2
import numpy as np
import time
from threading import Thread, Lock
from queue import Queue
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VideoProcessor')

class VideoProcessor:
    """
    Handles video capture and processing with adaptive frame rate based on activity detection.
    
    Features:
    - Low-resource baseline mode (1 frame per 5 seconds)
    - High-performance mode (up to 60 fps) when activity is detected
    - Frame processing for feature extraction and embedding generation
    """
    
    def __init__(self, camera_id=0, low_fps=0.2, high_fps=30, buffer_size=10):
        """
        Initialize the video processor.
        
        Args:
            camera_id: Camera device ID (default: 0)
            low_fps: Low frame rate for baseline mode (default: 0.2 fps = 1 frame per 5 seconds)
            high_fps: High frame rate for active mode (default: 30 fps)
            buffer_size: Size of the frame buffer (default: 10)
        """
        self.camera_id = camera_id
        self.low_fps = low_fps
        self.high_fps = high_fps
        self.current_fps = low_fps
        
        # Frame buffer and lock
        self.frame_buffer = Queue(maxsize=buffer_size)
        self.lock = Lock()
        
        # Processing state
        self.is_running = False
        self.is_high_performance = False
        
        # Video capture thread
        self.capture_thread = None
        
        # Last processed frame and embedding
        self.last_frame = None
        self.last_embedding = None
        
        logger.info(f"VideoProcessor initialized with camera {camera_id}, low FPS: {low_fps}, high FPS: {high_fps}")
    
    def start(self):
        """Start video capture in a separate thread."""
        if self.is_running:
            logger.warning("Video processor is already running")
            return
        
        self.is_running = True
        self.capture_thread = Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        logger.info("Video capture started")
    
    def stop(self):
        """Stop video capture."""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        logger.info("Video capture stopped")
    
    def set_high_performance_mode(self, enabled=True):
        """
        Switch between low and high performance modes.
        
        Args:
            enabled: True for high performance mode, False for low-resource mode
        """
        with self.lock:
            self.is_high_performance = enabled
            self.current_fps = self.high_fps if enabled else self.low_fps
            mode = "high-performance" if enabled else "low-resource baseline"
            logger.info(f"Switched to {mode} mode at {self.current_fps} fps")
    
    def get_latest_frame(self):
        """Get the most recent frame from the buffer."""
        if not self.frame_buffer.empty():
            self.last_frame = self.frame_buffer.get()
            return self.last_frame
        return self.last_frame
    
    def get_latest_embedding(self):
        """Get the embedding vector for the most recent frame."""
        frame = self.get_latest_frame()
        if frame is not None:
            self.last_embedding = self._extract_features(frame)
            return self.last_embedding
        return self.last_embedding
    
    def _capture_loop(self):
        """Main capture loop that runs in a separate thread."""
        cap = cv2.VideoCapture(self.camera_id)
        
        if not cap.isOpened():
            logger.error(f"Failed to open camera {self.camera_id}")
            self.is_running = False
            return
        
        logger.info(f"Camera {self.camera_id} opened successfully")
        
        last_capture_time = 0
        
        while self.is_running:
            current_time = time.time()
            time_since_last_capture = current_time - last_capture_time
            
            # Determine if we should capture a frame based on current FPS
            if time_since_last_capture >= 1.0 / self.current_fps:
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning("Failed to capture frame")
                    time.sleep(0.1)
                    continue
                
                # Process the frame
                processed_frame = self._preprocess_frame(frame)
                
                # Add to buffer, removing oldest if full
                if self.frame_buffer.full():
                    try:
                        self.frame_buffer.get_nowait()
                    except:
                        pass
                
                self.frame_buffer.put(processed_frame)
                last_capture_time = current_time
            
            # Sleep to avoid busy waiting, but be responsive
            sleep_time = min(0.01, 1.0 / self.current_fps / 2)
            time.sleep(sleep_time)
        
        # Clean up
        cap.release()
        logger.info("Camera released")
    
    def _preprocess_frame(self, frame):
        """
        Preprocess the frame for analysis.
        
        Args:
            frame: Raw frame from the camera
            
        Returns:
            Preprocessed frame
        """
        # Resize for consistency
        frame = cv2.resize(frame, (640, 480))
        
        # Convert to RGB (from BGR)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame
    
    def _extract_features(self, frame):
        """
        Extract feature embedding from a frame.
        
        Args:
            frame: Preprocessed frame
            
        Returns:
            Feature embedding vector (numpy array)
        """
        # In a real implementation, this would use a pre-trained model
        # For this prototype, we'll use a simple placeholder
        
        # Convert to grayscale for simple feature extraction
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # Resize to a smaller dimension for feature extraction
        small = cv2.resize(gray, (32, 32))
        
        # Flatten and normalize to create a simple embedding
        embedding = small.flatten().astype(np.float32) / 255.0
        
        return embedding
    
    def detect_motion(self, sensitivity=0.1):
        """
        Detect motion between consecutive frames.
        
        Args:
            sensitivity: Motion detection sensitivity (0.0 to 1.0)
            
        Returns:
            motion_detected: Boolean indicating if motion was detected
            motion_score: Float indicating the amount of motion (0.0 to 1.0)
        """
        if self.frame_buffer.qsize() < 2:
            return False, 0.0
        
        # Get the two most recent frames
        frames = list(self.frame_buffer.queue)[-2:]
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(frames[0], cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(frames[1], cv2.COLOR_RGB2GRAY)
        
        # Calculate absolute difference
        diff = cv2.absdiff(gray1, gray2)
        
        # Threshold the difference
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # Calculate the percentage of pixels that changed
        motion_score = np.sum(thresh > 0) / thresh.size
        
        # Detect motion if the score exceeds the sensitivity threshold
        motion_detected = motion_score > sensitivity
        
        if motion_detected:
            logger.info(f"Motion detected with score {motion_score:.4f}")
        
        return motion_detected, motion_score


# Example usage
if __name__ == "__main__":
    # Create video processor
    video_processor = VideoProcessor(camera_id=0, low_fps=0.2, high_fps=30)
    
    # Start video capture
    video_processor.start()
    
    try:
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            # Get the latest frame
            frame = video_processor.get_latest_frame()
            
            if frame is not None:
                # Detect motion
                motion_detected, motion_score = video_processor.detect_motion()
                
                # Switch to high performance mode if motion is detected
                if motion_detected:
                    video_processor.set_high_performance_mode(True)
                    # Stay in high performance mode for 5 seconds
                    time.sleep(5)
                    video_processor.set_high_performance_mode(False)
            
            time.sleep(0.1)
    
    finally:
        # Stop video capture
        video_processor.stop()
