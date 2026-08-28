"""
CortexOS Temporal Cognition v2.1
Phase Harmonics Module - Controls phase relationships between neural components
Implements temporal coding for sequence and causality reasoning with full Agharmonic Law compliance
"""

import math
import logging
import time
import json
import os
from datetime import datetime
import threading
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PhaseHarmonics:
    """
    Manages phase relationships and temporal coding for neural components.
    Implements full Agharmonic Law compliance for stable phase operations.
    """
    def __init__(self, config=None):
        """
        Initialize the phase harmonics controller.
        
        Args:
            config (dict, optional): Configuration parameters
        """
        # Core phase parameters
        self.phase_step = 0.1  # Default phase increment per time step
        self.base_frequency = 1.0  # Default oscillation frequency
        self.phase_tolerance = 0.05  # Default phase alignment tolerance
        self.frequency_range = [0.7, 1.3]  # Default frequency range
        self.output_phase_alignment = 0.05  # Default output phase alignment
        
        # Agharmonic compliance parameters
        self.last_sync_time = datetime.utcnow()
        self.sync_interval = 2.0  # seconds
        self.energy_conservation_factor = 0.95
        self.stability_threshold = 0.8
        self.field_stability = 1.0
        self.phase_lock = threading.RLock()
        self.fallback_mode = False
        self.fallback_level = 0
        
        # Performance monitoring
        self.performance_metrics = {
            "phase_adjustments": 0,
            "alignment_errors": 0,
            "last_harmony_score": 1.0,
            "temporal_penalties": []
        }
        
        # Vector history for self-regulation
        self.vector_history = {}
        self.max_history_size = 1000
        
        # Load fallback chains if available
        self.fallback_chains = self._load_fallback_chains()
        
        # Apply custom configuration if provided
        if config:
            self._apply_config(config)
        
        logger.info("PhaseHarmonics initialized with base frequency: %.2f", self.base_frequency)
    
    # === Agharmonic Law Compliance Methods ===
    
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for phase harmonics.
        
        Returns:
            dict: Harmonic signature parameters including frequency range and phase alignment
        """
        return {
            "module": "phase_harmonics",
            "input_frequency_range": self.frequency_range,
            "output_phase_alignment": self.output_phase_alignment,
            "resonance_threshold": 0.8,
            "harmonic_version": "2.1.0",
            "compatible_modules": [
                "neuroengine",
                "resonance_field",
                "swarm_resonance"
            ]
        }
    
    def interface_contract(self, phase_data=None):
        """
        Validates phase data against the expected interface contract.
        
        Args:
            phase_data (dict, optional): Phase data to validate
            
        Returns:
            bool or dict: True if data meets contract requirements, or contract specification if no data
            
        Raises:
            ValueError: If data violates contract requirements
        """
        # Define expected phase data structure
        if phase_data is None:
            return {
                "required_fields": {
                    "harmonic_vector": "list of floats",
                    "time_step": "int or float"
                },
                "optional_fields": {
                    "phase_config": "dict",
                    "frequency_override": "float",
                    "temporal_context": "dict"
                },
                "output_format": {
                    "phased_vector": "list of floats",
                    "phase_info": "dict",
                    "harmony_score": "float (0.0-1.0)"
                }
            }
        
        # Validate phase data
        if not isinstance(phase_data, dict):
            raise ValueError("Phase data must be a dictionary")
        
        # Check required fields
        if "harmonic_vector" not in phase_data:
            raise ValueError("Missing required field: harmonic_vector")
        
        if "time_step" not in phase_data:
            raise ValueError("Missing required field: time_step")
        
        # Validate field types
        if not isinstance(phase_data["harmonic_vector"], list):
            raise ValueError("harmonic_vector must be a list")
        
        if not isinstance(phase_data["time_step"], (int, float)):
            raise ValueError("time_step must be a number")
        
        # Validate optional fields if present
        if "phase_config" in phase_data and not isinstance(phase_data["phase_config"], dict):
            raise ValueError("phase_config must be a dictionary")
        
        if "frequency_override" in phase_data and not isinstance(phase_data["frequency_override"], (int, float)):
            raise ValueError("frequency_override must be a number")
        
        return True
    
    def cognitive_energy_flow(self, vector_amplitude=None):
        """
        Normalizes signal amplitude and information flow to maintain energy conservation.
        
        Args:
            vector_amplitude (float, optional): Input amplitude to normalize
            
        Returns:
            float: Normalized amplitude or current energy level if no input
        """
        # If no input, return current field stability as energy level
        if vector_amplitude is None:
            return self.field_stability
        
        # Ensure amplitude is within bounds
        normalized_amplitude = max(0.0, min(1.0, vector_amplitude))
        
        # Apply energy conservation based on current field stability
        if self.field_stability < self.stability_threshold:
            # Low stability state - conserve energy by dampening amplitude
            normalized_amplitude *= self.energy_conservation_factor
            logger.debug(f"Energy conservation applied: {self.energy_conservation_factor}")
        
        # Apply non-linear normalization to prevent phase saturation
        # This helps prevent destructive interference by smoothing amplitude peaks
        if normalized_amplitude > 0.8:
            # Soft cap on high amplitudes to prevent overloading
            normalized_amplitude = 0.8 + (normalized_amplitude - 0.8) * 0.5
        
        return normalized_amplitude
    
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
            
            # Perform phase alignment validation
            with self.phase_lock:
                # Check if phase alignment is within tolerance
                harmonic_sig = self.harmonic_signature()
                target_phase = harmonic_sig["output_phase_alignment"]
                
                # Calculate current phase alignment error across recent vectors
                alignment_error = self._calculate_phase_alignment_error(target_phase)
                
                # Update performance metrics
                self.performance_metrics["alignment_errors"] = alignment_error
                
                # Apply phase correction if needed
                if alignment_error > self.phase_tolerance:
                    self._adjust_phase_alignment(target_phase, alignment_error)
                    self.performance_metrics["phase_adjustments"] += 1
            
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
        
        with self.phase_lock:
            # Check vector history size and prune if necessary
            for vector_id, history in self.vector_history.items():
                if len(history) > self.max_history_size:
                    # Keep only the most recent entries
                    self.vector_history[vector_id] = history[-int(self.max_history_size/2):]
                    regulation_actions.append("history_pruned")
            
            # Calculate average harmony score from recent operations
            if self.performance_metrics["temporal_penalties"]:
                avg_penalty = sum(self.performance_metrics["temporal_penalties"]) / len(self.performance_metrics["temporal_penalties"])
                new_stability = 1.0 - avg_penalty
                
                # Apply smoothing to stability changes
                self.field_stability = self.field_stability * 0.7 + new_stability * 0.3
                regulation_actions.append("stability_updated")
                
                # Reset temporal penalties list if it gets too large
                if len(self.performance_metrics["temporal_penalties"]) > 100:
                    self.performance_metrics["temporal_penalties"] = self.performance_metrics["temporal_penalties"][-50:]
            
            # Check if field stability is below threshold
            if self.field_stability < self.stability_threshold:
                # Take corrective action
                logger.warning(f"Phase stability low: {self.field_stability:.2f}")
                self._stabilize_phase_field()
                regulation_actions.append("phase_stabilization")
                
                # If critically low, consider fallback mode
                if self.field_stability < 0.4 and not self.fallback_mode:
                    self.graceful_fallback(reason="low_stability")
            
            # Adjust phase step if needed based on performance
            if self.performance_metrics["alignment_errors"] > 0.2:
                # Reduce phase step to improve alignment
                self.phase_step *= 0.95
                regulation_actions.append("phase_step_adjusted")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "actions": regulation_actions,
            "metrics": {
                "field_stability": self.field_stability,
                "phase_step": self.phase_step,
                "alignment_error": self.performance_metrics["alignment_errors"],
                "harmony_score": self.performance_metrics["last_harmony_score"]
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
        if reason == "low_stability":
            self.fallback_level = 1
        elif reason == "phase_incoherence":
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
            issues.append(f"Phase field stability below threshold: {self.field_stability:.2f}")
            integrity *= (self.field_stability / self.stability_threshold)
        
        # Check phase alignment
        harmonic_sig = self.harmonic_signature()
        target_phase = harmonic_sig["output_phase_alignment"]
        alignment_error = self._calculate_phase_alignment_error(target_phase)
        
        if alignment_error > self.phase_tolerance:
            issues.append(f"Phase alignment error above tolerance: {alignment_error:.2f}")
            integrity *= (1.0 - alignment_error)
        
        # Check frequency compatibility
        freq_min, freq_max = harmonic_sig["input_frequency_range"]
        if self.base_frequency < freq_min or self.base_frequency > freq_max:
            issues.append(f"Base frequency {self.base_frequency} outside acceptable range [{freq_min}, {freq_max}]")
            # Calculate how far outside the range
            if self.base_frequency < freq_min:
                deviation = (freq_min - self.base_frequency) / freq_min
            else:
                deviation = (self.base_frequency - freq_max) / freq_max
            integrity *= (1.0 - min(deviation, 0.5))
        
        # Check temporal coherence
        if self.performance_metrics["temporal_penalties"]:
            avg_penalty = sum(self.performance_metrics["temporal_penalties"]) / len(self.performance_metrics["temporal_penalties"])
            if avg_penalty > 0.2:
                issues.append(f"High average temporal penalty: {avg_penalty:.2f}")
                integrity *= (1.0 - avg_penalty)
        
        return {
            "integrity": max(0.1, integrity),  # Ensure minimum integrity of 0.1
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # === Core Phase Harmonics Methods ===
    
    def add_phase_offset(self, harmonic_vector, time_step, config=None):
        """
        Apply phase offset to harmonic vector based on time step.
        
        Args:
            harmonic_vector (list): Input vector [R, G, B, intensity, freq1, freq2, ...]
            time_step (int): Temporal index
            config (dict, optional): Additional configuration parameters
        
        Returns:
            dict: Phase-adjusted vector and metadata
        """
        # Validate input through interface contract
        self.interface_contract({
            "harmonic_vector": harmonic_vector,
            "time_step": time_step,
            "phase_config": config
        })
        
        # Apply energy conservation to vector components
        normalized_vector = harmonic_vector.copy()
        for i in range(len(normalized_vector)):
            if i >= 4:  # Apply to frequency components
                normalized_vector[i] = self.cognitive_energy_flow(normalized_vector[i])
        
        # Extract configuration parameters
        phase_step = config.get("phase_step", self.phase_step) if config else self.phase_step
        base_frequency = config.get("frequency", self.base_frequency) if config else self.base_frequency
        
        # Apply phase offset
        phased_vector = normalized_vector.copy()
        for i in range(4, len(phased_vector)):  # Apply to frequency components
            phase = phase_step * time_step
            phased_vector[i] *= math.sin(base_frequency * time_step + phase)
        
        # Round values for precision
        phased_vector = [round(x, 3) for x in phased_vector]
        
        # Store in history for self-regulation
        vector_id = hash(tuple(harmonic_vector))
        if vector_id not in self.vector_history:
            self.vector_history[vector_id] = []
        self.vector_history[vector_id].append({
            "time_step": time_step,
            "phased_vector": phased_vector,
            "timestamp": time.time()
        })
        
        # Periodically self-regulate
        if time_step % 10 == 0:
            self.self_regulate()
        
        # Periodically sync clock
        self.sync_clock()
        
        return {
            "phased_vector": phased_vector,
            "phase_info": {
                "time_step": time_step,
                "phase": phase_step * time_step,
                "frequency": base_frequency
            },
            "field_stability": self.field_stability
        }

    def compute_phase_similarity(self, vec1, vec2, time_delta, config=None):
        """
        Compute similarity between two vectors with temporal penalty.
        
        Args:
            vec1 (list): First harmonic vector
            vec2 (list): Second harmonic vector
            time_delta (int): Difference in time steps
            config (dict, optional): Additional configuration parameters
        
        Returns:
            dict: Phase-aware similarity score and metadata
        """
        # Validate input
        if not isinstance(vec1, list) or not isinstance(vec2, list):
            raise ValueError("Vectors must be lists")
        
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have the same length")
        
        # Extract configuration parameters
        phase_step = config.get("phase_step", self.phase_step) if config else self.phase_step
        
        # Compute base similarity
        base_similarity = cosine_similarity(vec1, vec2)
        
        # Compute temporal penalty
        temporal_penalty = abs(math.cos(phase_step * time_delta))
        
        # Calculate final similarity score
        similarity_score = round(base_similarity * temporal_penalty, 3)
        
        # Store temporal penalty for self-regulation
        self.performance_metrics["temporal_penalties"].append(1.0 - temporal_penalty)
        self.performance_metrics["last_harmony_score"] = similarity_score
        
        # Periodically self-regulate
        if len(self.performance_metrics["temporal_penalties"]) % 10 == 0:
            self.self_regulate()
        
        return {
            "similarity": similarity_score,
            "base_similarity": base_similarity,
            "temporal_penalty": temporal_penalty,
            "time_delta": time_delta
        }
    
    def normalize_oscillatory_behavior(self, vectors, time_steps):
        """
        Normalize oscillatory behavior across multiple vectors.
        
        Args:
            vectors (list): List of harmonic vectors
            time_steps (list): Corresponding time steps
            
        Returns:
            list: Normalized vectors with consistent phase relationships
        """
        if not vectors or not time_steps or len(vectors) != len(time_steps):
            raise ValueError("Vectors and time_steps must be non-empty lists of the same length")
        
        # Skip detailed processing in fallback mode
        if self.fallback_mode and self.fallback_level >= 2:
            return vectors
        
        normalized_vectors = []
        
        # Calculate average phase
        avg_phase = sum(self.phase_step * t for t in time_steps) / len(time_steps)
        
        # Normalize each vector
        for i, (vec, t) in enumerate(zip(vectors, time_steps)):
            # Calculate phase difference from average
            phase_diff = self.phase_step * t - avg_phase
            
            # Create normalized vector
            norm_vec = vec.copy()
            
            # Adjust frequency components based on phase difference
            for j in range(4, len(norm_vec)):
                # Apply phase correction
                correction_factor = math.cos(phase_diff)
                norm_vec[j] *= correction_factor
            
            normalized_vectors.append(norm_vec)
        
        return normalized_vectors
    
    def phase_align_with_target(self, vector, current_phase, target_phase):
        """
        Align a vector's phase with a target phase.
        
        Args:
            vector (list): Harmonic vector to align
            current_phase (float): Current phase of the vector
            target_phase (float): Target phase to align with
            
        Returns:
            dict: Phase-aligned vector and alignment metrics
        """
        # Calculate phase difference
        phase_diff = (target_phase - current_phase) % (2 * math.pi)
        if phase_diff > math.pi:
            phase_diff = 2 * math.pi - phase_diff
        
        # Skip alignment in high fallback levels
        if self.fallback_mode and self.fallback_level >= 2:
            return {
                "vector": vector,
                "aligned": False,
                "phase_diff": phase_diff
            }
        
        # Create aligned vector
        aligned_vector = vector.copy()
        
        # Apply alignment to frequency components
        for i in range(4, len(aligned_vector)):
            # Calculate alignment factor
            alignment_factor = math.cos(phase_diff / 2)
            aligned_vector[i] *= alignment_factor
        
        # Update performance metrics
        self.performance_metrics["phase_adjustments"] += 1
        
        return {
            "vector": aligned_vector,
            "aligned": True,
            "phase_diff": phase_diff,
            "alignment_factor": math.cos(phase_diff / 2)
        }
    
    def get_phase_status(self):
        """
        Get current status of the phase harmonics system.
        
        Returns:
            dict: Phase status metrics
        """
        return {
            "stability": self.field_stability,
            "phase_step": self.phase_step,
            "base_frequency": self.base_frequency,
            "fallback_mode": self.fallback_mode,
            "fallback_level": self.fallback_level,
            "alignment_error": self.performance_metrics["alignment_errors"],
            "harmony_score": self.performance_metrics["last_harmony_score"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # === Private Helper Methods ===
    
    def _apply_config(self, config):
        """Apply configuration parameters."""
        if "phase_step" in config:
            self.phase_step = config["phase_step"]
        
        if "base_frequency" in config:
            self.base_frequency = config["base_frequency"]
        
        if "phase_tolerance" in config:
            self.phase_tolerance = config["phase_tolerance"]
        
        if "frequency_range" in config:
            self.frequency_range = config["frequency_range"]
        
        if "output_phase_alignment" in config:
            self.output_phase_alignment = config["output_phase_alignment"]
        
        if "sync_interval" in config:
            self.sync_interval = config["sync_interval"]
    
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
            return ["simplified_phase_processing", "energy_conservation"]
        elif self.fallback_level == 2:
            return ["minimal_phase_processing", "phase_stabilization"]
        elif self.fallback_level >= 3:
            return ["critical_only", "phase_isolation"]
        
        return []
    
    def _apply_fallback_mechanisms(self, level):
        """Apply fallback mechanisms based on level."""
        mechanisms = []
        
        # Apply mechanisms based on level
        if level >= 1:
            # Level 1: Simplify phase processing
            self.phase_step = max(0.05, self.phase_step * 0.5)  # Reduce phase step
            mechanisms.append("simplified_phase_processing")
        
        if level >= 2:
            # Level 2: Minimal phase processing
            mechanisms.append("minimal_phase_processing")
            
            # Reset to default frequency
            self.base_frequency = 1.0
        
        if level >= 3:
            # Level 3: Critical functions only
            mechanisms.append("critical_only")
            
            # Isolate phase from external influences
            self.phase_tolerance = 0.2  # Increase tolerance
        
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
    
    def _calculate_phase_alignment_error(self, target_phase):
        """Calculate phase alignment error across recent vectors."""
        if not self.vector_history:
            return 0.0
        
        total_error = 0.0
        count = 0
        
        # Check recent vectors in history
        for vector_id, history in self.vector_history.items():
            if not history:
                continue
            
            # Get most recent entry
            recent = history[-1]
            if "phase_info" in recent and "phase" in recent["phase_info"]:
                phase = recent["phase_info"]["phase"]
                
                # Calculate phase difference (0 to π)
                phase_diff = abs((phase - target_phase) % (2 * math.pi))
                if phase_diff > math.pi:
                    phase_diff = 2 * math.pi - phase_diff
                
                # Normalize to 0-1 range
                normalized_diff = phase_diff / math.pi
                total_error += normalized_diff
                count += 1
        
        # Return average error
        return total_error / count if count > 0 else 0.0
    
    def _adjust_phase_alignment(self, target_phase, error):
        """Adjust phase alignment to reduce error."""
        # Skip adjustment in fallback mode
        if self.fallback_mode and self.fallback_level >= 2:
            return
        
        # Calculate adjustment factor based on error
        adjustment = min(0.01, error / 10.0)
        
        # Adjust phase step to move toward target phase
        if error > 0:
            self.phase_step = max(0.01, self.phase_step * (1.0 - adjustment))
        
        logger.debug(f"Phase step adjusted to {self.phase_step} (error: {error:.3f})")
    
    def _stabilize_phase_field(self):
        """Apply stabilization measures to improve phase field stability."""
        logger.info("Applying phase field stabilization measures")
        
        # Reset phase step to default if it has drifted too far
        if self.phase_step < 0.05 or self.phase_step > 0.2:
            self.phase_step = 0.1
            logger.debug("Phase step reset to default")
        
        # Improve field stability metric
        self.field_stability = min(1.0, self.field_stability * 1.1)
        
        # Clear excessive history
        if sum(len(h) for h in self.vector_history.values()) > self.max_history_size:
            # Keep only the most recent entries for each vector
            for vector_id in self.vector_history:
                if len(self.vector_history[vector_id]) > 10:
                    self.vector_history[vector_id] = self.vector_history[vector_id][-10:]
            
            logger.debug("Vector history pruned during stabilization")


def cosine_similarity(vec1, vec2):
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec1 (list): First vector
        vec2 (list): Second vector
        
    Returns:
        float: Cosine similarity (0-1)
    """
    # Handle edge cases
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    try:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 * norm2 == 0:
            return 0.0
        
        return round(dot_product / (norm1 * norm2), 3)
    except Exception as e:
        logger.error(f"Error computing cosine similarity: {e}")
        return 0.0
