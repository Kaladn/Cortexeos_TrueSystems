"""
Self Repair module for CortexOS Temporal Cognition.

This module provides autonomous healing capabilities during corrupted activation or instability.
It monitors neural health, detects anomalies, and implements repair strategies to maintain
system integrity and performance.

This module implements the Agharmonic Law by providing:
- Harmonic Resonance through compatible repair frequencies
- Cognitive Isolation with well-defined repair interfaces
- Balanced Information Flow through prioritized repair operations
- Temporal Synchronization with the Global Sync Manager
- Self-Regulation through adaptive repair strategies
- Graceful Degradation with multi-level fallback mechanisms
- Resonance Chain Integrity through repair validation

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
from collections import deque

# Configure module logger
logger = logging.getLogger(__name__)

class SelfRepair:
    """
    Autonomous self-repair system for CortexOS neural architecture.
    
    Provides continuous monitoring, anomaly detection, and repair mechanisms
    to maintain neural integrity during operation. Implements the Agharmonic Law
    through self-regulation and graceful degradation capabilities.
    """
    
    def __init__(self, repair_threshold=0.75, scan_interval=5.0, global_sync_manager=None,
                 repair_log_file="repair_history.json"):
        """
        Initialize the self-repair system.
        
        Args:
            repair_threshold (float): Threshold for triggering repairs (0.0-1.0)
            scan_interval (float): Time between system scans in seconds
            global_sync_manager: Reference to global sync manager
            repair_log_file (str): File to store repair history
        """
        # Setup logging
        logger.info("Initializing SelfRepair module")
        
        # Configuration
        self.repair_threshold = repair_threshold
        self.scan_interval = scan_interval
        self.max_repair_attempts = 3
        self.repair_cooldown = 30.0  # seconds
        self.repair_log_file = repair_log_file
        self.global_sync_manager = global_sync_manager
        
        # State tracking
        self.is_active = False
        self.scan_thread = None
        self.repair_history = deque(maxlen=100)
        self.last_repair_time = 0
        self.repair_in_progress = False
        self.anomaly_registry = {}
        self._lock = threading.Lock()
        self._last_sync = datetime.utcnow()
        self._health_metrics = {
            "repairs_count": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "anomalies_detected": 0,
            "last_error": None,
            "avg_repair_time": 0.0
        }
        
        # Agharmonic compliance parameters
        self.input_frequency_range = (0.1, 2.0)  # in Hz
        self.output_phase_alignment = 0.0
        self.resonance_threshold = 0.65
        self.repair_energy_budget = 1.0
        self.fallback_levels = ["normal", "conservative", "minimal", "emergency"]
        self.current_fallback_level = "normal"
        
        # Try to import cortex_inspector, but provide fallback if not available
        try:
            from cortex_inspector import CortexInspector
            self.inspector = CortexInspector()
        except ImportError:
            logger.warning("CortexInspector not available, using fallback implementation")
            self.inspector = self._create_minimal_inspector()
        
        # Load repair history
        self._load_repair_history()
        
        # Initialize repair strategies
        self._init_repair_strategies()
        
        # Start monitoring thread
        self._start_monitor_thread()
        
        logger.info("SelfRepair module initialized successfully")
    
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establish frequency compatibility for Agharmonic Law compliance.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "self_repair",
            "rhythm_hz": 0.1,  # 10 seconds per cycle
            "input_range": self.input_frequency_range,
            "output_phase": self.output_phase_alignment,
            "threshold": self.resonance_threshold,
            "repair_threshold": self.repair_threshold,
            "repair_energy_budget": self.repair_energy_budget,
            "fallback_level": self.current_fallback_level
        }
    
    def interface_contract(self, repair_request: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Define and validate interface contract for Agharmonic Law compliance.
        Required for Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            repair_request: Optional repair request to validate
            
        Returns:
            Dict containing validation result or interface definition
        """
        # Define standard interface
        interface = {
            "inputs": ["system_state", "module_states", "anomaly_reports"],
            "outputs": ["repair_actions", "health_report", "stability_score"],
            "repair_types": list(self.repair_strategies.keys()),
            "fallback_levels": self.fallback_levels
        }
        
        # If no repair request, just return interface definition
        if repair_request is None:
            return interface
        
        # Validate repair request
        if not isinstance(repair_request, dict):
            return {
                "status": "error",
                "message": "Repair request must be a dictionary",
                "valid": False
            }
        
        # Check required fields
        required_fields = ["module_name", "request_id"]
        missing_fields = [field for field in required_fields if field not in repair_request]
        if missing_fields:
            return {
                "status": "error",
                "message": f"Missing required repair request fields: {', '.join(missing_fields)}",
                "valid": False
            }
        
        # Validate repair type if specified
        if "repair_type" in repair_request:
            if repair_request["repair_type"] not in self.repair_strategies:
                return {
                    "status": "error",
                    "message": f"Invalid repair type: {repair_request['repair_type']}. Must be one of {list(self.repair_strategies.keys())}",
                    "valid": False
                }
        
        # Validate priority if specified
        if "priority" in repair_request:
            priority = repair_request["priority"]
            if not isinstance(priority, (int, float)) or priority < 0 or priority > 1:
                return {
                    "status": "error",
                    "message": "Priority must be a number between 0 and 1",
                    "valid": False
                }
        
        return {
            "status": "success",
            "message": "Repair request is valid",
            "valid": True
        }
    
    def cognitive_energy_flow(self, repair_type: str, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize repair energy allocation and prioritize critical repairs.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            repair_type: Type of repair
            module_name: Module to repair
            anomalies: List of detected anomalies
            
        Returns:
            Dict containing normalized energy allocation
        """
        # Base energy consumption by repair type
        energy_map = {
            "restart": 0.3,
            "reinitialize": 0.5,
            "reconfigure": 0.4,
            "clear_cache": 0.2,
            "restore_defaults": 0.6,
            "partial_reset": 0.3,
            "adaptive_rebalance": 0.7,
            "emergency_stabilize": 0.9
        }
        
        base_energy = energy_map.get(repair_type, 0.5)
        
        # Calculate anomaly severity
        severity = self._calculate_anomaly_severity(anomalies)
        
        # Calculate priority based on module criticality and anomaly severity
        module_criticality = self._get_module_criticality(module_name)
        priority = (module_criticality + severity) / 2
        
        # Adjust energy based on priority
        energy_allocation = base_energy * (0.5 + 0.5 * priority)
        
        # Check if we're over budget
        if energy_allocation > self.repair_energy_budget:
            # Scale down to fit within budget
            energy_allocation = self.repair_energy_budget
            logger.warning(f"Repair energy scaled down to fit budget: {energy_allocation:.2f}")
        
        # Calculate expected success probability
        success_probability = max(0.1, min(0.9, 1.0 - (severity * 0.5)))
        
        # Apply system-wide energy conservation
        # If we're repairing multiple modules, distribute energy fairly
        with self._lock:
            active_repairs = sum(1 for v in self.anomaly_registry.values() if v.get("repair_in_progress", False))
            if active_repairs > 1:
                # Scale down energy allocation when multiple repairs are active
                energy_allocation *= (1.0 / active_repairs)
                logger.info(f"Energy allocation scaled to {energy_allocation:.2f} due to {active_repairs} active repairs")
        
        return {
            "repair_type": repair_type,
            "module_name": module_name,
            "energy_allocation": energy_allocation,
            "priority": priority,
            "severity": severity,
            "success_probability": success_probability,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _calculate_anomaly_severity(self, anomalies: List[Dict[str, Any]]) -> float:
        """
        Calculate severity of anomalies.
        
        Args:
            anomalies: List of anomalies
            
        Returns:
            float: Severity score (0.0-1.0)
        """
        if not anomalies:
            return 0.0
        
        # Calculate severity based on anomaly types and counts
        severity_map = {
            "critical": 1.0,
            "major": 0.7,
            "minor": 0.3,
            "warning": 0.1
        }
        
        total_severity = 0.0
        for anomaly in anomalies:
            severity_type = anomaly.get("severity", "minor")
            severity_score = severity_map.get(severity_type, 0.3)
            total_severity += severity_score
        
        # Normalize to 0.0-1.0 range
        normalized_severity = min(1.0, total_severity / max(1, len(anomalies)))
        
        return normalized_severity
    
    def _get_module_criticality(self, module_name: str) -> float:
        """
        Get criticality score for a module.
        
        Args:
            module_name: Module name
            
        Returns:
            float: Criticality score (0.0-1.0)
        """
        # Define criticality for core modules
        criticality_map = {
            "neuroengine": 1.0,
            "neural_gatekeeper": 0.9,
            "resonance_field": 0.9,
            "phase_harmonics": 0.8,
            "cortex_vectorizer": 0.8,
            "swarm_resonance": 0.7,
            "resonance_reinforcer": 0.7,
            "topk_sparse_resonance": 0.7,
            "knowledge_reinforcer": 0.6,
            "memory_inserter": 0.6,
            "cortex_cube_nvme": 0.6,
            "data_ingestor": 0.5,
            "trust_filter": 0.5,
            "cortex_core_hooks": 0.8,
            "cortex_inspector": 0.4,
            "mirror_reflector": 0.4,
            "symbolic_translator": 0.4,
            "mood_controller": 0.5,
            "neuromodulation": 0.5
        }
        
        return criticality_map.get(module_name, 0.3)
    
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
                        if "repair" in policy:
                            self.repair_threshold = policy["repair"].get("threshold", self.repair_threshold)
                            self.repair_cooldown = policy["repair"].get("cooldown", self.repair_cooldown)
                            self.max_repair_attempts = policy["repair"].get("max_attempts", self.max_repair_attempts)
                            
                    # Adjust scan interval based on system load
                    if stats.get('cycle_time', 5) > 5:  # System under load
                        logger.info("System under load, increasing scan interval")
                        # Increase scan interval under load
                        self.scan_interval = min(30.0, self.scan_interval * 1.5)
                    else:  # Normal load
                        # Reset to default values or policy values
                        self.scan_interval = 5.0
                        
                self._last_sync = current_time
                
                return {
                    "status": "synced",
                    "message": "Successfully synchronized with global clock",
                    "thresholds": {
                        "repair": self.repair_threshold,
                        "cooldown": self.repair_cooldown,
                        "max_attempts": self.max_repair_attempts
                    },
                    "scan_interval": self.scan_interval,
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
        Implement self-regulation with adaptive repair strategies.
        Required for Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            Dict containing self-regulation metrics
        """
        with self._lock:
            repair_count = self._health_metrics["repairs_count"]
            success_rate = self._health_metrics["successful_repairs"] / max(1, repair_count)
            
        # Check if we're overloaded with repair requests
        if repair_count > 50 and success_rate < 0.5:
            # Too many repairs with low success rate, adjust strategy
            logger.warning("Self-regulation: Too many failed repairs, adjusting strategy")
            
            # Increase repair threshold to be more selective
            self.repair_threshold = min(0.9, self.repair_threshold + 0.1)
            
            # Increase cooldown to reduce repair frequency
            self.repair_cooldown = min(120.0, self.repair_cooldown * 1.5)
            
            # Adjust scan interval
            self.scan_interval = min(30.0, self.scan_interval * 1.5)
            
            # Move to more conservative fallback level
            self._escalate_fallback_level()
        
        # If very few repairs or high success rate, gradually return to normal
        elif (repair_count < 5 or success_rate > 0.9) and self.current_fallback_level != "normal":
            logger.info("Self-regulation: Good repair performance, normalizing parameters")
            
            # Decrease repair threshold to be less selective
            self.repair_threshold = max(0.6, self.repair_threshold - 0.05)
            
            # Decrease cooldown to increase repair frequency
            self.repair_cooldown = max(15.0, self.repair_cooldown * 0.8)
            
            # Adjust scan interval
            self.scan_interval = max(5.0, self.scan_interval * 0.9)
            
            # Move to less conservative fallback level
            self._deescalate_fallback_level()
        
        # Check for stuck repairs
        with self._lock:
            current_time = time.time()
            for module, info in list(self.anomaly_registry.items()):
                if info.get("repair_in_progress", False):
                    repair_start_time = info.get("repair_start_time", 0)
                    if current_time - repair_start_time > 300:  # 5 minutes
                        logger.warning(f"Self-regulation: Repair for {module} stuck for over 5 minutes, resetting")
                        info["repair_in_progress"] = False
                        info["repair_attempts"] += 1
                        self._health_metrics["failed_repairs"] += 1
        
        # Save repair history periodically
        if repair_count % 10 == 0 and repair_count > 0:
            self._save_repair_history()
        
        return {
            "repair_threshold": self.repair_threshold,
            "repair_cooldown": self.repair_cooldown,
            "scan_interval": self.scan_interval,
            "fallback_level": self.current_fallback_level,
            "repair_energy_budget": self.repair_energy_budget,
            "success_rate": success_rate,
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
        Implement multi-level graceful degradation for Agharmonic Law compliance.
        Required for Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error: The exception that occurred
            context: Context information about the operation
            
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning(f"Executing graceful fallback: {error}")
        
        module_name = context.get("module_name", "unknown")
        repair_type = context.get("repair_type", "unknown")
        
        # Record error
        with self._lock:
            self._health_metrics["last_error"] = str(error)
            
        # Create fallback repair result
        fallback_result = {
            "module_name": module_name,
            "repair_type": repair_type,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "fallback",
            "error": str(error),
            "fallback_level": self.current_fallback_level
        }
        
        # Determine fallback action based on current level
        if self.current_fallback_level == "normal":
            # Try alternative repair strategy
            alternative_repair = self._get_alternative_repair(repair_type)
            fallback_result["fallback_action"] = f"try_alternative_{alternative_repair}"
            fallback_result["alternative_repair"] = alternative_repair
            
            # Attempt the alternative repair
            try:
                if alternative_repair in self.repair_strategies:
                    logger.info(f"Attempting alternative repair: {alternative_repair}")
                    repair_func = self.repair_strategies[alternative_repair]
                    alt_result = repair_func(module_name, context.get("anomalies", []))
                    fallback_result["alternative_result"] = alt_result
            except Exception as alt_error:
                logger.error(f"Alternative repair failed: {alt_error}")
                fallback_result["alternative_error"] = str(alt_error)
            
        elif self.current_fallback_level == "conservative":
            # Delay repairs and focus on critical modules only
            fallback_result["fallback_action"] = "delay_non_critical"
            self.repair_cooldown = max(60.0, self.repair_cooldown)
            
            # Only repair if module is critical
            module_criticality = self._get_module_criticality(module_name)
            if module_criticality >= 0.7:
                logger.info(f"Conservative mode: Still repairing critical module {module_name}")
                fallback_result["still_repairing"] = True
                
                # Try minimal repair
                try:
                    minimal_result = self._perform_minimal_repair(module_name)
                    fallback_result["minimal_repair"] = minimal_result
                except Exception as min_error:
                    logger.error(f"Minimal repair failed: {min_error}")
                    fallback_result["minimal_error"] = str(min_error)
            else:
                logger.info(f"Conservative mode: Delaying repair for non-critical module {module_name}")
                fallback_result["delayed"] = True
            
        elif self.current_fallback_level == "minimal":
            # Only perform minimal stabilization repairs
            fallback_result["fallback_action"] = "minimal_stabilization"
            
            # Try stabilization only
            try:
                stabilize_result = self._perform_stabilization(module_name)
                fallback_result["stabilization"] = stabilize_result
            except Exception as stab_error:
                logger.error(f"Stabilization failed: {stab_error}")
                fallback_result["stabilization_error"] = str(stab_error)
            
        else:  # emergency
            # Emergency mode - only critical system functions
            fallback_result["fallback_action"] = "emergency_only"
            self.repair_threshold = 0.9  # Only repair severe issues
            
            # Only repair if module is essential
            module_criticality = self._get_module_criticality(module_name)
            if module_criticality >= 0.9:
                logger.warning(f"Emergency mode: Attempting last-resort repair for essential module {module_name}")
                fallback_result["emergency_repair"] = True
                
                # Try emergency repair
                try:
                    emergency_result = self._perform_emergency_repair(module_name)
                    fallback_result["emergency_result"] = emergency_result
                except Exception as emerg_error:
                    logger.error(f"Emergency repair failed: {emerg_error}")
                    fallback_result["emergency_error"] = str(emerg_error)
            else:
                logger.warning(f"Emergency mode: Skipping repair for non-essential module {module_name}")
                fallback_result["skipped"] = True
            
        # Escalate fallback level if needed
        if self.current_fallback_level != "emergency":
            retry_count = context.get("retry_count", 0)
            if retry_count > 3:
                self._escalate_fallback_level()
                fallback_result["escalated_to"] = self.current_fallback_level
        
        # Add to repair history
        self._add_to_repair_history({
            "module": module_name,
            "repair_type": repair_type,
            "status": "fallback",
            "fallback_level": self.current_fallback_level,
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return fallback_result
    
    def _get_alternative_repair(self, repair_type: str) -> str:
        """
        Get alternative repair strategy.
        
        Args:
            repair_type: Original repair type
            
        Returns:
            str: Alternative repair type
        """
        # Define fallback chains
        fallback_chains = {
            "restart": "partial_reset",
            "reinitialize": "reconfigure",
            "reconfigure": "restore_defaults",
            "clear_cache": "restart",
            "restore_defaults": "reinitialize",
            "partial_reset": "clear_cache",
            "adaptive_rebalance": "reconfigure",
            "emergency_stabilize": "restart"
        }
        
        return fallback_chains.get(repair_type, "clear_cache")
    
    def _perform_minimal_repair(self, module_name: str) -> Dict[str, Any]:
        """
        Perform minimal repair for conservative mode.
        
        Args:
            module_name: Module to repair
            
        Returns:
            Dict containing repair results
        """
        # In a real implementation, this would perform a minimal repair
        # For this example, we'll simulate a minimal repair
        return {
            "status": "minimal_repair_completed",
            "module": module_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _perform_stabilization(self, module_name: str) -> Dict[str, Any]:
        """
        Perform stabilization for minimal mode.
        
        Args:
            module_name: Module to stabilize
            
        Returns:
            Dict containing stabilization results
        """
        # In a real implementation, this would perform stabilization
        # For this example, we'll simulate stabilization
        return {
            "status": "stabilized",
            "module": module_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _perform_emergency_repair(self, module_name: str) -> Dict[str, Any]:
        """
        Perform emergency repair for emergency mode.
        
        Args:
            module_name: Module to repair
            
        Returns:
            Dict containing emergency repair results
        """
        # In a real implementation, this would perform an emergency repair
        # For this example, we'll simulate an emergency repair
        return {
            "status": "emergency_repair_completed",
            "module": module_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def resonance_chain_validator(self, repair_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate repair result for resonance chain integrity.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            repair_result: Repair result to validate
            
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
        
        # Check for required repair result fields
        if not repair_result or not isinstance(repair_result, dict):
            validation_result["valid"] = False
            validation_result["issues"].append("Missing or invalid repair result")
            return validation_result
        
        required_fields = ["module", "status", "timestamp"]
        missing_fields = [field for field in required_fields if field not in repair_result]
        if missing_fields:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check for valid status
        valid_statuses = ["success", "partial", "failed", "fallback"]
        if "status" in repair_result and repair_result["status"] not in valid_statuses:
            validation_result["warnings"].append(f"Unknown status: {repair_result['status']}")
        
        # Check for resonance disruption
        if "resonance_impact" in repair_result:
            impact = repair_result["resonance_impact"]
            if impact > 0.5:
                validation_result["valid"] = False
                validation_result["issues"].append(f"High resonance impact: {impact:.2f}")
            elif impact > 0.2:
                validation_result["warnings"].append(f"Moderate resonance impact: {impact:.2f}")
        
        # Check for chain integrity
        if "affected_chains" in repair_result:
            affected_chains = repair_result["affected_chains"]
            if len(affected_chains) > 3:
                validation_result["valid"] = False
                validation_result["issues"].append(f"Too many affected chains: {len(affected_chains)}")
            elif len(affected_chains) > 1:
                validation_result["warnings"].append(f"Multiple affected chains: {len(affected_chains)}")
        
        # Check for timestamp validity
        if "timestamp" in repair_result:
            try:
                repair_time = datetime.fromisoformat(repair_result["timestamp"])
                current_time = datetime.utcnow()
                time_diff = (current_time - repair_time).total_seconds()
                
                # Repair should be recent
                if time_diff > 300:  # 5 minutes
                    validation_result["warnings"].append(f"Repair result is stale: {time_diff:.1f} seconds old")
            except (ValueError, TypeError):
                validation_result["warnings"].append("Invalid timestamp format")
        
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
                corrective_actions.append("Ensure repair result contains all required fields")
            elif "High resonance impact" in issue:
                corrective_actions.append("Perform gradual repair with lower impact")
            elif "Too many affected chains" in issue:
                corrective_actions.append("Repair chains sequentially instead of in parallel")
        
        return corrective_actions
    
    def _init_repair_strategies(self) -> None:
        """
        Initialize repair strategies.
        """
        self.repair_strategies = {
            "restart": self._repair_restart,
            "reinitialize": self._repair_reinitialize,
            "reconfigure": self._repair_reconfigure,
            "clear_cache": self._repair_clear_cache,
            "restore_defaults": self._repair_restore_defaults,
            "partial_reset": self._repair_partial_reset,
            "adaptive_rebalance": self._repair_adaptive_rebalance,
            "emergency_stabilize": self._repair_emergency_stabilize
        }
    
    def _repair_restart(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Restart module.
        
        Args:
            module_name: Module to restart
            anomalies: List of anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.info(f"Restarting module: {module_name}")
        
        # In a real implementation, this would restart the module
        # For this example, we'll simulate a restart
        
        return {
            "module": module_name,
            "status": "success",
            "repair_type": "restart",
            "anomalies_fixed": len(anomalies),
            "resonance_impact": 0.3,
            "affected_chains": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _repair_reinitialize(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reinitialize module.
        
        Args:
            module_name: Module to reinitialize
            anomalies: List of anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.info(f"Reinitializing module: {module_name}")
        
        # In a real implementation, this would reinitialize the module
        # For this example, we'll simulate reinitialization
        
        return {
            "module": module_name,
            "status": "success",
            "repair_type": "reinitialize",
            "anomalies_fixed": len(anomalies),
            "resonance_impact": 0.4,
            "affected_chains": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _repair_reconfigure(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reconfigure module.
        
        Args:
            module_name: Module to reconfigure
            anomalies: List of anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.info(f"Reconfiguring module: {module_name}")
        
        # In a real implementation, this would reconfigure the module
        # For this example, we'll simulate reconfiguration
        
        return {
            "module": module_name,
            "status": "success",
            "repair_type": "reconfigure",
            "anomalies_fixed": len(anomalies),
            "resonance_impact": 0.2,
            "affected_chains": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _repair_clear_cache(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Clear module cache.
        
        Args:
            module_name: Module to clear cache
            anomalies: List of anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.info(f"Clearing cache for module: {module_name}")
        
        # In a real implementation, this would clear the module's cache
        # For this example, we'll simulate cache clearing
        
        return {
            "module": module_name,
            "status": "success",
            "repair_type": "clear_cache",
            "anomalies_fixed": len(anomalies),
            "resonance_impact": 0.1,
            "affected_chains": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _repair_restore_defaults(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Restore module defaults.
        
        Args:
            module_name: Module to restore defaults
            anomalies: List of anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.info(f"Restoring defaults for module: {module_name}")
        
        # In a real implementation, this would restore the module's defaults
        # For this example, we'll simulate default restoration
        
        return {
            "module": module_name,
            "status": "success",
            "repair_type": "restore_defaults",
            "anomalies_fixed": len(anomalies),
            "resonance_impact": 0.3,
            "affected_chains": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _repair_partial_reset(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Partially reset module.
        
        Args:
            module_name: Module to partially reset
            anomalies: List of anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.info(f"Partially resetting module: {module_name}")
        
        # In a real implementation, this would partially reset the module
        # For this example, we'll simulate a partial reset
        
        return {
            "module": module_name,
            "status": "success",
            "repair_type": "partial_reset",
            "anomalies_fixed": len(anomalies),
            "resonance_impact": 0.2,
            "affected_chains": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _repair_adaptive_rebalance(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Adaptively rebalance module.
        
        Args:
            module_name: Module to rebalance
            anomalies: List of anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.info(f"Adaptively rebalancing module: {module_name}")
        
        # In a real implementation, this would rebalance the module
        # For this example, we'll simulate rebalancing
        
        return {
            "module": module_name,
            "status": "success",
            "repair_type": "adaptive_rebalance",
            "anomalies_fixed": len(anomalies),
            "resonance_impact": 0.3,
            "affected_chains": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _repair_emergency_stabilize(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Emergency stabilize module.
        
        Args:
            module_name: Module to stabilize
            anomalies: List of anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.warning(f"Emergency stabilizing module: {module_name}")
        
        # In a real implementation, this would stabilize the module
        # For this example, we'll simulate stabilization
        
        return {
            "module": module_name,
            "status": "success",
            "repair_type": "emergency_stabilize",
            "anomalies_fixed": len(anomalies),
            "resonance_impact": 0.5,
            "affected_chains": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _create_minimal_inspector(self) -> Any:
        """
        Create minimal inspector for fallback.
        
        Returns:
            Minimal inspector object
        """
        class MinimalInspector:
            def inspect(self, target_module, inspection_type, context=None):
                return {
                    "status": "success",
                    "target_module": target_module,
                    "inspection_type": inspection_type,
                    "health_score": 0.5,
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return MinimalInspector()
    
    def _load_repair_history(self) -> None:
        """
        Load repair history from file.
        """
        try:
            if os.path.exists(self.repair_log_file):
                with open(self.repair_log_file, 'r') as f:
                    history = json.load(f)
                    self.repair_history = deque(history, maxlen=100)
                    logger.info(f"Loaded {len(self.repair_history)} repair history entries")
        except Exception as e:
            logger.warning(f"Failed to load repair history: {e}")
    
    def _save_repair_history(self) -> None:
        """
        Save repair history to file.
        """
        try:
            with open(self.repair_log_file, 'w') as f:
                json.dump(list(self.repair_history), f, indent=2)
                logger.info(f"Saved {len(self.repair_history)} repair history entries")
        except Exception as e:
            logger.error(f"Failed to save repair history: {e}")
    
    def _add_to_repair_history(self, entry: Dict[str, Any]) -> None:
        """
        Add entry to repair history.
        
        Args:
            entry: Repair history entry
        """
        self.repair_history.append(entry)
    
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
                    
                    # Scan for anomalies
                    self._scan_for_anomalies()
                    
                    # Process repair queue
                    self._process_repair_queue()
                    
                    # Sleep for scan interval
                    time.sleep(self.scan_interval)
                except Exception as e:
                    logger.error(f"Error in monitor loop: {e}")
                    time.sleep(10)  # Sleep longer on error
        
        # Start thread
        self.scan_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.scan_thread.start()
        self.is_active = True
        logger.info("Monitor thread started")
    
    def _scan_for_anomalies(self) -> None:
        """
        Scan for anomalies.
        """
        # In a real implementation, this would scan for anomalies
        # For this example, we'll simulate anomaly detection
        pass
    
    def _process_repair_queue(self) -> None:
        """
        Process repair queue.
        """
        # In a real implementation, this would process the repair queue
        # For this example, we'll simulate queue processing
        pass
    
    def repair_module(self, module_name: str, repair_type: str = None, anomalies: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Repair a module.
        
        Args:
            module_name: Module to repair
            repair_type: Type of repair, or None for automatic selection
            anomalies: List of anomalies, or None to use detected anomalies
            
        Returns:
            Dict containing repair results
        """
        logger.info(f"Repairing module: {module_name}")
        
        # Get anomalies if not provided
        if anomalies is None:
            with self._lock:
                module_info = self.anomaly_registry.get(module_name, {})
                anomalies = module_info.get("anomalies", [])
        
        # Check if repair is needed
        if not anomalies:
            logger.info(f"No anomalies detected for module: {module_name}")
            return {
                "module": module_name,
                "status": "skipped",
                "message": "No anomalies detected",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Check cooldown
        current_time = time.time()
        with self._lock:
            module_info = self.anomaly_registry.get(module_name, {})
            last_repair_time = module_info.get("last_repair_time", 0)
            repair_attempts = module_info.get("repair_attempts", 0)
            
            if current_time - last_repair_time < self.repair_cooldown:
                logger.info(f"Repair cooldown for module: {module_name}")
                return {
                    "module": module_name,
                    "status": "cooldown",
                    "message": f"Repair cooldown: {self.repair_cooldown - (current_time - last_repair_time):.1f}s remaining",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Check max attempts
            if repair_attempts >= self.max_repair_attempts:
                logger.warning(f"Max repair attempts reached for module: {module_name}")
                return {
                    "module": module_name,
                    "status": "max_attempts",
                    "message": f"Max repair attempts reached: {repair_attempts}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Mark repair in progress
            module_info["repair_in_progress"] = True
            module_info["repair_start_time"] = current_time
            self.anomaly_registry[module_name] = module_info
        
        try:
            # Select repair strategy
            if repair_type is None:
                repair_type = self._select_repair_strategy(module_name, anomalies)
            
            # Check if repair strategy exists
            if repair_type not in self.repair_strategies:
                logger.error(f"Unknown repair type: {repair_type}")
                return {
                    "module": module_name,
                    "status": "error",
                    "message": f"Unknown repair type: {repair_type}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Calculate energy allocation
            energy = self.cognitive_energy_flow(repair_type, module_name, anomalies)
            
            # Check if energy allocation is sufficient
            if energy["energy_allocation"] < self.repair_threshold:
                logger.info(f"Insufficient energy for repair: {energy['energy_allocation']:.2f} < {self.repair_threshold:.2f}")
                return {
                    "module": module_name,
                    "status": "insufficient_energy",
                    "message": f"Insufficient energy: {energy['energy_allocation']:.2f} < {self.repair_threshold:.2f}",
                    "energy": energy,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Perform repair
            repair_func = self.repair_strategies[repair_type]
            repair_result = repair_func(module_name, anomalies)
            
            # Validate repair result
            validation = self.resonance_chain_validator(repair_result)
            if not validation["valid"]:
                logger.warning(f"Repair validation failed: {validation['issues']}")
                repair_result["validation_issues"] = validation["issues"]
                repair_result["status"] = "partial"
            
            # Update repair history
            self._add_to_repair_history({
                "module": module_name,
                "repair_type": repair_type,
                "status": repair_result["status"],
                "anomalies": len(anomalies),
                "energy": energy["energy_allocation"],
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update metrics
            with self._lock:
                self._health_metrics["repairs_count"] += 1
                if repair_result["status"] == "success":
                    self._health_metrics["successful_repairs"] += 1
                else:
                    self._health_metrics["failed_repairs"] += 1
                
                # Update module info
                module_info = self.anomaly_registry.get(module_name, {})
                module_info["repair_in_progress"] = False
                module_info["last_repair_time"] = current_time
                module_info["repair_attempts"] = module_info.get("repair_attempts", 0) + 1
                module_info["last_repair_result"] = repair_result
                
                if repair_result["status"] == "success":
                    module_info["anomalies"] = []
                
                self.anomaly_registry[module_name] = module_info
            
            # Add energy and validation to result
            repair_result["energy"] = energy
            repair_result["validation"] = validation
            
            return repair_result
            
        except Exception as e:
            logger.error(f"Error during repair: {e}")
            
            # Update module info
            with self._lock:
                module_info = self.anomaly_registry.get(module_name, {})
                module_info["repair_in_progress"] = False
                module_info["repair_attempts"] = module_info.get("repair_attempts", 0) + 1
                self.anomaly_registry[module_name] = module_info
                
                self._health_metrics["failed_repairs"] += 1
            
            # Use graceful fallback
            return self.graceful_fallback(e, {
                "module_name": module_name,
                "repair_type": repair_type,
                "anomalies": anomalies,
                "retry_count": module_info.get("repair_attempts", 0)
            })
    
    def _select_repair_strategy(self, module_name: str, anomalies: List[Dict[str, Any]]) -> str:
        """
        Select repair strategy based on anomalies.
        
        Args:
            module_name: Module to repair
            anomalies: List of anomalies
            
        Returns:
            str: Selected repair strategy
        """
        # Count anomaly types
        anomaly_types = {}
        for anomaly in anomalies:
            anomaly_type = anomaly.get("type", "unknown")
            anomaly_types[anomaly_type] = anomaly_types.get(anomaly_type, 0) + 1
        
        # Select strategy based on most common anomaly type
        if not anomaly_types:
            return "clear_cache"  # Default
        
        most_common_type = max(anomaly_types.items(), key=lambda x: x[1])[0]
        
        # Map anomaly types to repair strategies
        strategy_map = {
            "crash": "restart",
            "memory_leak": "restart",
            "configuration": "reconfigure",
            "corruption": "reinitialize",
            "performance": "adaptive_rebalance",
            "cache": "clear_cache",
            "resonance": "adaptive_rebalance",
            "critical": "emergency_stabilize"
        }
        
        return strategy_map.get(most_common_type, "clear_cache")
    
    def report_anomaly(self, module_name: str, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """
        Report an anomaly for a module.
        
        Args:
            module_name: Module with anomaly
            anomaly: Anomaly information
            
        Returns:
            Dict containing report status
        """
        logger.info(f"Anomaly reported for module: {module_name}")
        
        # Ensure anomaly has required fields
        if "type" not in anomaly:
            anomaly["type"] = "unknown"
        if "severity" not in anomaly:
            anomaly["severity"] = "minor"
        if "timestamp" not in anomaly:
            anomaly["timestamp"] = datetime.utcnow().isoformat()
        
        # Update anomaly registry
        with self._lock:
            module_info = self.anomaly_registry.get(module_name, {
                "anomalies": [],
                "repair_attempts": 0,
                "last_repair_time": 0,
                "repair_in_progress": False
            })
            
            module_info["anomalies"].append(anomaly)
            self.anomaly_registry[module_name] = module_info
            
            self._health_metrics["anomalies_detected"] += 1
        
        # Check if immediate repair is needed
        needs_immediate_repair = anomaly.get("severity") == "critical"
        
        # Trigger repair if needed
        if needs_immediate_repair:
            logger.warning(f"Critical anomaly detected, triggering immediate repair for module: {module_name}")
            repair_result = self.repair_module(module_name)
            
            return {
                "status": "reported_and_repaired",
                "module": module_name,
                "anomaly": anomaly,
                "repair_result": repair_result,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "reported",
            "module": module_name,
            "anomaly": anomaly,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_health_report(self) -> Dict[str, Any]:
        """
        Get health report.
        
        Returns:
            Dict containing health report
        """
        with self._lock:
            health_metrics = self._health_metrics.copy()
            anomaly_count = sum(len(info.get("anomalies", [])) for info in self.anomaly_registry.values())
            modules_with_anomalies = sum(1 for info in self.anomaly_registry.values() if info.get("anomalies"))
        
        return {
            "status": "healthy" if anomaly_count == 0 else "degraded",
            "anomaly_count": anomaly_count,
            "modules_with_anomalies": modules_with_anomalies,
            "repair_success_rate": health_metrics["successful_repairs"] / max(1, health_metrics["repairs_count"]),
            "repair_threshold": self.repair_threshold,
            "repair_cooldown": self.repair_cooldown,
            "scan_interval": self.scan_interval,
            "fallback_level": self.current_fallback_level,
            "health_metrics": health_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_module_status(self, module_name: str) -> Dict[str, Any]:
        """
        Get status for a specific module.
        
        Args:
            module_name: Module to get status for
            
        Returns:
            Dict containing module status
        """
        with self._lock:
            module_info = self.anomaly_registry.get(module_name, {})
            anomalies = module_info.get("anomalies", [])
            repair_attempts = module_info.get("repair_attempts", 0)
            last_repair_time = module_info.get("last_repair_time", 0)
            repair_in_progress = module_info.get("repair_in_progress", False)
            last_repair_result = module_info.get("last_repair_result", {})
        
        return {
            "module": module_name,
            "status": "healthy" if not anomalies else "degraded",
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "repair_attempts": repair_attempts,
            "last_repair_time": datetime.fromtimestamp(last_repair_time).isoformat() if last_repair_time > 0 else None,
            "repair_in_progress": repair_in_progress,
            "last_repair_result": last_repair_result,
            "criticality": self._get_module_criticality(module_name),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_repair_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get repair history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of repair history entries
        """
        return list(self.repair_history)[-limit:]
