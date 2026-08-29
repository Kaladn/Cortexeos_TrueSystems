import time
import logging
import os
import threading
import signal
import sys

# Import all components
from video_processor import VideoProcessor
from audio_processor import AudioProcessor
from activity_detector import ActivityDetector
from adaptive_scaler import AdaptiveScaler, ProcessingMode
from vector_fusion import VectorFusion, FusionMethod
from feedback_loop import FeedbackLoop

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("adaptive_av_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AdaptiveAVSystem')

class AdaptiveAVSystem:
    """
    Main system class that integrates all components of the Adaptive Live Video and Audio Feed Processing system.
    
    Features:
    - Integrated video and audio processing
    - Activity-based adaptive processing
    - Vector fusion for multimodal analysis
    - Reinforcement learning feedback loop
    - Graceful shutdown handling
    """
    
    def __init__(self, camera_id=0, sample_rate=16000, chunk_size=1024,
                 low_fps=0.2, medium_fps=10, high_fps=60,
                 fusion_method=FusionMethod.WEIGHTED_AVERAGE,
                 data_dir='./data'):
        """
        Initialize the Adaptive AV System.
        
        Args:
            camera_id: Camera device ID (default: 0)
            sample_rate: Audio sample rate in Hz (default: 16000)
            chunk_size: Audio chunk size (default: 1024)
            low_fps: Frame rate for low-resource mode (default: 0.2 fps)
            medium_fps: Frame rate for medium mode (default: 10 fps)
            high_fps: Frame rate for high-performance mode (default: 60 fps)
            fusion_method: Method to use for vector fusion (default: WEIGHTED_AVERAGE)
            data_dir: Directory for storing data and models (default: './data')
        """
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        logger.info("Initializing system components...")
        
        # Video and audio processors
        self.video_processor = VideoProcessor(
            camera_id=camera_id,
            low_fps=low_fps,
            high_fps=high_fps
        )
        
        self.audio_processor = AudioProcessor(
            sample_rate=sample_rate,
            chunk_size=chunk_size
        )
        
        # Activity detector
        self.activity_detector = ActivityDetector(
            video_processor=self.video_processor,
            audio_processor=self.audio_processor,
            motion_threshold=0.05,
            audio_threshold=0.3,
            env_change_threshold=0.1,
            combined_threshold=0.2
        )
        
        # Adaptive scaler
        self.adaptive_scaler = AdaptiveScaler(
            video_processor=self.video_processor,
            audio_processor=self.audio_processor,
            activity_detector=self.activity_detector,
            low_fps=low_fps,
            medium_fps=medium_fps,
            high_fps=high_fps,
            ramp_up_time=1.0,
            ramp_down_time=3.0,
            activity_threshold=0.2,
            cooldown_period=5.0
        )
        
        # Vector fusion
        self.vector_fusion = VectorFusion(
            video_processor=self.video_processor,
            audio_processor=self.audio_processor,
            fusion_method=fusion_method,
            video_weight=0.6,
            audio_weight=0.4,
            fusion_interval=0.2
        )
        
        # Feedback loop
        self.feedback_loop = FeedbackLoop(
            activity_detector=self.activity_detector,
            adaptive_scaler=self.adaptive_scaler,
            vector_fusion=self.vector_fusion,
            learning_rate=0.01,
            discount_factor=0.9,
            exploration_rate=0.2,
            min_exploration_rate=0.01,
            exploration_decay=0.995,
            update_interval=5.0,
            model_save_path=os.path.join(data_dir, 'feedback_model.pkl')
        )
        
        # System state
        self.is_running = False
        self.status_thread = None
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("System initialization complete")
    
    def start(self):
        """Start the Adaptive AV System."""
        if self.is_running:
            logger.warning("System is already running")
            return
        
        logger.info("Starting Adaptive AV System...")
        
        # Start all components
        self.video_processor.start()
        self.audio_processor.start()
        self.activity_detector.start()
        self.adaptive_scaler.start()
        self.vector_fusion.start()
        self.feedback_loop.start()
        
        # Start status reporting thread
        self.is_running = True
        self.status_thread = threading.Thread(target=self._status_reporting)
        self.status_thread.daemon = True
        self.status_thread.start()
        
        logger.info("Adaptive AV System started successfully")
    
    def stop(self):
        """Stop the Adaptive AV System."""
        if not self.is_running:
            logger.warning("System is not running")
            return
        
        logger.info("Stopping Adaptive AV System...")
        
        # Stop all components in reverse order
        self.is_running = False
        
        if self.status_thread:
            self.status_thread.join(timeout=1.0)
        
        self.feedback_loop.stop()
        self.vector_fusion.stop()
        self.adaptive_scaler.stop()
        self.activity_detector.stop()
        self.audio_processor.stop()
        self.video_processor.stop()
        
        logger.info("Adaptive AV System stopped successfully")
    
    def _status_reporting(self):
        """Thread for periodic status reporting."""
        while self.is_running:
            try:
                # Get current status
                mode = self.adaptive_scaler.get_current_mode()
                fps = self.video_processor.current_fps
                activity_score = self.activity_detector.get_activity_score()
                threat_level = self.vector_fusion.get_threat_level()
                
                # Get performance metrics
                metrics = self.feedback_loop.get_performance_metrics()
                
                # Calculate accuracy if possible
                total = sum([
                    metrics['true_positives'], 
                    metrics['true_negatives'], 
                    metrics['false_positives'], 
                    metrics['false_negatives']
                ])
                
                if total > 0:
                    accuracy = (metrics['true_positives'] + metrics['true_negatives']) / total
                else:
                    accuracy = 0.0
                
                # Log status
                logger.info(
                    f"Status: Mode={mode.name}, FPS={fps:.1f}, Activity={activity_score:.3f}, "
                    f"Threat={threat_level:.3f}, Accuracy={accuracy:.3f}"
                )
                
                # Sleep for a while
                time.sleep(5.0)
                
            except Exception as e:
                logger.error(f"Error in status reporting: {e}")
                time.sleep(1.0)
    
    def _signal_handler(self, sig, frame):
        """Handle signals for graceful shutdown."""
        logger.info(f"Received signal {sig}, shutting down...")
        self.stop()
        sys.exit(0)


def main():
    """Main function to run the Adaptive AV System."""
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Adaptive Live Video and Audio Feed Processing System')
    parser.add_argument('--camera', type=int, default=0, help='Camera device ID')
    parser.add_argument('--sample-rate', type=int, default=16000, help='Audio sample rate in Hz')
    parser.add_argument('--low-fps', type=float, default=0.2, help='Frame rate for low-resource mode')
    parser.add_argument('--high-fps', type=float, default=60, help='Frame rate for high-performance mode')
    parser.add_argument('--fusion-method', type=str, default='WEIGHTED_AVERAGE', 
                        choices=['CONCATENATION', 'WEIGHTED_AVERAGE', 'ATTENTION', 'GATING'],
                        help='Vector fusion method')
    parser.add_argument('--data-dir', type=str, default='./data', help='Directory for storing data and models')
    parser.add_argument('--runtime', type=int, default=0, help='Runtime in seconds (0 for indefinite)')
    
    args = parser.parse_args()
    
    # Map fusion method string to enum
    fusion_method_map = {
        'CONCATENATION': FusionMethod.CONCATENATION,
        'WEIGHTED_AVERAGE': FusionMethod.WEIGHTED_AVERAGE,
        'ATTENTION': FusionMethod.ATTENTION,
        'GATING': FusionMethod.GATING
    }
    
    fusion_method = fusion_method_map[args.fusion_method]
    
    # Create and start the system
    system = AdaptiveAVSystem(
        camera_id=args.camera,
        sample_rate=args.sample_rate,
        low_fps=args.low_fps,
        high_fps=args.high_fps,
        fusion_method=fusion_method,
        data_dir=args.data_dir
    )
    
    system.start()
    
    try:
        # Run for specified time or indefinitely
        if args.runtime > 0:
            logger.info(f"Running for {args.runtime} seconds...")
            time.sleep(args.runtime)
            system.stop()
        else:
            logger.info("Running indefinitely (press Ctrl+C to stop)...")
            # Keep the main thread alive
            while True:
                time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        system.stop()


if __name__ == "__main__":
    main()
