"""
Symbolic Translator module for CortexOS Temporal Cognition.

This module provides translation between symbolic representations and neural
activations, enabling the system to interface with symbolic reasoning systems,
legacy code, and human-readable formats while maintaining neural coherence.

This module implements the Agharmonic Law by providing:
- Harmonic Resonance through compatible translation frequencies
- Cognitive Isolation with well-defined translation interfaces
- Balanced Information Flow through normalized signal amplitudes
- Temporal Synchronization with the Global Sync Manager
- Self-Regulation through adaptive translation parameters
- Graceful Degradation with multi-level fallback mechanisms
- Resonance Chain Integrity through translation validation

Part of the CortexOS Temporal Cognition v2.1 architecture.
"""

import logging
import time
import numpy as np
import threading
import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from collections import defaultdict, deque

# Configure module logger
logger = logging.getLogger(__name__)

# Import core dependencies
try:
    import cortex_core_hooks as hooks
    from phase4.cortex_vectorizer import CortexVectorizer
except ImportError:
    logger.warning("Core dependencies not available, using fallback implementations")
    hooks = None
    CortexVectorizer = None

class SymbolicTranslator:
    """
    Symbolic-to-neural translation system for CortexOS neural architecture.
    
    Enables bidirectional translation between symbolic representations (text, 
    structured data, logical expressions) and neural activation patterns.
    Implements the Agharmonic Law through consistent signal normalization
    and interface contracts.
    """
    
    def __init__(self, vector_dimension=128, translation_threshold=0.65, global_sync_manager=None,
                 translation_log_file="translation_history.json"):
        """
        Initialize the symbolic translator system.
        
        Args:
            vector_dimension (int): Dimension of neural vector representations
            translation_threshold (float): Threshold for translation confidence (0.0-1.0)
            global_sync_manager: Reference to global sync manager
            translation_log_file (str): File to store translation history
        """
        # Setup logging
        logger.info("Initializing SymbolicTranslator module")
        
        # Configuration
        self.vector_dimension = vector_dimension
        self.translation_threshold = translation_threshold
        self.max_translation_time = 2.0  # seconds
        self.translation_log_file = translation_log_file
        self.global_sync_manager = global_sync_manager
        
        # State tracking
        self.translation_cache = {}
        self.symbol_registry = {}
        self.reverse_registry = {}
        self.translation_history = deque(maxlen=100)
        self._lock = threading.Lock()
        self._last_sync = datetime.utcnow()
        self._health_metrics = {
            "translations_count": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "cache_hits": 0,
            "last_error": None,
            "avg_translation_time": 0.0
        }
        
        # Agharmonic compliance parameters
        self.input_frequency_range = (0.2, 1.7)  # in Hz cognitive equivalent
        self.output_phase_alignment = 0.15
        self.resonance_threshold = 0.7
        self.translation_energy_budget = 1.0
        self.fallback_levels = ["normal", "simplified", "minimal", "emergency"]
        self.current_fallback_level = "normal"
        
        # Initialize vectorizer
        if CortexVectorizer:
            self.vectorizer = CortexVectorizer(vector_dimensions=vector_dimension)
        else:
            logger.warning("CortexVectorizer not available, using fallback implementation")
            self.vectorizer = self._create_minimal_vectorizer()
        
        # Load translation history
        self._load_translation_history()
        
        # Initialize symbol mappings
        self._init_symbol_mappings()
        
        # Start monitoring thread
        self._start_monitor_thread()
        
        logger.info("SymbolicTranslator module initialized successfully")
    
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establish frequency compatibility for Agharmonic Law compliance.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "symbolic_translator",
            "rhythm_hz": 0.5,  # 2 seconds per cycle
            "input_range": self.input_frequency_range,
            "output_phase": self.output_phase_alignment,
            "threshold": self.resonance_threshold,
            "vector_dimension": self.vector_dimension,
            "translation_threshold": self.translation_threshold,
            "translation_energy_budget": self.translation_energy_budget,
            "fallback_level": self.current_fallback_level
        }
    
    def interface_contract(self, translation_request: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Define and validate interface contract for Agharmonic Law compliance.
        Required for Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            translation_request: Optional translation request to validate
            
        Returns:
            Dict containing validation result or interface definition
        """
        # Define standard interface
        interface = {
            "inputs": ["symbolic_expression", "neural_pattern", "context", "translation_mode"],
            "outputs": ["translated_result", "confidence_score", "translation_metadata"],
            "translation_modes": ["symbolic_to_neural", "neural_to_symbolic"],
            "symbolic_types": ["text", "logical", "structured", "generic"],
            "fallback_levels": self.fallback_levels
        }
        
        # If no translation request, just return interface definition
        if translation_request is None:
            return interface
        
        # Validate translation request
        if not isinstance(translation_request, dict):
            return {
                "status": "error",
                "message": "Translation request must be a dictionary",
                "valid": False
            }
        
        # Check required fields based on mode
        if "mode" not in translation_request:
            return {
                "status": "error",
                "message": "Missing required field: mode",
                "valid": False
            }
        
        mode = translation_request["mode"]
        if mode not in interface["translation_modes"]:
            return {
                "status": "error",
                "message": f"Invalid translation mode: {mode}. Must be one of {interface['translation_modes']}",
                "valid": False
            }
        
        if mode == "symbolic_to_neural":
            if "symbolic_expression" not in translation_request:
                return {
                    "status": "error",
                    "message": "Missing required field for symbolic_to_neural: symbolic_expression",
                    "valid": False
                }
        elif mode == "neural_to_symbolic":
            if "neural_pattern" not in translation_request:
                return {
                    "status": "error",
                    "message": "Missing required field for neural_to_symbolic: neural_pattern",
                    "valid": False
                }
            
            if "target_type" in translation_request:
                target_type = translation_request["target_type"]
                if target_type not in interface["symbolic_types"]:
                    return {
                        "status": "error",
                        "message": f"Invalid target type: {target_type}. Must be one of {interface['symbolic_types']}",
                        "valid": False
                    }
        
        # Validate context if specified
        if "context" in translation_request:
            context = translation_request["context"]
            if not isinstance(context, dict):
                return {
                    "status": "error",
                    "message": "Context must be a dictionary",
                    "valid": False
                }
        
        return {
            "status": "success",
            "message": "Translation request is valid",
            "valid": True
        }
    
    def cognitive_energy_flow(self, signal: Any) -> Any:
        """
        Normalize signal amplitude for Agharmonic Law compliance.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            signal: Input signal to normalize
            
        Returns:
            Normalized signal
        """
        # Handle different signal types
        if isinstance(signal, (list, np.ndarray)):
            # Convert to numpy array if needed
            if not isinstance(signal, np.ndarray):
                try:
                    signal = np.array(signal)
                except:
                    logger.error("Failed to convert signal to numpy array")
                    return signal
            
            # Check if array is not empty
            if signal.size > 0:
                # Min-max normalization
                signal_min = signal.min()
                signal_max = signal.max()
                if signal_max > signal_min:
                    normalized_signal = (signal - signal_min) / (signal_max - signal_min)
                    
                    # Apply energy budget scaling
                    if self.translation_energy_budget < 1.0:
                        # Scale down signal amplitude
                        normalized_signal *= self.translation_energy_budget
                        logger.debug(f"Signal scaled by energy budget: {self.translation_energy_budget:.2f}")
                    
                    return normalized_signal
                else:
                    # If all values are the same, return zeros with same shape
                    return np.zeros_like(signal)
        elif isinstance(signal, str):
            # For string signals, we can't normalize directly
            # Instead, return a dict with metadata about the signal
            return {
                "type": "string",
                "length": len(signal),
                "complexity": min(1.0, len(signal) / 1000),  # Normalize by 1000 chars
                "energy_allocation": min(1.0, len(signal) / 1000) * self.translation_energy_budget
            }
        elif isinstance(signal, dict):
            # For dict signals, normalize values if numeric
            normalized_dict = {}
            for key, value in signal.items():
                if isinstance(value, (int, float)):
                    # Normalize to 0-1 range (assuming reasonable values)
                    normalized_dict[key] = min(1.0, max(0.0, value / 100))
                else:
                    normalized_dict[key] = value
            return normalized_dict
        
        # If we can't normalize, return original signal
        return signal
    
    def sync_clock(self, global_clock: Any = None) -> Dict[str, Any]:
        """
        Synchronize with global temporal framework for Agharmonic Law compliance.
        Required for Agharmonic Law Tenet 4: Temporal Synchronization.
        
        Args:
            global_clock: Global clock reference
            
        Returns:
            Dict containing synchronization status
        """
        try:
            current_time = datetime.utcnow()
            time_since_last_sync = (current_time - self._last_sync).total_seconds()
            
            # If we've synced recently, skip
            if time_since_last_sync < 60:  # 1 minute
                return {
                    "status": "skipped",
                    "message": f"Recent sync {time_since_last_sync:.1f}s ago, skipping",
                    "last_sync": self._last_sync.isoformat()
                }
            
            if global_clock:
                if hasattr(global_clock, 'get_sync_stats'):
                    stats = global_clock.get_sync_stats()
                    
                    # Get thresholds from sync_policy.json if available
                    if hasattr(global_clock, 'get_sync_policy'):
                        policy = global_clock.get_sync_policy()
                        if "translation" in policy:
                            self.translation_threshold = policy["translation"].get("threshold", self.translation_threshold)
                            self.max_translation_time = policy["translation"].get("max_time", self.max_translation_time)
                            self.translation_energy_budget = policy["translation"].get("energy_budget", self.translation_energy_budget)
                            
                    # Adjust translation parameters based on system load
                    if stats.get('cycle_time', 5) > 5:  # System under load
                        logger.info("System under load, adjusting translation parameters")
                        # Increase threshold under load to be more selective
                        self.translation_threshold = min(0.9, self.translation_threshold + 0.1)
                        # Decrease max translation time
                        self.max_translation_time = max(0.5, self.max_translation_time * 0.8)
                    else:  # Normal load
                        # Reset to default values or policy values
                        self.translation_threshold = 0.65
                        self.max_translation_time = 2.0
                        
                self._last_sync = current_time
                
                return {
                    "status": "synced",
                    "message": "Successfully synchronized with global clock",
                    "thresholds": {
                        "translation": self.translation_threshold,
                        "max_time": self.max_translation_time,
                        "energy_budget": self.translation_energy_budget
                    },
                    "last_sync": self._last_sync.isoformat()
                }
                
            elif self.global_sync_manager:
                return self.sync_clock(self.global_sync_manager)
            else:
                # No global clock, use internal timing
                self._last_sync = current_time
                
                return {
                    "status": "internal",
                    "message": "Using internal clock, no global sync manager available",
                    "last_sync": self._last_sync.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to sync with global clock: {e}")
            
            return {
                "status": "error",
                "message": f"Failed to sync with global clock: {e}",
                "last_sync": self._last_sync.isoformat()
            }
    
    def self_regulate(self) -> Dict[str, Any]:
        """
        Implement self-regulation with adaptive translation parameters.
        Required for Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            Dict containing self-regulation metrics
        """
        with self._lock:
            translation_count = self._health_metrics["translations_count"]
            success_rate = self._health_metrics["successful_translations"] / max(1, translation_count)
            cache_hit_rate = self._health_metrics["cache_hits"] / max(1, translation_count)
            
        # Check if we're having low success rate
        if translation_count > 10 and success_rate < 0.5:
            logger.warning("Self-regulation: Low translation success rate, adjusting parameters")
            
            # Decrease translation threshold to be less selective
            self.translation_threshold = max(0.4, self.translation_threshold - 0.1)
            
            # Move to more conservative fallback level
            self._escalate_fallback_level()
        
        # If very high success rate, gradually return to normal
        elif translation_count > 10 and success_rate > 0.9 and self.current_fallback_level != "normal":
            logger.info("Self-regulation: High translation success rate, normalizing parameters")
            
            # Increase translation threshold to be more selective
            self.translation_threshold = min(0.8, self.translation_threshold + 0.05)
            
            # Move to less conservative fallback level
            self._deescalate_fallback_level()
        
        # Check cache size and prune if necessary
        if len(self.translation_cache) > 1000:
            # Remove oldest 20% of entries
            prune_count = int(len(self.translation_cache) * 0.2)
            oldest_keys = sorted(self.translation_cache.keys(), 
                               key=lambda k: self.translation_cache[k].get('timestamp', 0))[:prune_count]
            
            for key in oldest_keys:
                del self.translation_cache[key]
            
            logger.info(f"Self-regulation: Pruned {prune_count} entries from translation cache")
        
        # Adjust cache behavior based on hit rate
        if cache_hit_rate < 0.2 and len(self.translation_cache) > 100:
            # Low hit rate with large cache, clear half the cache
            prune_count = int(len(self.translation_cache) * 0.5)
            oldest_keys = sorted(self.translation_cache.keys(), 
                               key=lambda k: self.translation_cache[k].get('timestamp', 0))[:prune_count]
            
            for key in oldest_keys:
                del self.translation_cache[key]
            
            logger.info(f"Self-regulation: Low cache hit rate, cleared {prune_count} entries")
        
        # Check for parameter coherence
        if self.translation_threshold > 0.9:
            logger.warning("Self-regulation: Translation threshold too high, adjusting")
            self.translation_threshold = 0.9
        elif self.translation_threshold < 0.3:
            logger.warning("Self-regulation: Translation threshold too low, adjusting")
            self.translation_threshold = 0.3
        
        # Save translation history periodically
        if translation_count % 10 == 0 and translation_count > 0:
            self._save_translation_history()
        
        return {
            "translation_threshold": self.translation_threshold,
            "max_translation_time": self.max_translation_time,
            "fallback_level": self.current_fallback_level,
            "translation_energy_budget": self.translation_energy_budget,
            "success_rate": success_rate,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self.translation_cache),
            "health_metrics": self._health_metrics,
            "last_sync": self._last_sync.isoformat()
        }
    
    def _escalate_fallback_level(self) -> None:
        """
        Escalate to more conservative fallback level.
        """
        current_index = self.fallback_levels.index(self.current_fallback_level)
        if current_index < len(self.fallback_levels) - 1:
            self.current_fallback_level = self.fallback_levels[current_index + 1]
            logger.warning(f"Escalated to fallback level: {self.current_fallback_level}")
    
    def _deescalate_fallback_level(self) -> None:
        """
        De-escalate to less conservative fallback level.
        """
        current_index = self.fallback_levels.index(self.current_fallback_level)
        if current_index > 0:
            self.current_fallback_level = self.fallback_levels[current_index - 1]
            logger.info(f"De-escalated to fallback level: {self.current_fallback_level}")
    
    def graceful_fallback(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement graceful degradation for Agharmonic Law compliance.
        Required for Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error: The exception that occurred
            context: Context information about the operation
            
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning(f"Executing graceful fallback: {error}")
        
        mode = context.get("mode", "unknown")
        
        # Record error
        with self._lock:
            self._health_metrics["last_error"] = str(error)
            
        # Create fallback translation result
        fallback_result = {
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "fallback",
            "error": str(error),
            "fallback_level": self.current_fallback_level
        }
        
        # Determine fallback action based on current level and mode
        if self.current_fallback_level == "normal":
            # Try alternative translation approach
            fallback_result["fallback_action"] = "alternative_approach"
            
            if mode == "symbolic_to_neural":
                symbolic_expression = context.get("symbolic_expression")
                if symbolic_expression:
                    # Try simplified vectorization
                    try:
                        simplified_result = self._simplified_vectorize(symbolic_expression)
                        fallback_result["result"] = simplified_result
                        fallback_result["confidence"] = 0.5
                    except Exception as alt_error:
                        logger.error(f"Simplified vectorization failed: {alt_error}")
                        fallback_result["simplified_error"] = str(alt_error)
            
            elif mode == "neural_to_symbolic":
                neural_pattern = context.get("neural_pattern")
                if isinstance(neural_pattern, (list, np.ndarray)):
                    # Try simplified devectorization
                    try:
                        simplified_result = self._simplified_devectorize(neural_pattern)
                        fallback_result["result"] = simplified_result
                        fallback_result["confidence"] = 0.5
                    except Exception as alt_error:
                        logger.error(f"Simplified devectorization failed: {alt_error}")
                        fallback_result["simplified_error"] = str(alt_error)
            
        elif self.current_fallback_level == "simplified":
            # Use cached translation if available
            fallback_result["fallback_action"] = "use_cached"
            
            if mode == "symbolic_to_neural":
                symbolic_expression = context.get("symbolic_expression")
                if symbolic_expression:
                    # Try to find similar cached translation
                    cached_result = self._find_similar_cached_translation(symbolic_expression, mode)
                    if cached_result:
                        fallback_result["result"] = cached_result.get("result")
                        fallback_result["confidence"] = cached_result.get("confidence", 0.4)
                        fallback_result["cache_match"] = True
                    else:
                        # If no cache, use minimal translation
                        try:
                            minimal_result = self._minimal_vectorize(symbolic_expression)
                            fallback_result["result"] = minimal_result
                            fallback_result["confidence"] = 0.3
                        except Exception as min_error:
                            logger.error(f"Minimal vectorization failed: {min_error}")
                            fallback_result["minimal_error"] = str(min_error)
            
            elif mode == "neural_to_symbolic":
                neural_pattern = context.get("neural_pattern")
                if isinstance(neural_pattern, (list, np.ndarray)):
                    # Try to find similar cached translation
                    cached_result = self._find_similar_cached_translation(neural_pattern, mode)
                    if cached_result:
                        fallback_result["result"] = cached_result.get("result")
                        fallback_result["confidence"] = cached_result.get("confidence", 0.4)
                        fallback_result["cache_match"] = True
                    else:
                        # If no cache, use minimal translation
                        try:
                            minimal_result = self._minimal_devectorize(neural_pattern)
                            fallback_result["result"] = minimal_result
                            fallback_result["confidence"] = 0.3
                        except Exception as min_error:
                            logger.error(f"Minimal devectorization failed: {min_error}")
                            fallback_result["minimal_error"] = str(min_error)
            
        elif self.current_fallback_level == "minimal":
            # Only return basic pattern matching
            fallback_result["fallback_action"] = "pattern_matching"
            
            if mode == "symbolic_to_neural":
                # Return zero vector
                fallback_result["result"] = np.zeros(self.vector_dimension)
                fallback_result["confidence"] = 0.1
            
            elif mode == "neural_to_symbolic":
                # Return empty string
                fallback_result["result"] = ""
                fallback_result["confidence"] = 0.1
            
        else:  # emergency
            # Emergency mode - only critical functions
            fallback_result["fallback_action"] = "emergency_only"
            
            # Return predefined emergency response
            if mode == "symbolic_to_neural":
                fallback_result["result"] = np.ones(self.vector_dimension) * 0.5
                fallback_result["confidence"] = 0.05
            elif mode == "neural_to_symbolic":
                fallback_result["result"] = "TRANSLATION_ERROR"
                fallback_result["confidence"] = 0.05
            
        # Escalate fallback level if needed
        if self.current_fallback_level != "emergency":
            retry_count = context.get("retry_count", 0)
            if retry_count > 3:
                self._escalate_fallback_level()
                fallback_result["escalated_to"] = self.current_fallback_level
        
        return fallback_result
    
    def _simplified_vectorize(self, symbolic_expression: Any) -> np.ndarray:
        """
        Perform simplified vectorization for normal fallback mode.
        
        Args:
            symbolic_expression: Symbolic expression to vectorize
            
        Returns:
            np.ndarray: Simplified vector representation
        """
        # Convert to string if not already
        if not isinstance(symbolic_expression, str):
            symbolic_expression = str(symbolic_expression)
        
        # Create a simple hash-based vector
        hash_val = int(hashlib.md5(symbolic_expression.encode()).hexdigest(), 16)
        np.random.seed(hash_val)
        
        # Generate a random but deterministic vector
        vector = np.random.rand(self.vector_dimension)
        
        # Normalize
        return vector / np.linalg.norm(vector)
    
    def _simplified_devectorize(self, neural_pattern: np.ndarray) -> str:
        """
        Perform simplified devectorization for normal fallback mode.
        
        Args:
            neural_pattern: Neural pattern to devectorize
            
        Returns:
            str: Simplified symbolic representation
        """
        # Ensure neural pattern is numpy array
        if not isinstance(neural_pattern, np.ndarray):
            neural_pattern = np.array(neural_pattern)
        
        # Normalize
        norm = np.linalg.norm(neural_pattern)
        if norm > 0:
            neural_pattern = neural_pattern / norm
        
        # Convert to hexadecimal string
        hex_str = hashlib.md5(neural_pattern.tobytes()).hexdigest()
        
        return f"VECTOR_{hex_str[:8]}"
    
    def _minimal_vectorize(self, symbolic_expression: Any) -> np.ndarray:
        """
        Perform minimal vectorization for simplified fallback mode.
        
        Args:
            symbolic_expression: Symbolic expression to vectorize
            
        Returns:
            np.ndarray: Minimal vector representation
        """
        # Return a vector of all 0.5
        return np.ones(self.vector_dimension) * 0.5
    
    def _minimal_devectorize(self, neural_pattern: np.ndarray) -> str:
        """
        Perform minimal devectorization for simplified fallback mode.
        
        Args:
            neural_pattern: Neural pattern to devectorize
            
        Returns:
            str: Minimal symbolic representation
        """
        return "MINIMAL_TRANSLATION"
    
    def _find_similar_cached_translation(self, input_data: Any, mode: str) -> Optional[Dict[str, Any]]:
        """
        Find similar cached translation for simplified fallback mode.
        
        Args:
            input_data: Input data to find similar translation for
            mode: Translation mode
            
        Returns:
            Dict containing cached translation, or None if not found
        """
        # In a real implementation, this would search the cache
        # For this example, we'll return None
        return None
    
    def resonance_chain_validator(self, translation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate translation result for resonance chain integrity.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            translation_result: Translation result to validate
            
        Returns:
            Dict containing validation results
        """
        # Initialize validation result
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check for required translation result fields
        if not translation_result or not isinstance(translation_result, dict):
            validation_result["valid"] = False
            validation_result["issues"].append("Missing or invalid translation result")
            return validation_result
        
        required_fields = ["result", "confidence", "mode", "timestamp"]
        missing_fields = [field for field in required_fields if field not in translation_result]
        if missing_fields:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check for valid mode
        valid_modes = ["symbolic_to_neural", "neural_to_symbolic"]
        if "mode" in translation_result and translation_result["mode"] not in valid_modes:
            validation_result["warnings"].append(f"Unknown mode: {translation_result['mode']}")
        
        # Check for valid confidence
        if "confidence" in translation_result:
            confidence = translation_result["confidence"]
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                validation_result["warnings"].append(f"Invalid confidence value: {confidence}")
        
        # Check for valid result based on mode
        if "result" in translation_result and "mode" in translation_result:
            result = translation_result["result"]
            mode = translation_result["mode"]
            
            if mode == "symbolic_to_neural":
                # Result should be a neural pattern (numpy array or list)
                if not isinstance(result, (np.ndarray, list)):
                    validation_result["valid"] = False
                    validation_result["issues"].append("Neural pattern result must be a numpy array or list")
                elif isinstance(result, list) and not all(isinstance(x, (int, float)) for x in result):
                    validation_result["valid"] = False
                    validation_result["issues"].append("Neural pattern result must contain only numeric values")
                elif isinstance(result, np.ndarray) and not np.issubdtype(result.dtype, np.number):
                    validation_result["valid"] = False
                    validation_result["issues"].append("Neural pattern result must contain only numeric values")
            
            elif mode == "neural_to_symbolic":
                # For text type, result should be a string
                if "target_type" in translation_result and translation_result["target_type"] == "text":
                    if not isinstance(result, str):
                        validation_result["valid"] = False
                        validation_result["issues"].append("Text result must be a string")
                
                # For structured type, result should be a dict
                elif "target_type" in translation_result and translation_result["target_type"] == "structured":
                    if not isinstance(result, dict):
                        validation_result["valid"] = False
                        validation_result["issues"].append("Structured result must be a dictionary")
        
        # Check for timestamp validity
        if "timestamp" in translation_result:
            try:
                translation_time = datetime.fromisoformat(translation_result["timestamp"])
                current_time = datetime.utcnow()
                time_diff = (current_time - translation_time).total_seconds()
                
                # Translation should be recent
                if time_diff > 60:  # 1 minute
                    validation_result["warnings"].append(f"Translation result is stale: {time_diff:.1f} seconds old")
            except (ValueError, TypeError):
                validation_result["warnings"].append("Invalid timestamp format")
        
        # Check for resonance disruption
        if "resonance_impact" in translation_result:
            impact = translation_result["resonance_impact"]
            if impact > 0.5:
                validation_result["valid"] = False
                validation_result["issues"].append(f"High resonance impact: {impact:.2f}")
            elif impact > 0.2:
                validation_result["warnings"].append(f"Moderate resonance impact: {impact:.2f}")
        
        # If validation failed, suggest corrective actions
        if not validation_result["valid"]:
            validation_result["corrective_actions"] = self._suggest_corrective_actions(validation_result["issues"])
        
        return validation_result
    
    def _suggest_corrective_actions(self, issues: List[str]) -> List[str]:
        """
        Suggest corrective actions for validation issues.
        
        Args:
            issues: List of validation issues
            
        Returns:
            List of suggested corrective actions
        """
        corrective_actions = []
        
        for issue in issues:
            if "Missing required fields" in issue:
                corrective_actions.append("Ensure translation result contains all required fields")
            elif "Neural pattern result must be" in issue:
                corrective_actions.append("Convert result to numpy array with numeric values")
            elif "Text result must be a string" in issue:
                corrective_actions.append("Convert result to string")
            elif "Structured result must be a dictionary" in issue:
                corrective_actions.append("Convert result to dictionary")
            elif "High resonance impact" in issue:
                corrective_actions.append("Reduce translation impact by using more conservative parameters")
        
        return corrective_actions
    
    def symbolic_to_neural(self, symbolic_expression: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Translate symbolic expression to neural activation pattern.
        
        Args:
            symbolic_expression: Symbolic expression to translate
            context (dict, optional): Additional context for translation
            
        Returns:
            dict: Translation results with neural pattern
        """
        # Initialize context if None
        context = context or {}
        
        # Check cache for existing translation
        cache_key = f"s2n:{hash(str(symbolic_expression))}"
        if cache_key in self.translation_cache:
            cached = self.translation_cache[cache_key]
            logger.debug(f"Cache hit for symbolic expression: {symbolic_expression}")
            
            with self._lock:
                self._health_metrics["cache_hits"] += 1
                self._health_metrics["translations_count"] += 1
                self._health_metrics["successful_translations"] += 1
            
            return cached
        
        # Start translation timer
        start_time = time.time()
        
        try:
            # Create translation request for validation
            translation_request = {
                "mode": "symbolic_to_neural",
                "symbolic_expression": symbolic_expression,
                "context": context
            }
            
            # Validate request
            validation = self.interface_contract(translation_request)
            if not validation.get("valid", False) and "status" in validation:
                logger.error(f"Invalid translation request: {validation.get('message')}")
                return {
                    'result': None,
                    'confidence': 0.0,
                    'error': validation.get('message', 'Invalid translation request'),
                    'mode': 'symbolic_to_neural',
                    'timestamp': time.time()
                }
            
            # Determine expression type
            expr_type = self._determine_expression_type(symbolic_expression)
            
            # Normalize input signal
            normalized_input = self.cognitive_energy_flow(symbolic_expression)
            
            # Select translation method based on type
            if expr_type == 'text':
                neural_pattern, confidence = self._translate_text(symbolic_expression, context)
            elif expr_type == 'logical':
                neural_pattern, confidence = self._translate_logical(symbolic_expression, context)
            elif expr_type == 'structured':
                neural_pattern, confidence = self._translate_structured(symbolic_expression, context)
            else:
                neural_pattern, confidence = self._translate_generic(symbolic_expression, context)
            
            # Check translation timeout
            if time.time() - start_time > self.max_translation_time:
                logger.warning(f"Translation timeout for expression: {symbolic_expression}")
                
                # Update metrics
                with self._lock:
                    self._health_metrics["translations_count"] += 1
                    self._health_metrics["failed_translations"] += 1
                
                return {
                    'result': None,
                    'confidence': 0.0,
                    'error': 'translation_timeout',
                    'mode': 'symbolic_to_neural',
                    'timestamp': time.time()
                }
            
            # Calculate translation time
            translation_time = time.time() - start_time
            
            # Create translation result
            translation_result = {
                'result': neural_pattern,
                'confidence': confidence,
                'expression_type': expr_type,
                'mode': 'symbolic_to_neural',
                'translation_time': translation_time,
                'timestamp': time.time()
            }
            
            # Update metrics
            with self._lock:
                self._health_metrics["translations_count"] += 1
                self._health_metrics["successful_translations"] += 1
                
                # Update average translation time with exponential moving average
                alpha = 0.1  # Smoothing factor
                self._health_metrics["avg_translation_time"] = (
                    (1 - alpha) * self._health_metrics["avg_translation_time"] + 
                    alpha * translation_time
                )
            
            # Add to translation history
            self._add_to_translation_history({
                "input": str(symbolic_expression)[:50] + "..." if len(str(symbolic_expression)) > 50 else str(symbolic_expression),
                "mode": "symbolic_to_neural",
                "expression_type": expr_type,
                "confidence": confidence,
                "translation_time": translation_time,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Cache result if confidence is high enough
            if confidence >= self.translation_threshold:
                self.translation_cache[cache_key] = translation_result
            
            # Validate resonance chain
            validation = self.resonance_chain_validator(translation_result)
            if not validation["valid"]:
                logger.warning(f"Resonance chain validation failed: {validation['issues']}")
                translation_result['resonance_warning'] = validation["issues"]
                translation_result['corrective_actions'] = validation.get("corrective_actions", [])
            
            return translation_result
            
        except Exception as e:
            logger.error(f"Error during symbolic to neural translation: {e}")
            
            # Update metrics
            with self._lock:
                self._health_metrics["translations_count"] += 1
                self._health_metrics["failed_translations"] += 1
                self._health_metrics["last_error"] = str(e)
            
            # Use graceful fallback
            return self.graceful_fallback(e, {
                "mode": "symbolic_to_neural",
                "symbolic_expression": symbolic_expression,
                "retry_count": context.get("retry_count", 0)
            })
    
    def neural_to_symbolic(self, neural_pattern: np.ndarray, target_type: str = 'text', context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Translate neural activation pattern to symbolic expression.
        
        Args:
            neural_pattern: Neural pattern to translate
            target_type (str): Target symbolic type ('text', 'logical', 'structured')
            context (dict, optional): Additional context for translation
            
        Returns:
            dict: Translation results with symbolic expression
        """
        # Initialize context if None
        context = context or {}
        
        # Ensure neural pattern is numpy array
        if not isinstance(neural_pattern, np.ndarray):
            try:
                neural_pattern = np.array(neural_pattern)
            except:
                logger.error("Failed to convert neural pattern to numpy array")
                return {
                    'result': None,
                    'confidence': 0.0,
                    'error': 'invalid_neural_pattern',
                    'mode': 'neural_to_symbolic',
                    'timestamp': time.time()
                }
        
        # Check cache for existing translation
        cache_key = f"n2s:{hash(neural_pattern.tobytes())}:{target_type}"
        if cache_key in self.translation_cache:
            cached = self.translation_cache[cache_key]
            logger.debug(f"Cache hit for neural pattern to {target_type}")
            
            with self._lock:
                self._health_metrics["cache_hits"] += 1
                self._health_metrics["translations_count"] += 1
                self._health_metrics["successful_translations"] += 1
            
            return cached
        
        # Start translation timer
        start_time = time.time()
        
        try:
            # Create translation request for validation
            translation_request = {
                "mode": "neural_to_symbolic",
                "neural_pattern": neural_pattern,
                "target_type": target_type,
                "context": context
            }
            
            # Validate request
            validation = self.interface_contract(translation_request)
            if not validation.get("valid", False) and "status" in validation:
                logger.error(f"Invalid translation request: {validation.get('message')}")
                return {
                    'result': None,
                    'confidence': 0.0,
                    'error': validation.get('message', 'Invalid translation request'),
                    'mode': 'neural_to_symbolic',
                    'timestamp': time.time()
                }
            
            # Normalize input signal
            normalized_pattern = self.cognitive_energy_flow(neural_pattern)
            
            # Select translation method based on target type
            if target_type == 'text':
                symbolic_expression, confidence = self._translate_to_text(normalized_pattern, context)
            elif target_type == 'logical':
                symbolic_expression, confidence = self._translate_to_logical(normalized_pattern, context)
            elif target_type == 'structured':
                symbolic_expression, confidence = self._translate_to_structured(normalized_pattern, context)
            else:
                symbolic_expression, confidence = self._translate_to_generic(normalized_pattern, context)
            
            # Check translation timeout
            if time.time() - start_time > self.max_translation_time:
                logger.warning(f"Translation timeout for neural pattern to {target_type}")
                
                # Update metrics
                with self._lock:
                    self._health_metrics["translations_count"] += 1
                    self._health_metrics["failed_translations"] += 1
                
                return {
                    'result': None,
                    'confidence': 0.0,
                    'error': 'translation_timeout',
                    'mode': 'neural_to_symbolic',
                    'timestamp': time.time()
                }
            
            # Calculate translation time
            translation_time = time.time() - start_time
            
            # Create translation result
            translation_result = {
                'result': symbolic_expression,
                'confidence': confidence,
                'target_type': target_type,
                'mode': 'neural_to_symbolic',
                'translation_time': translation_time,
                'timestamp': time.time()
            }
            
            # Update metrics
            with self._lock:
                self._health_metrics["translations_count"] += 1
                self._health_metrics["successful_translations"] += 1
                
                # Update average translation time with exponential moving average
                alpha = 0.1  # Smoothing factor
                self._health_metrics["avg_translation_time"] = (
                    (1 - alpha) * self._health_metrics["avg_translation_time"] + 
                    alpha * translation_time
                )
            
            # Add to translation history
            self._add_to_translation_history({
                "input": "neural_pattern",
                "mode": "neural_to_symbolic",
                "target_type": target_type,
                "confidence": confidence,
                "translation_time": translation_time,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Cache result if confidence is high enough
            if confidence >= self.translation_threshold:
                self.translation_cache[cache_key] = translation_result
            
            # Validate resonance chain
            validation = self.resonance_chain_validator(translation_result)
            if not validation["valid"]:
                logger.warning(f"Resonance chain validation failed: {validation['issues']}")
                translation_result['resonance_warning'] = validation["issues"]
                translation_result['corrective_actions'] = validation.get("corrective_actions", [])
            
            return translation_result
            
        except Exception as e:
            logger.error(f"Error during neural to symbolic translation: {e}")
            
            # Update metrics
            with self._lock:
                self._health_metrics["translations_count"] += 1
                self._health_metrics["failed_translations"] += 1
                self._health_metrics["last_error"] = str(e)
            
            # Use graceful fallback
            return self.graceful_fallback(e, {
                "mode": "neural_to_symbolic",
                "neural_pattern": neural_pattern,
                "target_type": target_type,
                "retry_count": context.get("retry_count", 0)
            })
    
    def _determine_expression_type(self, symbolic_expression: Any) -> str:
        """
        Determine the type of symbolic expression.
        
        Args:
            symbolic_expression: Symbolic expression to determine type for
            
        Returns:
            str: Expression type
        """
        if isinstance(symbolic_expression, str):
            return 'text'
        elif isinstance(symbolic_expression, dict):
            return 'structured'
        elif isinstance(symbolic_expression, bool) or (isinstance(symbolic_expression, str) and symbolic_expression.lower() in ['true', 'false']):
            return 'logical'
        else:
            return 'generic'
    
    def _translate_text(self, text: str, context: Dict[str, Any]) -> Tuple[np.ndarray, float]:
        """
        Translate text to neural pattern.
        
        Args:
            text: Text to translate
            context: Additional context
            
        Returns:
            Tuple of (neural_pattern, confidence)
        """
        # In a real implementation, this would use the vectorizer
        # For this example, we'll use a simple hash-based approach
        if self.vectorizer:
            try:
                vector = self.vectorizer.vectorize(text)
                return vector, 0.9
            except Exception as e:
                logger.error(f"Vectorizer failed: {e}")
                # Fall back to simplified approach
        
        # Simplified approach
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val)
        
        # Generate a random but deterministic vector
        vector = np.random.rand(self.vector_dimension)
        
        # Normalize
        vector = vector / np.linalg.norm(vector)
        
        return vector, 0.7
    
    def _translate_logical(self, logical_expr: Any, context: Dict[str, Any]) -> Tuple[np.ndarray, float]:
        """
        Translate logical expression to neural pattern.
        
        Args:
            logical_expr: Logical expression to translate
            context: Additional context
            
        Returns:
            Tuple of (neural_pattern, confidence)
        """
        # Convert to boolean if string
        if isinstance(logical_expr, str):
            logical_expr = logical_expr.lower() == 'true'
        
        # Create a vector with 1s for True, 0s for False
        vector = np.ones(self.vector_dimension) if logical_expr else np.zeros(self.vector_dimension)
        
        # Add some noise to avoid perfect correlation
        noise = np.random.rand(self.vector_dimension) * 0.1
        vector = vector + noise
        
        # Normalize
        vector = vector / np.linalg.norm(vector)
        
        return vector, 0.9
    
    def _translate_structured(self, structured_data: Dict[str, Any], context: Dict[str, Any]) -> Tuple[np.ndarray, float]:
        """
        Translate structured data to neural pattern.
        
        Args:
            structured_data: Structured data to translate
            context: Additional context
            
        Returns:
            Tuple of (neural_pattern, confidence)
        """
        # Convert to string representation
        data_str = json.dumps(structured_data, sort_keys=True)
        
        # Use text translation
        vector, confidence = self._translate_text(data_str, context)
        
        return vector, confidence * 0.9  # Slightly lower confidence for structured data
    
    def _translate_generic(self, generic_expr: Any, context: Dict[str, Any]) -> Tuple[np.ndarray, float]:
        """
        Translate generic expression to neural pattern.
        
        Args:
            generic_expr: Generic expression to translate
            context: Additional context
            
        Returns:
            Tuple of (neural_pattern, confidence)
        """
        # Convert to string representation
        expr_str = str(generic_expr)
        
        # Use text translation
        vector, confidence = self._translate_text(expr_str, context)
        
        return vector, confidence * 0.8  # Lower confidence for generic data
    
    def _translate_to_text(self, neural_pattern: np.ndarray, context: Dict[str, Any]) -> Tuple[str, float]:
        """
        Translate neural pattern to text.
        
        Args:
            neural_pattern: Neural pattern to translate
            context: Additional context
            
        Returns:
            Tuple of (text, confidence)
        """
        # In a real implementation, this would use the vectorizer
        # For this example, we'll use a simple approach
        if self.vectorizer and hasattr(self.vectorizer, 'devectorize'):
            try:
                text = self.vectorizer.devectorize(neural_pattern)
                return text, 0.8
            except Exception as e:
                logger.error(f"Devectorizer failed: {e}")
                # Fall back to simplified approach
        
        # Simplified approach - convert to hexadecimal string
        hex_str = hashlib.md5(neural_pattern.tobytes()).hexdigest()
        
        return f"NEURAL_{hex_str[:8]}", 0.5
    
    def _translate_to_logical(self, neural_pattern: np.ndarray, context: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Translate neural pattern to logical expression.
        
        Args:
            neural_pattern: Neural pattern to translate
            context: Additional context
            
        Returns:
            Tuple of (logical_expr, confidence)
        """
        # Calculate mean value
        mean_value = np.mean(neural_pattern)
        
        # If mean is greater than 0.5, return True, otherwise False
        logical_value = mean_value > 0.5
        
        # Calculate confidence based on distance from 0.5
        confidence = abs(mean_value - 0.5) * 2  # Scale to 0-1
        
        return logical_value, confidence
    
    def _translate_to_structured(self, neural_pattern: np.ndarray, context: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """
        Translate neural pattern to structured data.
        
        Args:
            neural_pattern: Neural pattern to translate
            context: Additional context
            
        Returns:
            Tuple of (structured_data, confidence)
        """
        # In a real implementation, this would use more sophisticated techniques
        # For this example, we'll create a simple structure
        
        # Use first few values as structure elements
        if neural_pattern.size >= 4:
            structured_data = {
                "value1": float(neural_pattern[0]),
                "value2": float(neural_pattern[1]),
                "value3": float(neural_pattern[2]),
                "value4": float(neural_pattern[3])
            }
        else:
            structured_data = {
                "value": float(np.mean(neural_pattern))
            }
        
        return structured_data, 0.6
    
    def _translate_to_generic(self, neural_pattern: np.ndarray, context: Dict[str, Any]) -> Tuple[Any, float]:
        """
        Translate neural pattern to generic expression.
        
        Args:
            neural_pattern: Neural pattern to translate
            context: Additional context
            
        Returns:
            Tuple of (generic_expr, confidence)
        """
        # For generic, we'll just use the text translation
        text, confidence = self._translate_to_text(neural_pattern, context)
        
        return text, confidence * 0.8  # Lower confidence for generic
    
    def register_symbol(self, symbol: Any, neural_pattern: np.ndarray = None) -> Dict[str, Any]:
        """
        Register a symbol with its neural pattern.
        
        Args:
            symbol: Symbol to register
            neural_pattern (numpy.ndarray, optional): Neural pattern for symbol
            
        Returns:
            dict: Registration results
        """
        # Generate neural pattern if not provided
        if neural_pattern is None:
            translation_result = self.symbolic_to_neural(symbol)
            if translation_result.get('result') is None:
                logger.error(f"Failed to generate neural pattern for symbol: {symbol}")
                return {
                    'success': False,
                    'error': 'pattern_generation_failed',
                    'symbol': symbol
                }
            neural_pattern = translation_result['result']
        
        # Ensure neural pattern is numpy array
        if not isinstance(neural_pattern, np.ndarray):
            try:
                neural_pattern = np.array(neural_pattern)
            except:
                logger.error(f"Failed to convert neural pattern for symbol: {symbol}")
                return {
                    'success': False,
                    'error': 'invalid_neural_pattern',
                    'symbol': symbol
                }
        
        # Register symbol
        symbol_id = f"sym_{hash(str(symbol)) % 1000000:06d}"
        self.symbol_registry[symbol_id] = {
            'symbol': symbol,
            'pattern': neural_pattern,
            'timestamp': time.time()
        }
        
        # Update reverse registry
        pattern_key = hash(neural_pattern.tobytes())
        self.reverse_registry[pattern_key] = symbol_id
        
        logger.info(f"Registered symbol: {symbol} with ID: {symbol_id}")
        
        return {
            'success': True,
            'symbol_id': symbol_id,
            'symbol': symbol
        }
    
    def lookup_symbol(self, symbol: Any) -> Dict[str, Any]:
        """
        Look up neural pattern for a symbol.
        
        Args:
            symbol: Symbol to look up
            
        Returns:
            dict: Lookup results
        """
        # Search for symbol in registry
        for symbol_id, info in self.symbol_registry.items():
            if info['symbol'] == symbol:
                return {
                    'success': True,
                    'symbol_id': symbol_id,
                    'symbol': symbol,
                    'pattern': info['pattern']
                }
        
        # Symbol not found, try to register it
        logger.info(f"Symbol not found, registering: {symbol}")
        registration = self.register_symbol(symbol)
        
        if registration['success']:
            symbol_id = registration['symbol_id']
            return {
                'success': True,
                'symbol_id': symbol_id,
                'symbol': symbol,
                'pattern': self.symbol_registry[symbol_id]['pattern'],
                'newly_registered': True
            }
        else:
            return {
                'success': False,
                'error': 'symbol_not_found',
                'symbol': symbol
            }
    
    def lookup_pattern(self, neural_pattern: np.ndarray, similarity_threshold: float = 0.9) -> Dict[str, Any]:
        """
        Look up symbol for a neural pattern.
        
        Args:
            neural_pattern: Neural pattern to look up
            similarity_threshold: Threshold for pattern similarity
            
        Returns:
            dict: Lookup results
        """
        # Ensure neural pattern is numpy array
        if not isinstance(neural_pattern, np.ndarray):
            try:
                neural_pattern = np.array(neural_pattern)
            except:
                logger.error("Failed to convert neural pattern to numpy array")
                return {
                    'success': False,
                    'error': 'invalid_neural_pattern'
                }
        
        # Normalize pattern
        norm = np.linalg.norm(neural_pattern)
        if norm > 0:
            neural_pattern = neural_pattern / norm
        
        # Try exact match first
        pattern_key = hash(neural_pattern.tobytes())
        if pattern_key in self.reverse_registry:
            symbol_id = self.reverse_registry[pattern_key]
            return {
                'success': True,
                'symbol_id': symbol_id,
                'symbol': self.symbol_registry[symbol_id]['symbol'],
                'similarity': 1.0
            }
        
        # Try similarity-based lookup
        best_match = None
        best_similarity = 0.0
        
        for symbol_id, info in self.symbol_registry.items():
            registered_pattern = info['pattern']
            
            # Calculate cosine similarity
            similarity = np.dot(neural_pattern, registered_pattern) / (np.linalg.norm(neural_pattern) * np.linalg.norm(registered_pattern))
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = symbol_id
        
        # Check if best match exceeds threshold
        if best_match and best_similarity >= similarity_threshold:
            return {
                'success': True,
                'symbol_id': best_match,
                'symbol': self.symbol_registry[best_match]['symbol'],
                'similarity': best_similarity
            }
        
        # No match found, translate to new symbol
        translation_result = self.neural_to_symbolic(neural_pattern)
        if translation_result.get('result') is not None:
            # Register the new symbol
            new_symbol = translation_result['result']
            registration = self.register_symbol(new_symbol, neural_pattern)
            
            if registration['success']:
                return {
                    'success': True,
                    'symbol_id': registration['symbol_id'],
                    'symbol': new_symbol,
                    'similarity': translation_result.get('confidence', 0.5),
                    'newly_registered': True
                }
        
        return {
            'success': False,
            'error': 'pattern_not_found',
            'best_similarity': best_similarity
        }
    
    def _create_minimal_vectorizer(self) -> Any:
        """
        Create minimal vectorizer for fallback.
        
        Returns:
            Minimal vectorizer object
        """
        class MinimalVectorizer:
            def __init__(self, dimension=128):
                self.dimension = dimension
            
            def vectorize(self, text):
                # Simple hash-based vectorization
                hash_val = int(hashlib.md5(str(text).encode()).hexdigest(), 16)
                np.random.seed(hash_val)
                vector = np.random.rand(self.dimension)
                return vector / np.linalg.norm(vector)
            
            def devectorize(self, vector):
                # Simple hash-based devectorization
                hex_str = hashlib.md5(vector.tobytes()).hexdigest()
                return f"VECTOR_{hex_str[:8]}"
        
        return MinimalVectorizer(dimension=self.vector_dimension)
    
    def _init_symbol_mappings(self) -> None:
        """
        Initialize symbol mappings.
        """
        # In a real implementation, this would initialize mappings
        # For this example, we'll do nothing
        pass
    
    def _load_translation_history(self) -> None:
        """
        Load translation history from file.
        """
        try:
            if os.path.exists(self.translation_log_file):
                with open(self.translation_log_file, 'r') as f:
                    history = json.load(f)
                    self.translation_history = deque(history, maxlen=100)
                    logger.info(f"Loaded {len(self.translation_history)} translation history entries")
        except Exception as e:
            logger.warning(f"Failed to load translation history: {e}")
    
    def _save_translation_history(self) -> None:
        """
        Save translation history to file.
        """
        try:
            with open(self.translation_log_file, 'w') as f:
                json.dump(list(self.translation_history), f, indent=2)
                logger.info(f"Saved {len(self.translation_history)} translation history entries")
        except Exception as e:
            logger.error(f"Failed to save translation history: {e}")
    
    def _add_to_translation_history(self, entry: Dict[str, Any]) -> None:
        """
        Add entry to translation history.
        
        Args:
            entry: Translation history entry
        """
        self.translation_history.append(entry)
    
    def _start_monitor_thread(self) -> None:
        """
        Start monitoring thread.
        """
        def monitor_loop():
            while True:
                try:
                    # Sync with global clock
                    self.sync_clock()
                    
                    # Self-regulate
                    self.self_regulate()
                    
                    # Sleep for a bit
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"Error in monitor loop: {e}")
                    time.sleep(10)  # Sleep longer on error
        
        # Start thread
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get health metrics.
        
        Returns:
            Dict containing health metrics
        """
        with self._lock:
            return self._health_metrics.copy()
    
    def get_translation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get translation history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of translation history entries
        """
        return list(self.translation_history)[-limit:]
