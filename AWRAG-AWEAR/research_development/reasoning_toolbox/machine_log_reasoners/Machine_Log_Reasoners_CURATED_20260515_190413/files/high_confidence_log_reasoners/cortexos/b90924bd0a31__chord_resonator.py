"""
Chord Resonator module for CortexOS Temporal Cognition v2.1

This module detects and manages harmonic chord patterns in resonance fields.
It implements pattern recognition across neural activations and provides
mechanisms for amplifying detected resonance patterns.

Fully compliant with Agharmonic Law.
"""

import json
import time
import logging
from collections import defaultdict
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ChordResonator:
    def __init__(self, chord_map_path: str, neuron_mapper):
        """
        Initialize the chord resonator with a chord map and neuron mapper.
        
        Args:
            chord_map_path: Path to the chord definition file
            neuron_mapper: Instance of NeuronMapper for coordinate translation
        """
        self.chords = self.load_chords(chord_map_path)
        self.mapper = neuron_mapper
        self.last_sync = datetime.utcnow()
        self.activation_history = defaultdict(list)
        self.resonance_buffer = []
        self.stability_metrics = {"pattern_stability": 1.0, "resonance_quality": 1.0}
        self.degradation_level = 0
        self.max_degradation_levels = 3
        self.resonance_chain_status = {"valid": True, "issues": []}
        logger.info("ChordResonator initialized with %d chords", len(self.chords))

    def harmonic_signature(self):
        """
        Provide frequency compatibility parameters for this module.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "chord_resonator",
            "input_frequency_range": [0.7, 1.5],
            "output_phase_alignment": 0.1,
            "resonance_threshold": 0.85,
            "harmonic_mode": "pattern_recognition"
        }
    
    def interface_contract(self, inputs=None, outputs=None):
        """
        Validate that inputs and outputs conform to expected structure.
        
        Args:
            inputs: Input data to validate
            outputs: Output data to validate
            
        Returns:
            bool: True if valid, raises exception otherwise
        """
        if inputs is not None:
            required_inputs = ["active_neuron_ids", "threshold"]
            if not all(key in inputs for key in required_inputs):
                missing = [k for k in required_inputs if k not in inputs]
                raise ValueError(f"Missing required inputs: {missing}")
            
            if not isinstance(inputs["active_neuron_ids"], list):
                raise TypeError("active_neuron_ids must be a list")
            
            if not isinstance(inputs["threshold"], (int, float)) or not 0 <= inputs["threshold"] <= 1:
                raise ValueError("threshold must be a number between 0 and 1")
        
        if outputs is not None:
            required_outputs = ["matches", "resonance_quality"]
            if not all(key in outputs for key in required_outputs):
                missing = [k for k in required_outputs if k not in outputs]
                raise ValueError(f"Missing required outputs: {missing}")
        
        return True
    
    def cognitive_energy_flow(self, match_scores):
        """
        Normalize resonance signal strength according to conservation principles.
        
        Args:
            match_scores: Raw match scores from chord detection
            
        Returns:
            list: Normalized match scores
        """
        if not match_scores:
            return []
        
        # Apply sigmoid normalization to prevent extreme values
        normalized = []
        for score in match_scores:
            # Soft cap at 0.95 to prevent resonance saturation
            norm_score = min(0.95, score)
            # Boost weak but valid signals
            if 0.6 <= score < 0.75:
                norm_score = score * 1.1
            normalized.append(norm_score)
        
        return normalized
    
    def sync_clock(self):
        """
        Check if it's time to process new chord detection cycle.
        
        Returns:
            bool: True if synchronization cycle should proceed
        """
        now = datetime.utcnow()
        delta = (now - self.last_sync).total_seconds()
        
        # Synchronize with global timing framework (10Hz max)
        if delta >= 0.1:
            self.last_sync = now
            return True
        return False
    
    def self_regulate(self):
        """
        Implement feedback loops to maintain stable operation.
        
        This method monitors pattern stability and resonance quality,
        adjusting internal parameters to maintain optimal performance.
        """
        # Prune activation history to prevent memory bloat
        for chord_id in list(self.activation_history.keys()):
            if len(self.activation_history[chord_id]) > 100:
                self.activation_history[chord_id] = self.activation_history[chord_id][-50:]
        
        # Clear resonance buffer if it grows too large
        if len(self.resonance_buffer) > 200:
            logger.warning("Resonance buffer overflow, clearing oldest entries")
            self.resonance_buffer = self.resonance_buffer[-100:]
        
        # Update stability metrics based on recent activations
        activation_counts = [len(history) for history in self.activation_history.values()]
        if activation_counts:
            variance = sum((c - sum(activation_counts)/len(activation_counts))**2 for c in activation_counts)
            self.stability_metrics["pattern_stability"] = max(0.5, min(1.0, 1.0 - (variance / (100 + variance))))
        
        # Reset degradation if stability is high
        if self.stability_metrics["pattern_stability"] > 0.9 and self.degradation_level > 0:
            logger.info("System stability high, resetting degradation level")
            self.degradation_level = max(0, self.degradation_level - 1)
    
    def graceful_fallback(self, error_type=None, context=None):
        """
        Implement degraded operation modes for fault tolerance.
        
        Args:
            error_type: Type of error triggering fallback
            context: Additional context about the error
            
        Returns:
            dict: Fallback strategy information
        """
        if error_type is None:
            # Check if we need to enter degraded mode based on stability
            if self.stability_metrics["pattern_stability"] < 0.6:
                self.degradation_level = min(self.max_degradation_levels, self.degradation_level + 1)
        else:
            # Explicit error handling
            logger.error("Error in chord resonator: %s, context: %s", error_type, context)
            self.degradation_level = min(self.max_degradation_levels, self.degradation_level + 1)
        
        # Apply fallback strategies based on degradation level
        strategy = {
            "degradation_level": self.degradation_level,
            "actions_taken": []
        }
        
        if self.degradation_level >= 1:
            strategy["actions_taken"].append("increasing_match_threshold")
            strategy["new_threshold"] = 0.7  # Require stronger matches
            
        if self.degradation_level >= 2:
            strategy["actions_taken"].append("limiting_active_chords")
            strategy["max_active_chords"] = 5  # Limit number of active chords
            
        if self.degradation_level >= 3:
            strategy["actions_taken"].append("emergency_mode")
            strategy["emergency_actions"] = ["reset_activation_history", "use_cached_patterns"]
            self.activation_history = defaultdict(list)
            
        logger.info("Chord resonator operating in degradation level %d", self.degradation_level)
        return strategy
    
    def resonance_chain_validator(self, upstream_modules=None, downstream_modules=None):
        """
        Validate resonance integrity across the module chain.
        
        Args:
            upstream_modules: List of upstream module states
            downstream_modules: List of downstream module states
            
        Returns:
            dict: Validation results
        """
        self.resonance_chain_status = {"valid": True, "issues": []}
        
        # Validate internal state
        if not self.chords:
            self.resonance_chain_status["valid"] = False
            self.resonance_chain_status["issues"].append("no_chord_definitions")
        
        if self.stability_metrics["pattern_stability"] < 0.5:
            self.resonance_chain_status["valid"] = False
            self.resonance_chain_status["issues"].append("low_pattern_stability")
        
        # Validate upstream connections (topk_sparse_resonance)
        if upstream_modules and "topk_sparse_resonance" in upstream_modules:
            upstream = upstream_modules["topk_sparse_resonance"]
            if upstream.get("output_frequency", 0) < self.harmonic_signature()["input_frequency_range"][0]:
                self.resonance_chain_status["valid"] = False
                self.resonance_chain_status["issues"].append("frequency_mismatch_with_upstream")
        
        # Validate downstream connections (resonance_reinforcer)
        if downstream_modules and "resonance_reinforcer" in downstream_modules:
            downstream = downstream_modules["resonance_reinforcer"]
            if self.harmonic_signature()["output_phase_alignment"] != downstream.get("input_phase_alignment", -1):
                self.resonance_chain_status["valid"] = False
                self.resonance_chain_status["issues"].append("phase_mismatch_with_downstream")
        
        return self.resonance_chain_status

    def load_chords(self, path: str) -> dict:
        """
        Load chord definitions from a file.
        
        Args:
            path: Path to the chord definition file
            
        Returns:
            dict: Loaded chord definitions
        """
        chords = {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    chord = json.loads(line.strip())
                    chords[chord["chord_id"]] = chord
            logger.info(f"Loaded {len(chords)} symbolic chords from {path}.")
        except FileNotFoundError:
            logger.error(f"Chord map file not found: {path}")
            self.graceful_fallback("file_not_found", {"path": path})
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON in {path}: {e}")
            self.graceful_fallback("json_decode_error", {"path": path, "error": str(e)})
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading chords from {path}: {e}")
            self.graceful_fallback("unexpected_error", {"path": path, "error": str(e)})
        return chords

    def detect_active_chords(self, active_neuron_ids: list[str], threshold: float = 0.6) -> list[dict]:
        """
        Detect active chord patterns based on active neurons.
        
        Args:
            active_neuron_ids: List of active neuron IDs
            threshold: Minimum match score threshold
            
        Returns:
            list: Detected chord matches
        """
        # Validate inputs through interface contract
        self.interface_contract({"active_neuron_ids": active_neuron_ids, "threshold": threshold})
        
        matches = []
        if not self.chords:
            logger.warning("No chords loaded. Cannot detect active chords.")
            return matches
        
        # Apply degradation strategies if needed
        fallback_info = self.graceful_fallback()
        if "new_threshold" in fallback_info:
            threshold = fallback_info["new_threshold"]
        
        active_neuron_set = set(active_neuron_ids)
        for chord_id, chord in self.chords.items():
            required = set(chord.get("neuron_ids", []))
            if not required:
                logger.warning(f"Chord {chord_id} has no neuron_ids defined. Skipping.")
                continue
            
            active_in_chord = required.intersection(active_neuron_set)
            score = len(active_in_chord) / len(required)
            
            if score >= threshold:
                match_info = {
                    "chord_id": chord_id,
                    "match_score": score,
                    "chord": chord,
                    "active_neurons_in_chord": list(active_in_chord),
                    "timestamp": datetime.utcnow().isoformat()
                }
                matches.append(match_info)
                
                # Record activation for stability tracking
                self.activation_history[chord_id].append({
                    "timestamp": time.time(),
                    "score": score
                })
        
        # Apply cognitive energy flow normalization
        raw_scores = [m["match_score"] for m in matches]
        normalized_scores = self.cognitive_energy_flow(raw_scores)
        
        for i, norm_score in enumerate(normalized_scores):
            matches[i]["normalized_score"] = norm_score
        
        # Sort by normalized score
        matches = sorted(matches, key=lambda x: -x.get("normalized_score", x["match_score"]))
        
        # Apply max active chords limit if in degraded mode
        if "max_active_chords" in fallback_info:
            matches = matches[:fallback_info["max_active_chords"]]
        
        # Store in resonance buffer for self-regulation
        self.resonance_buffer.extend(matches)
        
        # Update resonance quality metric
        if matches:
            self.stability_metrics["resonance_quality"] = sum(m["match_score"] for m in matches) / len(matches)
        
        # Self-regulate after processing
        self.self_regulate()
        
        # Validate output through interface contract
        self.interface_contract(outputs={"matches": matches, "resonance_quality": self.stability_metrics["resonance_quality"]})
        
        return matches

    def amplify_resonance(self, cortex_cube, chord: dict, intensity: float = 0.3, flush_now: bool = True):
        """
        Amplifies the resonance of a given chord in the Cortex Cube.
        
        Args:
            cortex_cube: The cortex cube instance to amplify in
            chord: Chord definition to amplify
            intensity: Amplification intensity (0-1)
            flush_now: Whether to flush changes immediately
            
        Returns:
            dict: Amplification results
        """
        result = {
            "success": False,
            "activated_count": 0,
            "chord_id": chord.get("chord_id", "UnknownChord")
        }
        
        if not cortex_cube or not chord or not self.mapper:
            logger.error("[Resonator] Error: Missing cortex_cube, chord, or neuron_mapper for amplification.")
            self.graceful_fallback("missing_dependencies", {"has_cube": bool(cortex_cube), "has_mapper": bool(self.mapper)})
            return result
        
        neuron_ids_to_activate = chord.get("neuron_ids", [])
        if not neuron_ids_to_activate:
            logger.warning(f"[Resonator] Warning: Chord {chord.get('chord_id', 'UnknownChord')} has no neuron_ids to activate.")
            return result

        # Apply cognitive energy flow to normalize intensity
        normalized_intensity = min(0.95, intensity)
        
        logger.info(f"[Resonator] Amplifying chord {chord.get('chord_id', 'UnknownChord')} with intensity {normalized_intensity:.2f}")
        activated_count = 0
        
        try:
            for neuron_id in neuron_ids_to_activate:
                try:
                    x, y, z = self.mapper.id_to_coords(neuron_id)
                    cortex_cube.activate_voxel(x, y, z, normalized_intensity)
                    activated_count += 1
                except Exception as e:
                    logger.warning(f"[Resonator] Failed to activate neuron {neuron_id}: {e}")
                    continue
            
            if flush_now and activated_count > 0:
                cortex_cube.flush()
                
            result["success"] = activated_count > 0
            result["activated_count"] = activated_count
            
            # Record this amplification in the resonance buffer
            self.resonance_buffer.append({
                "type": "amplification",
                "chord_id": chord.get("chord_id", "UnknownChord"),
                "intensity": normalized_intensity,
                "activated_count": activated_count,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Self-regulate after amplification
            self.self_regulate()
            
        except Exception as e:
            logger.error(f"[Resonator] Error during chord amplification: {e}")
            self.graceful_fallback("amplification_error", {"chord_id": chord.get("chord_id", "UnknownChord"), "error": str(e)})
        
        return result

    def get_stability_metrics(self):
        """
        Get current stability metrics for monitoring.
        
        Returns:
            dict: Current stability metrics
        """
        return {
            "pattern_stability": self.stability_metrics["pattern_stability"],
            "resonance_quality": self.stability_metrics["resonance_quality"],
            "degradation_level": self.degradation_level,
            "active_chords_count": len(self.activation_history),
            "resonance_buffer_size": len(self.resonance_buffer),
            "resonance_chain_valid": self.resonance_chain_status["valid"],
            "timestamp": datetime.utcnow().isoformat()
        }

# Legacy function interface for backward compatibility
def detect_active_chords(active_neuron_ids, threshold=0.6, chord_map_path=None, neuron_mapper=None):
    """
    Legacy function interface for backward compatibility.
    
    Args:
        active_neuron_ids: List of active neuron IDs
        threshold: Minimum match score threshold
        chord_map_path: Path to chord definition file
        neuron_mapper: NeuronMapper instance
        
    Returns:
        list: Detected chord matches
    """
    if not chord_map_path or not neuron_mapper:
        logger.error("Missing required parameters for chord detection")
        return []
    
    resonator = ChordResonator(chord_map_path, neuron_mapper)
    return resonator.detect_active_chords(active_neuron_ids, threshold)
