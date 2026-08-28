import time
import logging
import threading
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AdaptiveScaler')

class ProcessingMode(Enum):
    """Enum for different processing modes."""
    LOW_RESOURCE = 0
    MEDIUM = 1
    HIGH_PERFORMANCE = 2

class AdaptiveScaler:
    """
    Dynamically scales processing resources based on detected activity.
    
    Features:
    - Seamless transition between low and high performance modes
    - Gradual ramp-up and ramp-down to avoid resource spikes
    - Configurable thresholds and cooldown periods
    """
    
    def __init__(self, video_processor, audio_processor, activity_detector,
                 low_fps=0.2, medium_fps=10, high_fps=60,
                 ramp_up_time=1.0, ramp_down_time=3.0,
                 activity_threshold=0.2, cooldown_period=5.0):
        """
        Initialize the adaptive scaler.
        
        Args:
            video_processor: VideoProcessor instance
            audio_processor: AudioProcessor instance
            activity_detector: ActivityDetector instance
            low_fps: Frame rate for low-resource mode (default: 0.2 fps)
            medium_fps: Frame rate for medium mode (default: 10 fps)
            high_fps: Frame rate for high-performance mode (default: 60 fps)
            ramp_up_time: Time to ramp up from low to high mode in seconds (default: 1.0)
            ramp_down_time: Time to ramp down from high to low mode in seconds (default: 3.0)
            activity_threshold: Activity score threshold to trigger scaling (default: 0.2)
            cooldown_period: Time to stay in high mode after activity stops in seconds (default: 5.0)
        """
        self.video_processor = video_processor
        self.audio_processor = audio_processor
        self.activity_detector = activity_detector
        
        self.low_fps = low_fps
        self.medium_fps = medium_fps
        self.high_fps = high_fps
        
        self.ramp_up_time = ramp_up_time
        self.ramp_down_time = ramp_down_time
        
        self.activity_threshold = activity_threshold
        self.cooldown_period = cooldown_period
        
        # Current state
        self.current_mode = ProcessingMode.LOW_RESOURCE
        self.current_fps = low_fps
        self.last_activity_time = 0
        
        # Scaling thread
        self.scaling_thread = None
        self.is_running = False
        self.lock = threading.Lock()
        
        logger.info(f"AdaptiveScaler initialized with FPS - low: {low_fps}, medium: {medium_fps}, high: {high_fps}")
        logger.info(f"Ramp times - up: {ramp_up_time}s, down: {ramp_down_time}s, cooldown: {cooldown_period}s")
    
    def start(self):
        """Start adaptive scaling in a separate thread."""
        if self.is_running:
            logger.warning("Adaptive scaler is already running")
            return
        
        self.is_running = True
        self.scaling_thread = threading.Thread(target=self._scaling_loop)
        self.scaling_thread.daemon = True
        self.scaling_thread.start()
        logger.info("Adaptive scaling started")
    
    def stop(self):
        """Stop adaptive scaling."""
        self.is_running = False
        if self.scaling_thread:
            self.scaling_thread.join(timeout=1.0)
        logger.info("Adaptive scaling stopped")
    
    def get_current_mode(self):
        """Get the current processing mode."""
        with self.lock:
            return self.current_mode
    
    def _scaling_loop(self):
        """Main scaling loop that runs in a separate thread."""
        while self.is_running:
            try:
                # Check for activity
                activity_detected = self.activity_detector.is_activity_detected()
                activity_score = self.activity_detector.get_activity_score()
                
                # Update last activity time if activity is detected
                if activity_detected and activity_score > self.activity_threshold:
                    self.last_activity_time = time.time()
                
                # Calculate time since last activity
                time_since_activity = time.time() - self.last_activity_time
                
                # Determine target mode based on activity and cooldown
                if time_since_activity < self.cooldown_period:
                    target_mode = ProcessingMode.HIGH_PERFORMANCE
                else:
                    target_mode = ProcessingMode.LOW_RESOURCE
                
                # Scale processing resources
                self._scale_to_mode(target_mode)
                
                # Sleep to avoid busy waiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in adaptive scaling: {e}")
                time.sleep(0.5)
    
    def _scale_to_mode(self, target_mode):
        """
        Scale processing resources to the target mode.
        
        Args:
            target_mode: Target ProcessingMode
        """
        with self.lock:
            current_mode = self.current_mode
        
        # If already in target mode, do nothing
        if current_mode == target_mode:
            return
        
        # Determine target FPS based on mode
        if target_mode == ProcessingMode.LOW_RESOURCE:
            target_fps = self.low_fps
        elif target_mode == ProcessingMode.MEDIUM:
            target_fps = self.medium_fps
        else:  # HIGH_PERFORMANCE
            target_fps = self.high_fps
        
        # Determine ramp time based on direction
        if target_mode.value > current_mode.value:
            # Ramping up
            ramp_time = self.ramp_up_time
            logger.info(f"Ramping up from {current_mode.name} to {target_mode.name} over {ramp_time}s")
        else:
            # Ramping down
            ramp_time = self.ramp_down_time
            logger.info(f"Ramping down from {current_mode.name} to {target_mode.name} over {ramp_time}s")
        
        # Get current FPS
        with self.lock:
            start_fps = self.current_fps
        
        # Calculate FPS steps
        fps_diff = target_fps - start_fps
        steps = int(ramp_time * 10)  # 10 steps per second
        
        if steps > 0:
            fps_step = fps_diff / steps
            
            # Gradually adjust FPS
            for i in range(steps):
                new_fps = start_fps + fps_step * (i + 1)
                
                # Update video processor
                self.video_processor.current_fps = new_fps
                
                # Update current state
                with self.lock:
                    self.current_fps = new_fps
                
                # Sleep for a short time
                time.sleep(ramp_time / steps)
        else:
            # Immediate change
            self.video_processor.current_fps = target_fps
            with self.lock:
                self.current_fps = target_fps
        
        # Update mode
        with self.lock:
            self.current_mode = target_mode
        
        # Set high performance mode in video processor
        self.video_processor.set_high_performance_mode(target_mode == ProcessingMode.HIGH_PERFORMANCE)
        
        logger.info(f"Scaled to {target_mode.name} mode at {target_fps} fps")


