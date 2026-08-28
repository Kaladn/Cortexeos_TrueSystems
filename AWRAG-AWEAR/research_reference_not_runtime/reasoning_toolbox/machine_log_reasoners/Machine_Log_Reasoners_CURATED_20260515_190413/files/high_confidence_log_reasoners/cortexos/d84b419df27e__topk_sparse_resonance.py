"""
Top-k Sparse Resonance module for CortexOS Temporal Cognition v2.1.
Prioritizes high-similarity voxel matches with mood-based modulation and phase harmonics.
Fully compliant with Agharmonic Law for resonance stability and coherence.
"""
import numpy as np
import time
import logging
import threading
from datetime import datetime
from cortex_core_hooks import increment_voxel, log_chain
from neuromodulation import Neuromodulator
from phase_harmonics import PhaseHarmonics
from global_sync_manager import GlobalSyncManager

class TopKSparseResonance:
    """
    Implements top-k sparse resonance with mood-modulated parameters and phase harmonics.
    Fully compliant with all seven Agharmonic Law tenets.
    """
    def __init__(self, default_k=5, default_threshold=0.7, default_decay=0.05):
        self.default_k = default_k
        self.default_threshold = default_threshold
        self.default_decay = default_decay
        self.neuromod = Neuromodulator()
        self.phase_harmonics = PhaseHarmonics()
        self.last_sync = datetime.utcnow()
        self.last_regulation_time = time.time()
        self.regulation_interval = 300  # 5 minutes
        self.lock = threading.Lock()
        self.fallback_mode = False
        self.fallback_level = 0
        self.resonance_chain_health = 1.0
        self.activation_history = {}
        self.resonance_log = {"activations": [], "harmonic_diffs": [], "time_steps": []}
        
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
        Establishes frequency compatibility parameters for sparse resonance.
        Required by Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "topk_sparse_resonance",
            "input_frequency_range": [0.6, 1.4],
            "output_phase_alignment": 0.05,
            "resonance_threshold": 0.8,
            "harmonic_modes": ["sparse", "topk", "phase_aligned"],
            "compatible_modules": ["neuroengine", "resonance_field", "chord_resonator"]
        }
    
    def interface_contract(self, harmonic_vector=None, voxel_field=None, mood=None, time_step=None, k=None, threshold=None):
        """
        Validates input parameters against interface contract.
        Required by Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            harmonic_vector (list, optional): Harmonic vector for resonance
            voxel_field (dict, optional): Voxel field for matching
            mood (str, optional): Mood state for neuromodulation
            time_step (int, optional): Temporal index for phase harmonics
            k (int, optional): Number of top matches to return
            threshold (float, optional): Similarity threshold
            
        Returns:
            bool: True if contract is satisfied, raises exception otherwise
        """
        # Validate harmonic_vector if provided
        if harmonic_vector is not None:
            if not isinstance(harmonic_vector, (list, tuple, np.ndarray)):
                raise ValueError("harmonic_vector must be a list, tuple, or numpy array")
            if len(harmonic_vector) < 4:  # At least [R, G, B, intensity]
                raise ValueError("harmonic_vector must have at least 4 elements")
        
        # Validate voxel_field if provided
        if voxel_field is not None:
            if not isinstance(voxel_field, dict):
                raise ValueError("voxel_field must be a dictionary")
            for voxel_id, (vector, ts) in voxel_field.items():
                if not isinstance(vector, (list, tuple, np.ndarray)):
                    raise ValueError(f"voxel vector for {voxel_id} must be a list, tuple, or numpy array")
                if not isinstance(ts, (int, float)):
                    raise ValueError(f"time_step for {voxel_id} must be a number")
        
        # Validate mood if provided
        if mood is not None and not isinstance(mood, str):
            raise ValueError("mood must be a string")
        
        # Validate time_step if provided
        if time_step is not None and not isinstance(time_step, (int, float)):
            raise ValueError("time_step must be a number")
        
        # Validate k if provided
        if k is not None:
            if not isinstance(k, int) or k <= 0:
                raise ValueError("k must be a positive integer")
        
        # Validate threshold if provided
        if threshold is not None:
            if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 1):
                raise ValueError("threshold must be a float between 0 and 1")
        
        return True
    
    def cognitive_energy_flow(self, similarity_scores, k, threshold):
        """
        Normalizes signal amplitude and information flow for sparse resonance.
        Required by Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            similarity_scores (list): List of (voxel_id, similarity) tuples
            k (int): Number of top matches to return
            threshold (float): Similarity threshold
            
        Returns:
            list: Normalized top-k matches with balanced energy distribution
        """
        if not similarity_scores:
            return []
        
        # Sort by similarity (descending)
        sorted_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
        
        # Apply threshold filter
        filtered_scores = [s for s in sorted_scores if s[1] >= threshold]
        
        # Limit to top-k
        top_k = filtered_scores[:k]
        
        if not top_k:
            return []
        
        # Calculate total energy
        total_similarity = sum(score for _, score in top_k)
        
        # Normalize energy distribution
        normalized_matches = []
        for voxel_id, similarity in top_k:
            # Apply sigmoid normalization to prevent extreme values
            normalized_similarity = 1.0 / (1.0 + np.exp(-5 * (similarity - 0.5)))
            
            # Calculate energy-conserving resonance strength
            # Energy is distributed proportionally to similarity
            if total_similarity > 0:
                energy_share = similarity / total_similarity
            else:
                energy_share = 1.0 / len(top_k)
            
            resonance_strength = normalized_similarity * energy_share
            
            # Ensure we don't exceed input energy
            if resonance_strength > similarity and similarity > 0:
                resonance_strength = similarity
            
            normalized_matches.append((voxel_id, similarity, resonance_strength))
        
        return normalized_matches
    
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
                    self.logger.warning(f"TopK sparse resonance clock drift detected: {time_delta}s")
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
            self._prune_activation_history()
            self._prune_resonance_log()
            
            # Check for anomalies in resonance patterns
            anomalies = self._detect_resonance_anomalies()
            
            if anomalies:
                self.logger.warning(f"Detected {len(anomalies)} resonance anomalies")
                
                # If serious anomalies, trigger fallback
                if any(a["severity"] > 0.7 for a in anomalies):
                    if not self.fallback_mode:
                        self.graceful_fallback(error_type="resonance_anomaly")
                        return False
            elif self.fallback_mode and self.fallback_level < 3:
                # Recover from fallback if no anomalies
                self.logger.info("TopK sparse resonance stability recovered")
                self.fallback_mode = False
                self.fallback_level = 0
        
        return True
    
    def _detect_resonance_anomalies(self):
        """Detect anomalies in resonance patterns."""
        anomalies = []
        
        # Check for excessive activations of the same voxel
        voxel_counts = {}
        for activation in self.resonance_log["activations"]:
            voxel_id = activation["voxel_id"]
            voxel_counts[voxel_id] = voxel_counts.get(voxel_id, 0) + 1
        
        # Check for voxels with abnormally high activation counts
        if voxel_counts:
            mean_count = sum(voxel_counts.values()) / len(voxel_counts)
            std_dev = np.std(list(voxel_counts.values())) if len(voxel_counts) > 1 else 0
            
            for voxel_id, count in voxel_counts.items():
                if std_dev > 0 and count > mean_count + 2 * std_dev:
                    # More than 2 standard deviations above mean
                    anomalies.append({
                        "voxel_id": voxel_id,
                        "type": "excessive_activation",
                        "severity": min(1.0, (count - mean_count) / (3 * std_dev)),
                        "details": {
                            "count": count,
                            "mean": mean_count,
                            "std_dev": std_dev
                        }
                    })
        
        # Check for phase alignment issues
        if len(self.resonance_log["time_steps"]) > 10:
            time_steps = self.resonance_log["time_steps"][-10:]
            if max(time_steps) - min(time_steps) > 5:
                # Large time step variance indicates phase alignment issues
                anomalies.append({
                    "type": "phase_misalignment",
                    "severity": min(1.0, (max(time_steps) - min(time_steps)) / 10),
                    "details": {
                        "time_steps": time_steps,
                        "variance": np.var(time_steps)
                    }
                })
        
        return anomalies
    
    def _prune_activation_history(self):
        """Prune activation history to prevent memory bloat."""
        cutoff_time = time.time() - (3600)  # 1 hour
        for voxel_id in list(self.activation_history.keys()):
            self.activation_history[voxel_id] = [
                a for a in self.activation_history[voxel_id] 
                if a["timestamp"] >= cutoff_time
            ]
            
            # Remove empty entries
            if not self.activation_history[voxel_id]:
                del self.activation_history[voxel_id]
    
    def _prune_resonance_log(self):
        """Prune resonance log to prevent memory bloat."""
        # Keep only the last 1000 activations
        if len(self.resonance_log["activations"]) > 1000:
            self.resonance_log["activations"] = self.resonance_log["activations"][-1000:]
        
        # Keep only the last 1000 harmonic diffs
        if len(self.resonance_log["harmonic_diffs"]) > 1000:
            self.resonance_log["harmonic_diffs"] = self.resonance_log["harmonic_diffs"][-1000:]
        
        # Keep only the last 1000 time steps
        if len(self.resonance_log["time_steps"]) > 1000:
            self.resonance_log["time_steps"] = self.resonance_log["time_steps"][-1000:]
    
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
                # Level 1: Reduce sparsity complexity
                self.logger.info("Fallback Level 1: Reducing sparsity complexity")
                action = "reduce_sparsity_complexity"
                # Increase threshold to be more selective
                self.default_threshold *= 1.2
                # Reduce k to consider fewer matches
                self.default_k = max(1, self.default_k - 2)
                
            elif self.fallback_level == 2:
                # Level 2: Simplify phase calculations
                self.logger.info("Fallback Level 2: Simplifying phase calculations")
                action = "simplify_phase_calculations"
                # Use simpler algorithms, disable advanced features
                # Increase decay to forget problematic patterns faster
                self.default_decay *= 1.5
                
            elif self.fallback_level >= 3:
                # Level 3: Minimal operation mode
                self.logger.warning("Fallback Level 3: Minimal operation mode")
                action = "minimal_operation"
                # Only essential functions, no advanced features
                # Clear histories to start fresh
                self.activation_history = {}
                self.resonance_log = {"activations": [], "harmonic_diffs": [], "time_steps": []}
                
            else:
                action = "unknown_fallback"
            
            fallback_status = {
                "module": "topk_sparse_resonance",
                "fallback_level": self.fallback_level,
                "action": action,
                "error_type": error_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Log fallback event
            self.logger.warning(f"TopK sparse resonance fallback activated: {fallback_status}")
            
            return fallback_status
    
    def resonance_chain_validator(self, top_k_matches, resonance_log):
        """
        Verifies resonance integrity across the chain.
        Required by Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            top_k_matches (list): List of (voxel_id, similarity, resonance_strength) tuples
            resonance_log (dict): Log of activations, harmonic diffs, and time steps
            
        Returns:
            dict: Validation results with integrity metrics
        """
        if not top_k_matches:
            return {"valid": False, "integrity": 0.0, "issues": ["No matches found"]}
        
        issues = []
        integrity_scores = []
        
        # Check energy conservation
        total_input_energy = sum(similarity for _, similarity, _ in top_k_matches)
        total_output_energy = sum(strength for _, _, strength in top_k_matches)
        
        if total_input_energy > 0:
            energy_ratio = total_output_energy / total_input_energy
            if energy_ratio > 1.1:  # More than 10% energy gain
                issues.append(f"Energy conservation violation: {energy_ratio:.2f} ratio")
                energy_integrity = max(0, 1.0 - (energy_ratio - 1.0))
            else:
                energy_integrity = 1.0
        else:
            energy_integrity = 0.0
            issues.append("Zero input energy")
        
        integrity_scores.append(energy_integrity)
        
        # Check similarity distribution
        similarities = [similarity for _, similarity, _ in top_k_matches]
        if similarities:
            similarity_range = max(similarities) - min(similarities)
            if similarity_range > 0.5:  # Large range indicates potential issues
                issues.append(f"Wide similarity range: {similarity_range:.2f}")
                similarity_integrity = max(0, 1.0 - similarity_range)
            else:
                similarity_integrity = 1.0
            
            integrity_scores.append(similarity_integrity)
        
        # Check temporal coherence
        if resonance_log["time_steps"]:
            time_steps = resonance_log["time_steps"]
            time_step_variance = np.var(time_steps) if len(time_steps) > 1 else 0
            
            if time_step_variance > 4:  # High variance indicates temporal issues
                issues.append(f"High temporal variance: {time_step_variance:.2f}")
                temporal_integrity = max(0, 1.0 - min(1.0, time_step_variance / 10))
            else:
                temporal_integrity = 1.0
            
            integrity_scores.append(temporal_integrity)
        
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
    
    def assess_resonance(self, harmonic_vector, voxel_field, mood="neutral", time_step=0, k=None, threshold=None):
        """
        Perform top-k sparse resonance with mood-modulated parameters and phase harmonics.
        Fully compliant with Agharmonic Law.
        
        Args:
            harmonic_vector (list): [R, G, B, intensity, freq1, freq2, ...]
            voxel_field (dict): {voxel_id: (harmonic_vector, time_step), ...}
            mood (str): Mood state for neuromodulation (default: 'neutral')
            time_step (int): Temporal index for phase harmonics
            k (int, optional): Override for number of top matches to return
            threshold (float, optional): Override for similarity threshold
        
        Returns:
            top_k_matches (list): [(voxel_id, similarity, resonance_strength), ...]
            resonance_log (dict): Log of activations, harmonic diffs, and time steps
            validation_result (dict): Resonance chain validation results
        """
        try:
            # Validate inputs against interface contract
            self.interface_contract(harmonic_vector, voxel_field, mood, time_step, k, threshold)
            
            # Synchronize with global clock
            self.sync_clock()
            
            # Apply fallback mode if active
            if self.fallback_mode and self.fallback_level >= 3:
                # Minimal operation mode
                self.logger.info("Operating in minimal mode due to fallback level 3")
                return [], {"activations": [], "harmonic_diffs": [], "time_steps": []}, {"valid": False, "reason": "minimal_operation_mode"}
            
            # Get parameters from neuromodulator with mood adjustment
            params = self.neuromod.adjust_resonance_params(mood)
            
            # Use provided parameters or defaults
            k = k or params.get("k", self.default_k)
            threshold = threshold or params.get("threshold", self.default_threshold)
            decay = params.get("decay", self.default_decay)
            phase_step = params.get("phase_step", 0.1)
            base_frequency = params.get("base_frequency", 1.0)
            
            # Apply phase offset to input vector
            self.phase_harmonics.phase_step = phase_step
            self.phase_harmonics.base_frequency = base_frequency
            phased_vector = self.phase_harmonics.add_phase_offset(harmonic_vector, time_step)
            
            with self.lock:
                similarity_scores = []
                local_resonance_log = {"activations": [], "harmonic_diffs": [], "time_steps": []}
                
                # Calculate similarities
                for voxel_id, (voxel_vector, voxel_time) in voxel_field.items():
                    similarity = self.phase_harmonics.compute_phase_similarity(
                        phased_vector, voxel_vector, time_step - voxel_time
                    )
                    if similarity >= threshold:
                        similarity_scores.append((voxel_id, similarity))
                
                # Apply cognitive energy flow for balanced distribution
                top_k_matches = self.cognitive_energy_flow(similarity_scores, k, threshold)
                
                # Process matches and update logs
                for voxel_id, similarity, resonance_strength in top_k_matches:
                    self._reinforce_voxel(voxel_id, resonance_strength, decay)
                    
                    # Record activation
                    activation = {
                        "voxel_id": voxel_id,
                        "similarity": similarity,
                        "strength": resonance_strength,
                        "decay": decay,
                        "phase_step": phase_step,
                        "timestamp": time.time()
                    }
                    
                    if voxel_id not in self.activation_history:
                        self.activation_history[voxel_id] = []
                    self.activation_history[voxel_id].append(activation)
                    
                    # Update resonance logs
                    local_resonance_log["activations"].append(activation)
                    local_resonance_log["harmonic_diffs"].append(
                        self._harmonic_diff(phased_vector, voxel_field[voxel_id][0])
                    )
                    local_resonance_log["time_steps"].append(time_step - voxel_field[voxel_id][1])
                
                # Update global resonance log
                self.resonance_log["activations"].extend(local_resonance_log["activations"])
                self.resonance_log["harmonic_diffs"].extend(local_resonance_log["harmonic_diffs"])
                self.resonance_log["time_steps"].extend(local_resonance_log["time_steps"])
            
            # Validate resonance chain integrity
            validation_result = self.resonance_chain_validator(top_k_matches, local_resonance_log)
            
            # Self-regulate
            self.self_regulate()
            
            return top_k_matches, local_resonance_log, validation_result
            
        except Exception as e:
            self.logger.error(f"Error in sparse resonance assessment: {e}")
            # Activate graceful fallback on error
            fallback_status = self.graceful_fallback(error_type=str(e))
            # Return minimal valid result
            return [], {"activations": [], "harmonic_diffs": [], "time_steps": []}, {"valid": False, "reason": str(e), "fallback": fallback_status}
    
    def _reinforce_voxel(self, voxel_id, strength, decay):
        """Reinforce voxel's resonance weight with decay using CortexCore hooks."""
        current_strength = 1.0  # Stub: Fetch from CortexCube
        adjusted_strength = max(0, current_strength * (1 - decay) + strength)
        increment_voxel(voxel_id, adjusted_strength)
        log_chain(voxel_id, adjusted_strength)
    
    def _harmonic_diff(self, vec1, vec2):
        """Return absolute difference vector for analysis/debugging."""
        return [round(abs(a - b), 3) for a, b in zip(vec1, vec2)]
    
    def cosine_similarity(self, vec1, vec2):
        """Compute cosine similarity between two harmonic vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        return round(dot_product / (norm1 * norm2), 3) if norm1 * norm2 != 0 else 0.0
    
    def compute_resonance_strength(self, similarity):
        """Map similarity score (0–1) to resonance activation strength."""
        return round(similarity ** 2, 3)
    
    def get_activation_history(self, voxel_id=None, limit=10):
        """
        Get activation history for a voxel or all voxels.
        
        Args:
            voxel_id (str, optional): Specific voxel ID to query
            limit (int): Maximum number of entries to return per voxel
            
        Returns:
            dict: Activation history by voxel ID
        """
        with self.lock:
            if voxel_id:
                history = self.activation_history.get(voxel_id, [])
                return {voxel_id: history[-limit:]}
            else:
                return {vid: history[-limit:] for vid, history in self.activation_history.items()}
    
    def get_resonance_log(self, limit=100):
        """
        Get resonance log.
        
        Args:
            limit (int): Maximum number of entries to return
            
        Returns:
            dict: Resonance log
        """
        with self.lock:
            return {
                "activations": self.resonance_log["activations"][-limit:],
                "harmonic_diffs": self.resonance_log["harmonic_diffs"][-limit:],
                "time_steps": self.resonance_log["time_steps"][-limit:]
            }
    
    def export_resonance_stats(self):
        """
        Export resonance statistics for analysis.
        
        Returns:
            dict: Resonance statistics
        """
        with self.lock:
            stats = {
                "total_voxels": len(self.activation_history),
                "total_activations": len(self.resonance_log["activations"]),
                "agharmonic_compliance": {
                    "resonance_chain_health": self.resonance_chain_health,
                    "fallback_mode": self.fallback_mode,
                    "fallback_level": self.fallback_level
                },
                "voxels": {}
            }
            
            # Calculate per-voxel statistics
            for voxel_id in self.activation_history.keys():
                activations = self.activation_history.get(voxel_id, [])
                
                if activations:
                    stats["voxels"][voxel_id] = {
                        "activation_count": len(activations),
                        "avg_similarity": sum(a["similarity"] for a in activations) / len(activations),
                        "avg_strength": sum(a["strength"] for a in activations) / len(activations),
                        "last_activation": max(a["timestamp"] for a in activations)
                    }
            
            return stats


# Create singleton instance for module-level functions
_instance = TopKSparseResonance()

# Module-level functions that delegate to the singleton
def assess_resonance(harmonic_vector, voxel_field, mood="neutral", time_step=0, k=None, threshold=None):
    """
    Module-level function that delegates to the singleton instance.
    Maintains backward compatibility with existing code.
    """
    return _instance.assess_resonance(harmonic_vector, voxel_field, mood, time_step, k, threshold)

def cosine_similarity(vec1, vec2):
    """Module-level function that delegates to the singleton instance."""
    return _instance.cosine_similarity(vec1, vec2)

def compute_resonance_strength(similarity):
    """Module-level function that delegates to the singleton instance."""
    return _instance.compute_resonance_strength(similarity)

def harmonic_diff(vec1, vec2):
    """Module-level function that delegates to the singleton instance."""
    return _instance._harmonic_diff(vec1, vec2)

def reinforce_voxel(voxel_id, strength, decay):
    """Module-level function that delegates to the singleton instance."""
    return _instance._reinforce_voxel(voxel_id, strength, decay)
