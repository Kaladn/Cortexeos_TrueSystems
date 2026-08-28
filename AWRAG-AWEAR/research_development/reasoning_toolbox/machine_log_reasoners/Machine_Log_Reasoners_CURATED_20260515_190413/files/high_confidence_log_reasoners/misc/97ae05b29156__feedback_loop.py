import numpy as np
import time
import logging
import threading
import pickle
import os
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FeedbackLoop')

class FeedbackLoop:
    """
    Implements a reinforcement learning-based feedback loop for adaptive sensitivity tuning.
    
    Features:
    - Continuous learning via reinforcement learning
    - Automatic sensitivity adjustment based on performance
    - Persistence of learned parameters
    - Performance metrics tracking
    """
    
    def __init__(self, activity_detector, adaptive_scaler, vector_fusion,
                 learning_rate=0.01, discount_factor=0.9,
                 exploration_rate=0.2, min_exploration_rate=0.01,
                 exploration_decay=0.995, update_interval=5.0,
                 model_save_path='./data/feedback_model.pkl'):
        """
        Initialize the feedback loop system.
        
        Args:
            activity_detector: ActivityDetector instance
            adaptive_scaler: AdaptiveScaler instance
            vector_fusion: VectorFusion instance
            learning_rate: Learning rate for RL algorithm (default: 0.01)
            discount_factor: Discount factor for future rewards (default: 0.9)
            exploration_rate: Initial exploration rate (default: 0.2)
            min_exploration_rate: Minimum exploration rate (default: 0.01)
            exploration_decay: Rate at which exploration decreases (default: 0.995)
            update_interval: Time between parameter updates in seconds (default: 5.0)
            model_save_path: Path to save the learned model (default: './data/feedback_model.pkl')
        """
        self.activity_detector = activity_detector
        self.adaptive_scaler = adaptive_scaler
        self.vector_fusion = vector_fusion
        
        # RL parameters
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.min_exploration_rate = min_exploration_rate
        self.exploration_decay = exploration_decay
        
        # Update parameters
        self.update_interval = update_interval
        self.model_save_path = model_save_path
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.model_save_path), exist_ok=True)
        
        # State and action space
        self.state_dim = 4  # activity_score, current_fps, threat_level, time_since_activity
        self.action_dim = 3  # decrease, maintain, increase sensitivity
        
        # Q-table for RL
        self.q_table = {}
        
        # Load existing model if available
        self._load_model()
        
        # Performance metrics
        self.metrics = {
            'false_positives': 0,
            'false_negatives': 0,
            'true_positives': 0,
            'true_negatives': 0,
            'resource_usage': []
        }
        
        # Experience replay buffer
        self.experience_buffer = deque(maxlen=100)
        
        # Feedback loop thread
        self.feedback_thread = None
        self.is_running = False
        self.lock = threading.Lock()
        
        # Last update time
        self.last_update_time = 0
        
        logger.info(f"FeedbackLoop initialized with learning rate: {learning_rate}, "
                   f"discount factor: {discount_factor}, exploration rate: {exploration_rate}")
    
    def start(self):
        """Start feedback loop in a separate thread."""
        if self.is_running:
            logger.warning("Feedback loop is already running")
            return
        
        self.is_running = True
        self.feedback_thread = threading.Thread(target=self._feedback_loop)
        self.feedback_thread.daemon = True
        self.feedback_thread.start()
        logger.info("Feedback loop started")
    
    def stop(self):
        """Stop feedback loop."""
        self.is_running = False
        if self.feedback_thread:
            self.feedback_thread.join(timeout=1.0)
        
        # Save model before stopping
        self._save_model()
        
        logger.info("Feedback loop stopped")
    
    def get_performance_metrics(self):
        """Get current performance metrics."""
        with self.lock:
            return self.metrics.copy()
    
    def _feedback_loop(self):
        """Main feedback loop that runs in a separate thread."""
        while self.is_running:
            try:
                current_time = time.time()
                
                # Check if it's time to update parameters
                if current_time - self.last_update_time >= self.update_interval:
                    # Get current state
                    state = self._get_current_state()
                    
                    # Choose action based on current state
                    action = self._select_action(state)
                    
                    # Apply action
                    self._apply_action(action)
                    
                    # Wait for effect and observe new state
                    time.sleep(1.0)
                    new_state = self._get_current_state()
                    
                    # Calculate reward
                    reward = self._calculate_reward(state, action, new_state)
                    
                    # Update Q-table
                    self._update_q_table(state, action, reward, new_state)
                    
                    # Add to experience buffer
                    self.experience_buffer.append((state, action, reward, new_state))
                    
                    # Perform experience replay
                    self._experience_replay()
                    
                    # Update metrics
                    self._update_metrics(state, action, new_state)
                    
                    # Decay exploration rate
                    self.exploration_rate = max(
                        self.min_exploration_rate,
                        self.exploration_rate * self.exploration_decay
                    )
                    
                    # Save model periodically
                    if len(self.experience_buffer) % 10 == 0:
                        self._save_model()
                    
                    self.last_update_time = current_time
                
                # Sleep to avoid busy waiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in feedback loop: {e}")
                time.sleep(0.5)
    
    def _get_current_state(self):
        """
        Get the current state of the system.
        
        Returns:
            Tuple representing the current state
        """
        # Get activity score
        activity_score = self.activity_detector.get_activity_score()
        
        # Get current FPS
        current_fps = self.adaptive_scaler.current_fps
        
        # Get threat level
        threat_level = self.vector_fusion.get_threat_level()
        
        # Get time since last activity
        time_since_activity = time.time() - self.adaptive_scaler.last_activity_time
        
        # Discretize state for Q-table
        discrete_state = (
            self._discretize(activity_score, 0, 1, 10),
            self._discretize(current_fps, 0, 60, 10),
            self._discretize(threat_level, 0, 1, 10),
            self._discretize(time_since_activity, 0, 10, 10)
        )
        
        return discrete_state
    
    def _discretize(self, value, min_val, max_val, bins):
        """
        Discretize a continuous value into bins.
        
        Args:
            value: Continuous value to discretize
            min_val: Minimum possible value
            max_val: Maximum possible value
            bins: Number of bins
            
        Returns:
            Discretized value (0 to bins-1)
        """
        # Clip value to range
        value = max(min_val, min(value, max_val))
        
        # Discretize
        bin_size = (max_val - min_val) / bins
        return int((value - min_val) / bin_size) if bin_size > 0 else 0
    
    def _select_action(self, state):
        """
        Select an action based on the current state using epsilon-greedy policy.
        
        Args:
            state: Current state tuple
            
        Returns:
            Selected action (0: decrease, 1: maintain, 2: increase sensitivity)
        """
        # Exploration: random action
        if np.random.random() < self.exploration_rate:
            return np.random.randint(0, self.action_dim)
        
        # Exploitation: best known action
        if state not in self.q_table:
            self.q_table[state] = np.zeros(self.action_dim)
        
        return np.argmax(self.q_table[state])
    
    def _apply_action(self, action):
        """
        Apply the selected action to adjust system parameters.
        
        Args:
            action: Selected action (0: decrease, 1: maintain, 2: increase sensitivity)
        """
        # Get current thresholds
        motion_threshold = self.activity_detector.motion_threshold
        audio_threshold = self.activity_detector.audio_threshold
        env_change_threshold = self.activity_detector.env_change_threshold
        combined_threshold = self.activity_detector.combined_threshold
        
        # Adjustment factor
        adjustment = 0.01
        
        if action == 0:
            # Decrease sensitivity (increase thresholds)
            self.activity_detector.motion_threshold = min(1.0, motion_threshold + adjustment)
            self.activity_detector.audio_threshold = min(1.0, audio_threshold + adjustment)
            self.activity_detector.env_change_threshold = min(1.0, env_change_threshold + adjustment)
            self.activity_detector.combined_threshold = min(1.0, combined_threshold + adjustment)
            logger.info(f"Decreased sensitivity: motion={self.activity_detector.motion_threshold:.3f}, "
                       f"audio={self.activity_detector.audio_threshold:.3f}")
        
        elif action == 2:
            # Increase sensitivity (decrease thresholds)
            self.activity_detector.motion_threshold = max(0.01, motion_threshold - adjustment)
            self.activity_detector.audio_threshold = max(0.01, audio_threshold - adjustment)
            self.activity_detector.env_change_threshold = max(0.01, env_change_threshold - adjustment)
            self.activity_detector.combined_threshold = max(0.01, combined_threshold - adjustment)
            logger.info(f"Increased sensitivity: motion={self.activity_detector.motion_threshold:.3f}, "
                       f"audio={self.activity_detector.audio_threshold:.3f}")
        
        # Action 1: maintain current sensitivity (do nothing)
    
    def _calculate_reward(self, state, action, new_state):
        """
        Calculate reward for the RL agent.
        
        Args:
            state: Previous state
            action: Action taken
            new_state: New state after action
            
        Returns:
            Reward value
        """
        # Extract state components
        activity_score = state[0] / 10.0  # Rescale to 0-1
        current_fps = state[1] / 10.0 * 60.0  # Rescale to 0-60
        threat_level = state[2] / 10.0  # Rescale to 0-1
        
        # Extract new state components
        new_activity_score = new_state[0] / 10.0
        new_current_fps = new_state[1] / 10.0 * 60.0
        new_threat_level = new_state[2] / 10.0
        
        # Get current activity detection
        activity_detected = self.activity_detector.is_activity_detected()
        
        # Calculate reward components
        
        # 1. Resource efficiency: reward for using low resources when no activity
        resource_efficiency = 0
        if not activity_detected and new_current_fps < 1.0:
            resource_efficiency = 1.0
        elif activity_detected and new_current_fps > 30.0:
            resource_efficiency = 0.5
        
        # 2. Threat response: reward for high FPS during high threat
        threat_response = 0
        if new_threat_level > 0.5 and new_current_fps > 30.0:
            threat_response = new_threat_level
        
        # 3. Sensitivity adjustment: reward for appropriate sensitivity
        sensitivity_reward = 0
        if action == 0 and activity_score < 0.2:  # Decrease sensitivity when low activity
            sensitivity_reward = 0.5
        elif action == 2 and activity_score > 0.5:  # Increase sensitivity when high activity
            sensitivity_reward = 0.5
        
        # 4. Penalty for rapid oscillation in sensitivity
        oscillation_penalty = 0
        if len(self.experience_buffer) > 1:
            last_action = self.experience_buffer[-1][1]
            if (action == 0 and last_action == 2) or (action == 2 and last_action == 0):
                oscillation_penalty = -0.5
        
        # Combine rewards
        total_reward = resource_efficiency + threat_response + sensitivity_reward + oscillation_penalty
        
        return total_reward
    
    def _update_q_table(self, state, action, reward, new_state):
        """
        Update Q-table using Q-learning algorithm.
        
        Args:
            state: Previous state
            action: Action taken
            reward: Reward received
            new_state: New state after action
        """
        # Initialize Q-values if not exist
        if state not in self.q_table:
            self.q_table[state] = np.zeros(self.action_dim)
        
        if new_state not in self.q_table:
            self.q_table[new_state] = np.zeros(self.action_dim)
        
        # Q-learning update
        best_next_action = np.argmax(self.q_table[new_state])
        td_target = reward + self.discount_factor * self.q_table[new_state][best_next_action]
        td_error = td_target - self.q_table[state][action]
        
        self.q_table[state][action] += self.learning_rate * td_error
    
    def _experience_replay(self):
        """Perform experience replay to improve learning."""
        if len(self.experience_buffer) < 10:
            return
        
        # Sample a batch of experiences
        batch_size = min(10, len(self.experience_buffer))
        batch_indices = np.random.choice(len(self.experience_buffer), batch_size, replace=False)
        
        for i in batch_indices:
            state, action, reward, new_state = self.experience_buffer[i]
            self._update_q_table(state, action, reward, new_state)
    
    def _update_metrics(self, state, action, new_state):
        """
        Update performance metrics.
        
        Args:
            state: Previous state
            action: Action taken
            new_state: New state after action
        """
        with self.lock:
            # Track resource usage
            current_fps = self.adaptive_scaler.current_fps
            self.metrics['resource_usage'].append(current_fps)
            
            # Limit resource usage history
            if len(self.metrics['resource_usage']) > 100:
                self.metrics['resource_usage'] = self.metrics['resource_usage'][-100:]
            
            # Track detection accuracy
            activity_detected = self.activity_detector.is_activity_detected()
            threat_level = self.vector_fusion.get_threat_level()
            
            # For this prototype, we'll use threat_level > 0.5 as ground truth
            # In a real system, this would come from user feedback or external validation
            actual_threat = threat_level > 0.5
            
            if activity_detected and actual_threat:
                self.metrics['true_positives'] += 1
            elif activity_detected and not actual_threat:
                self.metrics['false_positives'] += 1
            elif not activity_detected and actual_threat:
                self.metrics['false_negatives'] += 1
            else:  # not activity_detected and not actual_threat
                self.metrics['true_negatives'] += 1
    
    def _save_model(self):
        """Save the learned model to disk."""
        try:
            with open(self.model_save_path, 'wb') as f:
                pickle.dump({
                    'q_table': self.q_table,
                    'exploration_rate': self.exploration_rate,
                    'metrics': self.metrics
                }, f)
            logger.info(f"Model saved to {self.model_save_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def _load_model(self):
        """Load the learned model from disk if available."""
        try:
            if os.path.exists(self.model_save_path):
                with open(self.model_save_path, 'rb') as f:
                    data = pickle.load(f)
                    self.q_table = data['q_table']
                    self.exploration_rate = data['exploration_rate']
                    self.metrics = data['metrics']
                logger.info(f"Model loaded from {self.model_save_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")


# Example usage
if __name__ == "__main__":
    from video_processor import VideoProcessor
    from audio_processor import AudioProcessor
    from activity_detector import ActivityDetector
    from adaptive_scaler import AdaptiveScaler
    from vector_fusion import VectorFusion, FusionMethod
    
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
    
    # Create vector fusion
    vector_fusion = VectorFusion(
        video_processor=video_processor,
        audio_processor=audio_processor,
        fusion_method=FusionMethod.WEIGHTED_AVERAGE,
        video_weight=0.6,
        audio_weight=0.4,
        fusion_interval=0.2
    )
    
    # Create feedback loop
    feedback_loop = FeedbackLoop(
        activity_detector=activity_detector,
        adaptive_scaler=adaptive_scaler,
        vector_fusion=vector_fusion,
        learning_rate=0.01,
        discount_factor=0.9,
        exploration_rate=0.2,
        min_exploration_rate=0.01,
        exploration_decay=0.995,
        update_interval=5.0,
        model_save_path='./data/feedback_model.pkl'
    )
    
    # Start everything
    video_processor.start()
    audio_processor.start()
    activity_detector.start()
    adaptive_scaler.start()
    vector_fusion.start()
    feedback_loop.start()
    
    try:
        # Run for 60 seconds
        start_time = time.time()
        while time.time() - start_time < 60:
            # Print current metrics
            metrics = feedback_loop.get_performance_metrics()
            
            # Calculate accuracy if possible
            total = sum([metrics['true_positives'], metrics['true_negatives'], 
                         metrics['false_positives'], metrics['false_negatives']])
            
            if total > 0:
                accuracy = (metrics['true_positives'] + metrics['true_negatives']) / total
                print(f"Accuracy: {accuracy:.4f}, Resource usage: {np.mean(metrics['resource_usage']):.2f} fps")
            
            time.sleep(5.0)
    
    finally:
        # Stop everything
        feedback_loop.stop()
        vector_fusion.stop()
        adaptive_scaler.stop()
        activity_detector.stop()
        video_processor.stop()
        audio_processor.stop()