# Example usage
if __name__ == "__main__":
    from video_processor import VideoProcessor
    from audio_processor import AudioProcessor
    from activity_detector import ActivityDetector
    
    # Create processors
    video_processor = VideoProcessor(camera_id=0, low_fps=0.2, high_fps=30)
    audio_processor = AudioProcessor(sample_rate=16000, chunk_size=1024)
    
    # Create activity detector
    activity_detector = ActivityDetector(
        video_processor=video_processor,
        audio_processor=audio_processor,
        motion_threshold=0.05,
        audio_threshold=0.3,
        env_change_threshold=0.1,
        combined_threshold=0.2
    )
    
    # Create adaptive scaler
    adaptive_scaler = AdaptiveScaler(
        video_processor=video_processor,
        audio_processor=audio_processor,
        activity_detector=activity_detector,
        low_fps=0.2,
        medium_fps=10,
        high_fps=60,
        ramp_up_time=1.0,
        ramp_down_time=3.0,
        activity_threshold=0.2,
        cooldown_period=5.0
    )
    
    # Start everything
    video_processor.start()
    audio_processor.start()
    activity_detector.start()
    adaptive_scaler.start()
    
    try:
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            # Print current mode and FPS
            mode = adaptive_scaler.get_current_mode()
            print(f"Current mode: {mode.name}, FPS: {video_processor.current_fps:.1f}")
            
            time.sleep(1.0)
    
    finally:
        # Stop everything
        adaptive_scaler.stop()
        activity_detector.stop()
        video_processor.stop()
        audio_processor.stop()
