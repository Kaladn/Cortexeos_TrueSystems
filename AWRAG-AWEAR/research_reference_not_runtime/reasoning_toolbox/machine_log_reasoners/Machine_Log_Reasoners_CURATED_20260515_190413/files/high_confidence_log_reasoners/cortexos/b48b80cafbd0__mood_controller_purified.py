"""
Mood Controller module for CortexOS.
Manages system-wide mood state transitions and their effects on neural processing.
Fully compliant with Agharmonic Law.
"""

import json
import time
import random
import logging
import threading
from datetime import datetime
from neuromodulation import Neuromodulator

class MoodController:
    """
    Controls system-wide mood states and transitions for CortexOS.
    Manages mood persistence, transitions, and effects on neural processing parameters.
    Implements all seven Agharmonic Law interfaces for full compliance.
    """
    def __init__(self, mood_to_color_file="mood_to_color.json", initial_mood="neutral", 
                 global_sync_manager=None, resonance_monitor=None):
        self.neuromod = Neuromodulator()
        self.current_mood = initial_mood
        self.mood_start_time = time.time()
        self.mood_history = []
        self.mood_to_color = self._load_mood_to_color(mood_to_color_file)
        self.transition_probabilities = self._initialize_transition_matrix()
        
        # Agharmonic Law compliance components
        self.global_sync_manager = global_sync_manager
        self.resonance_monitor = resonance_monitor
        self.frequency_range = [0.5, 1.5]  # Default frequency range
        self.phase_alignment = 0.1  # Default phase alignment
        self.resonance_threshold = 0.8  # Default resonance threshold
        self.last_sync_time = time.time()
        self.sync_interval = 60  # Default sync interval in seconds
        self.health_metrics = {
            "mood_transitions": 0,
            "anomalies_detected": 0,
            "fallbacks_triggered": 0,
            "last_health_check": time.time()
        }
        self.fallback_mood = "neutral"  # Default fallback mood
        self.validation_lock = threading.RLock()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Log initial mood
        self.logger.info(f"Initialized with mood: {self.current_mood}")
        self._record_mood_change(self.current_mood, "initialization", 1.0)
        
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for mood transitions.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters
        """
        # Calculate dynamic frequency range based on current mood
        mood_params = self.neuromod.adjust_resonance_params(self.current_mood)
        base_frequency = mood_params["base_frequency"]
        
        # Adjust frequency range based on current mood's base frequency
        self.frequency_range = [base_frequency * 0.5, base_frequency * 1.5]
        
        # Create diagnostic payload signature for system-wide tracing
        diagnostic_payload = {
            "source": "mood_controller",
            "mood": self.current_mood,
            "timestamp": time.time()
        }
        
        return {
            "input_frequency_range": self.frequency_range,
            "output_phase_alignment": self.phase_alignment,
            "resonance_threshold": self.resonance_threshold,
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
            "get_mood": [],
            "set_mood": ["mood", "reason"],
            "update_mood": ["input_type", "input_data"],
            "get_history": ["limit"],
            "export_parameters": []
        }
        
        # If no operation specified, return the contract
        if operation is None:
            return {
                "allowed_operations": allowed_operations,
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
            
        # Block recursive self-inspection unless authenticated
        if operation == "get_mood" and payload.get("_internal_inspection") and not payload.get("_auth_token"):
            return {
                "status": "unauthorized",
                "message": "Recursive self-inspection requires authentication"
            }
            
        return {
            "status": "valid",
            "message": f"Operation '{operation}' with payload is valid"
        }
        
    def cognitive_energy_flow(self, input_signal, source_credibility=1.0):
        """
        Normalizes signal amplitude and information flow for mood transitions.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            input_signal (dict): Input signal data
            source_credibility (float): Credibility score of the source (0-1)
            
        Returns:
            dict: Normalized signal
        """
        # Validate input signal
        if not isinstance(input_signal, dict):
            self.logger.warning("Invalid input signal format")
            return None
            
        # Extract signal components
        signal_type = input_signal.get("type", "unknown")
        signal_strength = input_signal.get("strength", 0.5)
        signal_mood = input_signal.get("mood")
        
        # Scale signal strength by source credibility
        normalized_strength = signal_strength * source_credibility
        
        # Apply mood-specific scaling based on current state
        if signal_mood and signal_mood in self.neuromod.mood_configs:
            # Calculate mood distance factor
            current_mood_params = self.neuromod.adjust_resonance_params(self.current_mood)
            target_mood_params = self.neuromod.adjust_resonance_params(signal_mood)
            
            # Use frequency difference as a distance metric
            freq_diff = abs(current_mood_params["base_frequency"] - target_mood_params["base_frequency"])
            mood_distance = min(freq_diff / 2.0, 1.0)  # Normalize to 0-1 range
            
            # Distant moods require stronger signals
            if mood_distance > 0.5:
                required_strength = 0.5 + mood_distance / 2
                if normalized_strength < required_strength:
                    normalized_strength = normalized_strength * 0.8  # Attenuate distant mood signals
                    
        # Prevent signal saturation
        if normalized_strength > 0.95:
            normalized_strength = 0.95
            
        # Create normalized output signal
        normalized_signal = {
            "type": signal_type,
            "strength": normalized_strength,
            "mood": signal_mood,
            "source_credibility": source_credibility,
            "timestamp": time.time()
        }
        
        return normalized_signal
        
    def sync_clock(self):
        """
        Connects to the master temporal framework for synchronized mood transitions.
        Required for Agharmonic Law Tenet 4: Temporal Synchronization.
        
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
            
        # If GlobalSyncManager is available, use it
        if self.global_sync_manager:
            try:
                # Get timing policy from GlobalSyncManager
                sync_policy = self.global_sync_manager.get_sync_policy()
                self.sync_interval = sync_policy.get("mood_transition_interval", 60)
                
                # Align mood transition probabilities with global timing
                transition_scale = sync_policy.get("transition_probability_scale", 1.0)
                if transition_scale != 1.0:
                    self._scale_transition_probabilities(transition_scale)
                    
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
        
    def self_regulate(self):
        """
        Implements feedback loops for mood stability and adaptation.
        Required for Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            dict: Self-regulation status and metrics
        """
        # Update health metrics
        current_time = time.time()
        time_since_health_check = current_time - self.health_metrics["last_health_check"]
        
        # Perform health check every 5 minutes
        if time_since_health_check >= 300:  # 5 minutes
            # Check for mood stagnation
            mood_duration = current_time - self.mood_start_time
            if mood_duration > 3600:  # 1 hour
                self.logger.info(f"Mood '{self.current_mood}' has been active for {mood_duration/3600:.2f} hours")
                
                # Suggest mood transition if stagnant
                suggestion = self.suggest_mood_transition()
                if suggestion["suggested_mood"] != self.current_mood:
                    self.set_mood(
                        suggestion["suggested_mood"],
                        "self_regulation_anti_stagnation",
                        suggestion["confidence"] * 0.8  # Reduce confidence for self-regulation
                    )
                    self.health_metrics["mood_transitions"] += 1
                    
            # Check for rapid mood oscillation
            if len(self.mood_history) >= 10:
                recent_moods = [entry["mood"] for entry in self.mood_history[-10:]]
                unique_moods = set(recent_moods)
                
                # If oscillating between just 2-3 moods rapidly
                if len(unique_moods) <= 3 and len(unique_moods) > 1:
                    oscillation_count = 0
                    for i in range(1, len(recent_moods)):
                        if recent_moods[i] != recent_moods[i-1]:
                            oscillation_count += 1
                            
                    if oscillation_count >= 6:  # High oscillation
                        self.logger.warning("Detected mood oscillation, stabilizing")
                        self.health_metrics["anomalies_detected"] += 1
                        
                        # Stabilize by forcing neutral mood for a period
                        self.set_mood("neutral", "self_regulation_anti_oscillation", 0.9)
                        
            # Update last health check time
            self.health_metrics["last_health_check"] = current_time
            
        # Auto-escalate persistent anomalies to resonance monitor if available
        if self.health_metrics["anomalies_detected"] > 5 and self.resonance_monitor:
            try:
                self.resonance_monitor.report_anomaly("mood_controller", {
                    "type": "persistent_mood_anomalies",
                    "count": self.health_metrics["anomalies_detected"],
                    "current_mood": self.current_mood,
                    "history": self.mood_history[-5:]
                })
            except Exception as e:
                self.logger.error(f"Failed to report anomalies to resonance monitor: {e}")
                
        return {
            "status": "healthy" if self.health_metrics["anomalies_detected"] < 3 else "attention_needed",
            "metrics": self.health_metrics,
            "current_mood_duration": current_time - self.mood_start_time
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
            "mood_reset": False,
            "history_preserved": True,
            "using_default_parameters": False,
            "error_logged": True
        }
        
        # Log the error
        if context:
            self.logger.error(f"Fallback triggered: {error_type} - Context: {context}")
        else:
            self.logger.error(f"Fallback triggered: {error_type}")
            
        # Handle different error types
        if error_type == "invalid_mood":
            # Fallback to neutral mood
            old_mood = self.current_mood
            self.current_mood = self.fallback_mood
            self.mood_start_time = time.time()
            self._record_mood_change(self.fallback_mood, f"fallback_from_{error_type}", 1.0)
            fallback_actions["mood_reset"] = True
            
        elif error_type == "neuromodulator_failure":
            # Use default parameters if neuromodulator fails
            fallback_actions["using_default_parameters"] = True
            
            # Create default parameters
            default_params = {
                "k": 10, 
                "threshold": 0.85, 
                "decay": 0.2, 
                "phase_step": 0.1, 
                "base_frequency": 1.0
            }
            
            # Return default parameters directly
            return {
                "status": "degraded",
                "actions": fallback_actions,
                "fallback_parameters": default_params
            }
            
        elif error_type == "transition_matrix_corruption":
            # Rebuild transition matrix with defaults
            self.transition_probabilities = {
                mood: {mood: 0.7, self.fallback_mood: 0.3} 
                for mood in self.neuromod.mood_configs.keys()
            }
            
        elif error_type == "history_corruption":
            # Clear history but preserve current mood
            self.mood_history = []
            self._record_mood_change(self.current_mood, "history_reset", 1.0)
            fallback_actions["history_preserved"] = False
            
        # If passive signal listening is needed
        if error_type in ["catastrophic_failure", "system_overload"]:
            # Shift to passive mode - only listen for strong signals
            fallback_actions["passive_mode"] = True
            
            # In passive mode, we only respond to high-confidence signals
            self.logger.warning("Entering passive signal listening mode")
            
            # Reset to neutral mood as a safe state
            old_mood = self.current_mood
            self.current_mood = self.fallback_mood
            self.mood_start_time = time.time()
            self._record_mood_change(self.fallback_mood, f"fallback_passive_mode", 1.0)
            fallback_actions["mood_reset"] = True
            
        return {
            "status": "degraded",
            "actions": fallback_actions,
            "current_mood": self.current_mood
        }
        
    def resonance_chain_validator(self, mood_transition=None):
        """
        Verifies mood transition integrity to prevent resonance disruption.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            mood_transition (dict): Proposed mood transition to validate
            
        Returns:
            dict: Validation result with status and metrics
        """
        with self.validation_lock:
            # If no specific transition to validate, check current state
            if mood_transition is None:
                # Verify current mood is valid
                if self.current_mood not in self.neuromod.mood_configs:
                    return {
                        "status": "invalid",
                        "message": f"Current mood '{self.current_mood}' is invalid",
                        "action_required": True
                    }
                    
                # Verify mood history integrity
                if len(self.mood_history) > 0:
                    last_mood = self.mood_history[-1]["mood"]
                    if last_mood != self.current_mood:
                        return {
                            "status": "chain_broken",
                            "message": f"Mood history inconsistency: last recorded {last_mood}, current {self.current_mood}",
                            "action_required": True
                        }
                        
                return {
                    "status": "valid",
                    "message": "Current mood state and history are consistent",
                    "action_required": False
                }
                
            # Validate specific mood transition
            source_mood = mood_transition.get("source_mood", self.current_mood)
            target_mood = mood_transition.get("target_mood")
            confidence = mood_transition.get("confidence", 0.5)
            reason = mood_transition.get("reason", "unspecified")
            
            # Verify moods exist
            if source_mood not in self.neuromod.mood_configs:
                return {
                    "status": "invalid_source",
                    "message": f"Source mood '{source_mood}' is invalid",
                    "action_required": False
                }
                
            if target_mood not in self.neuromod.mood_configs:
                return {
                    "status": "invalid_target",
                    "message": f"Target mood '{target_mood}' is invalid",
                    "action_required": False
                }
                
            # Check for rapid oscillation
            if len(self.mood_history) >= 4:
                recent_moods = [entry["mood"] for entry in self.mood_history[-4:]]
                
                # Check if we're oscillating between two moods
                if target_mood in recent_moods:
                    # Count occurrences
                    target_count = recent_moods.count(target_mood)
                    
                    # If target appears multiple times in recent history
                    if target_count >= 2:
                        # Check for alternating pattern
                        alternating = True
                        for i in range(1, len(recent_moods)):
                            if recent_moods[i] == recent_moods[i-1]:
                                alternating = False
                                break
                                
                        if alternating and source_mood != target_mood:
                            return {
                                "status": "oscillation_risk",
                                "message": f"Detected potential oscillation between {source_mood} and {target_mood}",
                                "action_required": True,
                                "confidence_modifier": 0.5  # Reduce confidence to dampen oscillation
                            }
                            
            # Check for mood whiplash (dramatic mood shifts)
            if source_mood != target_mood:
                source_params = self.neuromod.adjust_resonance_params(source_mood)
                target_params = self.neuromod.adjust_resonance_params(target_mood)
                
                # Calculate parameter distance
                freq_diff = abs(source_params["base_frequency"] - target_params["base_frequency"])
                threshold_diff = abs(source_params["threshold"] - target_params["threshold"])
                
                # If large parameter jumps, flag as potential resonance disruptor
                if freq_diff > 1.0 or threshold_diff > 0.2:
                    # Only allow high-confidence transitions for large jumps
                    if confidence < 0.8:
                        return {
                            "status": "resonance_risk",
                            "message": f"Large mood shift from {source_mood} to {target_mood} requires higher confidence",
                            "action_required": True,
                            "minimum_confidence": 0.8
                        }
                        
            # All checks passed
            return {
                "status": "valid",
                "message": f"Transition from {source_mood} to {target_mood} is valid",
                "action_required": False
            }
            
    def _load_mood_to_color(self, mood_to_color_file):
        """Load mood-to-color mapping from JSON file."""
        try:
            with open(mood_to_color_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load mood colors from {mood_to_color_file}: {e}")
            # Fallback to basic colors
            return {
                "neutral": [1.0, 1.0, 1.0],
                "excited": [1.0, 0.6, 0.2],
                "focused": [0.2, 0.4, 0.8],
                "cautious": [0.8, 0.8, 0.2],
                "curious": [0.4, 0.8, 1.0]
            }
            
    def _initialize_transition_matrix(self):
        """Initialize mood transition probability matrix."""
        # Default transition probabilities
        transitions = {
            "neutral": {
                "neutral": 0.7,
                "curious": 0.1,
                "focused": 0.1,
                "excited": 0.05,
                "cautious": 0.05
            },
            "curious": {
                "curious": 0.6,
                "excited": 0.2,
                "neutral": 0.1,
                "focused": 0.05,
                "imaginative": 0.05
            },
            "focused": {
                "focused": 0.7,
                "neutral": 0.1,
                "alert": 0.1,
                "reflective": 0.05,
                "cautious": 0.05
            },
            "excited": {
                "excited": 0.6,
                "curious": 0.15,
                "impulsive": 0.1,
                "neutral": 0.1,
                "playful": 0.05
            },
            "cautious": {
                "cautious": 0.65,
                "alert": 0.15,
                "neutral": 0.1,
                "anxious": 0.05,
                "focused": 0.05
            },
            "alert": {
                "alert": 0.6,
                "cautious": 0.2,
                "focused": 0.1,
                "neutral": 0.05,
                "paranoid": 0.05
            },
            "reflective": {
                "reflective": 0.7,
                "neutral": 0.1,
                "focused": 0.1,
                "calm": 0.05,
                "dreamy": 0.05
            },
            "imaginative": {
                "imaginative": 0.6,
                "curious": 0.15,
                "dreamy": 0.1,
                "playful": 0.1,
                "neutral": 0.05
            },
            "impulsive": {
                "impulsive": 0.55,
                "excited": 0.2,
                "playful": 0.1,
                "aggressive": 0.1,
                "neutral": 0.05
            },
            "anxious": {
                "anxious": 0.6,
                "cautious": 0.15,
                "alert": 0.1,
                "paranoid": 0.1,
                "neutral": 0.05
            },
            "paranoid": {
                "paranoid": 0.5,
                "anxious": 0.2,
                "alert": 0.15,
                "cautious": 0.1,
                "neutral": 0.05
            },
            "dreamy": {
                "dreamy": 0.65,
                "imaginative": 0.15,
                "reflective": 0.1,
                "neutral": 0.05,
                "fatigued": 0.05
            },
            "playful": {
                "playful": 0.6,
                "excited": 0.15,
                "curious": 0.1,
                "impulsive": 0.1,
                "neutral": 0.05
            },
            "aggressive": {
                "aggressive": 0.55,
                "impulsive": 0.2,
                "alert": 0.1,
                "neutral": 0.1,
                "paranoid": 0.05
            },
            "calm": {
                "calm": 0.7,
                "neutral": 0.15,
                "reflective": 0.1,
                "dreamy": 0.05
            },
            "fatigued": {
                "fatigued": 0.6,
                "neutral": 0.2,
                "dreamy": 0.1,
                "calm": 0.1
            }
        }
        
        # Ensure all moods have transition probabilities
        for mood in self.neuromod.mood_configs.keys():
            if mood not in transitions:
                transitions[mood] = {"neutral": 0.3, mood: 0.7}
                
        return transitions
        
    def _scale_transition_probabilities(self, scale_factor):
        """Scale transition probabilities by a factor."""
        for source_mood in self.transition_probabilities:
            # Get self-transition probability
            self_prob = self.transition_probabilities[source_mood].get(source_mood, 0.7)
            
            # Adjust self-transition probability
            new_self_prob = min(1.0, max(0.1, self_prob * scale_factor))
            
            # Calculate scaling for other transitions
            other_total = 1.0 - self_prob
            new_other_total = 1.0 - new_self_prob
            
            if other_total > 0:
                # Scale other probabilities proportionally
                for target_mood in self.transition_probabilities[source_mood]:
                    if target_mood != source_mood:
                        old_prob = self.transition_probabilities[source_mood][target_mood]
                        ratio = old_prob / other_total
                        self.transition_probabilities[source_mood][target_mood] = ratio * new_other_total
                        
            # Update self-transition probability
            self.transition_probabilities[source_mood][source_mood] = new_self_prob
        
    def get_current_mood(self):
        """
        Get the current system mood state.
        
        Returns:
            dict: Current mood information
        """
        # Sync with temporal framework periodically
        if time.time() - self.last_sync_time > self.sync_interval:
            self.sync_clock()
            
        # Self-regulate periodically
        if time.time() - self.health_metrics["last_health_check"] > 300:
            self.self_regulate()
            
        duration = time.time() - self.mood_start_time
        color = self.mood_to_color.get(self.current_mood, [1.0, 1.0, 1.0])
        
        try:
            params = self.neuromod.adjust_resonance_params(self.current_mood)
        except Exception as e:
            self.logger.error(f"Failed to get resonance parameters: {e}")
            # Use graceful fallback
            fallback_result = self.graceful_fallback("neuromodulator_failure", {"error": str(e)})
            params = fallback_result.get("fallback_parameters", {
                "k": 10, "threshold": 0.85, "decay": 0.2, "phase_step": 0.1, "base_frequency": 1.0
            })
        
        return {
            "mood": self.current_mood,
            "duration": duration,
            "start_time": self.mood_start_time,
            "color": color,
            "params": params,
            "harmonic_signature": self.harmonic_signature()
        }
        
    def set_mood(self, mood, reason="manual", confidence=1.0):
        """
        Set the system mood state.
        
        Args:
            mood (str): Target mood state
            reason (str): Reason for mood change
            confidence (float): Confidence level for this mood (0-1)
            
        Returns:
            bool: Success status
        """
        # Validate operation through interface contract
        contract_result = self.interface_contract("set_mood", {"mood": mood, "reason": reason})
        if contract_result["status"] != "valid":
            self.logger.warning(f"Invalid mood operation: {contract_result['message']}")
            return False
            
        # Validate mood exists
        if mood not in self.neuromod.mood_configs:
            self.logger.warning(f"Invalid mood state: {mood}")
            # Use graceful fallback
            self.graceful_fallback("invalid_mood", {"requested_mood": mood})
            return False
            
        # Validate mood transition through resonance chain validator
        transition = {
            "source_mood": self.current_mood,
            "target_mood": mood,
            "confidence": confidence,
            "reason": reason
        }
        
        validation_result = self.resonance_chain_validator(transition)
        if validation_result["status"] != "valid" and validation_result.get("action_required", False):
            self.logger.warning(f"Mood transition validation failed: {validation_result['message']}")
            
            # If confidence modifier provided, adjust confidence
            if "confidence_modifier" in validation_result:
                confidence *= validation_result["confidence_modifier"]
                
            # If minimum confidence required, check if we meet it
            if "minimum_confidence" in validation_result and confidence < validation_result["minimum_confidence"]:
                self.logger.warning(f"Confidence too low for transition: {confidence} < {validation_result['minimum_confidence']}")
                return False
                
        # Normalize input signal through cognitive energy flow
        input_signal = {
            "type": "mood_change",
            "strength": confidence,
            "mood": mood
        }
        
        # Source credibility based on reason
        source_credibility = 1.0
        if reason == "manual":
            source_credibility = 1.0  # Manual changes are fully trusted
        elif reason.startswith("self_regulation"):
            source_credibility = 0.8  # Self-regulation is mostly trusted
        elif reason.startswith("fallback"):
            source_credibility = 0.9  # Fallbacks are highly trusted
        elif reason.startswith("probabilistic"):
            source_credibility = 0.6  # Probabilistic transitions are less trusted
            
        normalized_signal = self.cognitive_energy_flow(input_signal, source_credibility)
        
        # Only proceed if signal is strong enough
        if normalized_signal["strength"] < 0.3:
            self.logger.info(f"Mood change signal too weak: {normalized_signal['strength']:.2f}")
            return False
            
        # Record the mood change
        old_mood = self.current_mood
        self.current_mood = mood
        self.mood_start_time = time.time()
        
        self._record_mood_change(mood, reason, confidence)
        self.health_metrics["mood_transitions"] += 1
        
        self.logger.info(f"Mood changed from {old_mood} to {mood} (reason: {reason}, confidence: {confidence:.2f})")
        return True
        
    def _record_mood_change(self, mood, reason, confidence):
        """Record mood change in history."""
        self.mood_history.append({
            "mood": mood,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "reason": reason,
            "confidence": confidence
        })
        
        # Limit history size
        if len(self.mood_history) > 100:
            self.mood_history = self.mood_history[-100:]
            
    def suggest_mood_transition(self, input_data=None):
        """
        Suggest a mood transition based on current state and optional input.
        
        Args:
            input_data (dict, optional): External data influencing mood
            
        Returns:
            dict: Suggested mood transition
        """
        # Validate current state
        validation_result = self.resonance_chain_validator()
        if validation_result["status"] != "valid" and validation_result.get("action_required", False):
            self.logger.warning(f"Current mood state invalid: {validation_result['message']}")
            # Return suggestion to move to neutral mood
            return {
                "current_mood": self.current_mood,
                "suggested_mood": "neutral",
                "confidence": 0.9,
                "reason": "state_correction"
            }
            
        current_mood = self.current_mood
        
        # Get transition probabilities for current mood
        if current_mood in self.transition_probabilities:
            transitions = self.transition_probabilities[current_mood]
        else:
            # Fallback to neutral transitions
            transitions = self.transition_probabilities["neutral"]
            
        # Apply any input data influences (stub for future enhancement)
        if input_data:
            # Example: Adjust probabilities based on input sentiment
            pass
            
        # Select next mood based on probabilities
        moods = list(transitions.keys())
        probabilities = list(transitions.values())
        
        # Normalize probabilities
        total = sum(probabilities)
        if total > 0:
            probabilities = [p/total for p in probabilities]
            
        next_mood = random.choices(moods, weights=probabilities, k=1)[0]
        confidence = transitions.get(next_mood, 0.5)
        
        return {
            "current_mood": current_mood,
            "suggested_mood": next_mood,
            "confidence": confidence,
            "reason": "probabilistic_transition"
        }
        
    def update_mood_based_on_input(self, input_type, input_data):
        """
        Update mood based on external input.
        
        Args:
            input_type (str): Type of input ('text', 'image', 'resonance', etc.)
            input_data (dict): Input data with relevant features
            
        Returns:
            dict: Mood update result
        """
        # Validate operation through interface contract
        contract_result = self.interface_contract("update_mood", {
            "input_type": input_type, 
            "input_data": input_data
        })
        
        if contract_result["status"] != "valid":
            self.logger.warning(f"Invalid update operation: {contract_result['message']}")
            return {
                "previous_mood": self.current_mood,
                "new_mood": self.current_mood,
                "changed": False,
                "confidence": 1.0,
                "reason": "invalid_operation"
            }
            
        # Default: no change
        result = {
            "previous_mood": self.current_mood,
            "new_mood": self.current_mood,
            "changed": False,
            "confidence": 1.0,
            "reason": "no_change"
        }
        
        # Process different input types
        if input_type == "text":
            # Example: Text sentiment analysis
            if "sentiment" in input_data:
                sentiment = input_data["sentiment"]
                if sentiment > 0.7:
                    self.set_mood("excited", "high_positive_sentiment", sentiment)
                    result = {"previous_mood": result["previous_mood"], "new_mood": "excited", 
                             "changed": True, "confidence": sentiment, "reason": "high_positive_sentiment"}
                elif sentiment > 0.3:
                    self.set_mood("curious", "positive_sentiment", sentiment)
                    result = {"previous_mood": result["previous_mood"], "new_mood": "curious", 
                             "changed": True, "confidence": sentiment, "reason": "positive_sentiment"}
                elif sentiment < -0.7:
                    self.set_mood("cautious", "high_negative_sentiment", abs(sentiment))
                    result = {"previous_mood": result["previous_mood"], "new_mood": "cautious", 
                             "changed": True, "confidence": abs(sentiment), "reason": "high_negative_sentiment"}
                elif sentiment < -0.3:
                    self.set_mood("alert", "negative_sentiment", abs(sentiment))
                    result = {"previous_mood": result["previous_mood"], "new_mood": "alert", 
                             "changed": True, "confidence": abs(sentiment), "reason": "negative_sentiment"}
                    
        elif input_type == "resonance":
            # Example: Resonance pattern analysis
            if "pattern" in input_data:
                pattern = input_data["pattern"]
                if pattern == "high_novelty":
                    self.set_mood("curious", "novel_resonance_pattern", 0.8)
                    result = {"previous_mood": result["previous_mood"], "new_mood": "curious", 
                             "changed": True, "confidence": 0.8, "reason": "novel_resonance_pattern"}
                elif pattern == "high_focus":
                    self.set_mood("focused", "focused_resonance_pattern", 0.9)
                    result = {"previous_mood": result["previous_mood"], "new_mood": "focused", 
                             "changed": True, "confidence": 0.9, "reason": "focused_resonance_pattern"}
                    
        # Apply probabilistic transition if no change and enough time has passed
        if not result["changed"] and (time.time() - self.mood_start_time) > 300:  # 5 minutes
            # Sync with temporal framework before transition
            self.sync_clock()
            
            suggestion = self.suggest_mood_transition()
            if suggestion["suggested_mood"] != self.current_mood:
                success = self.set_mood(
                    suggestion["suggested_mood"],
                    suggestion["reason"],
                    suggestion["confidence"]
                )
                
                if success:
                    result = {
                        "previous_mood": result["previous_mood"],
                        "new_mood": suggestion["suggested_mood"],
                        "changed": True,
                        "confidence": suggestion["confidence"],
                        "reason": suggestion["reason"]
                    }
                
        return result
        
    def get_mood_history(self, limit=10):
        """
        Get recent mood history.
        
        Args:
            limit (int): Maximum number of history entries to return
            
        Returns:
            list: Recent mood history
        """
        # Validate operation through interface contract
        contract_result = self.interface_contract("get_history", {"limit": limit})
        if contract_result["status"] != "valid":
            self.logger.warning(f"Invalid history operation: {contract_result['message']}")
            return []
            
        return self.mood_history[-limit:]
        
    def export_mood_parameters(self):
        """
        Export current mood parameters for visualization and debugging.
        
        Returns:
            dict: Current mood parameters
        """
        # Validate operation through interface contract
        contract_result = self.interface_contract("export_parameters", {})
        if contract_result["status"] != "valid":
            self.logger.warning(f"Invalid export operation: {contract_result['message']}")
            return {}
            
        mood_info = self.get_current_mood()
        params = mood_info["params"]
        
        return {
            "mood": mood_info["mood"],
            "color": mood_info["color"],
            "duration": mood_info["duration"],
            "k": params["k"],
            "threshold": params["threshold"],
            "decay": params["decay"],
            "phase_step": params["phase_step"],
            "base_frequency": params["base_frequency"],
            "harmonic_signature": mood_info["harmonic_signature"]
        }
