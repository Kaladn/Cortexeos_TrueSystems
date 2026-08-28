"""
Resonance Reinforcer module for CortexOS Temporal Cognition v2.1.
Strengthens neural resonance patterns based on activation history and feedback.
Fully compliant with Agharmonic Law for resonance stability and coherence.
"""

import numpy as np
import time
import logging
import threading
from datetime import datetime
import cortex_core_hooks as hooks
from global_sync_manager import GlobalSyncManager

class ResonanceReinforcer:
    """
    Reinforces neural resonance patterns based on activation history and feedback.
    Implements adaptive reinforcement with temporal decay and feedback integration.
    Fully compliant with all seven Agharmonic Law tenets.
    """
    def __init__(self, base_reinforcement_rate=0.05, decay_rate=0.01, feedback_weight=0.3):
        self.base_reinforcement_rate = base_reinforcement_rate
        self.decay_rate = decay_rate
        self.feedback_weight = feedback_weight
        self.activation_history = {}
        self.reinforcement_history = {}
        self.feedback_log = []
        self.last_sync = datetime.utcnow()
        self.last_regulation_time = time.time()
        self.regulation_interval = 300  # 5 minutes
        self.lock = threading.Lock()
        self.fallback_mode = False
        self.fallback_level = 0
        self.resonance_chain_health = 1.0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Connect to global sync
        try:
            self.sync_manager = GlobalSyncManager.get_instance()
        except Exception as e:
            self.logger.warning(f"Could not connect to GlobalSyncManager: {e}")
            self.sync_manager = None
    
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for resonance reinforcement.
        Required by Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "resonance_reinforcer",
            "input_frequency_range": [0.6, 1.3],
            "output_phase_alignment": 0.1,
            "resonance_threshold": 0.8,
            "harmonic_modes": ["reinforcement", "feedback", "adaptive"],
            "compatible_modules": ["neuroengine", "swarm_resonance", "knowledge_reinforcer"]
        }
    
    def interface_contract(self, resonance_id, strength=None, context=None, feedback_value=None, source=None):
        """
        Validates input parameters against interface contract.
        Required by Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            resonance_id (str): Resonance pattern identifier
            strength (float, optional): Activation or reinforcement strength
            context (dict, optional): Additional context information
            feedback_value (float, optional): Feedback value for reinforcement
            source (str, optional): Source of feedback
            
        Returns:
            bool: True if contract is satisfied, raises exception otherwise
        """
        # Validate resonance_id
        if not isinstance(resonance_id, str) or not resonance_id:
            raise ValueError("resonance_id must be a non-empty string")
        
        # Validate strength if provided
        if strength is not None:
            if not isinstance(strength, (int, float)) or not (0 <= strength <= 1):
                raise ValueError("strength must be a float between 0 and 1")
        
        # Validate context if provided
        if context is not None and not isinstance(context, dict):
            raise ValueError("context must be a dictionary")
        
        # Validate feedback_value if provided
        if feedback_value is not None:
            if not isinstance(feedback_value, (int, float)) or not (-1 <= feedback_value <= 1):
                raise ValueError("feedback_value must be a float between -1 and 1")
        
        # Validate source if provided
        if source is not None and not isinstance(source, str):
            raise ValueError("source must be a string")
        
        return True
    
    def cognitive_energy_flow(self, reinforcement_strength, activation_count):
        """
        Normalizes signal amplitude and information flow for reinforcement.
        Required by Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            reinforcement_strength (float): Raw reinforcement strength
            activation_count (int): Number of activations being considered
            
        Returns:
            float: Normalized reinforcement strength
        """
        if activation_count == 0:
            return 0.0
        
        # Apply sigmoid normalization to prevent extreme values
        normalized = 1.0 / (1.0 + np.exp(-5 * (reinforcement_strength - 0.5)))
        
        # Scale based on activation count (more activations = more confidence)
        confidence_factor = min(1.0, activation_count / 10.0)  # Saturates at 10 activations
        
        # Apply energy conservation principle
        # As activation count increases, we can allow stronger reinforcement
        # but still maintain an upper bound
        conserved_strength = normalized * confidence_factor
        
        # Ensure we don't exceed input energy
        if conserved_strength > reinforcement_strength and reinforcement_strength > 0:
            return reinforcement_strength
        
        return conserved_strength
    
    def sync_clock(self):
        """
        Connects to the master temporal framework.
        Required by Agharmonic Law Tenet 4: Temporal Synchronization.
        
        Returns:
            bool: True if synchronized, False otherwise
        """
        if self.sync_manager:
            try:
                current_time = self.sync_manager.get_global_time()
                time_delta = (current_time - self.last_sync).total_seconds()
                self.last_sync = current_time
                
                # Check if we're in sync with global clock
                if time_delta > 5.0:  # More than 5 seconds drift
                    self.logger.warning(f"Resonance reinforcer clock drift detected: {time_delta}s")
                    return False
                
                return True
            except Exception as e:
                self.logger.error(f"Error synchronizing with global clock: {e}")
                return False
        else:
            # Fallback to local time if no sync manager
            self.last_sync = datetime.utcnow()
            return True
    
    def self_regulate(self):
        """
        Implements feedback loops for stability.
        Required by Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            bool: True if regulation successful, False otherwise
        """
        current_time = time.time()
        if current_time - self.last_regulation_time < self.regulation_interval:
            return True  # Not time to regulate yet
        
        self.last_regulation_time = current_time
        
        with self.lock:
            # Prune old data
            self._prune_all_histories()
            
            # Check for anomalies in reinforcement patterns
            anomalies = self._detect_reinforcement_anomalies()
            
            if anomalies:
                self.logger.warning(f"Detected {len(anomalies)} reinforcement anomalies")
                
                # If serious anomalies, trigger fallback
                if any(a["severity"] > 0.7 for a in anomalies):
                    if not self.fallback_mode:
                        self.graceful_fallback(error_type="reinforcement_anomaly")
                        return False
            elif self.fallback_mode and self.fallback_level < 3:
                # Recover from fallback if no anomalies
                self.logger.info("Reinforcement stability recovered")
                self.fallback_mode = False
                self.fallback_level = 0
        
        return True
    
    def _detect_reinforcement_anomalies(self):
        """Detect anomalies in reinforcement patterns."""
        anomalies = []
        
        # Check for rapid oscillations in reinforcement
        for resonance_id, history in self.reinforcement_history.items():
            if len(history) < 5:
                continue
            
            # Check last 5 reinforcements
            recent = history[-5:]
            strengths = [r["strength"] for r in recent]
            
            # Calculate variance
            variance = np.var(strengths)
            
            # Check for oscillation pattern
            oscillating = False
            for i in range(1, len(strengths) - 1):
                if (strengths[i] > strengths[i-1] and strengths[i] > strengths[i+1]) or \
                   (strengths[i] < strengths[i-1] and strengths[i] < strengths[i+1]):
                    oscillating = True
            
            # High variance and oscillation pattern indicates anomaly
            if variance > 0.1 and oscillating:
                anomalies.append({
                    "resonance_id": resonance_id,
                    "type": "oscillation",
                    "severity": min(1.0, variance * 5),  # Scale severity
                    "details": {
                        "variance": variance,
                        "strengths": strengths
                    }
                })
        
        return anomalies
    
    def _prune_all_histories(self):
        """Prune all histories to prevent memory bloat."""
        # Prune activation history
        cutoff_time = time.time() - (24 * 3600)  # 24 hours
        for resonance_id in list(self.activation_history.keys()):
            self.activation_history[resonance_id] = [
                a for a in self.activation_history[resonance_id] 
                if a["timestamp"] >= cutoff_time
            ]
            
            # Remove empty entries
            if not self.activation_history[resonance_id]:
                del self.activation_history[resonance_id]
        
        # Prune reinforcement history
        for resonance_id in list(self.reinforcement_history.keys()):
            self.reinforcement_history[resonance_id] = [
                r for r in self.reinforcement_history[resonance_id] 
                if r["timestamp"] >= cutoff_time
            ]
            
            # Remove empty entries
            if not self.reinforcement_history[resonance_id]:
                del self.reinforcement_history[resonance_id]
        
        # Prune feedback log
        self.feedback_log = [
            f for f in self.feedback_log 
            if f["timestamp"] >= cutoff_time
        ]
        
        # Limit overall size
        max_entries = 1000
        if sum(len(history) for history in self.activation_history.values()) > max_entries:
            self.logger.info(f"Pruning activation history to prevent memory bloat")
            for resonance_id in self.activation_history:
                if len(self.activation_history[resonance_id]) > 100:
                    self.activation_history[resonance_id] = self.activation_history[resonance_id][-100:]
        
        if sum(len(history) for history in self.reinforcement_history.values()) > max_entries:
            self.logger.info(f"Pruning reinforcement history to prevent memory bloat")
            for resonance_id in self.reinforcement_history:
                if len(self.reinforcement_history[resonance_id]) > 100:
                    self.reinforcement_history[resonance_id] = self.reinforcement_history[resonance_id][-100:]
        
        if len(self.feedback_log) > max_entries:
            self.logger.info(f"Pruning feedback log to prevent memory bloat")
            self.feedback_log = self.feedback_log[-max_entries:]
    
    def graceful_fallback(self, error_type=None):
        """
        Provides mechanisms for partial operation during failures.
        Required by Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error_type (str, optional): Type of error triggering fallback
            
        Returns:
            dict: Fallback status and actions taken
        """
        with self.lock:
            self.fallback_mode = True
            self.fallback_level += 1
            
            # Implement multi-level fallback strategy
            if self.fallback_level == 1:
                # Level 1: Reduce reinforcement complexity
                self.logger.info("Fallback Level 1: Reducing reinforcement complexity")
                action = "reduce_reinforcement_complexity"
                # Increase decay rate to forget problematic patterns faster
                self.decay_rate *= 1.5
                # Reduce feedback weight to minimize oscillations
                self.feedback_weight *= 0.7
                
            elif self.fallback_level == 2:
                # Level 2: Simplify reinforcement calculations
                self.logger.info("Fallback Level 2: Simplifying reinforcement calculations")
                action = "simplify_calculations"
                # Use simpler algorithms, disable advanced features
                self.base_reinforcement_rate *= 0.5  # Reduce reinforcement strength
                
            elif self.fallback_level >= 3:
                # Level 3: Minimal operation mode
                self.logger.warning("Fallback Level 3: Minimal operation mode")
                action = "minimal_operation"
                # Only essential functions, no advanced features
                # Clear histories to start fresh
                self.activation_history = {}
                self.reinforcement_history = {}
                self.feedback_log = []
                
            else:
                action = "unknown_fallback"
            
            fallback_status = {
                "module": "resonance_reinforcer",
                "fallback_level": self.fallback_level,
                "action": action,
                "error_type": error_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Log fallback event
            self.logger.warning(f"Resonance reinforcer fallback activated: {fallback_status}")
            
            return fallback_status
    
    def resonance_chain_validator(self, resonance_id, reinforcement_result):
        """
        Verifies resonance integrity across the chain.
        Required by Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            resonance_id (str): Resonance pattern identifier
            reinforcement_result (dict): Result of reinforcement operation
            
        Returns:
            dict: Validation results with integrity metrics
        """
        if not reinforcement_result or not reinforcement_result.get("success", False):
            return {"valid": False, "integrity": 0.0, "issues": ["Invalid reinforcement result"]}
        
        issues = []
        integrity_scores = []
        
        # Check activation-reinforcement coherence
        activations = self.activation_history.get(resonance_id, [])
        reinforcements = self.reinforcement_history.get(resonance_id, [])
        
        if not activations:
            issues.append("No activation history for reinforcement")
            activation_integrity = 0.0
        else:
            # Check if reinforcement strength is proportional to activation patterns
            avg_activation = sum(a["strength"] for a in activations) / len(activations)
            reinforcement_strength = reinforcement_result["strength"]
            
            # Calculate ratio (should be close to base_reinforcement_rate)
            if avg_activation > 0:
                ratio = reinforcement_strength / avg_activation
                expected_ratio = self.base_reinforcement_rate
                ratio_diff = abs(ratio - expected_ratio) / expected_ratio
                
                if ratio_diff > 0.5:  # More than 50% deviation
                    issues.append(f"Reinforcement-activation ratio deviation: {ratio_diff:.2f}")
                
                activation_integrity = max(0, 1.0 - ratio_diff)
            else:
                activation_integrity = 0.0
                issues.append("Zero average activation strength")
        
        integrity_scores.append(activation_integrity)
        
        # Check temporal coherence
        if len(reinforcements) > 1:
            timestamps = [r["timestamp"] for r in reinforcements]
            intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                interval_variance = sum((i - avg_interval)**2 for i in intervals) / len(intervals)
                
                # Normalize variance to a score (lower variance = higher integrity)
                temporal_integrity = max(0, 1.0 - min(1.0, interval_variance / (avg_interval**2)))
                
                if temporal_integrity < 0.7:
                    issues.append(f"High temporal variance in reinforcement: {interval_variance:.2f}")
                
                integrity_scores.append(temporal_integrity)
        
        # Check feedback integration
        feedback = [f for f in self.feedback_log if f["resonance_id"] == resonance_id]
        
        if feedback:
            # Check if reinforcement aligns with feedback direction
            recent_feedback = sorted(feedback, key=lambda f: f["timestamp"], reverse=True)[:5]
            avg_feedback = sum(f["value"] for f in recent_feedback) / len(recent_feedback)
            
            # Reinforcement should be stronger for positive feedback, weaker for negative
            if (avg_feedback > 0.3 and reinforcement_result["strength"] < 0.3) or \
               (avg_feedback < -0.3 and reinforcement_result["strength"] > 0.7):
                issues.append(f"Reinforcement-feedback misalignment: feedback={avg_feedback:.2f}, reinforcement={reinforcement_result['strength']:.2f}")
                feedback_integrity = 0.5  # Partial integrity
            else:
                feedback_integrity = 1.0
                
            integrity_scores.append(feedback_integrity)
        
        # Calculate overall integrity
        overall_integrity = sum(integrity_scores) / len(integrity_scores) if integrity_scores else 0.0
        
        # Update resonance chain health
        self.resonance_chain_health = overall_integrity
        
        return {
            "valid": overall_integrity >= 0.7,
            "integrity": overall_integrity,
            "issues": issues,
            "chain_health": self.resonance_chain_health
        }
        
    def record_activation(self, resonance_id, strength, context=None):
        """
        Record resonance activation for reinforcement processing with Agharmonic compliance.
        
        Args:
            resonance_id (str): Unique identifier for the resonance pattern
            strength (float): Activation strength (0-1)
            context (dict, optional): Additional context information
            
        Returns:
            dict: Activation record
        """
        try:
            # Validate inputs against interface contract
            self.interface_contract(resonance_id, strength, context)
            
            # Synchronize with global clock
            self.sync_clock()
            
            # Apply fallback mode if active
            if self.fallback_mode and self.fallback_level >= 3:
                # Minimal operation mode
                self.logger.info("Operating in minimal mode due to fallback level 3")
                return {"success": False, "reason": "minimal_operation_mode"}
            
            timestamp = time.time()
            
            with self.lock:
                if resonance_id not in self.activation_history:
                    self.activation_history[resonance_id] = []
                    
                # Create activation record
                activation = {
                    "strength": strength,
                    "timestamp": timestamp,
                    "context": context or {}
                }
                
                # Add to history
                self.activation_history[resonance_id].append(activation)
                
                # Prune old activations
                self._prune_activation_history(resonance_id)
            
            # Log through core hooks
            hooks.log_chain(resonance_id, strength)
            
            # Self-regulate
            self.self_regulate()
            
            return activation
            
        except Exception as e:
            self.logger.error(f"Error recording activation: {e}")
            # Activate graceful fallback on error
            fallback_status = self.graceful_fallback(error_type=str(e))
            # Return minimal valid result
            return {"success": False, "reason": str(e), "fallback": fallback_status}
        
    def _prune_activation_history(self, resonance_id):
        """Remove activations older than 24 hours."""
        if resonance_id in self.activation_history:
            cutoff_time = time.time() - (24 * 3600)  # 24 hours in seconds
            self.activation_history[resonance_id] = [
                a for a in self.activation_history[resonance_id] 
                if a["timestamp"] >= cutoff_time
            ]
            
    def reinforce(self, resonance_id, explicit_strength=None):
        """
        Reinforce a resonance pattern based on activation history with Agharmonic compliance.
        
        Args:
            resonance_id (str): Resonance pattern identifier
            explicit_strength (float, optional): Explicit reinforcement strength override
            
        Returns:
            dict: Reinforcement result
        """
        try:
            # Validate inputs against interface contract
            self.interface_contract(resonance_id, explicit_strength)
            
            # Synchronize with global clock
            self.sync_clock()
            
            # Apply fallback mode if active
            if self.fallback_mode:
                if self.fallback_level >= 3:
                    # Minimal operation mode
                    self.logger.info("Operating in minimal mode due to fallback level 3")
                    return {"success": False, "reason": "minimal_operation_mode"}
                elif self.fallback_level == 2:
                    # Simplify calculations in fallback level 2
                    self.logger.info("Using simplified calculations due to fallback level 2")
            
            with self.lock:
                if resonance_id not in self.activation_history:
                    self.logger.warning(f"No activation history for resonance ID: {resonance_id}")
                    return {"success": False, "reason": "no_activation_history"}
                    
                # Calculate reinforcement strength
                if explicit_strength is not None:
                    raw_strength = max(0.0, min(1.0, explicit_strength))
                else:
                    raw_strength = self._calculate_reinforcement_strength(resonance_id)
                
                # Apply cognitive energy flow normalization
                activation_count = len(self.activation_history.get(resonance_id, []))
                strength = self.cognitive_energy_flow(raw_strength, activation_count)
                    
                # Apply reinforcement
                timestamp = time.time()
                
                if resonance_id not in self.reinforcement_history:
                    self.reinforcement_history[resonance_id] = []
                    
                # Create reinforcement record
                reinforcement = {
                    "strength": strength,
                    "timestamp": timestamp,
                    "explicit": explicit_strength is not None
                }
                
                # Add to history
                self.reinforcement_history[resonance_id].append(reinforcement)
            
            # Apply through core hooks
            hooks.increment_voxel(resonance_id, strength)
            
            self.logger.info(f"Reinforced resonance {resonance_id} with strength {strength:.4f}")
            
            result = {
                "success": True,
                "resonance_id": resonance_id,
                "strength": strength,
                "timestamp": timestamp
            }
            
            # Validate resonance chain integrity
            validation = self.resonance_chain_validator(resonance_id, result)
            result["validation"] = validation
            
            # Self-regulate
            self.self_regulate()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in reinforcement: {e}")
            # Activate graceful fallback on error
            fallback_status = self.graceful_fallback(error_type=str(e))
            # Return minimal valid result
            return {"success": False, "reason": str(e), "fallback": fallback_status}
        
    def _calculate_reinforcement_strength(self, resonance_id):
        """Calculate reinforcement strength based on activation history and feedback."""
        activations = self.activation_history.get(resonance_id, [])
        
        if not activations:
            return 0.0
            
        # Calculate recency-weighted activation strength
        current_time = time.time()
        total_weighted_strength = 0.0
        total_weight = 0.0
        
        for activation in activations:
            # Calculate time-based weight (more recent = higher weight)
            time_diff = current_time - activation["timestamp"]
            time_weight = np.exp(-self.decay_rate * time_diff / 3600)  # Convert to hours
            
            # Apply weight to strength
            weighted_strength = activation["strength"] * time_weight
            
            total_weighted_strength += weighted_strength
            total_weight += time_weight
            
        # Calculate average weighted strength
        avg_strength = total_weighted_strength / max(1e-6, total_weight)
        
        # Apply feedback adjustment if available
        feedback_adjustment = self._calculate_feedback_adjustment(resonance_id)
        
        # Calculate final reinforcement strength
        reinforcement_strength = (
            self.base_reinforcement_rate * 
            avg_strength * 
            (1.0 + feedback_adjustment)
        )
        
        return max(0.0, min(1.0, reinforcement_strength))
        
    def _calculate_feedback_adjustment(self, resonance_id):
        """Calculate adjustment factor based on feedback history."""
        # Filter feedback for this resonance ID
        relevant_feedback = [
            f for f in self.feedback_log 
            if f["resonance_id"] == resonance_id and f["timestamp"] > time.time() - 86400  # Last 24 hours
        ]
        
        if not relevant_feedback:
            return 0.0
            
        # Calculate weighted average of feedback values
        total_weighted_value = 0.0
        total_weight = 0.0
        
        current_time = time.time()
        
        for feedback in relevant_feedback:
            # Calculate time-based weight (more recent = higher weight)
            time_diff = current_time - feedback["timestamp"]
            time_weight = np.exp(-self.decay_rate * time_diff / 3600)  # Convert to hours
            
            # Apply weight to value
            weighted_value = feedback["value"] * time_weight
            
            total_weighted_value += weighted_value
            total_weight += time_weight
            
        # Calculate average weighted value
        avg_value = total_weighted_value / max(1e-6, total_weight)
        
        # Scale by feedback weight
        return avg_value * self.feedback_weight
        
    def record_feedback(self, resonance_id, value, source="system"):
        """
        Record feedback for a resonance pattern with Agharmonic compliance.
        
        Args:
            resonance_id (str): Resonance pattern identifier
            value (float): Feedback value (-1 to 1, negative = inhibitory, positive = excitatory)
            source (str): Source of feedback
            
        Returns:
            dict: Feedback record
        """
        try:
            # Validate inputs against interface contract
            self.interface_contract(resonance_id, feedback_value=value, source=source)
            
            # Synchronize with global clock
            self.sync_clock()
            
            # Apply fallback mode if active
            if self.fallback_mode and self.fallback_level >= 3:
                # Minimal operation mode
                self.logger.info("Operating in minimal mode due to fallback level 3")
                return {"success": False, "reason": "minimal_operation_mode"}
            
            # Ensure value is in valid range
            value = max(-1.0, min(1.0, value))
            
            with self.lock:
                # Create feedback record
                feedback = {
                    "resonance_id": resonance_id,
                    "value": value,
                    "source": source,
                    "timestamp": time.time()
                }
                
                # Add to log
                self.feedback_log.append(feedback)
                
                # Limit log size
                if len(self.feedback_log) > 1000:
                    self.feedback_log = self.feedback_log[-1000:]
            
            self.logger.info(f"Recorded feedback for {resonance_id}: {value:.2f} from {source}")
            
            # Self-regulate
            self.self_regulate()
            
            return feedback
            
        except Exception as e:
            self.logger.error(f"Error recording feedback: {e}")
            # Activate graceful fallback on error
            fallback_status = self.graceful_fallback(error_type=str(e))
            # Return minimal valid result
            return {"success": False, "reason": str(e), "fallback": fallback_status}
        
    def get_reinforcement_history(self, resonance_id=None, limit=10):
        """
        Get reinforcement history for a resonance pattern or all patterns.
        
        Args:
            resonance_id (str, optional): Specific resonance ID to query
            limit (int): Maximum number of entries to return per resonance ID
            
        Returns:
            dict: Reinforcement history by resonance ID
        """
        with self.lock:
            if resonance_id:
                history = self.reinforcement_history.get(resonance_id, [])
                return {resonance_id: history[-limit:]}
            else:
                return {rid: history[-limit:] for rid, history in self.reinforcement_history.items()}
            
    def get_activation_history(self, resonance_id=None, limit=10):
        """
        Get activation history for a resonance pattern or all patterns.
        
        Args:
            resonance_id (str, optional): Specific resonance ID to query
            limit (int): Maximum number of entries to return per resonance ID
            
        Returns:
            dict: Activation history by resonance ID
        """
        with self.lock:
            if resonance_id:
                history = self.activation_history.get(resonance_id, [])
                return {resonance_id: history[-limit:]}
            else:
                return {rid: history[-limit:] for rid, history in self.activation_history.items()}
            
    def get_feedback_history(self, resonance_id=None, limit=10):
        """
        Get feedback history for a resonance pattern or all patterns.
        
        Args:
            resonance_id (str, optional): Specific resonance ID to query
            limit (int): Maximum number of entries to return
            
        Returns:
            list: Feedback history
        """
        with self.lock:
            if resonance_id:
                history = [f for f in self.feedback_log if f["resonance_id"] == resonance_id]
                return history[-limit:]
            else:
                return self.feedback_log[-limit:]
            
    def export_reinforcement_stats(self):
        """
        Export reinforcement statistics for analysis.
        
        Returns:
            dict: Reinforcement statistics
        """
        with self.lock:
            stats = {
                "total_resonance_patterns": len(self.activation_history),
                "total_reinforcements": sum(len(history) for history in self.reinforcement_history.values()),
                "total_activations": sum(len(history) for history in self.activation_history.values()),
                "total_feedback": len(self.feedback_log),
                "agharmonic_compliance": {
                    "resonance_chain_health": self.resonance_chain_health,
                    "fallback_mode": self.fallback_mode,
                    "fallback_level": self.fallback_level
                },
                "patterns": {}
            }
            
            # Calculate per-pattern statistics
            for resonance_id in self.activation_history.keys():
                activations = self.activation_history.get(resonance_id, [])
                reinforcements = self.reinforcement_history.get(resonance_id, [])
                feedback = [f for f in self.feedback_log if f["resonance_id"] == resonance_id]
                
                if activations:
                    stats["patterns"][resonance_id] = {
                        "activation_count": len(activations),
                        "reinforcement_count": len(reinforcements),
                        "feedback_count": len(feedback),
                        "avg_activation_strength": sum(a["strength"] for a in activations) / len(activations),
                        "avg_reinforcement_strength": sum(r["strength"] for r in reinforcements) / max(1, len(reinforcements)),
                        "avg_feedback_value": sum(f["value"] for f in feedback) / max(1, len(feedback))
                    }
            
            return stats
