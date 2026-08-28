"""
Neuromodulation module for CortexOS.
Dynamically adjusts resonance parameters based on mood states.
Fully compliant with Agharmonic Law.
"""

import time
import logging
import threading
import json

class Neuromodulation:
    """
    Manages mood states to modulate resonance behavior in CortexOS.
    Adjusts k, threshold, decay, phase_step, and base_frequency for TopKSparseResonance.
    Implements all seven Agharmonic Law interfaces for full compliance.
    """
    def __init__(self, global_sync_manager=None):
        # Core mood configuration parameters
        self.mood_configs = {
            "neutral": {"k": 10, "threshold": 0.85, "decay": 0.20, "phase_step": 0.1, "base_frequency": 1.0},
            "excited": {"k": 15, "threshold": 0.80, "decay": 0.10, "phase_step": 0.05, "base_frequency": 2.0},
            "focused": {"k": 5, "threshold": 0.90, "decay": 0.50, "phase_step": 0.01, "base_frequency": 1.5},
            "cautious": {"k": 8, "threshold": 0.95, "decay": 0.30, "phase_step": 0.02, "base_frequency": 1.2},
            "curious": {"k": 20, "threshold": 0.75, "decay": 0.05, "phase_step": 0.15, "base_frequency": 0.8},
            "alert": {"k": 12, "threshold": 0.88, "decay": 0.15, "phase_step": 0.05, "base_frequency": 1.3},
            "fatigued": {"k": 6, "threshold": 0.70, "decay": 0.05, "phase_step": 0.3, "base_frequency": 0.5},
            "paranoid": {"k": 4, "threshold": 0.98, "decay": 0.40, "phase_step": 0.01, "base_frequency": 1.8},
            "imaginative": {"k": 25, "threshold": 0.70, "decay": 0.03, "phase_step": 0.25, "base_frequency": 0.7},
            "reflective": {"k": 8, "threshold": 0.82, "decay": 0.25, "phase_step": 0.15, "base_frequency": 0.9},
            "impulsive": {"k": 18, "threshold": 0.65, "decay": 0.10, "phase_step": 0.08, "base_frequency": 1.4},
            "dreamy": {"k": 16, "threshold": 0.65, "decay": 0.01, "phase_step": 0.5, "base_frequency": 0.3},
            "aggressive": {"k": 12, "threshold": 0.80, "decay": 0.05, "phase_step": 0.06, "base_frequency": 1.6},
            "calm": {"k": 7, "threshold": 0.88, "decay": 0.35, "phase_step": 0.2, "base_frequency": 0.6},
            "anxious": {"k": 14, "threshold": 0.92, "decay": 0.50, "phase_step": 0.03, "base_frequency": 2.0},
            "playful": {"k": 13, "threshold": 0.78, "decay": 0.08, "phase_step": 0.1, "base_frequency": 1.1}
        }
        
        # Agharmonic Law compliance components
        self.global_sync_manager = global_sync_manager
        self.last_sync_time = time.time()
        self.sync_interval = 300  # Default sync interval in seconds
        self.parameter_limits = {
            "k": {"min": 3, "max": 30},
            "threshold": {"min": 0.5, "max": 0.99},
            "decay": {"min": 0.01, "max": 0.5},
            "phase_step": {"min": 0.01, "max": 0.5},
            "base_frequency": {"min": 0.3, "max": 2.0}
        }
        self.health_metrics = {
            "parameter_adjustments": 0,
            "parameter_violations": 0,
            "fallbacks_triggered": 0,
            "last_health_check": time.time()
        }
        self.validation_lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def harmonic_signature(self, mood=None):
        """
        Establishes frequency compatibility parameters for resonance modulation.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Args:
            mood (str, optional): Specific mood to get signature for
            
        Returns:
            dict: Harmonic signature parameters
        """
        # Use specified mood or default to neutral
        target_mood = mood if mood in self.mood_configs else "neutral"
        mood_params = self.mood_configs[target_mood]
        
        # Calculate frequency range based on mood's base frequency
        base_frequency = mood_params["base_frequency"]
        frequency_range = [base_frequency * 0.5, base_frequency * 1.5]
        
        # Calculate phase alignment based on mood's phase step
        phase_step = mood_params["phase_step"]
        phase_alignment = min(0.2, phase_step * 2)
        
        # Calculate resonance threshold based on mood's threshold
        threshold = mood_params["threshold"]
        resonance_threshold = max(0.7, threshold - 0.1)
        
        # Create diagnostic payload signature for system-wide tracing
        diagnostic_payload = {
            "source": "neuromodulator",
            "mood": target_mood,
            "timestamp": time.time()
        }
        
        return {
            "input_frequency_range": frequency_range,
            "output_phase_alignment": phase_alignment,
            "resonance_threshold": resonance_threshold,
            "diagnostic_payload": diagnostic_payload
        }
        
    def interface_contract(self, operation=None, payload=None):
        """
        Defines allowed function calls and data structures.
        Required for Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            operation (str): Requested operation
            payload (dict): Operation parameters
            
        Returns:
            dict: Validation result with status and message
        """
        # Define allowed operations and their required parameters
        allowed_operations = {
            "adjust_resonance": ["mood"],
            "update_config": ["mood", "parameters"],
            "get_signature": ["mood"],
            "validate_parameters": ["parameters"]
        }
        
        # If no operation specified, return the contract
        if operation is None:
            return {
                "allowed_operations": allowed_operations,
                "parameter_limits": self.parameter_limits,
                "status": "contract_provided"
            }
            
        # Validate operation
        if operation not in allowed_operations:
            return {
                "status": "invalid_operation",
                "message": f"Operation '{operation}' not allowed. Valid operations: {list(allowed_operations.keys())}"
            }
            
        # Validate payload for operation
        if payload is None:
            payload = {}
            
        # Check required parameters
        missing_params = []
        for param in allowed_operations[operation]:
            if param not in payload:
                missing_params.append(param)
                
        if missing_params:
            return {
                "status": "invalid_payload",
                "message": f"Missing required parameters: {missing_params}"
            }
            
        # Specific validation for each operation
        if operation == "adjust_resonance":
            mood = payload["mood"]
            if mood not in self.mood_configs:
                return {
                    "status": "invalid_mood",
                    "message": f"Invalid mood: {mood}. Valid moods: {list(self.mood_configs.keys())}"
                }
                
        elif operation == "update_config":
            mood = payload["mood"]
            parameters = payload["parameters"]
            
            # Validate mood
            if mood not in self.mood_configs and not payload.get("create_if_missing", False):
                return {
                    "status": "invalid_mood",
                    "message": f"Invalid mood: {mood}. Valid moods: {list(self.mood_configs.keys())}"
                }
                
            # Validate parameters
            for param, value in parameters.items():
                if param not in self.parameter_limits:
                    return {
                        "status": "invalid_parameter",
                        "message": f"Invalid parameter: {param}. Valid parameters: {list(self.parameter_limits.keys())}"
                    }
                    
                limits = self.parameter_limits[param]
                if value < limits["min"] or value > limits["max"]:
                    return {
                        "status": "parameter_out_of_range",
                        "message": f"Parameter {param} value {value} outside allowed range [{limits['min']}, {limits['max']}]"
                    }
                    
        return {
            "status": "valid",
            "message": f"Operation '{operation}' with payload is valid"
        }
        
    def cognitive_energy_flow(self, parameters, source_credibility=1.0):
        """
        Normalizes parameter values to maintain balanced resonance.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            parameters (dict): Raw parameter values
            source_credibility (float): Credibility score of the source (0-1)
            
        Returns:
            dict: Normalized parameters
        """
        # Validate input parameters
        if not isinstance(parameters, dict):
            self.logger.warning("Invalid parameters format")
            return None
            
        # Create a copy to avoid modifying the input
        normalized_params = parameters.copy()
        
        # Apply source credibility scaling
        for param in normalized_params:
            if param in self.parameter_limits:
                # Get parameter limits
                limits = self.parameter_limits[param]
                min_val, max_val = limits["min"], limits["max"]
                
                # Get current value
                current_val = normalized_params[param]
                
                # Calculate midpoint of range
                midpoint = (min_val + max_val) / 2
                
                # Calculate distance from midpoint
                distance = abs(current_val - midpoint)
                max_distance = (max_val - min_val) / 2
                
                # Scale distance based on source credibility
                # Lower credibility pulls values closer to midpoint
                scaled_distance = distance * source_credibility
                
                # Recalculate value
                if current_val > midpoint:
                    normalized_params[param] = min(midpoint + scaled_distance, max_val)
                else:
                    normalized_params[param] = max(midpoint - scaled_distance, min_val)
                    
        # Ensure parameter relationships are maintained
        # For example, ensure decay and threshold have an inverse relationship
        if "decay" in normalized_params and "threshold" in normalized_params:
            decay = normalized_params["decay"]
            threshold = normalized_params["threshold"]
            
            # If both decay and threshold are high, reduce decay
            if decay > 0.3 and threshold > 0.9:
                normalized_params["decay"] = 0.3
                
        # Ensure k and threshold have appropriate relationship
        if "k" in normalized_params and "threshold" in normalized_params:
            k = normalized_params["k"]
            threshold = normalized_params["threshold"]
            
            # High k should generally have lower threshold
            if k > 15 and threshold > 0.85:
                normalized_params["threshold"] = 0.85
                
            # Low k should generally have higher threshold
            if k < 8 and threshold < 0.8:
                normalized_params["threshold"] = 0.8
                
        return normalized_params
        
    def sync_clock(self, global_sync_manager=None):
        """
        Connects to the master temporal framework for synchronized parameter updates.
        Required for Agharmonic Law Tenet 4: Temporal Synchronization.
        
        Args:
            global_sync_manager: Optional external sync manager to use
            
        Returns:
            dict: Synchronization status
        """
        current_time = time.time()
        time_since_last_sync = current_time - self.last_sync_time
        
        # Check if sync is needed
        if time_since_last_sync < self.sync_interval:
            return {
                "status": "skipped",
                "message": f"Sync not needed, {self.sync_interval - time_since_last_sync:.2f}s until next sync",
                "last_sync": self.last_sync_time
            }
            
        # Use provided global_sync_manager if available, otherwise use instance one
        sync_manager = global_sync_manager if global_sync_manager else self.global_sync_manager
            
        # If GlobalSyncManager is available, use it
        if sync_manager:
            try:
                # Get timing policy from GlobalSyncManager
                sync_policy = sync_manager.get_sync_policy()
                self.sync_interval = sync_policy.get("neuromodulation_interval", 300)
                
                # Get parameter adjustment factors if available
                if "parameter_adjustment_factors" in sync_policy:
                    factors = sync_policy["parameter_adjustment_factors"]
                    self._apply_adjustment_factors(factors)
                    
            except Exception as e:
                self.logger.warning(f"Failed to sync with GlobalSyncManager: {e}")
                
        # Update last sync time
        self.last_sync_time = current_time
        
        return {
            "status": "synced",
            "message": "Successfully synchronized with temporal framework",
            "sync_interval": self.sync_interval,
            "next_sync": current_time + self.sync_interval
        }
        
    def _apply_adjustment_factors(self, factors):
        """Apply global adjustment factors to all mood parameters."""
        for mood in self.mood_configs:
            for param, factor in factors.items():
                if param in self.mood_configs[mood]:
                    # Apply factor with bounds checking
                    current_val = self.mood_configs[mood][param]
                    new_val = current_val * factor
                    
                    # Ensure within limits
                    if param in self.parameter_limits:
                        limits = self.parameter_limits[param]
                        new_val = max(limits["min"], min(limits["max"], new_val))
                        
                    self.mood_configs[mood][param] = new_val
                    
        self.health_metrics["parameter_adjustments"] += 1
        
    def self_regulate(self):
        """
        Implements feedback loops for parameter stability and adaptation.
        Required for Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            dict: Self-regulation status and metrics
        """
        # Update health metrics
        current_time = time.time()
        time_since_health_check = current_time - self.health_metrics["last_health_check"]
        
        # Initialize regulation actions and fallback level
        regulation_actions = []
        fallback_level = 0
        
        # Perform health check every 10 minutes
        if time_since_health_check >= 600:  # 10 minutes
            # Check for parameter violations
            violations = []
            
            for mood, config in self.mood_configs.items():
                for param, value in config.items():
                    if param in self.parameter_limits:
                        limits = self.parameter_limits[param]
                        if value < limits["min"] or value > limits["max"]:
                            violations.append({
                                "mood": mood,
                                "parameter": param,
                                "value": value,
                                "limits": limits
                            })
                            
            # Fix violations
            for violation in violations:
                mood = violation["mood"]
                param = violation["parameter"]
                value = violation["value"]
                limits = violation["limits"]
                
                # Clamp to limits
                new_value = max(limits["min"], min(limits["max"], value))
                self.mood_configs[mood][param] = new_value
                
                # Record regulation action
                regulation_actions.append(f"fixed_{param}_for_{mood}")
                
            # Update fallback level based on violation count
            if len(violations) > 10:
                fallback_level = 3  # Critical
            elif len(violations) > 5:
                fallback_level = 2  # Moderate
            elif len(violations) > 0:
                fallback_level = 1  # Minor
                
            self.logger.warning(f"Fixed {len(violations)} parameter violations")
            self.health_metrics["parameter_violations"] += len(violations)
            
        # Update health check time
        self.health_metrics["last_health_check"] = current_time
        
        # Return regulation status with required fields
        return {
            "timestamp": current_time,
            "actions": regulation_actions,
            "fallback_level": fallback_level,
            "health_metrics": self.health_metrics,
            "status": "healthy" if fallback_level == 0 else "regulated"
        }
                
            # Check for parameter coherence
            for mood, config in self.mood_configs.items():
                # Ensure parameter relationships make sense
                if "decay" in config and "threshold" in config:
                    decay = config["decay"]
                    threshold = config["threshold"]
                    
                    # If both decay and threshold are high, reduce decay
                    if decay > 0.3 and threshold > 0.9:
                        self.mood_configs[mood]["decay"] = 0.3
                        self.logger.info(f"Self-regulated {mood}: reduced decay to maintain coherence with high threshold")
                        
                # Ensure k and threshold have appropriate relationship
                if "k" in config and "threshold" in config:
                    k = config["k"]
                    threshold = config["threshold"]
                    
                    # High k should generally have lower threshold
                    if k > 15 and threshold > 0.85:
                        self.mood_configs[mood]["threshold"] = 0.85
                        self.logger.info(f"Self-regulated {mood}: reduced threshold to maintain coherence with high k")
                        
                    # Low k should generally have higher threshold
                    if k < 8 and threshold < 0.8:
                        self.mood_configs[mood]["threshold"] = 0.8
                        self.logger.info(f"Self-regulated {mood}: increased threshold to maintain coherence with low k")
                        
            # Update last health check time
            self.health_metrics["last_health_check"] = current_time
            
        return {
            "status": "healthy" if self.health_metrics["parameter_violations"] < 5 else "attention_needed",
            "metrics": self.health_metrics
        }
        
    def graceful_fallback(self, error_type, context=None):
        """
        Provides mechanisms for partial operation during failures.
        Required for Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error_type (str): Type of error triggering fallback
            context (dict): Error context information
            
        Returns:
            dict: Fallback status and actions taken
        """
        self.health_metrics["fallbacks_triggered"] += 1
        
        # Default fallback actions
        fallback_actions = {
            "using_default_parameters": False,
            "mood_reset": False,
            "error_logged": True
        }
        
        # Log the error
        if context:
            self.logger.error(f"Fallback triggered: {error_type} - Context: {context}")
        else:
            self.logger.error(f"Fallback triggered: {error_type}")
            
        # Handle different error types
        if error_type == "invalid_mood":
            # Return neutral mood parameters
            fallback_actions["using_default_parameters"] = True
            
            # Get context information
            requested_mood = context.get("requested_mood", "unknown") if context else "unknown"
            
            self.logger.warning(f"Invalid mood '{requested_mood}', falling back to neutral parameters")
            
            # Return neutral parameters
            return {
                "status": "degraded",
                "actions": fallback_actions,
                "parameters": self.mood_configs["neutral"]
            }
            
        elif error_type == "parameter_corruption":
            # Reset corrupted parameters to defaults
            mood = context.get("mood", "neutral") if context else "neutral"
            
            if mood in self.mood_configs:
                # Create default parameters for this mood
                if mood == "neutral":
                    default_params = {"k": 10, "threshold": 0.85, "decay": 0.20, "phase_step": 0.1, "base_frequency": 1.0}
                elif mood == "excited":
                    default_params = {"k": 15, "threshold": 0.80, "decay": 0.10, "phase_step": 0.05, "base_frequency": 2.0}
                elif mood == "focused":
                    default_params = {"k": 5, "threshold": 0.90, "decay": 0.50, "phase_step": 0.01, "base_frequency": 1.5}
                else:
                    # For other moods, use neutral with slight variations
                    default_params = {"k": 10, "threshold": 0.85, "decay": 0.20, "phase_step": 0.1, "base_frequency": 1.0}
                    
                # Update mood config
                self.mood_configs[mood] = default_params
                
                fallback_actions["parameters_reset"] = True
                self.logger.info(f"Reset corrupted parameters for mood '{mood}'")
                
                return {
                    "status": "degraded",
                    "actions": fallback_actions,
                    "parameters": default_params
                }
            else:
                # Mood doesn't exist, fall back to neutral
                fallback_actions["using_default_parameters"] = True
                fallback_actions["mood_reset"] = True
                
                return {
                    "status": "degraded",
                    "actions": fallback_actions,
                    "parameters": self.mood_configs["neutral"]
                }
                
        elif error_type == "catastrophic_failure":
            # Reset all mood configs to defaults
            self._initialize_default_configs()
            
            fallback_actions["full_reset"] = True
            self.logger.warning("Catastrophic failure: reset all mood configurations to defaults")
            
            return {
                "status": "degraded",
                "actions": fallback_actions,
                "message": "All mood configurations reset to defaults"
            }
            
        # Default fallback: return neutral parameters
        return {
            "status": "degraded",
            "actions": fallback_actions,
            "parameters": self.mood_configs["neutral"]
        }
        
    def _initialize_default_configs(self):
        """Reset all mood configurations to defaults."""
        self.mood_configs = {
            "neutral": {"k": 10, "threshold": 0.85, "decay": 0.20, "phase_step": 0.1, "base_frequency": 1.0},
            "excited": {"k": 15, "threshold": 0.80, "decay": 0.10, "phase_step": 0.05, "base_frequency": 2.0},
            "focused": {"k": 5, "threshold": 0.90, "decay": 0.50, "phase_step": 0.01, "base_frequency": 1.5},
            "cautious": {"k": 8, "threshold": 0.95, "decay": 0.30, "phase_step": 0.02, "base_frequency": 1.2},
            "curious": {"k": 20, "threshold": 0.75, "decay": 0.05, "phase_step": 0.15, "base_frequency": 0.8}
        }
        
    def resonance_chain_validator(self, parameters=None, mood=None):
        """
        Verifies parameter integrity to prevent resonance disruption.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            parameters (dict, optional): Parameters to validate
            mood (str, optional): Mood context for validation
            
        Returns:
            dict: Validation result with status and metrics
        """
        with self.validation_lock:
            # If no specific parameters to validate, check all mood configs
            if parameters is None:
                if mood is not None and mood in self.mood_configs:
                    # Validate specific mood
                    parameters = self.mood_configs[mood]
                else:
                    # Validate all moods
                    invalid_moods = []
                    
                    for mood_name, config in self.mood_configs.items():
                        validation_result = self._validate_parameters(config, mood_name)
                        if validation_result["status"] != "valid":
                            invalid_moods.append({
                                "mood": mood_name,
                                "issues": validation_result["issues"]
                            })
                            
                    if invalid_moods:
                        return {
                            "status": "chain_broken",
                            "message": f"Found {len(invalid_moods)} moods with invalid parameters",
                            "invalid_moods": invalid_moods,
                            "action_required": True
                        }
                        
                    return {
                        "status": "valid",
                        "message": "All mood configurations are valid",
                        "action_required": False
                    }
                    
            # Validate specific parameters
            return self._validate_parameters(parameters, mood)
            
    def _validate_parameters(self, parameters, mood=None):
        """Validate parameter set for resonance integrity."""
        if not parameters:
            return {
                "status": "invalid",
                "message": "Empty parameters",
                "issues": ["empty_parameters"],
                "action_required": True
            }
            
        issues = []
        
        # Check parameter existence
        required_params = ["k", "threshold", "decay", "phase_step", "base_frequency"]
        missing_params = [param for param in required_params if param not in parameters]
        
        if missing_params:
            issues.append({
                "type": "missing_parameters",
                "parameters": missing_params
            })
            
        # Check parameter ranges
        range_violations = []
        for param, value in parameters.items():
            if param in self.parameter_limits:
                limits = self.parameter_limits[param]
                if value < limits["min"] or value > limits["max"]:
                    range_violations.append({
                        "parameter": param,
                        "value": value,
                        "allowed_range": [limits["min"], limits["max"]]
                    })
                    
        if range_violations:
            issues.append({
                "type": "range_violations",
                "violations": range_violations
            })
            
        # Check parameter relationships
        relationship_issues = []
        
        # k and threshold relationship
        if "k" in parameters and "threshold" in parameters:
            k = parameters["k"]
            threshold = parameters["threshold"]
            
            # Very high k with very high threshold is problematic
            if k > 20 and threshold > 0.9:
                relationship_issues.append({
                    "parameters": ["k", "threshold"],
                    "values": [k, threshold],
                    "issue": "high_k_high_threshold"
                })
                
            # Very low k with very low threshold is problematic
            if k < 5 and threshold < 0.7:
                relationship_issues.append({
                    "parameters": ["k", "threshold"],
                    "values": [k, threshold],
                    "issue": "low_k_low_threshold"
                })
                
        # decay and phase_step relationship
        if "decay" in parameters and "phase_step" in parameters:
            decay = parameters["decay"]
            phase_step = parameters["phase_step"]
            
            # High decay with high phase_step causes instability
            if decay > 0.4 and phase_step > 0.3:
                relationship_issues.append({
                    "parameters": ["decay", "phase_step"],
                    "values": [decay, phase_step],
                    "issue": "high_decay_high_phase_step"
                })
                
        # base_frequency and phase_step relationship
        if "base_frequency" in parameters and "phase_step" in parameters:
            base_frequency = parameters["base_frequency"]
            phase_step = parameters["phase_step"]
            
            # High frequency with high phase_step causes resonance disruption
            if base_frequency > 1.5 and phase_step > 0.2:
                relationship_issues.append({
                    "parameters": ["base_frequency", "phase_step"],
                    "values": [base_frequency, phase_step],
                    "issue": "high_frequency_high_phase_step"
                })
                
        if relationship_issues:
            issues.append({
                "type": "parameter_relationships",
                "issues": relationship_issues
            })
            
        # Return validation result
        if issues:
            return {
                "status": "invalid",
                "message": f"Found {len(issues)} issue types in parameters",
                "issues": issues,
                "action_required": True,
                "mood": mood
            }
            
        return {
            "status": "valid",
            "message": "Parameters are valid and maintain resonance integrity",
            "action_required": False,
            "mood": mood
        }
        
    def adjust_resonance_params(self, mood):
        """
        Get resonance parameters for a given mood state.
        
        Args:
            mood (str): Mood state (e.g., 'excited', 'curious', 'paranoid')
        
        Returns:
            dict: Resonance parameters {'k', 'threshold', 'decay', 'phase_step', 'base_frequency'}
        
        Raises:
            ValueError: If mood is invalid
        """
        # Validate operation through interface contract
        contract_result = self.interface_contract("adjust_resonance", {"mood": mood})
        if contract_result["status"] != "valid":
            self.logger.warning(f"Invalid operation: {contract_result['message']}")
            
            # Use graceful fallback
            fallback_result = self.graceful_fallback("invalid_mood", {"requested_mood": mood})
            return fallback_result["parameters"]
            
        # Periodically sync with temporal framework
        if time.time() - self.last_sync_time > self.sync_interval:
            self.sync_clock()
            
        # Periodically self-regulate
        if time.time() - self.health_metrics["last_health_check"] > 600:
            self.self_regulate()
            
        # Validate parameters through resonance chain validator
        if mood in self.mood_configs:
            validation_result = self.resonance_chain_validator(self.mood_configs[mood], mood)
            if validation_result["status"] != "valid" and validation_result.get("action_required", False):
                self.logger.warning(f"Invalid parameters for mood '{mood}': {validation_result['message']}")
                
                # Use graceful fallback
                fallback_result = self.graceful_fallback("parameter_corruption", {"mood": mood})
                return fallback_result["parameters"]
                
            return self.mood_configs[mood]
        else:
            raise ValueError(f"Invalid mood state: {mood}")
            
    def update_mood_config(self, mood, k=None, threshold=None, decay=None, phase_step=None, base_frequency=None):
        """
        Update parameters for a mood state.
        
        Args:
            mood (str): Mood state to update
            k (int, optional): Number of top resonances
            threshold (float, optional): Similarity threshold
            decay (float, optional): Decay rate for voxel strength
            phase_step (float, optional): Phase increment for temporal coding
            base_frequency (float, optional): Base frequency for phase oscillations
        """
        # Prepare parameters dictionary
        parameters = {}
        if k is not None:
            parameters["k"] = k
        if threshold is not None:
            parameters["threshold"] = threshold
        if decay is not None:
            parameters["decay"] = decay
        if phase_step is not None:
            parameters["phase_step"] = phase_step
        if base_frequency is not None:
            parameters["base_frequency"] = base_frequency
            
        # Validate operation through interface contract
        contract_result = self.interface_contract("update_config", {
            "mood": mood,
            "parameters": parameters,
            "create_if_missing": True
        })
        
        if contract_result["status"] != "valid":
            self.logger.warning(f"Invalid update operation: {contract_result['message']}")
            return
            
        # Normalize parameters through cognitive energy flow
        normalized_params = self.cognitive_energy_flow(parameters, 0.9)  # 0.9 credibility for manual updates
        
        # Initialize mood if it doesn't exist
        if mood not in self.mood_configs:
            self.mood_configs[mood] = {
                "k": 10, "threshold": 0.85, "decay": 0.2, "phase_step": 0.1, "base_frequency": 1.0
            }
            
        # Update parameters
        for param, value in normalized_params.items():
            self.mood_configs[mood][param] = value
            
        # Validate updated configuration
        validation_result = self.resonance_chain_validator(self.mood_configs[mood], mood)
        if validation_result["status"] != "valid" and validation_result.get("action_required", False):
            self.logger.warning(f"Updated parameters for mood '{mood}' may cause resonance issues: {validation_result['message']}")
            
        # Log the update
        self.logger.info(f"Updated mood configuration for '{mood}': {normalized_params}")
