import numpy as np
import time
import logging
import threading
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VectorFusion')

class FusionMethod(Enum):
    """Enum for different vector fusion methods."""
    CONCATENATION = 0
    WEIGHTED_AVERAGE = 1
    ATTENTION = 2
    GATING = 3

class VectorFusion:
    """
    Combines video and audio embeddings using various fusion techniques.
    
    Features:
    - Multiple fusion methods (concatenation, weighted average, attention, gating)
    - Context-aware threat prediction
    - Dynamic weighting based on signal quality
    """
    
    def __init__(self, video_processor, audio_processor, 
                 fusion_method=FusionMethod.WEIGHTED_AVERAGE,
                 video_weight=0.6, audio_weight=0.4,
                 fusion_interval=0.2):
        """
        Initialize the vector fusion pipeline.
        
        Args:
            video_processor: VideoProcessor instance
            audio_processor: AudioProcessor instance
            fusion_method: Method to use for fusion (default: WEIGHTED_AVERAGE)
            video_weight: Weight for video embeddings in weighted average (default: 0.6)
            audio_weight: Weight for audio embeddings in weighted average (default: 0.4)
            fusion_interval: Time interval between fusion operations in seconds (default: 0.2)
        """
        self.video_processor = video_processor
        self.audio_processor = audio_processor
        
        self.fusion_method = fusion_method
        self.video_weight = video_weight
        self.audio_weight = audio_weight
        self.fusion_interval = fusion_interval
        
        # Fusion state
        self.fused_embedding = None
        self.last_fusion_time = 0
        self.lock = threading.Lock()
        
        # Fusion thread
        self.fusion_thread = None
        self.is_running = False
        
        # Context state for threat prediction
        self.context_history = []
        self.max_context_history = 10
        self.threat_level = 0.0
        
        logger.info(f"VectorFusion initialized with method: {fusion_method.name}, "
                   f"weights: video={video_weight}, audio={audio_weight}")
    
    def start(self):
        """Start vector fusion in a separate thread."""
        if self.is_running:
            logger.warning("Vector fusion is already running")
            return
        
        self.is_running = True
        self.fusion_thread = threading.Thread(target=self._fusion_loop)
        self.fusion_thread.daemon = True
        self.fusion_thread.start()
        logger.info("Vector fusion started")
    
    def stop(self):
        """Stop vector fusion."""
        self.is_running = False
        if self.fusion_thread:
            self.fusion_thread.join(timeout=1.0)
        logger.info("Vector fusion stopped")
    
    def get_fused_embedding(self):
        """Get the most recent fused embedding."""
        with self.lock:
            return self.fused_embedding
    
    def get_threat_level(self):
        """Get the current threat level (0.0 to 1.0)."""
        with self.lock:
            return self.threat_level
    
    def _fusion_loop(self):
        """Main fusion loop that runs in a separate thread."""
        while self.is_running:
            try:
                current_time = time.time()
                
                # Check if it's time to perform fusion
                if current_time - self.last_fusion_time >= self.fusion_interval:
                    # Get latest embeddings
                    video_embedding = self.video_processor.get_latest_embedding()
                    audio_embedding = self.audio_processor.get_latest_embedding()
                    
                    if video_embedding is not None and audio_embedding is not None:
                        # Perform fusion
                        fused_embedding = self._fuse_embeddings(video_embedding, audio_embedding)
                        
                        # Update state
                        with self.lock:
                            self.fused_embedding = fused_embedding
                            self.last_fusion_time = current_time
                        
                        # Update context history
                        self._update_context_history(fused_embedding)
                        
                        # Predict threat level
                        threat_level = self._predict_threat_level()
                        
                        with self.lock:
                            self.threat_level = threat_level
                
                # Sleep to avoid busy waiting
                time.sleep(min(0.01, self.fusion_interval / 10))
                
            except Exception as e:
                logger.error(f"Error in vector fusion: {e}")
                time.sleep(0.5)
    
    def _fuse_embeddings(self, video_embedding, audio_embedding):
        """
        Fuse video and audio embeddings using the selected method.
        
        Args:
            video_embedding: Video feature embedding
            audio_embedding: Audio feature embedding
            
        Returns:
            Fused embedding vector
        """
        # Normalize embeddings
        video_embedding = self._normalize_embedding(video_embedding)
        audio_embedding = self._normalize_embedding(audio_embedding)
        
        # Apply fusion method
        if self.fusion_method == FusionMethod.CONCATENATION:
            return self._concatenation_fusion(video_embedding, audio_embedding)
        elif self.fusion_method == FusionMethod.WEIGHTED_AVERAGE:
            return self._weighted_average_fusion(video_embedding, audio_embedding)
        elif self.fusion_method == FusionMethod.ATTENTION:
            return self._attention_fusion(video_embedding, audio_embedding)
        elif self.fusion_method == FusionMethod.GATING:
            return self._gating_fusion(video_embedding, audio_embedding)
        else:
            # Default to weighted average
            return self._weighted_average_fusion(video_embedding, audio_embedding)
    
    def _normalize_embedding(self, embedding):
        """
        Normalize an embedding vector.
        
        Args:
            embedding: Feature embedding vector
            
        Returns:
            Normalized embedding vector
        """
        # L2 normalization
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    def _concatenation_fusion(self, video_embedding, audio_embedding):
        """
        Fuse embeddings by concatenation.
        
        Args:
            video_embedding: Video feature embedding
            audio_embedding: Audio feature embedding
            
        Returns:
            Concatenated embedding vector
        """
        return np.concatenate([video_embedding, audio_embedding])
    
    def _weighted_average_fusion(self, video_embedding, audio_embedding):
        """
        Fuse embeddings by weighted average.
        
        Args:
            video_embedding: Video feature embedding
            audio_embedding: Audio feature embedding
            
        Returns:
            Weighted average embedding vector
        """
        # Ensure embeddings have the same dimensionality
        if video_embedding.shape != audio_embedding.shape:
            # Resize to match the smaller dimension
            min_dim = min(video_embedding.shape[0], audio_embedding.shape[0])
            video_embedding = video_embedding[:min_dim]
            audio_embedding = audio_embedding[:min_dim]
        
        # Apply weights
        return self.video_weight * video_embedding + self.audio_weight * audio_embedding
    
    def _attention_fusion(self, video_embedding, audio_embedding):
        """
        Fuse embeddings using a simple attention mechanism.
        
        Args:
            video_embedding: Video feature embedding
            audio_embedding: Audio feature embedding
            
        Returns:
            Attention-fused embedding vector
        """
        # Ensure embeddings have the same dimensionality
        if video_embedding.shape != audio_embedding.shape:
            # Resize to match the smaller dimension
            min_dim = min(video_embedding.shape[0], audio_embedding.shape[0])
            video_embedding = video_embedding[:min_dim]
            audio_embedding = audio_embedding[:min_dim]
        
        # Calculate attention scores
        video_energy = np.sum(np.square(video_embedding))
        audio_energy = np.sum(np.square(audio_embedding))
        
        # Normalize energies to get attention weights
        total_energy = video_energy + audio_energy
        if total_energy > 0:
            video_attention = video_energy / total_energy
            audio_attention = audio_energy / total_energy
        else:
            video_attention = 0.5
            audio_attention = 0.5
        
        # Apply attention weights
        return video_attention * video_embedding + audio_attention * audio_embedding
    
    def _gating_fusion(self, video_embedding, audio_embedding):
        """
        Fuse embeddings using a gating mechanism.
        
        Args:
            video_embedding: Video feature embedding
            audio_embedding: Audio feature embedding
            
        Returns:
            Gated embedding vector
        """
        # Ensure embeddings have the same dimensionality
        if video_embedding.shape != audio_embedding.shape:
            # Resize to match the smaller dimension
            min_dim = min(video_embedding.shape[0], audio_embedding.shape[0])
            video_embedding = video_embedding[:min_dim]
            audio_embedding = audio_embedding[:min_dim]
        
        # Calculate gate values (sigmoid of dot product)
        gate = 1 / (1 + np.exp(-np.dot(video_embedding, audio_embedding)))
        
        # Apply gate
        return gate * video_embedding + (1 - gate) * audio_embedding
    
    def _update_context_history(self, fused_embedding):
        """
        Update the context history with the latest fused embedding.
        
        Args:
            fused_embedding: Latest fused embedding vector
        """
        self.context_history.append(fused_embedding)
        
        # Limit history size
        if len(self.context_history) > self.max_context_history:
            self.context_history.pop(0)
    
    def _predict_threat_level(self):
        """
        Predict threat level based on context history.
        
        Returns:
            Threat level (0.0 to 1.0)
        """
        if not self.context_history:
            return 0.0
        
        # In a real implementation, this would use a trained model
        # For this prototype, we'll use a simple heuristic
        
        # Calculate the variance in the context history
        if len(self.context_history) > 1:
            context_array = np.array(self.context_history)
            variance = np.mean(np.var(context_array, axis=0))
            
            # High variance indicates potential threats
            threat_level = min(1.0, variance * 10)
        else:
            threat_level = 0.0
        
        return threat_level


# Example usage
if __name__ == "__main__":
    from video_processor import VideoProcessor
    from audio_processor import AudioProcessor
    
    # Create processors
    video_processor = VideoProcessor(camera_id=0, low_fps=0.2, high_fps=30)
    audio_processor = AudioProcessor(sample_rate=16000, chunk_size=1024)
    
    # Create vector fusion
    vector_fusion = VectorFusion(
        video_processor=video_processor,
        audio_processor=audio_processor,
        fusion_method=FusionMethod.WEIGHTED_AVERAGE,
        video_weight=0.6,
        audio_weight=0.4,
        fusion_interval=0.2
    )
    
    # Start processors and fusion
    video_processor.start()
    audio_processor.start()
    vector_fusion.start()
    
    try:
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            # Get fused embedding and threat level
            fused_embedding = vector_fusion.get_fused_embedding()
            threat_level = vector_fusion.get_threat_level()
            
            if fused_embedding is not None:
                print(f"Fused embedding shape: {fused_embedding.shape}, Threat level: {threat_level:.4f}")
            
            time.sleep(1.0)
    
    finally:
        # Stop everything
        vector_fusion.stop()
        video_processor.stop()
        audio_processor.stop()
