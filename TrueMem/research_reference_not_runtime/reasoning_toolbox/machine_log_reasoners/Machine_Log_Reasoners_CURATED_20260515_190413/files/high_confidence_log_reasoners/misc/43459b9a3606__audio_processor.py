import pyaudio
import numpy as np
import time
import threading
import queue
import logging
from scipy.signal import find_peaks

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AudioProcessor')

class AudioProcessor:
    """
    Handles audio capture and processing with event detection capabilities.
    
    Features:
    - Continuous audio monitoring
    - Audio event detection (sharp sounds, patterns)
    - Feature extraction and embedding generation
    """
    
    def __init__(self, sample_rate=16000, chunk_size=1024, buffer_seconds=5):
        """
        Initialize the audio processor.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 16000)
            chunk_size: Number of samples per chunk (default: 1024)
            buffer_seconds: Size of the audio buffer in seconds (default: 5)
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.buffer_seconds = buffer_seconds
        
        # Calculate buffer size in chunks
        self.buffer_size = int(self.buffer_seconds * self.sample_rate / self.chunk_size)
        
        # Audio buffer and lock
        self.audio_buffer = queue.Queue(maxsize=self.buffer_size)
        self.lock = threading.Lock()
        
        # Processing state
        self.is_running = False
        self.is_event_detected = False
        
        # Audio capture thread
        self.capture_thread = None
        
        # Last processed audio and embedding
        self.last_audio_chunk = None
        self.last_embedding = None
        
        # Audio stream
        self.audio = None
        self.stream = None
        
        logger.info(f"AudioProcessor initialized with sample rate: {sample_rate}Hz, chunk size: {chunk_size}")
    
    def start(self):
        """Start audio capture in a separate thread."""
        if self.is_running:
            logger.warning("Audio processor is already running")
            return
        
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        logger.info("Audio capture started")
    
    def stop(self):
        """Stop audio capture."""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        logger.info("Audio capture stopped")
    
    def get_latest_audio(self):
        """Get the most recent audio chunk from the buffer."""
        if not self.audio_buffer.empty():
            self.last_audio_chunk = self.audio_buffer.get()
            return self.last_audio_chunk
        return self.last_audio_chunk
    
    def get_latest_embedding(self):
        """Get the embedding vector for the most recent audio chunk."""
        audio_chunk = self.get_latest_audio()
        if audio_chunk is not None:
            self.last_embedding = self._extract_features(audio_chunk)
            return self.last_embedding
        return self.last_embedding
    
    def _capture_loop(self):
        """Main capture loop that runs in a separate thread."""
        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            logger.info("Audio stream opened successfully")
            
            while self.is_running:
                try:
                    # Read audio chunk
                    audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    audio_array = np.frombuffer(audio_data, dtype=np.float32)
                    
                    # Process the audio
                    processed_audio = self._preprocess_audio(audio_array)
                    
                    # Add to buffer, removing oldest if full
                    if self.audio_buffer.full():
                        try:
                            self.audio_buffer.get_nowait()
                        except:
                            pass
                    
                    self.audio_buffer.put(processed_audio)
                    
                    # Check for audio events
                    self._detect_audio_events(processed_audio)
                    
                except Exception as e:
                    logger.error(f"Error in audio capture: {e}")
                    time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            self.is_running = False
    
    def _preprocess_audio(self, audio_array):
        """
        Preprocess the audio for analysis.
        
        Args:
            audio_array: Raw audio data as numpy array
            
        Returns:
            Preprocessed audio array
        """
        # Normalize audio
        if np.max(np.abs(audio_array)) > 0:
            audio_array = audio_array / np.max(np.abs(audio_array))
        
        return audio_array
    
    def _extract_features(self, audio_array):
        """
        Extract feature embedding from audio.
        
        Args:
            audio_array: Preprocessed audio array
            
        Returns:
            Feature embedding vector (numpy array)
        """
        # In a real implementation, this would use a pre-trained model
        # For this prototype, we'll use simple audio features
        
        # Calculate basic audio features
        features = []
        
        # RMS energy
        features.append(np.sqrt(np.mean(np.square(audio_array))))
        
        # Zero crossing rate
        zero_crossings = np.sum(np.abs(np.diff(np.signbit(audio_array))))
        features.append(zero_crossings / len(audio_array))
        
        # Spectral centroid
        fft = np.abs(np.fft.rfft(audio_array))
        freqs = np.fft.rfftfreq(len(audio_array), 1.0/self.sample_rate)
        if np.sum(fft) > 0:
            spectral_centroid = np.sum(freqs * fft) / np.sum(fft)
            features.append(spectral_centroid / (self.sample_rate/2))  # Normalize
        else:
            features.append(0)
        
        # Add more features as needed
        
        return np.array(features, dtype=np.float32)
    
    def _detect_audio_events(self, audio_array, threshold=0.5):
        """
        Detect audio events like sharp sounds or patterns.
        
        Args:
            audio_array: Preprocessed audio array
            threshold: Detection threshold (0.0 to 1.0)
            
        Returns:
            Boolean indicating if an event was detected
        """
        # Calculate audio energy
        energy = np.sqrt(np.mean(np.square(audio_array)))
        
        # Detect peaks in the audio
        peaks, _ = find_peaks(np.abs(audio_array), height=threshold)
        
        # Event is detected if energy is above threshold or there are significant peaks
        event_detected = energy > threshold or len(peaks) > 5
        
        # Update state
        with self.lock:
            self.is_event_detected = event_detected
        
        if event_detected:
            logger.info(f"Audio event detected with energy {energy:.4f} and {len(peaks)} peaks")
        
        return event_detected
    
    def is_audio_event_detected(self):
        """Check if an audio event is currently detected."""
        with self.lock:
            return self.is_event_detected


# Example usage
if __name__ == "__main__":
    # Create audio processor
    audio_processor = AudioProcessor(sample_rate=16000, chunk_size=1024)
    
    # Start audio capture
    audio_processor.start()
    
    try:
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            # Check for audio events
            if audio_processor.is_audio_event_detected():
                print("Audio event detected!")
                
                # Get the latest embedding
                embedding = audio_processor.get_latest_embedding()
                print(f"Audio embedding: {embedding}")
            
            time.sleep(0.1)
    
    finally:
        # Stop audio capture
        audio_processor.stop()
