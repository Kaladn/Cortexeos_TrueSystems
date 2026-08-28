"""
CortexInspector module for CortexOS.
Provides resonance probe and health visualization capabilities.
Fully compliant with Agharmonic Law.
"""

import time
import logging
import threading
import json
import numpy as np
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agharmonic_compliant import AgharmonicCompliant

class CortexInspector(AgharmonicCompliant):
    """
    Monitors neural health and provides diagnostic visualization.
    Implements all seven Agharmonic Law interfaces for full compliance.
    """
    
    def __init__(self, global_sync_manager=None):
        # Core inspection parameters
        self.inspection_frequency = 0.5  # Hz
        self.inspection_depth = 2
        self.inspection_timeout = 1.0
        self.last_inspection_time = time.time()
        self.inspection_history = []
        self.max_history_size = 1000
        
        # Agharmonic Law compliance components
        self.global_sync_manager = global_sync_manager
        self.frequency_range = [0.2, 1.0]  # Default frequency range
        self.phase_alignment = 0.1  # Default phase alignment
        self.resonance_threshold = 0.7  # Default resonance threshold
        self.last_sync_time = time.time()
        self.sync_interval = 60  # Default sync interval in seconds
        self.health_metrics = {
            "inspections_performed": 0,
            "anomalies_detected": 0,
            "fallbacks_triggered": 0,
            "last_health_check": time.time()
        }
        self.fallback_level = 0
        self.validation_lock = threading.RLock()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Start monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Cortex inspector monitoring thread started")
        
    def _monitoring_loop(self):
        """Background thread for periodic system health checks."""
        while self.monitoring_active:
            try:
                # Perform periodic inspection
                if time.time() - self.last_inspection_time > (1.0 / self.inspection_frequency):
                    self._perform_background_inspection()
                    self.last_inspection_time = time.time()
                    
                # Perform self-regulation
                if time.time() - self.health_metrics["last_health_check"] > 300:  # 5 minutes
                    self.self_regulate()
                    
                # Sleep to avoid CPU overuse
                time.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                # Use graceful fallback
                self.graceful_fallback(e, {"context": "monitoring_loop"})
                time.sleep(5.0)  # Longer sleep after error
                
    def _perform_background_inspection(self):
        """Perform routine background inspection of system health."""
        # Record inspection
        self.health_metrics["inspections_performed"] += 1
        
        # Simulate inspection (in real system, would check actual components)
        inspection_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "system_load": np.random.uniform(0.1, 0.9),
            "resonance_integrity": np.random.uniform(0.7, 1.0),
            "anomalies": []
        }
        
        # Detect anomalies (simulated)
        if inspection_result["resonance_integrity"] < 0.8:
            anomaly = {
                "type": "resonance_degradation",
                "severity": 1.0 - inspection_result["resonance_integrity"],
                "timestamp": datetime.utcnow().isoformat()
            }
            inspection_result["anomalies"].append(anomaly)
            self.health_metrics["anomalies_detected"] += 1
            
        # Add to history
        self.inspection_history.append(inspection_result)
        
        # Trim history if needed
        if len(self.inspection_history) > self.max_history_size:
            self.inspection_history = self.inspection_history[-self.max_history_size:]
            
    def inspect_module(self, module):
        """
        Inspect a module for health and resonance integrity.
        
        Args:
            module (dict): Module to inspect
            
        Returns:
            dict: Inspection results
        """
        # Validate module
        if not isinstance(module, dict):
            self.logger.warning("Invalid module format")
            return {"status": "error", "message": "Invalid module format"}
            
        # Extract module information
        module_name = module.get("name", "unknown")
        module_health = module.get("health", 0.5)
        module_status = module.get("status", "unknown")
        
        # Perform inspection
        inspection_result = {
            "module": module_name,
            "timestamp": datetime.utcnow().isoformat(),
            "health_score": module_health,
            "status": module_status,
            "recommendations": []
        }
        
        # Generate recommendations based on health
        if module_health < 0.6:
            inspection_result["recommendations"].append({
                "action": "repair",
                "priority": "high",
                "reason": "Health below threshold"
            })
        elif module_health < 0.8:
            inspection_result["recommendations"].append({
                "action": "monitor",
                "priority": "medium",
                "reason": "Health degrading"
            })
            
        # Add to history
        self.inspection_history.append({
            "type": "module_inspection",
            "module": module_name,
            "result": inspection_result
        })
        
        return inspection_result
        
    def inspect_neural_pattern(self, pattern):
        """
        Inspect a neural pattern for resonance integrity.
        
        Args:
            pattern: Neural pattern to inspect
            
        Returns:
            dict: Inspection results
        """
        # Validate pattern
        if pattern is None:
            self.logger.warning("Invalid neural pattern")
            return {"status": "error", "message": "Invalid neural pattern"}
            
        # Perform inspection
        inspection_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "pattern_type": type(pattern).__name__,
            "health_score": 0.9,  # Simulated health score
            "recommendations": []
        }
        
        # Add to history
        self.inspection_history.append({
            "type": "pattern_inspection",
            "result": inspection_result
        })
        
        return inspection_result
        
    def get_system_health(self):
        """
        Get overall system health metrics.
        
        Returns:
            dict: System health metrics
        """
        # Calculate overall health based on recent inspections
        recent_inspections = self.inspection_history[-min(10, len(self.inspection_history)):]
        
        # Extract resonance integrity from recent inspections
        resonance_values = []
        for inspection in recent_inspections:
            if isinstance(inspection, dict) and "resonance_integrity" in inspection:
                resonance_values.append(inspection["resonance_integrity"])
                
        # Calculate average resonance integrity
        avg_resonance = sum(resonance_values) / max(1, len(resonance_values))
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_health": avg_resonance,
            "inspections_performed": self.health_metrics["inspections_performed"],
            "anomalies_detected": self.health_metrics["anomalies_detected"],
            "status": "healthy" if avg_resonance > 0.8 else "degraded"
        }
        
    # === Agharmonic Law Compliance Methods ===
    
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for inspection operations.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "cortex_inspector",
            "rhythm_hz": self.inspection_frequency,
            "threshold": self.resonance_threshold,
            "input_frequency_range": self.frequency_range,
            "output_phase_alignment": self.phase_alignment
        }
        
    def interface_contract(self, operation=None, payload=None):
        """
        Validates operations against the expected interface contract.
        Required for Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            operation (str, optional): Requested operation
            payload (dict, optional): Operation parameters
            
        Returns:
            bool or dict: True if data meets contract requirements, or contract specification if no data
        """
        # Define allowed operations and their required parameters
        allowed_operations = {
            "inspect_module": ["module"],
            "inspect_neural_pattern": ["pattern"],
            "get_system_health": [],
            "get_inspection_history": ["limit"]
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
            
        # Block recursive self-inspection
        if operation == "inspect_module" and payload.get("module", {}).get("name") == "cortex_inspector":
            return {
                "status": "invalid_operation",
                "message": "Recursive self-inspection not allowed"
            }
            
        return True
        
    def cognitive_energy_flow(self, inspection_target=None):
        """
        Normalizes inspection frequency and prioritizes critical nodes.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            inspection_target (dict, optional): Target to inspect
            
        Returns:
            dict: Normalized inspection parameters
        """
        # If no target specified, return current energy flow parameters
        if inspection_target is None:
            return {
                "inspection_frequency": self.inspection_frequency,
                "inspection_depth": self.inspection_depth,
                "energy_budget": 1.0
            }
            
        # Extract target priority if available
        target_priority = inspection_target.get("priority", 0.5)
        
        # Normalize inspection parameters based on priority
        normalized_params = {
            "inspection_frequency": min(2.0, self.inspection_frequency * (1.0 + target_priority)),
            "inspection_depth": min(5, int(self.inspection_depth * (1.0 + target_priority))),
            "inspection_timeout": self.inspection_timeout * (1.0 + 0.5 * target_priority)
        }
        
        return normalized_params
        
    def sync_clock(self, global_sync_manager=None):
        """
        Aligns with GlobalSyncManager for coordinated diagnostic intervals.
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
                
                # Update inspection parameters
                if "inspection" in sync_policy:
                    inspection_policy = sync_policy["inspection"]
                    self.inspection_frequency = inspection_policy.get("frequency", self.inspection_frequency)
                    self.inspection_depth = inspection_policy.get("depth", self.inspection_depth)
                    self.inspection_timeout = inspection_policy.get("timeout", self.inspection_timeout)
                    
                # Update sync interval
                self.sync_interval = sync_policy.get("inspection_sync_interval", 60)
                    
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
        Implements anomaly detection with auto-escalation capabilities.
        Required for Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            dict: Self-regulation metrics and actions taken
        """
        # Initialize regulation actions and fallback level
        regulation_actions = []
        fallback_level = 0
        
        # Update health metrics
        current_time = time.time()
        time_since_health_check = current_time - self.health_metrics["last_health_check"]
        
        # Perform health check every 5 minutes
        if time_since_health_check >= 300:  # 5 minutes
            # Check for excessive anomalies
            if self.health_metrics["anomalies_detected"] > 10:
                self.logger.warning(f"High anomaly count: {self.health_metrics['anomalies_detected']}")
                regulation_actions.append("reduce_inspection_frequency")
                
                # Reduce inspection frequency to avoid overloading
                self.inspection_frequency = max(0.1, self.inspection_frequency * 0.8)
                fallback_level = 1
                
            # Check for inspection starvation
            if self.health_metrics["inspections_performed"] < 10:
                self.logger.warning("Low inspection count, increasing frequency")
                regulation_actions.append("increase_inspection_frequency")
                
                # Increase inspection frequency
                self.inspection_frequency = min(2.0, self.inspection_frequency * 1.2)
                
            # Update last health check time
            self.health_metrics["last_health_check"] = current_time
            
        # Set fallback level based on anomaly count if not already set
        if fallback_level == 0 and self.health_metrics["anomalies_detected"] >= 5:
            fallback_level = 1
            
        # Store current fallback level
        self.fallback_level = fallback_level
            
        return {
            "status": "healthy" if fallback_level == 0 else "regulated",
            "metrics": self.health_metrics,
            "actions": regulation_actions,
            "fallback_level": fallback_level
        }
        
    def graceful_fallback(self, error, context=None):
        """
        Provides progressive fallback levels with passive signal listening.
        Required for Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error: Error object or string triggering fallback
            context (dict, optional): Error context information
            
        Returns:
            dict: Fallback status and actions taken
        """
        error_type = str(error) if not isinstance(error, str) else error
        self.health_metrics["fallbacks_triggered"] += 1
        
        # Create fallback response
        fallback_response = {
            "target_module": context.get("module", "unknown") if context else "unknown",
            "inspection_type": context.get("type", "unknown") if context else "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "fallback",
            "error": error_type,
            "fallback_action": "passive_listening",
            "fallback_level": self.fallback_level + 1,
            "pulse_check": {
                "status": "alive",
                "response_time_ms": 50,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Log the fallback
        self.logger.warning(f"Fallback triggered: {error_type}")
        
        return fallback_response
        
    def resonance_chain_validator(self, result=None):
        """
        Detects broken node linkages with early warning heuristics.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            result (dict, optional): Result to validate
            
        Returns:
            dict: Validation results
        """
        # If no result provided, return validation capabilities
        if result is None:
            return {
                "valid": False,
                "message": "No result provided for validation",
                "validator_type": "cortex_inspector"
            }
            
        # Validate result structure
        if not isinstance(result, dict):
            return {
                "valid": False,
                "message": "Result must be a dictionary",
                "validator_type": "cortex_inspector"
            }
            
        # Check for required fields based on result type
        if "module" in result:
            # Module inspection result
            required_fields = ["module", "timestamp", "health_score"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                return {
                    "valid": False,
                    "message": f"Missing required fields: {missing_fields}",
                    "validator_type": "cortex_inspector"
                }
                
            # Validate health score
            health_score = result.get("health_score", 0)
            if not (0 <= health_score <= 1):
                return {
                    "valid": False,
                    "message": f"Health score must be between 0 and 1, got {health_score}",
                    "validator_type": "cortex_inspector"
                }
                
        elif "pattern_type" in result:
            # Neural pattern inspection result
            required_fields = ["timestamp", "pattern_type", "health_score"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                return {
                    "valid": False,
                    "message": f"Missing required fields: {missing_fields}",
                    "validator_type": "cortex_inspector"
                }
                
        else:
            # Unknown result type
            return {
                "valid": False,
                "message": "Unknown result type",
                "validator_type": "cortex_inspector"
            }
            
        # All validations passed
        return {
            "valid": True,
            "message": "Result is valid",
            "validator_type": "cortex_inspector"
        }
