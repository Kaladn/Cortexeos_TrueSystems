import numpy as np
import time
import logging
from threading import Thread, Lock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ActivityDetector')

class ActivityDetector:
    """
    Combines video and audio processing to detect activity and trigger high-performance mode.
    
    Features:
    - Motion detection from video frames
    - Audio event detection
    - Environmental change detection
    - Combined activity scoring
    """
    
    def __init__(self, video_processor, audio_processor, 
                 motion_threshold=0.05, audio_threshold=0.3, 
                 env_change_threshold=0.1, combined_threshold=0.2):
        """
        Initialize the activity detector.
        
        Args:
            video_processor: VideoProcessor instance
            audio_processor: AudioProcessor instance
            motion_threshold: Threshold for motion detection (0.0 to 1.0)
            audio_threshold: Threshold for audio event detection (0.0 to 1.0)
            env_change_threshold: Threshold for environmental changes (0.0 to 1.0)
            combined_threshold: Threshold for combined activity score (0.0 to 1.0)
        """
        self.video_processor = video_processor
        self.audio_processor = audio_processor
        
        self.motion_threshold = motion_threshold
        self.audio_threshold = audio_threshold
        self.env_change_threshold = env_change_threshold
        self.combined_threshold = combined_threshold
        
        # Activity state
        self.is_activity_detected = False
        self.activity_score = 0.0
        self.lock = Lock()
        
        # Background model for environmental change detection
        self.background_embedding = None
        self.background_update_rate = 0.01  # Slow update rate for background model
        
        # Detection thread
        self.detection_thread = None
        self.is_running = False
        
        logger.info(f"ActivityDetector initialized with thresholds - motion: {motion_threshold}, "
                   f"audio: {audio_threshold}, env: {env_change_threshold}, combined: {combined_threshold}")
    
    def start(self):
        """Start activity detection in a separate thread."""
        if self.is_running:
            logger.warning("Activity detector is already running")
            return
        
        self.is_running = True
        self.detection_thread = Thread(target=self._detection_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        logger.info("Activity detection started")
    
    def stop(self):
        """Stop activity detection."""
        self.is_running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=1.0)
        logger.info("Activity detection stopped")
    
    def is_activity_detected(self):
        """Check if activity is currently detected."""
        with self.lock:
            return self.is_activity_detected
    
    def get_activity_score(self):
        """Get the current activity score."""
        with self.lock:
            return self.activity_score
    
    def _detection_loop(self):
        """Main detection loop that runs in a separate thread."""
        while self.is_running:
            try:
                # Get latest data
                video_frame = self.video_processor.get_latest_frame()
                audio_chunk = self.audio_processor.get_latest_audio()
                
                if video_frame is not None and audio_chunk is not None:
                    # Detect activity
                    activity_detected, activity_score = self._detect_activity(video_frame, audio_chunk)
                    
                    # Update state
                    with self.lock:
                        self.is_activity_detected = activity_detected
                        self.activity_score = activity_score
                
                # Sleep to avoid busy waiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in activity detection: {e}")
                time.sleep(0.5)
    
    def _detect_activity(self, video_frame, audio_chunk):
        """
        Detect activity based on video and audio data.
        
        Args:
            video_frame: Processed video frame
            audio_chunk: Processed audio chunk
            
        Returns:
            activity_detected: Boolean indicating if activity was detected
            activity_score: Float indicating the activity level (0.0 to 1.0)
        """
        # Detect motion
        motion_detected, motion_score = self.video_processor.detect_motion(sensitivity=self.motion_threshold)
        
        # Detect audio events
        audio_event_detected = self.audio_processor.is_audio_event_detected()
        audio_embedding = self.audio_processor.get_latest_embedding()
        audio_score = np.mean(audio_embedding) if audio_embedding is not None else 0.0
        
        # Detect environmental changes
        env_change_detected, env_change_score = self._detect_environmental_changes(video_frame)
        
        # Calculate combined activity score
        # We weight motion more heavily than audio or environmental changes
        activity_score = 0.5 * motion_score + 0.3 * audio_score + 0.2 * env_change_score
        
        # Detect activity if any individual score exceeds its threshold or the combined score exceeds its threshold
        activity_detected = (
            motion_score > self.motion_threshold or 
            audio_score > self.audio_threshold or 
            env_change_score > self.env_change_threshold or
            activity_score > self.combined_threshold
        )
        
        if activity_detected:
            logger.info(f"Activity detected with score {activity_score:.4f} "
                       f"(motion: {motion_score:.4f}, audio: {audio_score:.4f}, env: {env_change_score:.4f})")
        
        return activity_detected, activity_score
    
    def _detect_environmental_changes(self, video_frame):
        """
        Detect environmental changes by comparing current frame to background model.
        
        Args:
            video_frame: Processed video frame
            
        Returns:
            env_change_detected: Boolean indicating if environmental changes were detected
            env_change_score: Float indicating the level of change (0.0 to 1.0)
        """
        # Extract video embedding
        video_embedding = self.video_processor._extract_features(video_frame)
        
        # Initialize background model if needed
        if self.background_embedding is None:
            self.background_embedding = video_embedding
            return False, 0.0
        
        # Calculate difference from background
        diff = np.abs(video_embedding - self.background_embedding)
        env_change_score = np.mean(diff)
        
        # Update background model slowly
        self.background_embedding = (
            (1 - self.background_update_rate) * self.background_embedding + 
            self.background_update_rate * video_embedding
        )
        
        # Detect environmental changes if the score exceeds the threshold
        env_change_detected = env_change_score > self.env_change_threshold
        
        if env_change_detected:
            logger.info(f"Environmental change detected with score {env_change_score:.4f}")
        
        return env_change_detected, env_change_score


# Example usage
if __name__ == "__main__":
    from video_processor import VideoProcessor
    from audio_processor import AudioProcessor
    
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
    
    # Start processors and detector
    video_processor.start()
    audio_processor.start()
    activity_detector.start()
    
    try:
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            # Check for activity
            if activity_detector.is_activity_detected():
                print(f"Activity detected with score {activity_detector.get_activity_score():.4f}")
            
            time.sleep(0.5)
    
    finally:
        # Stop everything
        activity_detector.stop()
        video_processor.stop()
        audio_processor.stop()
