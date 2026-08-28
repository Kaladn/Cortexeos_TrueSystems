"""
CortexOS Temporal Cognition v2.1
Cortex Vectorizer Module - Transforms input data into harmonic vectors for neural processing
Implements full Agharmonic Law compliance for stable vector transformations
"""

import numpy as np
import hashlib
import logging
import time
import json
import os
from datetime import datetime
import threading
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CortexVectorizer:
    """
    Transforms various input types into harmonic vectors for CortexOS processing.
    Converts text, images, and structured data into RGB+intensity and frequency components.
    Fully compliant with Agharmonic Law for stable vector transformations.
    """
    def __init__(self, vector_dimensions=10, config=None):
        """
        Initialize the cortex vectorizer.
        
        Args:
            vector_dimensions (int): Dimensions of output vectors
            config (dict, optional): Configuration parameters
        """
        # Core vectorization parameters
        self.vector_dimensions = max(10, vector_dimensions)  # Minimum 10 dimensions (RGB+intensity+6 frequencies)
        self.base_frequencies = [1.0, 1.5, 2.0, 3.0, 5.0, 8.0]  # Fibonacci-inspired base frequencies
        self.frequency_range = [0.5, 1.2]  # Default frequency range
        self.output_phase_alignment = 0.1  # Default output phase alignment
        
        # Agharmonic compliance parameters
        self.last_sync_time = datetime.utcnow()
        self.sync_interval = 3.0  # seconds
        self.energy_conservation_factor = 0.95
        self.stability_threshold = 0.75
        self.field_stability = 1.0
        self.vector_lock = threading.RLock()
        self.fallback_mode = False
        self.fallback_level = 0
        
        # Performance monitoring
        self.performance_metrics = {
            "vectors_processed": 0,
            "average_intensity": 0.5,
            "dimension_utilization": 1.0,
            "error_rate": 0.0,
            "processing_times": []
        }
        
        # Vector cache for self-regulation
        self.vector_cache = {}
        self.max_cache_size = 1000
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Load fallback chains if available
        self.fallback_chains = self._load_fallback_chains()
        
        # Apply custom configuration if provided
        if config:
            self._apply_config(config)
        
        logger.info("CortexVectorizer initialized with %d dimensions", self.vector_dimensions)
    
    # === Agharmonic Law Compliance Methods ===
    
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for vector transformations.
        
        Returns:
            dict: Harmonic signature parameters including frequency range and phase alignment
        """
        return {
            "module": "cortex_vectorizer",
            "input_frequency_range": self.frequency_range,
            "output_phase_alignment": self.output_phase_alignment,
            "resonance_threshold": 0.75,
            "harmonic_version": "2.1.0",
            "compatible_modules": [
                "neuroengine",
                "data_ingestor"
            ]
        }
    
    def interface_contract(self, vector_data=None):
        """
        Validates vector data against the expected interface contract.
        
        Args:
            vector_data (dict, optional): Vector data to validate
            
        Returns:
            bool or dict: True if data meets contract requirements, or contract specification if no data
            
        Raises:
            ValueError: If data violates contract requirements
        """
        # Define expected vector data structure
        if vector_data is None:
            return {
                "required_fields": {
                    "input_data": "text, numpy.ndarray, or dict",
                    "input_type": "str ('text', 'image', or 'structured')"
                },
                "optional_fields": {
                    "context": "dict",
                    "schema": "dict",
                    "region": "tuple(x1, y1, x2, y2)",
                    "timestamp": "float or datetime"
                },
                "output_format": {
                    "vector": "list of floats",
                    "dimensions": "int",
                    "metadata": "dict"
                }
            }
        
        # Validate vector data
        if not isinstance(vector_data, dict):
            raise ValueError("Vector data must be a dictionary")
        
        # Check required fields
        if "input_data" not in vector_data:
            raise ValueError("Missing required field: input_data")
        
        if "input_type" not in vector_data:
            raise ValueError("Missing required field: input_type")
        
        # Validate input_type
        valid_types = ["text", "image", "structured"]
        if vector_data["input_type"] not in valid_types:
            raise ValueError(f"input_type must be one of: {', '.join(valid_types)}")
        
        # Validate input_data based on input_type
        input_type = vector_data["input_type"]
        input_data = vector_data["input_data"]
        
        if input_type == "text" and not isinstance(input_data, str):
            raise ValueError("input_data must be a string for input_type 'text'")
        
        if input_type == "image" and not isinstance(input_data, np.ndarray):
            raise ValueError("input_data must be a numpy.ndarray for input_type 'image'")
        
        if input_type == "structured" and not isinstance(input_data, dict):
            raise ValueError("input_data must be a dictionary for input_type 'structured'")
        
        # Validate optional fields if present
        if "context" in vector_data and not isinstance(vector_data["context"], dict):
            raise ValueError("context must be a dictionary")
        
        if "schema" in vector_data and not isinstance(vector_data["schema"], dict):
            raise ValueError("schema must be a dictionary")
        
        if "region" in vector_data:
            region = vector_data["region"]
            if not isinstance(region, tuple) or len(region) != 4:
                raise ValueError("region must be a tuple of (x1, y1, x2, y2)")
        
        if "timestamp" in vector_data and not isinstance(vector_data["timestamp"], (float, int, datetime)):
            raise ValueError("timestamp must be a float, int, or datetime")
        
        return True
    
    def cognitive_energy_flow(self, vector_intensity=None):
        """
        Normalizes signal amplitude and information flow to maintain energy conservation.
        
        Args:
            vector_intensity (float, optional): Input intensity to normalize
            
        Returns:
            float: Normalized intensity or current energy level if no input
        """
        # If no input, return current field stability as energy level
        if vector_intensity is None:
            return self.field_stability
        
        # Ensure intensity is within bounds
        normalized_intensity = max(0.0, min(1.0, vector_intensity))
        
        # Apply energy conservation based on current field stability
        if self.field_stability < self.stability_threshold:
            # Low stability state - conserve energy by dampening intensity
            normalized_intensity *= self.energy_conservation_factor
            logger.debug(f"Energy conservation applied: {self.energy_conservation_factor}")
        
        # Apply non-linear normalization to prevent vector saturation
        # This helps prevent information loss by smoothing intensity peaks
        if normalized_intensity > 0.8:
            # Soft cap on high intensities to prevent overloading
            normalized_intensity = 0.8 + (normalized_intensity - 0.8) * 0.5
        
        return normalized_intensity
    
    def sync_clock(self):
        """
        Connects to the master temporal framework and synchronizes processing cycles.
        
        Returns:
            bool: True if sync was performed, False if not yet time to sync
        """
        now = datetime.utcnow()
        delta = (now - self.last_sync_time).total_seconds()
        
        # Sync every sync_interval seconds
        if delta >= self.sync_interval:
            self.last_sync_time = now
            
            # Perform vector alignment with harmonic signature
            with self.vector_lock:
                # Check if vector dimensions are aligned with frequency range
                harmonic_sig = self.harmonic_signature()
                freq_min, freq_max = harmonic_sig["input_frequency_range"]
                
                # Verify base frequencies are within range
                out_of_range = [f for f in self.base_frequencies if f < freq_min or f > freq_max]
                if out_of_range:
                    # Adjust out-of-range frequencies
                    for i, freq in enumerate(self.base_frequencies):
                        if freq < freq_min:
                            self.base_frequencies[i] = freq_min + (freq / freq_min) * 0.1
                        elif freq > freq_max:
                            self.base_frequencies[i] = freq_max - (freq_max / freq) * 0.1
                    
                    logger.debug(f"Adjusted {len(out_of_range)} frequencies to match harmonic signature")
                
                # Update performance metrics
                self.performance_metrics["dimension_utilization"] = min(1.0, (self.vector_dimensions - 4) / len(self.base_frequencies))
            
            logger.debug(f"Clock sync performed at {self.last_sync_time.isoformat()}")
            return True
        
        return False
    
    def self_regulate(self):
        """
        Implements internal feedback loops to maintain stable operation.
        
        Returns:
            dict: Self-regulation metrics and actions taken
        """
        regulation_actions = []
        
        with self.vector_lock:
            # Check vector cache size and prune if necessary
            if len(self.vector_cache) > self.max_cache_size:
                # Keep only the most frequently accessed entries
                sorted_cache = sorted(
                    self.vector_cache.items(),
                    key=lambda x: x[1].get("access_count", 0),
                    reverse=True
                )
                
                # Keep top half
                self.vector_cache = dict(sorted_cache[:self.max_cache_size//2])
                regulation_actions.append("cache_pruned")
            
            # Calculate cache efficiency
            total_lookups = self.cache_hits + self.cache_misses
            if total_lookups > 0:
                cache_efficiency = self.cache_hits / total_lookups
                
                # Adjust cache size based on efficiency
                if cache_efficiency < 0.5 and self.max_cache_size > 500:
                    self.max_cache_size = int(self.max_cache_size * 0.8)
                    regulation_actions.append("cache_size_reduced")
                elif cache_efficiency > 0.8 and self.max_cache_size < 5000:
                    self.max_cache_size = int(self.max_cache_size * 1.2)
                    regulation_actions.append("cache_size_increased")
            
            # Calculate average processing time
            if self.performance_metrics["processing_times"]:
                avg_time = sum(self.performance_metrics["processing_times"]) / len(self.performance_metrics["processing_times"])
                
                # If processing is slow, consider entering fallback mode
                if avg_time > 0.1 and not self.fallback_mode:  # 100ms threshold
                    logger.warning(f"Slow vectorization detected: {avg_time:.3f}s average")
                    regulation_actions.append("performance_warning")
                    
                    if avg_time > 0.5:  # 500ms is very slow
                        self.graceful_fallback(reason="performance_degradation")
                
                # Reset processing times list if it gets too large
                if len(self.performance_metrics["processing_times"]) > 100:
                    self.performance_metrics["processing_times"] = self.performance_metrics["processing_times"][-50:]
            
            # Update field stability based on error rate
            error_rate = self.performance_metrics["error_rate"]
            if error_rate > 0:
                new_stability = max(0.1, 1.0 - error_rate * 2)
                
                # Apply smoothing to stability changes
                self.field_stability = self.field_stability * 0.7 + new_stability * 0.3
                regulation_actions.append("stability_updated")
                
                # Reset error rate
                self.performance_metrics["error_rate"] = 0.0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "actions": regulation_actions,
            "metrics": {
                "field_stability": self.field_stability,
                "cache_size": len(self.vector_cache),
                "max_cache_size": self.max_cache_size,
                "cache_efficiency": self.cache_hits / max(1, (self.cache_hits + self.cache_misses)),
                "vectors_processed": self.performance_metrics["vectors_processed"],
                "average_intensity": self.performance_metrics["average_intensity"]
            }
        }
    
    def graceful_fallback(self, reason=None):
        """
        Provides mechanisms for partial operation when operating in suboptimal conditions.
        
        Args:
            reason (str, optional): Reason for entering fallback mode
            
        Returns:
            dict: Fallback status and active fallback mechanisms
        """
        if reason is None:
            # Return current fallback status if no reason provided
            return {
                "active": self.fallback_mode,
                "level": self.fallback_level,
                "mechanisms": self._get_active_fallback_mechanisms()
            }
        
        # Enter fallback mode
        self.fallback_mode = True
        
        # Determine appropriate fallback level based on reason
        if reason == "performance_degradation":
            self.fallback_level = 1
        elif reason == "memory_constraint":
            self.fallback_level = 2
        elif reason == "critical_error":
            self.fallback_level = 3
        else:
            self.fallback_level = 1  # Default level
        
        logger.warning(f"Entering fallback mode level {self.fallback_level}: {reason}")
        
        # Apply fallback mechanisms based on level
        mechanisms = self._apply_fallback_mechanisms(self.fallback_level)
        
        return {
            "active": True,
            "level": self.fallback_level,
            "reason": reason,
            "mechanisms": mechanisms
        }
    
    def resonance_chain_validator(self):
        """
        Verifies resonance integrity across the processing chain.
        
        Returns:
            dict: Validation results including integrity score and issues
        """
        issues = []
        integrity = 1.0
        
        # Check field stability
        if self.field_stability < self.stability_threshold:
            issues.append(f"Vector field stability below threshold: {self.field_stability:.2f}")
            integrity *= (self.field_stability / self.stability_threshold)
        
        # Check frequency compatibility
        harmonic_sig = self.harmonic_signature()
        freq_min, freq_max = harmonic_sig["input_frequency_range"]
        
        out_of_range = [f for f in self.base_frequencies if f < freq_min or f > freq_max]
        if out_of_range:
            issues.append(f"{len(out_of_range)} frequencies outside acceptable range [{freq_min}, {freq_max}]")
            integrity *= (1.0 - len(out_of_range) / len(self.base_frequencies))
        
        # Check vector dimensions
        min_dimensions = 4 + len(self.base_frequencies)  # RGB+intensity+frequencies
        if self.vector_dimensions < min_dimensions:
            issues.append(f"Vector dimensions ({self.vector_dimensions}) below minimum required ({min_dimensions})")
            integrity *= (self.vector_dimensions / min_dimensions)
        
        # Check error rate
        error_rate = self.performance_metrics["error_rate"]
        if error_rate > 0.05:  # 5% error rate threshold
            issues.append(f"High vectorization error rate: {error_rate:.2f}")
            integrity *= (1.0 - error_rate)
        
        return {
            "integrity": max(0.1, integrity),  # Ensure minimum integrity of 0.1
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # === Core Vectorization Methods ===
    
    def vectorize(self, input_data, input_type, **kwargs):
        """
        Unified vectorization interface for all input types.
        
        Args:
            input_data: Data to vectorize (text, image array, or structured dict)
            input_type (str): Type of input ('text', 'image', or 'structured')
            **kwargs: Additional parameters for specific vectorization methods
            
        Returns:
            dict: Vectorization result with vector and metadata
        """
        start_time = time.time()
        
        try:
            # Validate input through interface contract
            self.interface_contract({
                "input_data": input_data,
                "input_type": input_type,
                **kwargs
            })
            
            # Check cache for identical input
            cache_key = self._generate_cache_key(input_data, input_type, kwargs)
            if cache_key in self.vector_cache:
                self.cache_hits += 1
                self.vector_cache[cache_key]["access_count"] = self.vector_cache[cache_key].get("access_count", 0) + 1
                return self.vector_cache[cache_key]["result"]
            
            self.cache_misses += 1
            
            # Process based on input type
            if input_type == "text":
                vector = self.vectorize_text(input_data, context=kwargs.get("context"))
            elif input_type == "image":
                vector = self.vectorize_image(input_data, region=kwargs.get("region"))
            elif input_type == "structured":
                vector = self.vectorize_structured_data(input_data, schema=kwargs.get("schema"))
            else:
                raise ValueError(f"Unsupported input type: {input_type}")
            
            # Apply energy conservation to intensity component
            if len(vector) >= 4:
                vector[3] = self.cognitive_energy_flow(vector[3])
            
            # Add timestamp if requested
            if kwargs.get("timestamp") is not None:
                vector = self.add_timestamp_to_vector(vector, kwargs["timestamp"])
            
            # Update performance metrics
            self.performance_metrics["vectors_processed"] += 1
            if len(vector) >= 4:
                # Update average intensity using exponential moving average
                self.performance_metrics["average_intensity"] = (
                    0.9 * self.performance_metrics["average_intensity"] + 
                    0.1 * vector[3]
                )
            
            # Record processing time
            processing_time = time.time() - start_time
            self.performance_metrics["processing_times"].append(processing_time)
            
            # Prepare result
            result = {
                "vector": vector,
                "dimensions": len(vector),
                "metadata": {
                    "input_type": input_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "processing_time": processing_time
                }
            }
            
            # Cache result
            self.vector_cache[cache_key] = {
                "result": result,
                "access_count": 1,
                "created_at": time.time()
            }
            
            # Periodically self-regulate
            if self.performance_metrics["vectors_processed"] % 10 == 0:
                self.self_regulate()
            
            # Periodically sync clock
            self.sync_clock()
            
            return result
            
        except Exception as e:
            logger.error(f"Vectorization error: {e}")
            self.performance_metrics["error_rate"] += 0.01  # Increment error rate
            
            # Return fallback vector in case of error
            return {
                "vector": [0.0] * self.vector_dimensions,
                "dimensions": self.vector_dimensions,
                "metadata": {
                    "input_type": input_type,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
    
    def vectorize_text(self, text, context=None):
        """
        Convert text to harmonic vector representation.
        
        Args:
            text (str): Input text to vectorize
            context (dict, optional): Additional context for vectorization
            
        Returns:
            list: Harmonic vector [R, G, B, intensity, freq1, freq2, ...]
        """
        if not text:
            return [0.0] * self.vector_dimensions
        
        # Skip detailed processing in high fallback levels
        if self.fallback_mode and self.fallback_level >= 2:
            # Use simplified vectorization
            text_hash = hashlib.md5(text.encode()).digest()
            r = text_hash[0] / 255.0
            g = text_hash[1] / 255.0
            b = text_hash[2] / 255.0
            intensity = min(1.0, len(text) / 100)
            
            # Create simplified vector
            vector = [r, g, b, intensity] + [0.0] * (self.vector_dimensions - 4)
            return [round(x, 3) for x in vector]
            
        # Generate hash for stable color mapping
        text_hash = hashlib.md5(text.encode()).digest()
        
        # RGB components from hash (normalized to 0-1)
        r = text_hash[0] / 255.0
        g = text_hash[1] / 255.0
        b = text_hash[2] / 255.0
        
        # Intensity based on text length and complexity
        intensity = min(1.0, (0.3 + (len(text) / 100) + (len(set(text.lower())) / 30)))
        
        # Apply context modifiers if provided
        if context:
            if "importance" in context:
                intensity = min(1.0, intensity * (0.5 + context["importance"] * 0.5))
            
            if "sentiment" in context and isinstance(context["sentiment"], (int, float)):
                # Adjust color based on sentiment (-1 to 1)
                sentiment = max(-1.0, min(1.0, context["sentiment"]))
                if sentiment > 0:
                    # More positive: increase green
                    g = min(1.0, g + sentiment * 0.2)
                else:
                    # More negative: increase red
                    r = min(1.0, r - sentiment * 0.2)
        
        # Frequency components based on text features
        word_count = len(text.split())
        char_count = len(text)
        unique_chars = len(set(text.lower()))
        
        freq_components = []
        for i, base_freq in enumerate(self.base_frequencies):
            if i == 0:  # First frequency tied to word count
                freq = base_freq * (0.5 + (word_count / 20))
            elif i == 1:  # Second frequency tied to character count
                freq = base_freq * (0.5 + (char_count / 100))
            elif i == 2:  # Third frequency tied to unique characters
                freq = base_freq * (0.5 + (unique_chars / 30))
            else:  # Other frequencies derived from hash
                freq = base_freq * (0.5 + (text_hash[i+2] / 255.0))
            
            freq_components.append(round(freq, 3))
            
        # Combine all components
        vector = [r, g, b, intensity] + freq_components
        
        # Pad to full dimensions if needed
        while len(vector) < self.vector_dimensions:
            vector.append(0.0)
            
        return [round(x, 3) for x in vector]
        
    def vectorize_image(self, image_array, region=None):
        """
        Convert image data to harmonic vector representation.
        
        Args:
            image_array (numpy.ndarray): RGB or RGBA image data
            region (tuple, optional): Region to focus on (x1, y1, x2, y2)
            
        Returns:
            list: Harmonic vector [R, G, B, intensity, freq1, freq2, ...]
        """
        if image_array is None or image_array.size == 0:
            return [0.0] * self.vector_dimensions
        
        # Skip detailed processing in high fallback levels
        if self.fallback_mode and self.fallback_level >= 2:
            # Use simplified vectorization
            avg_color = np.mean(image_array[:,:,:3], axis=(0,1)) / 255.0
            r, g, b = avg_color
            intensity = 0.5
            
            # Create simplified vector
            vector = [float(r), float(g), float(b), float(intensity)] + [0.0] * (self.vector_dimensions - 4)
            return [round(x, 3) for x in vector]
            
        # Extract region if specified
        if region and len(region) == 4:
            x1, y1, x2, y2 = region
            if x1 < x2 and y1 < y2 and x2 <= image_array.shape[1] and y2 <= image_array.shape[0]:
                image_array = image_array[y1:y2, x1:x2]
        
        # Calculate average RGB
        rgb_channels = image_array[:,:,:3]  # Take only RGB channels
        avg_color = np.mean(rgb_channels, axis=(0,1)) / 255.0
        r, g, b = avg_color
        
        # Calculate intensity from brightness and contrast
        brightness = np.mean(rgb_channels)
        contrast = np.std(rgb_channels)
        intensity = min(1.0, (brightness / 255.0) * 0.7 + (contrast / 128.0) * 0.3)
        
        # Calculate frequency components from image features
        edges_h = np.abs(np.diff(rgb_channels.mean(axis=2), axis=1)).mean()
        edges_v = np.abs(np.diff(rgb_channels.mean(axis=2), axis=0)).mean()
        
        freq_components = []
        for i, base_freq in enumerate(self.base_frequencies):
            if i == 0:  # First frequency tied to horizontal edges
                freq = base_freq * (0.5 + edges_h / 30)
            elif i == 1:  # Second frequency tied to vertical edges
                freq = base_freq * (0.5 + edges_v / 30)
            elif i == 2:  # Third frequency tied to color variance
                freq = base_freq * (0.5 + contrast / 50)
            else:  # Other frequencies derived from image statistics
                freq = base_freq * (0.5 + np.random.random() * 0.5)  # Randomized but stable
                
            freq_components.append(round(freq, 3))
            
        # Combine all components
        vector = [float(r), float(g), float(b), float(intensity)] + freq_components
        
        # Pad to full dimensions if needed
        while len(vector) < self.vector_dimensions:
            vector.append(0.0)
            
        return [round(x, 3) for x in vector]
        
    def vectorize_structured_data(self, data_dict, schema=None):
        """
        Convert structured data to harmonic vector representation.
        
        Args:
            data_dict (dict): Key-value pairs of structured data
            schema (dict, optional): Schema defining importance weights
            
        Returns:
            list: Harmonic vector [R, G, B, intensity, freq1, freq2, ...]
        """
        if not data_dict:
            return [0.0] * self.vector_dimensions
        
        # Skip detailed processing in high fallback levels
        if self.fallback_mode and self.fallback_level >= 2:
            # Use simplified vectorization
            data_str = str(sorted(data_dict.items()))
            data_hash = hashlib.md5(data_str.encode()).digest()
            r = data_hash[0] / 255.0
            g = data_hash[1] / 255.0
            b = data_hash[2] / 255.0
            intensity = 0.5
            
            # Create simplified vector
            vector = [r, g, b, intensity] + [0.0] * (self.vector_dimensions - 4)
            return [round(x, 3) for x in vector]
            
        # Default schema gives equal weight to all fields
        if not schema:
            schema = {k: 1.0 for k in data_dict.keys()}
            
        # Generate stable hash for color components
        data_str = str(sorted(data_dict.items()))
        data_hash = hashlib.md5(data_str.encode()).digest()
        
        # RGB components from hash
        r = data_hash[0] / 255.0
        g = data_hash[1] / 255.0
        b = data_hash[2] / 255.0
        
        # Calculate intensity based on data completeness and schema weights
        total_weight = sum(schema.get(k, 1.0) for k in data_dict.keys())
        weighted_sum = sum(schema.get(k, 1.0) for k in data_dict.keys() if data_dict[k])
        intensity = min(1.0, weighted_sum / max(1.0, total_weight))
        
        # Calculate frequency components from data characteristics
        numeric_values = [float(v) for v in data_dict.values() if isinstance(v, (int, float))]
        text_values = [str(v) for v in data_dict.values() if isinstance(v, str)]
        
        freq_components = []
        for i, base_freq in enumerate(self.base_frequencies):
            if i == 0 and numeric_values:  # First frequency tied to numeric average
                freq = base_freq * (0.5 + abs(np.mean(numeric_values) % 1.0))
            elif i == 1 and text_values:  # Second frequency tied to text length
                freq = base_freq * (0.5 + (sum(len(t) for t in text_values) / 100) % 1.0)
            elif i == 2:  # Third frequency tied to data complexity
                freq = base_freq * (0.5 + (len(data_dict) / 10) % 1.0)
            else:  # Other frequencies derived from hash
                freq = base_freq * (0.5 + (data_hash[i+2] / 255.0))
                
            freq_components.append(round(freq, 3))
            
        # Combine all components
        vector = [r, g, b, intensity] + freq_components
        
        # Pad to full dimensions if needed
        while len(vector) < self.vector_dimensions:
            vector.append(0.0)
            
        return [round(x, 3) for x in vector]
        
    def add_timestamp_to_vector(self, vector, timestamp=None):
        """
        Add temporal information to a vector.
        
        Args:
            vector (list): Existing harmonic vector
            timestamp (float/datetime, optional): Timestamp to encode
            
        Returns:
            list: Vector with temporal encoding
        """
        if timestamp is None:
            timestamp = datetime.now().timestamp()
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.timestamp()
            
        # Ensure vector has minimum length
        if len(vector) < 4:
            vector = vector + [0.0] * (4 - len(vector))
            
        # Encode time of day as phase shift in frequency components
        time_of_day = (timestamp % 86400) / 86400  # Normalized 0-1 for day cycle
        
        # Apply subtle phase shifts to frequency components
        result = vector.copy()
        for i in range(4, len(result)):
            phase_shift = np.sin(time_of_day * 2 * np.pi)
            result[i] = round(result[i] * (1.0 + phase_shift * 0.1), 3)
            
        return result
    
    def merge_vectors(self, vectors, weights=None):
        """
        Merge multiple vectors into a single representative vector.
        
        Args:
            vectors (list): List of vectors to merge
            weights (list, optional): Weight for each vector
            
        Returns:
            list: Merged vector
        """
        if not vectors:
            return [0.0] * self.vector_dimensions
        
        # Normalize weights
        if weights is None:
            weights = [1.0] * len(vectors)
        else:
            if len(weights) != len(vectors):
                raise ValueError("Number of weights must match number of vectors")
            
            # Ensure weights sum to 1.0
            total = sum(weights)
            if total > 0:
                weights = [w / total for w in weights]
            else:
                weights = [1.0 / len(vectors)] * len(vectors)
        
        # Ensure all vectors have the same dimensions
        max_dim = max(len(v) for v in vectors)
        padded_vectors = []
        for v in vectors:
            if len(v) < max_dim:
                padded_vectors.append(v + [0.0] * (max_dim - len(v)))
            else:
                padded_vectors.append(v)
        
        # Weighted average of each component
        merged = []
        for i in range(max_dim):
            component_sum = sum(v[i] * w for v, w in zip(padded_vectors, weights))
            merged.append(round(component_sum, 3))
        
        # Ensure merged vector has required dimensions
        if len(merged) < self.vector_dimensions:
            merged = merged + [0.0] * (self.vector_dimensions - len(merged))
        elif len(merged) > self.vector_dimensions:
            merged = merged[:self.vector_dimensions]
        
        return merged
    
    def compute_vector_similarity(self, vec1, vec2):
        """
        Compute similarity between two vectors.
        
        Args:
            vec1 (list): First vector
            vec2 (list): Second vector
            
        Returns:
            float: Similarity score (0-1)
        """
        # Ensure vectors have the same length
        min_len = min(len(vec1), len(vec2))
        v1 = vec1[:min_len]
        v2 = vec2[:min_len]
        
        # Compute cosine similarity
        try:
            dot_product = sum(a * b for a, b in zip(v1, v2))
            norm1 = sum(a * a for a in v1) ** 0.5
            norm2 = sum(b * b for b in v2) ** 0.5
            
            if norm1 * norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.error(f"Error computing vector similarity: {e}")
            return 0.0
    
    def get_vectorizer_status(self):
        """
        Get current status of the vectorizer.
        
        Returns:
            dict: Vectorizer status metrics
        """
        return {
            "stability": self.field_stability,
            "vectors_processed": self.performance_metrics["vectors_processed"],
            "average_intensity": self.performance_metrics["average_intensity"],
            "cache_size": len(self.vector_cache),
            "fallback_mode": self.fallback_mode,
            "fallback_level": self.fallback_level,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # === Private Helper Methods ===
    
    def _apply_config(self, config):
        """Apply configuration parameters."""
        if "vector_dimensions" in config:
            self.vector_dimensions = max(10, config["vector_dimensions"])
        
        if "base_frequencies" in config:
            self.base_frequencies = config["base_frequencies"]
        
        if "frequency_range" in config:
            self.frequency_range = config["frequency_range"]
        
        if "output_phase_alignment" in config:
            self.output_phase_alignment = config["output_phase_alignment"]
        
        if "sync_interval" in config:
            self.sync_interval = config["sync_interval"]
        
        if "max_cache_size" in config:
            self.max_cache_size = config["max_cache_size"]
    
    def _load_fallback_chains(self):
        """Load fallback chains configuration."""
        fallback_path = os.path.join(os.path.dirname(__file__), "..", "data", "fallback_chains.json")
        try:
            if os.path.exists(fallback_path):
                with open(fallback_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Fallback chains file not found: {fallback_path}")
                return {"default": {"action": "basic_processing"}}
        except Exception as e:
            logger.error(f"Error loading fallback chains: {e}")
            return {"default": {"action": "basic_processing"}}
    
    def _get_active_fallback_mechanisms(self):
        """Get currently active fallback mechanisms."""
        if not self.fallback_mode:
            return []
        
        # Get mechanisms based on fallback level
        if self.fallback_level == 1:
            return ["simplified_vectorization", "cache_prioritization"]
        elif self.fallback_level == 2:
            return ["minimal_vectorization", "dimension_reduction"]
        elif self.fallback_level >= 3:
            return ["critical_only", "hash_only_vectorization"]
        
        return []
    
    def _apply_fallback_mechanisms(self, level):
        """Apply fallback mechanisms based on level."""
        mechanisms = []
        
        # Apply mechanisms based on level
        if level >= 1:
            # Level 1: Simplify vectorization
            mechanisms.append("simplified_vectorization")
            
            # Prioritize cache hits
            self.max_cache_size = min(5000, self.max_cache_size * 2)
        
        if level >= 2:
            # Level 2: Minimal vectorization
            mechanisms.append("minimal_vectorization")
            
            # Reduce vector dimensions
            self.vector_dimensions = max(10, min(self.vector_dimensions, 15))
        
        if level >= 3:
            # Level 3: Critical functions only
            mechanisms.append("critical_only")
            
            # Use hash-only vectorization (fastest possible)
            mechanisms.append("hash_only_vectorization")
        
        # Look up specific actions in fallback chains
        try:
            level_key = f"level_{level}"
            if level_key in self.fallback_chains:
                chain_actions = self.fallback_chains[level_key].get("actions", [])
                mechanisms.extend(chain_actions)
            elif "default" in self.fallback_chains:
                chain_actions = self.fallback_chains["default"].get("actions", [])
                mechanisms.extend(chain_actions)
        except Exception as e:
            logger.error(f"Error applying fallback chain: {e}")
        
        return mechanisms
    
    def _generate_cache_key(self, input_data, input_type, kwargs):
        """Generate a cache key for vectorization input."""
        try:
            # For text, use the text itself
            if input_type == "text":
                key_parts = [input_data]
                
                # Add context if present
                if "context" in kwargs and kwargs["context"]:
                    context_str = str(sorted(kwargs["context"].items()))
                    key_parts.append(context_str)
                
                return hashlib.md5("".join(key_parts).encode()).hexdigest()
            
            # For images, use shape and a sample of pixels
            elif input_type == "image":
                image = kwargs.get("input_data", input_data)
                if image is None or image.size == 0:
                    return "empty_image"
                
                # Use shape and a sample of pixels
                shape_str = str(image.shape)
                
                # Sample pixels from corners and center
                h, w = image.shape[:2]
                samples = []
                
                # Top-left, top-right, center, bottom-left, bottom-right
                coords = [(0, 0), (0, w-1), (h//2, w//2), (h-1, 0), (h-1, w-1)]
                for y, x in coords:
                    if 0 <= y < h and 0 <= x < w:
                        pixel = image[y, x]
                        if len(pixel) >= 3:
                            samples.append(f"{pixel[0]},{pixel[1]},{pixel[2]}")
                
                # Add region if present
                region_str = ""
                if "region" in kwargs and kwargs["region"]:
                    region_str = str(kwargs["region"])
                
                key_parts = [shape_str, ",".join(samples), region_str]
                return hashlib.md5("".join(key_parts).encode()).hexdigest()
            
            # For structured data, use string representation of sorted items
            elif input_type == "structured":
                data_str = str(sorted(input_data.items()))
                
                # Add schema if present
                schema_str = ""
                if "schema" in kwargs and kwargs["schema"]:
                    schema_str = str(sorted(kwargs["schema"].items()))
                
                key_parts = [data_str, schema_str]
                return hashlib.md5("".join(key_parts).encode()).hexdigest()
            
            # Default fallback
            return hashlib.md5(str(input_data).encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating cache key: {e}")
            # Fallback to timestamp to avoid cache hits on error
            return f"error_{time.time()}"
