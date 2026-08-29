"""
CortexInspector module for CortexOS.
Exports resonance data as WebGL-compatible JSON for 4D visualization.
Provides comprehensive monitoring, visualization, and early warning for neural degradation.

This module implements the Agharmonic Law by providing:
- Harmonic Resonance through synchronized inspection frequencies
- Cognitive Isolation with well-defined probe interfaces
- Balanced Information Flow through prioritized node inspection
- Temporal Synchronization with the Global Sync Manager
- Self-Regulation through anomaly detection and auto-escalation
- Graceful Degradation with passive signal listening fallback
- Resonance Chain Integrity through comprehensive chain validation
"""

import json
import logging
import threading
import time
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Callable

# Configure module logger
logger = logging.getLogger(__name__)

class CortexInspector:
    """
    Exports CortexOS resonance data for WebGL/Three.js visualization.
    Renders mood-colored voxels, pulsating phase offsets, and time-aligned resonance arcs.
    Implements all seven Agharmonic Law interfaces for full compliance.
    """
    def __init__(self, mood_to_color_file="mood_to_color.json", global_sync_manager=None, 
                 degradation_log_file="cortex_degradation_log.json"):
        self.mood_to_color = self.load_mood_to_color(mood_to_color_file)
        self.global_sync_manager = global_sync_manager
        self.degradation_log_file = degradation_log_file
        self._lock = threading.Lock()
        self._last_sync = datetime.utcnow()
        self._inspection_queue = []
        self._anomaly_counters = {}
        self._inspection_history = []
        self._degradation_log = self._load_degradation_log()
        self._health_metrics = {
            "inspections_count": 0,
            "anomalies_detected": 0,
            "chain_breaches": 0,
            "last_error": None,
            "avg_processing_time": 0.0
        }
        
        # Agharmonic Law compliance parameters
        self.inspection_threshold = 0.75
        self.anomaly_threshold = 3
        self.escalation_threshold = 5
        self.chain_breach_threshold = 0.6
        
        # Try to import neuromodulator, but provide fallback if not available
        try:
            from neuromodulation import Neuromodulator
            self.neuromod = Neuromodulator()
        except ImportError:
            logger.warning("Neuromodulator not available, using fallback implementation")
            self.neuromod = self._create_fallback_neuromodulator()
            
        # Start monitoring thread
        self._start_monitor_thread()
        
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility parameters for this module.
        Syncs resonance signature with swarm_resonance and neuroengine.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        signature = {
            "module": "cortex_inspector",
            "rhythm_hz": 0.2,  # 5 seconds per cycle
            "input_range": (0.1, 1.0),  # in Hz
            "output_phase": 0.0,
            "threshold": 0.85,
            "inspection_threshold": self.inspection_threshold,
            "diagnostic_enabled": True
        }
        
        # Add diagnostic payload signature for probe tracing
        signature["diagnostic_payload"] = self.diagnostic_payload_signature()
        
        return signature
    
    def diagnostic_payload_signature(self) -> Dict[str, Any]:
        """
        Creates a unique signature for diagnostic payloads to trace inspector probes.
        
        Returns:
            Dict containing diagnostic payload signature
        """
        timestamp = datetime.utcnow().isoformat()
        probe_id = hashlib.md5(f"cortex_inspector_{timestamp}".encode()).hexdigest()
        
        return {
            "probe_id": probe_id,
            "source": "cortex_inspector",
            "timestamp": timestamp,
            "trace_enabled": True,
            "signature_version": "1.0"
        }
    
    def interface_contract(self, probe_request: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Defines allowed probe requests and data formats.
        Blocks recursive self-inspection unless authenticated.
        Required for Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            probe_request: The inspection probe request
            
        Returns:
            Dict containing validation result or interface definition
        """
        # Define standard interface
        interface = {
            "inputs": ["target_module", "inspection_type", "request_id", "auth_token"],
            "outputs": ["inspection_result", "anomalies", "health_score", "visualization_data"],
            "inspection_types": ["health", "resonance", "chain", "voxel", "full"],
            "auth_required_for": ["cortex_inspector", "neural_gatekeeper", "neuroengine"]
        }
        
        # If no probe request, just return interface definition
        if probe_request is None:
            return interface
            
        if not isinstance(probe_request, dict):
            return {
                "status": "error",
                "message": "Probe request must be a dictionary",
                "valid": False
            }
            
        # Check required fields
        required_fields = ["target_module", "inspection_type", "request_id"]
        missing_fields = [field for field in required_fields if field not in probe_request]
        if missing_fields:
            return {
                "status": "error",
                "message": f"Missing required probe request fields: {', '.join(missing_fields)}",
                "valid": False
            }
            
        # Validate inspection type
        if probe_request["inspection_type"] not in interface["inspection_types"]:
            return {
                "status": "error",
                "message": f"Invalid inspection type: {probe_request['inspection_type']}. Must be one of {interface['inspection_types']}",
                "valid": False
            }
            
        # Prevent recursive self-inspection without authentication
        if probe_request["target_module"] in interface["auth_required_for"]:
            if "auth_token" not in probe_request or not self._validate_auth_token(probe_request["auth_token"]):
                return {
                    "status": "error",
                    "message": "Recursive self-inspection requires valid authentication",
                    "valid": False
                }
                
        return {
            "status": "success",
            "message": "Probe request is valid",
            "valid": True
        }
    
    def _validate_auth_token(self, token: str) -> bool:
        """
        Validates authentication token for sensitive operations.
        
        Args:
            token: Authentication token
            
        Returns:
            bool: True if token is valid
        """
        # In a real implementation, this would validate against a secure token store
        # For this example, we'll use a simple validation
        if not token:
            return False
            
        # Check if token has the correct format (example: "inspector_auth_TIMESTAMP_HASH")
        parts = token.split('_')
        if len(parts) != 4 and parts[0] != "inspector" and parts[1] != "auth":
            return False
            
        # In production, validate timestamp and hash
        return True
    
    def cognitive_energy_flow(self, target_module: str, inspection_type: str, priority: float = 0.5) -> Dict[str, Any]:
        """
        Normalizes inspection frequency and prioritizes critical nodes.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            target_module: Module to inspect
            inspection_type: Type of inspection
            priority: Priority level (0.0-1.0)
            
        Returns:
            Dict containing normalized signal data
        """
        # Base energy consumption by inspection type
        energy_map = {
            "health": 0.2,
            "resonance": 0.4,
            "chain": 0.6,
            "voxel": 0.3,
            "full": 1.0
        }
        
        base_energy = energy_map.get(inspection_type, 0.5)
        
        # Check if target module is in anomaly list
        with self._lock:
            anomaly_count = self._anomaly_counters.get(target_module, 0)
            
        # Prioritize modules with anomalies
        priority_factor = 1.0
        if anomaly_count > 0:
            # Increase priority based on anomaly count
            priority_factor = min(3.0, 1.0 + (anomaly_count * 0.5))
            logger.info(f"Prioritizing {target_module} inspection due to {anomaly_count} anomalies")
            
        # Apply user-specified priority
        priority_factor *= (0.5 + priority)
            
        # Calculate final energy consumption
        energy_consumption = base_energy * priority_factor
        
        # Calculate signal strength (inverse of energy consumption)
        signal_strength = 1.0 / max(0.1, energy_consumption)
        
        # Apply system-wide energy conservation
        # If we're inspecting too many modules, reduce signal strength
        with self._lock:
            queue_size = len(self._inspection_queue)
            if queue_size > 10:
                # Scale down signal strength when queue is large
                signal_strength *= (10 / queue_size)
                
        return {
            "target_module": target_module,
            "inspection_type": inspection_type,
            "energy_consumption": energy_consumption,
            "signal_strength": signal_strength,
            "priority_factor": priority_factor,
            "anomaly_count": anomaly_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def sync_clock(self, global_clock: Any = None) -> Dict[str, Any]:
        """
        Aligns diagnostic intervals with GlobalSyncManager's thresholds.
        Required for Agharmonic Law Tenet 4: Temporal Synchronization.
        
        Args:
            global_clock: Optional reference to a global clock object
            
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
                        if "inspection" in policy:
                            self.inspection_threshold = policy["inspection"].get("threshold", self.inspection_threshold)
                            self.anomaly_threshold = policy["inspection"].get("anomaly_threshold", self.anomaly_threshold)
                            self.escalation_threshold = policy["inspection"].get("escalation_threshold", self.escalation_threshold)
                            self.chain_breach_threshold = policy["inspection"].get("chain_breach_threshold", self.chain_breach_threshold)
                            
                    # Adjust inspection frequency based on system load
                    if stats.get('cycle_time', 5) > 5:  # System under load
                        logger.info("System under load, reducing inspection frequency")
                        # Reduce inspection frequency under load
                        self.inspection_threshold = min(0.9, self.inspection_threshold + 0.1)
                    else:  # Normal load
                        # Reset to default values or policy values
                        self.inspection_threshold = 0.75
                        
                self._last_sync = current_time
                
                return {
                    "status": "synced",
                    "message": "Successfully synchronized with global clock",
                    "thresholds": {
                        "inspection": self.inspection_threshold,
                        "anomaly": self.anomaly_threshold,
                        "escalation": self.escalation_threshold,
                        "chain_breach": self.chain_breach_threshold
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
        Auto-escalates when anomalies persist beyond threshold.
        Encodes anomaly memory for pattern recognition.
        Required for Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            Dict containing self-regulation metrics
        """
        with self._lock:
            anomaly_modules = {k: v for k, v in self._anomaly_counters.items() if v > 0}
            escalation_modules = {k: v for k, v in self._anomaly_counters.items() if v >= self.escalation_threshold}
            
        # Process escalations
        for module, count in escalation_modules.items():
            logger.warning(f"Auto-escalating {module} due to persistent anomalies ({count} occurrences)")
            
            # Log to degradation log
            self._add_to_degradation_log(module, {
                "anomaly_count": count,
                "escalation_level": min(3, count // self.escalation_threshold),
                "timestamp": datetime.utcnow().isoformat(),
                "type": "persistent_anomaly"
            })
            
            # Optional: encode anomaly memory in knowledge_reinforcer
            self._encode_anomaly_memory(module, count)
            
        # Clean up old inspection history
        if len(self._inspection_history) > 100:
            self._inspection_history = self._inspection_history[-50:]
            
        # Save degradation log periodically
        if len(self._degradation_log) % 10 == 0 and self._degradation_log:
            self._save_degradation_log()
            
        # Adjust inspection parameters based on system health
        with self._lock:
            health_metrics = self._health_metrics.copy()
            
        # If we're detecting too many anomalies, adjust thresholds
        if health_metrics["anomalies_detected"] > 50:
            # Increase inspection threshold to be more selective
            self.inspection_threshold = min(0.9, self.inspection_threshold + 0.05)
            logger.info(f"Self-regulation: Increased inspection threshold to {self.inspection_threshold:.2f}")
            
        # If processing time is too high, reduce inspection frequency
        if health_metrics["avg_processing_time"] > 1.0:  # 1 second
            # Increase inspection threshold to reduce frequency
            self.inspection_threshold = min(0.9, self.inspection_threshold + 0.1)
            logger.info(f"Self-regulation: Increased inspection threshold to {self.inspection_threshold:.2f} due to high processing time")
            
        # If very few anomalies, gradually return to normal
        if health_metrics["anomalies_detected"] < 5 and self.inspection_threshold > 0.75:
            # Decrease inspection threshold to be less selective
            self.inspection_threshold = max(0.6, self.inspection_threshold - 0.05)
            logger.info(f"Self-regulation: Decreased inspection threshold to {self.inspection_threshold:.2f}")
            
        return {
            "anomaly_modules": anomaly_modules,
            "escalation_modules": escalation_modules,
            "inspection_threshold": self.inspection_threshold,
            "anomaly_threshold": self.anomaly_threshold,
            "escalation_threshold": self.escalation_threshold,
            "chain_breach_threshold": self.chain_breach_threshold,
            "inspection_history_size": len(self._inspection_history),
            "degradation_log_size": len(self._degradation_log),
            "health_metrics": health_metrics,
            "last_sync": self._last_sync.isoformat()
        }
    
    def _encode_anomaly_memory(self, module: str, count: int) -> None:
        """
        Encodes anomaly memory for pattern recognition.
        
        Args:
            module: Module with anomalies
            count: Anomaly count
        """
        try:
            # Try to import knowledge_reinforcer
            from knowledge_reinforcer import KnowledgeReinforcer
            reinforcer = KnowledgeReinforcer()
            
            # Create memory entry
            memory_entry = {
                "type": "anomaly_pattern",
                "module": module,
                "count": count,
                "timestamp": datetime.utcnow().isoformat(),
                "inspector_id": id(self)
            }
            
            # Encode memory
            reinforcer.encode_memory(memory_entry, priority=0.7)
            logger.info(f"Encoded anomaly memory for {module}")
            
        except ImportError:
            logger.warning("KnowledgeReinforcer not available, skipping anomaly memory encoding")
            
        except Exception as e:
            logger.error(f"Failed to encode anomaly memory: {e}")
    
    def graceful_fallback(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Shifts to passive signal listening if inspection fails.
        Uses weighted pulse checks for minimal monitoring.
        Required for Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error: The exception that occurred
            context: Context information about the operation
            
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning(f"Executing graceful fallback: {error}")
        
        target_module = context.get("target_module", "unknown")
        inspection_type = context.get("inspection_type", "unknown")
        
        # Record error
        with self._lock:
            self._health_metrics["last_error"] = str(error)
            
        # Create fallback inspection result
        fallback_result = {
            "target_module": target_module,
            "inspection_type": inspection_type,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "fallback",
            "error": str(error),
            "fallback_mode": "passive_listening"
        }
        
        # Add to inspection history
        with self._lock:
            self._inspection_history.append(fallback_result)
            
        # Perform passive signal listening
        try:
            # Minimal pulse check
            pulse_result = self._perform_pulse_check(target_module)
            fallback_result["pulse_check"] = pulse_result
        except Exception as e:
            logger.error(f"Failed to perform pulse check: {e}")
            fallback_result["pulse_check"] = {"status": "failed", "error": str(e)}
            
        # Log fallback to degradation log
        self._add_to_degradation_log(target_module, {
            "type": "inspection_fallback",
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "inspection_type": inspection_type
        })
        
        # Implement progressive fallback levels
        if "retry_count" in context and context["retry_count"] > 2:
            # After multiple retries, switch to minimal mode
            fallback_result["fallback_mode"] = "minimal_only"
            fallback_result["message"] = "Switched to minimal inspection mode after multiple failures"
            
            # Only perform critical health checks
            try:
                minimal_result = self._perform_minimal_health_check(target_module)
                fallback_result["minimal_check"] = minimal_result
            except Exception as e:
                logger.error(f"Failed to perform minimal health check: {e}")
                fallback_result["minimal_check"] = {"status": "failed", "error": str(e)}
                
        # If even minimal checks fail, provide static last known good data
        if "retry_count" in context and context["retry_count"] > 5:
            fallback_result["fallback_mode"] = "static_last_known"
            fallback_result["message"] = "Using last known good data after multiple failures"
            
            # Try to retrieve last known good data
            last_known = self._get_last_known_good_data(target_module)
            if last_known:
                fallback_result["data"] = last_known
                fallback_result["data_timestamp"] = last_known.get("timestamp", "unknown")
                fallback_result["data_freshness"] = "stale"
            else:
                fallback_result["data"] = None
                fallback_result["message"] = "No last known good data available"
                
        return fallback_result
    
    def _perform_pulse_check(self, target_module: str) -> Dict[str, Any]:
        """
        Performs minimal pulse check on a module.
        
        Args:
            target_module: Module to check
            
        Returns:
            Dict containing pulse check results
        """
        # In a real implementation, this would perform a minimal health check
        # For this example, we'll simulate a pulse check
        return {
            "status": "alive",
            "response_time_ms": 50,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _perform_minimal_health_check(self, target_module: str) -> Dict[str, Any]:
        """
        Performs minimal health check on a module.
        
        Args:
            target_module: Module to check
            
        Returns:
            Dict containing health check results
        """
        # In a real implementation, this would perform a minimal health check
        # For this example, we'll simulate a health check
        return {
            "status": "degraded",
            "health_score": 0.6,
            "critical_functions": "operational",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_last_known_good_data(self, target_module: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves last known good data for a module.
        
        Args:
            target_module: Module to get data for
            
        Returns:
            Dict containing last known good data, or None if not available
        """
        # In a real implementation, this would retrieve cached data
        # For this example, we'll return None
        return None
    
    def resonance_chain_validator(self, chain_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detects broken node linkages or cascade failures.
        Implements chain breach heuristics for early warning.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            chain_data: Chain data to validate
            
        Returns:
            Dict containing validation results and breach heuristics
        """
        # Initialize validation result
        validation_result = {
            "valid": True,
            "breaches": [],
            "warnings": [],
            "health_score": 1.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check for required chain data
        if not chain_data or "chains" not in chain_data or not chain_data["chains"]:
            validation_result["valid"] = False
            validation_result["warnings"].append("Missing or empty chain data")
            validation_result["health_score"] = 0.0
            return validation_result
            
        chains = chain_data["chains"]
        
        # Check for broken chains
        broken_chains = []
        weak_chains = []
        
        for i, chain in enumerate(chains):
            # Check for missing source or target
            if "source" not in chain or "target" not in chain:
                broken_chains.append({
                    "index": i,
                    "reason": "Missing source or target",
                    "chain": chain
                })
                continue
                
            # Check for zero or negative strength
            if "strength" not in chain or chain["strength"] <= 0:
                broken_chains.append({
                    "index": i,
                    "reason": "Invalid strength",
                    "chain": chain
                })
                continue
                
            # Check for weak chains
            if chain["strength"] < self.chain_breach_threshold:
                weak_chains.append({
                    "index": i,
                    "strength": chain["strength"],
                    "threshold": self.chain_breach_threshold,
                    "source": chain["source"],
                    "target": chain["target"]
                })
                
        # Check for cascade failures
        cascade_risks = self._detect_cascade_risks(chains)
        
        # Update validation result
        if broken_chains:
            validation_result["valid"] = False
            validation_result["breaches"] = broken_chains
            
        if weak_chains:
            validation_result["warnings"].append({
                "type": "weak_chains",
                "chains": weak_chains
            })
            
        if cascade_risks:
            validation_result["warnings"].append({
                "type": "cascade_risks",
                "risks": cascade_risks
            })
            
        # Calculate health score
        broken_count = len(broken_chains)
        weak_count = len(weak_chains)
        cascade_count = len(cascade_risks)
        total_chains = len(chains)
        
        if total_chains > 0:
            # Health score formula: 1.0 - (broken * 0.5 + weak * 0.2 + cascade * 0.3) / total
            health_score = 1.0 - ((broken_count * 0.5 + weak_count * 0.2 + cascade_count * 0.3) / total_chains)
            validation_result["health_score"] = max(0.0, min(1.0, health_score))
        else:
            validation_result["health_score"] = 0.0
            
        # Record chain breaches
        with self._lock:
            self._health_metrics["chain_breaches"] += broken_count
            
        return validation_result
    
    def _detect_cascade_risks(self, chains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detects potential cascade failure risks in resonance chains.
        
        Args:
            chains: List of resonance chains
            
        Returns:
            List of cascade risks
        """
        # In a real implementation, this would analyze chain topology
        # For this example, we'll return an empty list
        return []
    
    def load_mood_to_color(self, mood_to_color_file: str) -> Dict[str, List[float]]:
        """
        Loads mood-to-color mapping from JSON file.
        
        Args:
            mood_to_color_file: Path to mood-to-color JSON file
            
        Returns:
            Dict mapping moods to RGB colors
        """
        try:
            with open(mood_to_color_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load mood colors from {mood_to_color_file}: {e}")
            # Fallback to basic colors
            return {
                "neutral": [1.0, 1.0, 1.0],
                "excited": [1.0, 0.6, 0.2],
                "focused": [0.2, 0.4, 0.8],
                "cautious": [0.8, 0.8, 0.2],
                "curious": [0.4, 0.8, 1.0]
            }
    
    def _load_degradation_log(self) -> List[Dict[str, Any]]:
        """
        Loads degradation log from file.
        
        Returns:
            List of degradation log entries
        """
        try:
            if os.path.exists(self.degradation_log_file):
                with open(self.degradation_log_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.warning(f"Failed to load degradation log: {e}")
            return []
    
    def _save_degradation_log(self) -> None:
        """
        Saves degradation log to file.
        """
        try:
            with open(self.degradation_log_file, 'w') as f:
                json.dump(self._degradation_log, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save degradation log: {e}")
    
    def _add_to_degradation_log(self, module: str, entry: Dict[str, Any]) -> None:
        """
        Adds entry to degradation log.
        
        Args:
            module: Module name
            entry: Log entry
        """
        entry["module"] = module
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.utcnow().isoformat()
            
        self._degradation_log.append(entry)
        
        # Keep log size reasonable
        if len(self._degradation_log) > 1000:
            self._degradation_log = self._degradation_log[-500:]
    
    def _create_fallback_neuromodulator(self) -> Any:
        """
        Creates a minimal fallback neuromodulator.
        
        Returns:
            Minimal neuromodulator object
        """
        class MinimalNeuromodulator:
            def adjust_resonance_params(self, mood):
                return {
                    "k": 10,
                    "threshold": 0.85,
                    "decay": 0.2,
                    "phase_step": 0.1,
                    "base_frequency": 1.0
                }
                
        return MinimalNeuromodulator()
    
    def _start_monitor_thread(self) -> None:
        """
        Starts background monitoring thread.
        """
        def monitor_loop():
            while True:
                try:
                    # Sync with global clock
                    self.sync_clock()
                    
                    # Self-regulate
                    self.self_regulate()
                    
                    # Process inspection queue
                    self._process_inspection_queue()
                    
                    # Sleep for a bit
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error in monitor loop: {e}")
                    time.sleep(10)  # Sleep longer on error
                    
        # Start thread
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def _process_inspection_queue(self) -> None:
        """
        Processes inspection queue.
        """
        with self._lock:
            queue = self._inspection_queue.copy()
            self._inspection_queue = []
            
        for request in queue:
            try:
                # Process request
                result = self.inspect(
                    request["target_module"],
                    request["inspection_type"],
                    request.get("context", {})
                )
                
                # Call callback if provided
                callback = request.get("callback")
                if callback and callable(callback):
                    callback(result)
                    
            except Exception as e:
                logger.error(f"Error processing inspection request: {e}")
                
                # Call error callback if provided
                error_callback = request.get("error_callback")
                if error_callback and callable(error_callback):
                    error_callback(e)
    
    def queue_inspection(self, target_module: str, inspection_type: str, 
                        context: Dict[str, Any] = None, callback: Callable = None,
                        error_callback: Callable = None) -> str:
        """
        Queues an inspection request for asynchronous processing.
        
        Args:
            target_module: Module to inspect
            inspection_type: Type of inspection
            context: Additional context
            callback: Callback function for result
            error_callback: Callback function for errors
            
        Returns:
            str: Request ID
        """
        request_id = hashlib.md5(f"{target_module}_{inspection_type}_{time.time()}".encode()).hexdigest()
        
        request = {
            "request_id": request_id,
            "target_module": target_module,
            "inspection_type": inspection_type,
            "context": context or {},
            "callback": callback,
            "error_callback": error_callback,
            "timestamp": time.time()
        }
        
        with self._lock:
            self._inspection_queue.append(request)
            
        return request_id
    
    def inspect(self, target_module: str, inspection_type: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Performs inspection of a module.
        
        Args:
            target_module: Module to inspect
            inspection_type: Type of inspection
            context: Additional context
            
        Returns:
            Dict containing inspection results
        """
        context = context or {}
        start_time = time.time()
        
        try:
            # Validate request
            probe_request = {
                "target_module": target_module,
                "inspection_type": inspection_type,
                "request_id": context.get("request_id", hashlib.md5(f"{target_module}_{inspection_type}_{time.time()}".encode()).hexdigest())
            }
            
            validation = self.interface_contract(probe_request)
            if not validation.get("valid", False):
                return {
                    "status": "error",
                    "message": validation.get("message", "Invalid probe request"),
                    "target_module": target_module,
                    "inspection_type": inspection_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            # Normalize energy flow
            energy = self.cognitive_energy_flow(
                target_module, 
                inspection_type,
                context.get("priority", 0.5)
            )
            
            # Check if signal strength is too low
            if energy["signal_strength"] < self.inspection_threshold:
                logger.info(f"Skipping inspection of {target_module} due to low signal strength: {energy['signal_strength']:.2f}")
                return {
                    "status": "skipped",
                    "message": f"Signal strength below threshold: {energy['signal_strength']:.2f} < {self.inspection_threshold:.2f}",
                    "target_module": target_module,
                    "inspection_type": inspection_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            # Perform inspection based on type
            if inspection_type == "health":
                result = self._inspect_health(target_module, context)
            elif inspection_type == "resonance":
                result = self._inspect_resonance(target_module, context)
            elif inspection_type == "chain":
                result = self._inspect_chain(target_module, context)
            elif inspection_type == "voxel":
                result = self._inspect_voxel(target_module, context)
            elif inspection_type == "full":
                result = self._inspect_full(target_module, context)
            else:
                # Should never happen due to validation
                raise ValueError(f"Unknown inspection type: {inspection_type}")
                
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update health metrics
            with self._lock:
                self._health_metrics["inspections_count"] += 1
                
                # Update average processing time with exponential moving average
                alpha = 0.1  # Smoothing factor
                self._health_metrics["avg_processing_time"] = (
                    (1 - alpha) * self._health_metrics["avg_processing_time"] + 
                    alpha * processing_time
                )
                
                # Add to inspection history
                self._inspection_history.append({
                    "target_module": target_module,
                    "inspection_type": inspection_type,
                    "status": "success",
                    "processing_time": processing_time,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            # Add processing metadata
            result["processing_time"] = processing_time
            result["energy"] = energy
            
            return result
            
        except Exception as e:
            logger.error(f"Error during inspection: {e}")
            
            # Update retry count in context
            retry_count = context.get("retry_count", 0) + 1
            context["retry_count"] = retry_count
            
            # Use graceful fallback
            return self.graceful_fallback(e, {
                "target_module": target_module,
                "inspection_type": inspection_type,
                "retry_count": retry_count
            })
    
    def _inspect_health(self, target_module: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs health inspection of a module.
        
        Args:
            target_module: Module to inspect
            context: Additional context
            
        Returns:
            Dict containing health inspection results
        """
        # In a real implementation, this would inspect the module's health
        # For this example, we'll return simulated health data
        return {
            "status": "success",
            "target_module": target_module,
            "inspection_type": "health",
            "health_score": 0.9,
            "metrics": {
                "memory_usage": 0.3,
                "cpu_usage": 0.2,
                "error_rate": 0.01,
                "response_time": 0.05
            },
            "anomalies": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _inspect_resonance(self, target_module: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs resonance inspection of a module.
        
        Args:
            target_module: Module to inspect
            context: Additional context
            
        Returns:
            Dict containing resonance inspection results
        """
        # In a real implementation, this would inspect the module's resonance
        # For this example, we'll return simulated resonance data
        return {
            "status": "success",
            "target_module": target_module,
            "inspection_type": "resonance",
            "resonance_score": 0.85,
            "frequencies": [0.5, 1.0, 1.5],
            "phase_offsets": [0.0, 0.1, 0.2],
            "amplitude": 0.7,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _inspect_chain(self, target_module: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs chain inspection of a module.
        
        Args:
            target_module: Module to inspect
            context: Additional context
            
        Returns:
            Dict containing chain inspection results
        """
        # In a real implementation, this would inspect the module's chains
        # For this example, we'll return simulated chain data
        chains = [
            {"source": target_module, "target": "module1", "strength": 0.9},
            {"source": target_module, "target": "module2", "strength": 0.8},
            {"source": target_module, "target": "module3", "strength": 0.7}
        ]
        
        # Validate chains
        chain_data = {"chains": chains}
        validation = self.resonance_chain_validator(chain_data)
        
        return {
            "status": "success",
            "target_module": target_module,
            "inspection_type": "chain",
            "chains": chains,
            "validation": validation,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _inspect_voxel(self, target_module: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs voxel inspection of a module.
        
        Args:
            target_module: Module to inspect
            context: Additional context
            
        Returns:
            Dict containing voxel inspection results
        """
        # In a real implementation, this would inspect the module's voxels
        # For this example, we'll return simulated voxel data
        return {
            "status": "success",
            "target_module": target_module,
            "inspection_type": "voxel",
            "voxel_count": 100,
            "active_voxels": 30,
            "voxel_density": 0.3,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _inspect_full(self, target_module: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs full inspection of a module.
        
        Args:
            target_module: Module to inspect
            context: Additional context
            
        Returns:
            Dict containing full inspection results
        """
        # Perform all inspection types
        health = self._inspect_health(target_module, context)
        resonance = self._inspect_resonance(target_module, context)
        chain = self._inspect_chain(target_module, context)
        voxel = self._inspect_voxel(target_module, context)
        
        # Combine results
        return {
            "status": "success",
            "target_module": target_module,
            "inspection_type": "full",
            "health": health,
            "resonance": resonance,
            "chain": chain,
            "voxel": voxel,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def export_visualization_data(self, target_module: str = None) -> Dict[str, Any]:
        """
        Exports visualization data for WebGL rendering.
        
        Args:
            target_module: Optional module to focus on
            
        Returns:
            Dict containing visualization data
        """
        # In a real implementation, this would export visualization data
        # For this example, we'll return simulated visualization data
        return {
            "status": "success",
            "target_module": target_module,
            "nodes": [],
            "edges": [],
            "voxels": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """
        Gets current health metrics.
        
        Returns:
            Dict containing health metrics
        """
        with self._lock:
            return self._health_metrics.copy()
    
    def get_degradation_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Gets degradation log.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of degradation log entries
        """
        return self._degradation_log[-limit:]
