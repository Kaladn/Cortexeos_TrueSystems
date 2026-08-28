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
    
    def interface_contract(self, repair_request: Dict[str, Any] = None) -> bool:
        """
        Define and validate interface contract for Agharmonic Law compliance.
        
        Args:
            repair_request: Optional repair request to validate
            
        Returns:
            bool: True if contract is valid
            
        Raises:
            ValueError: If contract is invalid
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
            raise ValueError("Repair request must be a dictionary")
        
        # Check required fields
        required_fields = ["module_name", "request_id"]
        missing_fields = [field for field in required_fields if field not in repair_request]
        if missing_fields:
            raise ValueError(f"Missing required repair request fields: {', '.join(missing_fields)}")
        
        # Validate repair type if specified
        if "repair_type" in repair_request:
            if repair_request["repair_type"] not in self.repair_strategies:
                raise ValueError(f"Invalid repair type: {repair_request['repair_type']}. Must be one of {list(self.repair_strategies.keys())}")
        
        # Validate priority if specified
        if "priority" in repair_request:
            priority = repair_request["priority"]
            if not isinstance(priority, (int, float)) or priority < 0 or priority > 1:
                raise ValueError("Priority must be a number between 0 and 1")
        
        return True
    
    def cognitive_energy_flow(self, repair_type: str, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize repair energy allocation and prioritize critical repairs.
        
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
        
        return {
            "repair_type": repair_type,
            "module_name": module_name,
            "energy_allocation": energy_allocation,
            "priority": priority,
            "severity": severity,
            "success_probability": success_probability,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def sync_clock(self, global_clock: Any = None) -> bool:
        """
        Synchronize with global temporal framework for Agharmonic Law compliance.
        
        Args:
            global_clock: Global clock reference
            
        Returns:
            bool: True if synchronization successful
        """
        try:
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
                        
                self._last_sync = datetime.utcnow()
                return True
            elif self.global_sync_manager:
                return self.sync_clock(self.global_sync_manager)
            else:
                # No global clock, use internal timing
                self.current_time = time.time()
                self._last_sync = datetime.utcnow()
                logger.debug(f"Using internal clock: {self.current_time}")
                return True
        except Exception as e:
            logger.error(f"Failed to sync with global clock: {e}")
            return False
    
    def self_regulate(self) -> Dict[str, Any]:
        """
        Implement self-regulation with adaptive repair strategies.
        
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
    
    def graceful_fallback(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement multi-level graceful degradation for Agharmonic Law compliance.
        
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
            
        elif self.current_fallback_level == "conservative":
            # Delay repairs and focus on critical modules only
            fallback_result["fallback_action"] = "delay_non_critical"
            self.repair_cooldown = max(60.0, self.repair_cooldown)
            
        elif self.current_fallback_level == "minimal":
            # Only perform minimal stabilization repairs
            fallback_result["fallback_action"] = "minimal_stabilization"
            
        else:  # emergency
            # Emergency mode - only critical system functions
            fallback_result["fallback_action"] = "emergency_only"
            self.repair_threshold = 0.9  # Only repair severe issues
            
        # Escalate fallback level if needed
        if self.current_fallback_level != "emergency":
            self._escalate_fallback_level()
            fallback_result["new_fallback_level"] = self.current_fallback_level
            
        # Add to repair history
        repair_record = {
            'module': module_name,
            'repair_type': repair_type,
            'success': False,
            'fallback': True,
            'fallback_level': self.current_fallback_level,
            'error': str(error),
            'timestamp': time.time()
        }
        self.repair_history.append(repair_record)
        
        with self._lock:
            self._health_metrics["failed_repairs"] += 1
            
        return fallback_result
    
    def resonance_chain_validator(self, repair_action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate repair integrity for Agharmonic Law compliance.
        
        Args:
            repair_action: Repair action to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            ValueError: If repair action is invalid
        """
        # Initialize validation result
        validation_result = {
            "valid": True,
            "warnings": [],
            "integrity_score": 1.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Basic validation
        if not repair_action or not isinstance(repair_action, dict):
            validation_result["valid"] = False
            validation_result["warnings"].append("Invalid repair action format")
            validation_result["integrity_score"] = 0.0
            return validation_result
        
        # Check required fields
        required_keys = ['module_name', 'repair_type', 'timestamp']
        missing_keys = [k for k in required_keys if k not in repair_action]
        if missing_keys:
            validation_result["valid"] = False
            validation_result["warnings"].append(f"Missing required keys: {missing_keys}")
            validation_result["integrity_score"] = 0.0
            return validation_result
        
        # Verify timestamp is recent
        try:
            timestamp = datetime.fromisoformat(repair_action['timestamp'])
            time_diff = abs((datetime.utcnow() - timestamp).total_seconds())
            if time_diff > 60:
                validation_result["warnings"].append(f"Repair action timestamp outside acceptable range: {time_diff}s old")
                validation_result["integrity_score"] -= 0.3
        except (ValueError, TypeError):
            validation_result["warnings"].append("Invalid timestamp format")
            validation_result["integrity_score"] -= 0.3
        
        # Verify repair type is valid
        if repair_action['repair_type'] not in self.repair_strategies:
            validation_result["warnings"].append(f"Unknown repair type: {repair_action['repair_type']}")
            validation_result["integrity_score"] -= 0.3
        
        # Check for recent repairs to same module
        module_name = repair_action['module_name']
        recent_repairs = [r for r in self.repair_history 
                         if r['module'] == module_name and time.time() - r['timestamp'] < 300]
        
        if len(recent_repairs) > 2:
            validation_result["warnings"].append(f"Multiple recent repairs to same module: {len(recent_repairs)} in last 5 minutes")
            validation_result["integrity_score"] -= 0.2
        
        # Check for repair loops (same repair type repeatedly)
        if len(recent_repairs) >= 2:
            repair_types = [r.get('repair_type') for r in recent_repairs]
            if repair_action['repair_type'] in repair_types:
                validation_result["warnings"].append(f"Potential repair loop detected: {repair_action['repair_type']} repeated")
                validation_result["integrity_score"] -= 0.4
        
        # Update final validity based on integrity score
        if validation_result["integrity_score"] < 0.6:
            validation_result["valid"] = False
        
        # Ensure integrity score is in valid range
        validation_result["integrity_score"] = max(0.0, min(1.0, validation_result["integrity_score"]))
        
        return validation_result
    
    def start(self) -> bool:
        """
        Start the self-repair monitoring system.
        
        Returns:
            bool: Success status
        """
        if self.is_active:
            logger.warning("Self-repair system already active")
            return False
        
        self.is_active = True
        self.scan_thread = threading.Thread(target=self._monitoring_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        
        logger.info("Self-repair system activated")
        return True
    
    def stop(self) -> bool:
        """
        Stop the self-repair monitoring system.
        
        Returns:
            bool: Success status
        """
        if not self.is_active:
            logger.warning("Self-repair system not active")
            return False
        
        self.is_active = False
        if self.scan_thread:
            self.scan_thread.join(timeout=2.0)
        
        logger.info("Self-repair system deactivated")
        return True
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get current system health assessment.
        
        Returns:
            dict: System health metrics
        """
        # Get system state from inspector
        try:
            system_state = self.inspector.get_health_status()
        except Exception as e:
            logger.error(f"Failed to get system state: {e}")
            system_state = {}
        
        # Calculate health metrics
        with self._lock:
            repair_count = self._health_metrics["repairs_count"]
            success_count = self._health_metrics["successful_repairs"]
            failed_count = self._health_metrics["failed_repairs"]
        
        recent_repairs = sum(1 for r in self.repair_history 
                            if time.time() - r['timestamp'] < 300)
        
        # Calculate stability score (0.0-1.0)
        stability = 1.0
        if repair_count > 0:
            # More repairs = lower stability
            stability -= min(0.5, recent_repairs * 0.1)
            
            # Failed repairs = lower stability
            stability -= min(0.3, failed_count * 0.05)
        
        # Adjust based on system metrics
        if system_state:
            if 'anomalies_detected' in system_state:
                stability -= min(0.2, system_state['anomalies_detected'] * 0.02)
            if 'chain_breaches' in system_state:
                stability -= min(0.3, system_state['chain_breaches'] * 0.05)
        
        # Ensure stability is in valid range
        stability = max(0.0, min(1.0, stability))
        
        return {
            'stability_score': stability,
            'repair_count_total': repair_count,
            'repair_count_recent': recent_repairs,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': success_count / max(1, repair_count),
            'last_repair_time': self.last_repair_time,
            'repair_in_progress': self.repair_in_progress,
            'anomaly_count': len(self.anomaly_registry),
            'fallback_level': self.current_fallback_level,
            'timestamp': datetime.utcnow().isoformat(),
            'health_metrics': self._health_metrics
        }
    
    def repair_module(self, module_name: str, repair_type: str = None, 
                     force: bool = False) -> Dict[str, Any]:
        """
        Trigger repair for a specific module.
        
        Args:
            module_name: Name of module to repair
            repair_type: Specific repair strategy to use
            force: Whether to force repair regardless of cooldown
            
        Returns:
            dict: Repair results
        """
        start_time = time.time()
        
        try:
            # Validate through interface contract
            repair_request = {
                "module_name": module_name,
                "request_id": hashlib.md5(f"{module_name}_{time.time()}".encode()).hexdigest()
            }
            if repair_type:
                repair_request["repair_type"] = repair_type
                
            self.interface_contract(repair_request)
            
            if self.repair_in_progress and not force:
                logger.warning(f"Cannot repair {module_name}: another repair in progress")
                return {'success': False, 'reason': 'repair_in_progress'}
            
            # Check cooldown period
            if not force and time.time() - self.last_repair_time < self.repair_cooldown:
                logger.warning(f"Cannot repair {module_name}: in cooldown period")
                return {'success': False, 'reason': 'cooldown_period'}
            
            # Get module state
            try:
                module_state = self.inspector.inspect_module(module_name)
            except Exception as e:
                logger.error(f"Failed to inspect module {module_name}: {e}")
                module_state = None
                
            if not module_state:
                logger.error(f"Cannot repair {module_name}: module not found or inspection failed")
                return {'success': False, 'reason': 'module_not_found'}
            
            # Detect anomalies if not specified
            anomalies = self._detect_anomalies(module_state)
            if not anomalies and not force:
                logger.info(f"No anomalies detected in {module_name}")
                return {'success': True, 'reason': 'no_anomalies_detected'}
            
            # Apply cognitive energy flow
            if not repair_type:
                repair_type = self._select_repair_strategy(module_name, anomalies)
                
            energy_data = self.cognitive_energy_flow(repair_type, module_name, anomalies)
            
            # Create repair action
            repair_action = {
                'module_name': module_name,
                'repair_type': repair_type,
                'anomalies': anomalies,
                'energy_data': energy_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Validate through resonance chain
            validation_result = self.resonance_chain_validator(repair_action)
            if not validation_result["valid"] and not force:
                logger.warning(f"Repair validation failed for {module_name}: {validation_result['warnings']}")
                return {'success': False, 'reason': 'validation_failed', 'validation': validation_result}
            
            # Perform repair
            self.repair_in_progress = True
            repair_result = self._execute_repair(module_name, anomalies, repair_type)
            self.repair_in_progress = False
            
            # Record repair attempt
            self.last_repair_time = time.time()
            repair_record = {
                'module': module_name,
                'anomalies': anomalies,
                'repair_type': repair_result.get('repair_type', repair_type),
                'success': repair_result.get('success', False),
                'timestamp': self.last_repair_time,
                'validation': validation_result
            }
            self.repair_history.append(repair_record)
            
            # Update metrics
            with self._lock:
                self._health_metrics["repairs_count"] += 1
                processing_time = time.time() - start_time
                self._health_metrics["avg_repair_time"] = 0.9 * self._health_metrics["avg_repair_time"] + 0.1 * processing_time
                
                if repair_result.get('success', False):
                    self._health_metrics["successful_repairs"] += 1
                else:
                    self._health_metrics["failed_repairs"] += 1
            
            # Log result
            if repair_result.get('success'):
                logger.info(f"Successfully repaired {module_name} using {repair_type}")
            else:
                logger.warning(f"Failed to repair {module_name}: {repair_result.get('reason')}")
            
            return repair_result
            
        except Exception as e:
            logger.error(f"Error in repair_module: {e}")
            context = {
                "module_name": module_name,
                "repair_type": repair_type
            }
            return self.graceful_fallback(e, context)
    
    def register_anomaly(self, module_name: str, anomaly_type: str, details: Dict[str, Any] = None) -> str:
        """
        Register an anomaly for tracking and repair.
        
        Args:
            module_name: Name of affected module
            anomaly_type: Type of anomaly
            details: Additional anomaly details
            
        Returns:
            str: Anomaly ID
        """
        anomaly_id = f"anomaly-{int(time.time())}-{hash(module_name) % 10000}"
        
        anomaly = {
            'id': anomaly_id,
            'module': module_name,
            'type': anomaly_type,
            'details': details or {},
            'timestamp': time.time(),
            'status': 'registered'
        }
        
        self.anomaly_registry[anomaly_id] = anomaly
        
        with self._lock:
            self._health_metrics["anomalies_detected"] += 1
            
        logger.info(f"Registered anomaly {anomaly_id} in {module_name}: {anomaly_type}")
        
        return anomaly_id
    
    def get_repair_history(self, limit: int = 10, module_name: str = None) -> List[Dict[str, Any]]:
        """
        Get recent repair history.
        
        Args:
            limit: Maximum number of history entries to return
            module_name: Optional module name to filter by
            
        Returns:
            list: Recent repair history
        """
        if module_name:
            filtered_history = [r for r in self.repair_history if r['module'] == module_name]
            return filtered_history[-limit:]
        else:
            return list(self.repair_history)[-limit:]
    
    def get_anomaly_registry(self, status: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Get anomaly registry.
        
        Args:
            status: Optional status to filter by
            
        Returns:
            dict: Anomaly registry
        """
        if status:
            return {k: v for k, v in self.anomaly_registry.items() if v['status'] == status}
        else:
            return self.anomaly_registry.copy()
    
    def _monitoring_loop(self) -> None:
        """Background thread for continuous system monitoring."""
        logger.info("Monitoring loop started")
        
        while self.is_active:
            try:
                # Self-regulation
                self.self_regulate()
                
                # Sync with global clock
                self.sync_clock()
                
                # Get system state
                try:
                    system_state = self.inspector.get_health_status()
                except Exception as e:
                    logger.error(f"Failed to get system state: {e}")
                    system_state = {}
                    
                if not system_state:
                    logger.warning("Could not retrieve system state")
                    time.sleep(self.scan_interval)
                    continue
                
                # Scan for anomalies across all modules
                try:
                    modules = self.inspector.list_modules()
                except Exception as e:
                    logger.error(f"Failed to list modules: {e}")
                    modules = []
                    
                for module_name in modules:
                    # Skip if we're in cooldown period
                    if time.time() - self.last_repair_time < self.repair_cooldown:
                        continue
                    
                    # Skip if repair already in progress
                    if self.repair_in_progress:
                        continue
                    
                    # Skip based on fallback level
                    if self.current_fallback_level != "normal":
                        # In conservative mode, only check critical modules
                        if self.current_fallback_level == "conservative":
                            if not self._is_critical_module(module_name):
                                continue
                        # In minimal mode, only check essential modules
                        elif self.current_fallback_level == "minimal":
                            if not self._is_essential_module(module_name):
                                continue
                        # In emergency mode, only check core modules
                        elif self.current_fallback_level == "emergency":
                            if not self._is_core_module(module_name):
                                continue
                    
                    # Inspect module
                    try:
                        module_state = self.inspector.inspect_module(module_name)
                    except Exception as e:
                        logger.error(f"Failed to inspect module {module_name}: {e}")
                        continue
                        
                    if not module_state:
                        continue
                    
                    # Detect anomalies
                    anomalies = self._detect_anomalies(module_state)
                    if not anomalies:
                        continue
                    
                    # Calculate anomaly severity
                    severity = self._calculate_anomaly_severity(anomalies)
                    
                    # If severity exceeds threshold, attempt repair
                    if severity >= self.repair_threshold:
                        logger.info(f"Anomaly detected in {module_name}, severity: {severity:.2f}")
                        self.repair_module(module_name)
                
                # Sleep until next scan
                time.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(max(1.0, self.scan_interval / 2))
        
        logger.info("Monitoring loop stopped")
    
    def _init_repair_strategies(self) -> None:
        """Initialize repair strategies registry."""
        self.repair_strategies = {
            'restart': self._repair_by_restart,
            'reinitialize': self._repair_by_reinitialize,
            'reconfigure': self._repair_by_reconfigure,
            'clear_cache': self._repair_by_clear_cache,
            'restore_defaults': self._repair_by_restore_defaults,
            'partial_reset': self._repair_by_partial_reset,
            'adaptive_rebalance': self._repair_by_adaptive_rebalance,
            'emergency_stabilize': self._repair_by_emergency_stabilize
        }
    
    def _detect_anomalies(self, module_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect anomalies in module state.
        
        Args:
            module_state: Module state data
            
        Returns:
            list: Detected anomalies
        """
        anomalies = []
        
        # Skip if no state data
        if not module_state:
            return anomalies
        
        # Check for common anomalies
        if 'error_count' in module_state and module_state['error_count'] > 5:
            anomalies.append({
                'type': 'high_error_rate',
                'value': module_state['error_count'],
                'threshold': 5
            })
        
        if 'response_time' in module_state and module_state['response_time'] > 1000:
            anomalies.append({
                'type': 'slow_response',
                'value': module_state['response_time'],
                'threshold': 1000
            })
        
        if 'memory_usage' in module_state and module_state['memory_usage'] > 0.9:
            anomalies.append({
                'type': 'high_memory_usage',
                'value': module_state['memory_usage'],
                'threshold': 0.9
            })
        
        if 'stability_score' in module_state and module_state['stability_score'] < 0.5:
            anomalies.append({
                'type': 'low_stability',
                'value': module_state['stability_score'],
                'threshold': 0.5
            })
        
        if 'chain_breaches' in module_state and module_state['chain_breaches'] > 0:
            anomalies.append({
                'type': 'chain_breach',
                'value': module_state['chain_breaches'],
                'threshold': 0
            })
        
        if 'health_score' in module_state and module_state['health_score'] < 0.7:
            anomalies.append({
                'type': 'poor_health',
                'value': module_state['health_score'],
                'threshold': 0.7
            })
        
        return anomalies
    
    def _calculate_anomaly_severity(self, anomalies: List[Dict[str, Any]]) -> float:
        """
        Calculate overall severity of anomalies.
        
        Args:
            anomalies: List of detected anomalies
            
        Returns:
            float: Severity score (0.0-1.0)
        """
        if not anomalies:
            return 0.0
        
        # Severity weights by anomaly type
        severity_weights = {
            'high_error_rate': 0.7,
            'slow_response': 0.5,
            'high_memory_usage': 0.6,
            'low_stability': 0.8,
            'chain_breach': 0.9,
            'poor_health': 0.7,
            'default': 0.5
        }
        
        # Calculate weighted severity
        total_weight = 0.0
        total_severity = 0.0
        
        for anomaly in anomalies:
            anomaly_type = anomaly['type']
            weight = severity_weights.get(anomaly_type, severity_weights['default'])
            
            # Calculate normalized severity for this anomaly
            if 'value' in anomaly and 'threshold' in anomaly:
                # For numeric anomalies, calculate how far beyond threshold
                value = anomaly['value']
                threshold = anomaly['threshold']
                
                if threshold > value:  # Lower is worse (e.g., health score)
                    severity = 1.0 - (value / threshold)
                else:  # Higher is worse (e.g., error count)
                    severity = min(1.0, value / (threshold * 2))
            else:
                # Default severity if no value/threshold
                severity = 0.5
            
            total_severity += weight * severity
            total_weight += weight
        
        # Normalize to 0.0-1.0
        if total_weight > 0:
            return total_severity / total_weight
        else:
            return 0.0
    
    def _select_repair_strategy(self, module_name: str, anomalies: List[Dict[str, Any]]) -> str:
        """
        Select appropriate repair strategy based on anomalies.
        
        Args:
            module_name: Module to repair
            anomalies: Detected anomalies
            
        Returns:
            str: Selected repair strategy
        """
        # Default strategy
        strategy = 'restart'
        
        # Check for specific anomaly types
        anomaly_types = [a['type'] for a in anomalies]
        
        if 'chain_breach' in anomaly_types:
            strategy = 'adaptive_rebalance'
        elif 'high_memory_usage' in anomaly_types:
            strategy = 'clear_cache'
        elif 'low_stability' in anomaly_types:
            strategy = 'reinitialize'
        elif 'poor_health' in anomaly_types:
            strategy = 'restore_defaults'
        elif 'slow_response' in anomaly_types:
            strategy = 'partial_reset'
        
        # Check fallback level
        if self.current_fallback_level == "emergency":
            strategy = 'emergency_stabilize'
        
        logger.info(f"Selected repair strategy for {module_name}: {strategy}")
        return strategy
    
    def _execute_repair(self, module_name: str, anomalies: List[Dict[str, Any]], 
                       repair_type: str = None) -> Dict[str, Any]:
        """
        Execute repair operation.
        
        Args:
            module_name: Module to repair
            anomalies: Detected anomalies
            repair_type: Repair strategy to use
            
        Returns:
            dict: Repair results
        """
        if not repair_type:
            repair_type = self._select_repair_strategy(module_name, anomalies)
        
        # Get repair function
        repair_func = self.repair_strategies.get(repair_type)
        if not repair_func:
            logger.error(f"Unknown repair type: {repair_type}")
            return {'success': False, 'reason': 'unknown_repair_type'}
        
        # Execute repair
        try:
            logger.info(f"Executing {repair_type} repair on {module_name}")
            result = repair_func(module_name, anomalies)
            result['repair_type'] = repair_type
            return result
        except Exception as e:
            logger.error(f"Error executing {repair_type} repair on {module_name}: {e}")
            return {
                'success': False,
                'repair_type': repair_type,
                'reason': f'repair_error: {str(e)}'
            }
    
    def _repair_by_restart(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Repair by restarting the module."""
        logger.info(f"Restarting module: {module_name}")
        # Simulate restart
        time.sleep(0.5)
        return {'success': True, 'action': 'restart'}
    
    def _repair_by_reinitialize(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Repair by reinitializing the module."""
        logger.info(f"Reinitializing module: {module_name}")
        # Simulate reinitialization
        time.sleep(1.0)
        return {'success': True, 'action': 'reinitialize'}
    
    def _repair_by_reconfigure(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Repair by reconfiguring the module."""
        logger.info(f"Reconfiguring module: {module_name}")
        # Simulate reconfiguration
        time.sleep(0.8)
        return {'success': True, 'action': 'reconfigure'}
    
    def _repair_by_clear_cache(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Repair by clearing module cache."""
        logger.info(f"Clearing cache for module: {module_name}")
        # Simulate cache clearing
        time.sleep(0.3)
        return {'success': True, 'action': 'clear_cache'}
    
    def _repair_by_restore_defaults(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Repair by restoring default settings."""
        logger.info(f"Restoring defaults for module: {module_name}")
        # Simulate defaults restoration
        time.sleep(1.2)
        return {'success': True, 'action': 'restore_defaults'}
    
    def _repair_by_partial_reset(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Repair by partial reset of problematic components."""
        logger.info(f"Partial reset for module: {module_name}")
        # Simulate partial reset
        time.sleep(0.7)
        return {'success': True, 'action': 'partial_reset'}
    
    def _repair_by_adaptive_rebalance(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Repair by adaptively rebalancing module parameters."""
        logger.info(f"Adaptive rebalancing for module: {module_name}")
        # Simulate adaptive rebalancing
        time.sleep(1.5)
        return {'success': True, 'action': 'adaptive_rebalance'}
    
    def _repair_by_emergency_stabilize(self, module_name: str, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Emergency stabilization for critical modules."""
        logger.info(f"Emergency stabilization for module: {module_name}")
        # Simulate emergency stabilization
        time.sleep(0.5)
        return {'success': True, 'action': 'emergency_stabilize'}
    
    def _get_alternative_repair(self, repair_type: str) -> str:
        """Get alternative repair strategy if primary fails."""
        alternatives = {
            'restart': 'partial_reset',
            'reinitialize': 'restore_defaults',
            'reconfigure': 'adaptive_rebalance',
            'clear_cache': 'restart',
            'restore_defaults': 'reinitialize',
            'partial_reset': 'clear_cache',
            'adaptive_rebalance': 'reconfigure',
            'emergency_stabilize': 'restart'
        }
        return alternatives.get(repair_type, 'restart')
    
    def _get_module_criticality(self, module_name: str) -> float:
        """
        Get criticality score for a module.
        
        Args:
            module_name: Module name
            
        Returns:
            float: Criticality score (0.0-1.0)
        """
        # Core modules have highest criticality
        if self._is_core_module(module_name):
            return 1.0
        
        # Essential modules have high criticality
        if self._is_essential_module(module_name):
            return 0.8
        
        # Critical modules have medium-high criticality
        if self._is_critical_module(module_name):
            return 0.6
        
        # Default criticality
        return 0.4
    
    def _is_core_module(self, module_name: str) -> bool:
        """Check if module is a core module."""
        core_modules = [
            'neuroengine',
            'global_sync_manager',
            'neural_fabric',
            'cortex_core_hooks'
        ]
        return module_name in core_modules
    
    def _is_essential_module(self, module_name: str) -> bool:
        """Check if module is an essential module."""
        essential_modules = [
            'neuroengine',
            'global_sync_manager',
            'neural_fabric',
            'cortex_core_hooks',
            'resonance_field',
            'phase_harmonics',
            'cortex_vectorizer',
            'neural_gatekeeper',
            'context_engine'
        ]
        return module_name in essential_modules
    
    def _is_critical_module(self, module_name: str) -> bool:
        """Check if module is a critical module."""
        critical_modules = [
            'neuroengine',
            'global_sync_manager',
            'neural_fabric',
            'cortex_core_hooks',
            'resonance_field',
            'phase_harmonics',
            'cortex_vectorizer',
            'neural_gatekeeper',
            'context_engine',
            'swarm_resonance',
            'resonance_reinforcer',
            'topk_sparse_resonance',
            'chord_resonator',
            'knowledge_reinforcer',
            'memory_inserter',
            'cortex_cube_nvme',
            'data_ingestor',
            'trust_filter'
        ]
        return module_name in critical_modules
    
    def _escalate_fallback_level(self) -> None:
        """Escalate to more conservative fallback level."""
        current_index = self.fallback_levels.index(self.current_fallback_level)
        if current_index < len(self.fallback_levels) - 1:
            self.current_fallback_level = self.fallback_levels[current_index + 1]
            logger.warning(f"Escalated fallback level to: {self.current_fallback_level}")
    
    def _deescalate_fallback_level(self) -> None:
        """De-escalate to less conservative fallback level."""
        current_index = self.fallback_levels.index(self.current_fallback_level)
        if current_index > 0:
            self.current_fallback_level = self.fallback_levels[current_index - 1]
            logger.info(f"De-escalated fallback level to: {self.current_fallback_level}")
    
    def _create_minimal_inspector(self):
        """Create minimal inspector when real one is not available."""
        class MinimalInspector:
            def get_health_status(self):
                return {"status": "unknown", "health_score": 0.5}
                
            def inspect_module(self, module_name):
                return {"module": module_name, "status": "unknown"}
                
            def list_modules(self):
                return ["neuroengine", "global_sync_manager"]
                
            def get_system_state(self):
                return {"status": "unknown"}
                
        return MinimalInspector()
    
    def _load_repair_history(self) -> None:
        """Load repair history from file."""
        try:
            if os.path.exists(self.repair_log_file):
                with open(self.repair_log_file, 'r') as f:
                    history = json.load(f)
                    # Convert to deque
                    self.repair_history = deque(history, maxlen=100)
                    logger.info(f"Loaded {len(self.repair_history)} repair history entries")
        except Exception as e:
            logger.warning(f"Failed to load repair history: {e}")
    
    def _save_repair_history(self) -> bool:
        """Save repair history to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.repair_log_file)), exist_ok=True)
            
            with open(self.repair_log_file, 'w') as f:
                # Convert deque to list for serialization
                json.dump(list(self.repair_history), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save repair history: {e}")
            return False
    
    def _start_monitor_thread(self) -> None:
        """Start the monitoring thread."""
        def monitor_loop():
            while True:
                try:
                    # Perform self-regulation
                    self.self_regulate()
                    
                    # Sync with global clock
                    self.sync_clock()
                except Exception as e:
                    logger.error(f"Error in monitor thread: {e}")
                    
                # Sleep before next check
                time.sleep(10)
                
        # Start the monitoring thread
        threading.Thread(target=monitor_loop, daemon=True).start()
        logger.info("Self repair monitoring thread started")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status of the self repair module.
        
        Returns:
            Dict containing health status metrics
        """
        with self._lock:
            metrics = self._health_metrics.copy()
            
        # Add additional status information
        status = {
            **metrics,
            "repair_threshold": self.repair_threshold,
            "repair_cooldown": self.repair_cooldown,
            "scan_interval": self.scan_interval,
            "fallback_level": self.current_fallback_level,
            "repair_energy_budget": self.repair_energy_budget,
            "repair_history_size": len(self.repair_history),
            "anomaly_registry_size": len(self.anomaly_registry),
            "is_active": self.is_active,
            "repair_in_progress": self.repair_in_progress,
            "last_sync": self._last_sync.isoformat()
        }
        
        return status
