"""
SelfRepair module for CortexOS.
Provides fault healing and rebalancing capabilities.
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

class SelfRepair(AgharmonicCompliant):
    """
    Provides autonomous healing and rebalancing for the neural architecture.
    Implements all seven Agharmonic Law interfaces for full compliance.
    """
    
    def __init__(self, global_sync_manager=None, cortex_inspector=None):
        # Core repair parameters
        self.repair_frequency = 0.1  # Hz
        self.repair_priority_threshold = 0.7
        self.repair_timeout = 5.0
        self.last_repair_time = time.time()
        self.repair_history = []
        self.max_history_size = 100
        self.repair_queue = []
        
        # External components
        self.cortex_inspector = cortex_inspector
        
        # Agharmonic Law compliance components
        self.global_sync_manager = global_sync_manager
        self.frequency_range = [0.05, 0.2]  # Default frequency range
        self.phase_alignment = 0.2  # Default phase alignment
        self.resonance_threshold = 0.6  # Default resonance threshold
        self.last_sync_time = time.time()
        self.sync_interval = 120  # Default sync interval in seconds
        self.health_metrics = {
            "repairs_performed": 0,
            "repairs_failed": 0,
            "repairs_pending": 0,
            "last_health_check": time.time()
        }
        self.fallback_level = 0
        self.validation_lock = threading.RLock()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing SelfRepair module")
        
        # Start monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Monitor thread started")
        self.logger.info("SelfRepair module initialized successfully")
        
    def _monitoring_loop(self):
        """Background thread for processing repair queue."""
        while self.monitoring_active:
            try:
                # Process repair queue
                if self.repair_queue:
                    with self.validation_lock:
                        repair_item = self.repair_queue.pop(0)
                        self._perform_repair(repair_item)
                        
                # Perform self-regulation
                if time.time() - self.health_metrics["last_health_check"] > 300:  # 5 minutes
                    self.self_regulate()
                    
                # Sleep to avoid CPU overuse
                time.sleep(1.0 / self.repair_frequency)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                # Use graceful fallback
                self.graceful_fallback(e, {"context": "monitoring_loop"})
                time.sleep(5.0)  # Longer sleep after error
                
    def _perform_repair(self, repair_item):
        """
        Perform a repair operation.
        
        Args:
            repair_item (dict): Repair item to process
        """
        # Extract repair information
        target = repair_item.get("target", "unknown")
        issue = repair_item.get("issue", "unknown")
        priority = repair_item.get("priority", 0.5)
        
        self.logger.info(f"Performing repair on {target}: {issue} (priority: {priority})")
        
        # Simulate repair process
        success = np.random.random() > 0.1  # 90% success rate
        
        # Record repair
        repair_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "target": target,
            "issue": issue,
            "priority": priority,
            "success": success,
            "duration": np.random.uniform(0.1, 2.0)
        }
        
        # Update metrics
        if success:
            self.health_metrics["repairs_performed"] += 1
        else:
            self.health_metrics["repairs_failed"] += 1
            
        # Add to history
        self.repair_history.append(repair_result)
        
        # Trim history if needed
        if len(self.repair_history) > self.max_history_size:
            self.repair_history = self.repair_history[-self.max_history_size:]
            
        return repair_result
        
    def queue_repair(self, target, issue, priority=0.5):
        """
        Queue a repair operation.
        
        Args:
            target (str): Target to repair
            issue (str): Issue to repair
            priority (float): Repair priority (0-1)
            
        Returns:
            dict: Queuing result
        """
        # Validate inputs
        if not target or not issue:
            return {"status": "error", "message": "Invalid repair request"}
            
        # Create repair item
        repair_item = {
            "timestamp": datetime.utcnow().isoformat(),
            "target": target,
            "issue": issue,
            "priority": priority
        }
        
        # Add to queue
        with self.validation_lock:
            # Sort queue by priority
            self.repair_queue.append(repair_item)
            self.repair_queue.sort(key=lambda x: x["priority"], reverse=True)
            self.health_metrics["repairs_pending"] = len(self.repair_queue)
            
        return {
            "status": "queued",
            "position": len(self.repair_queue),
            "estimated_time": len(self.repair_queue) / self.repair_frequency
        }
        
    def get_repair_status(self):
        """
        Get repair system status.
        
        Returns:
            dict: Repair system status
        """
        return {
            "queue_length": len(self.repair_queue),
            "repairs_performed": self.health_metrics["repairs_performed"],
            "repairs_failed": self.health_metrics["repairs_failed"],
            "success_rate": self.health_metrics["repairs_performed"] / max(1, self.health_metrics["repairs_performed"] + self.health_metrics["repairs_failed"]),
            "status": "active" if self.monitoring_active else "inactive"
        }
        
    # === Agharmonic Law Compliance Methods ===
    
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for repair operations.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "self_repair",
            "rhythm_hz": self.repair_frequency,
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
            "queue_repair": ["target", "issue"],
            "get_repair_status": [],
            "get_repair_history": ["limit"]
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
            
        # Block recursive self-repair
        if operation == "queue_repair" and payload.get("target") == "self_repair":
            return {
                "status": "invalid_operation",
                "message": "Recursive self-repair not allowed"
            }
            
        return True
        
    def cognitive_energy_flow(self, repair_target=None):
        """
        Normalizes repair priority and energy allocation.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            repair_target (dict, optional): Target to repair
            
        Returns:
            dict: Normalized repair parameters
        """
        # If no target specified, return current energy flow parameters
        if repair_target is None:
            return {
                "repair_frequency": self.repair_frequency,
                "repair_priority_threshold": self.repair_priority_threshold,
                "energy_budget": 1.0
            }
            
        # Extract target priority if available
        target_priority = repair_target.get("priority", 0.5)
        
        # Normalize repair parameters based on priority
        normalized_params = {
            "repair_timeout": self.repair_timeout * (1.0 + target_priority),
            "repair_depth": int(3 * target_priority) + 1,
            "energy_allocation": min(1.0, target_priority * 1.5)
        }
        
        return normalized_params
        
    def sync_clock(self, global_sync_manager=None):
        """
        Aligns with GlobalSyncManager for coordinated repair scheduling.
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
                
                # Update repair parameters
                if "repair" in sync_policy:
                    repair_policy = sync_policy["repair"]
                    self.repair_frequency = repair_policy.get("frequency", self.repair_frequency)
                    self.repair_priority_threshold = repair_policy.get("priority_threshold", self.repair_priority_threshold)
                    self.repair_timeout = repair_policy.get("timeout", self.repair_timeout)
                    
                # Update sync interval
                self.sync_interval = sync_policy.get("repair_sync_interval", 120)
                    
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
        Implements priority-based repair scheduling and queue management.
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
            # Check for excessive failed repairs
            if self.health_metrics["repairs_failed"] > 5:
                self.logger.warning(f"High repair failure count: {self.health_metrics['repairs_failed']}")
                regulation_actions.append("increase_repair_timeout")
                
                # Increase repair timeout to allow more time for complex repairs
                self.repair_timeout = min(10.0, self.repair_timeout * 1.5)
                fallback_level = 1
                
            # Check for queue overload
            if len(self.repair_queue) > 10:
                self.logger.warning(f"Repair queue overloaded: {len(self.repair_queue)} items")
                regulation_actions.append("increase_repair_frequency")
                
                # Increase repair frequency to process queue faster
                self.repair_frequency = min(0.5, self.repair_frequency * 1.5)
                fallback_level = 1
                
            # Check for idle repair system
            if self.health_metrics["repairs_performed"] == 0 and len(self.repair_queue) == 0:
                self.logger.info("Repair system idle, performing system scan")
                regulation_actions.append("system_scan")
                
                # Queue a system scan if cortex_inspector is available
                if self.cortex_inspector:
                    try:
                        system_health = self.cortex_inspector.get_system_health()
                        if system_health["overall_health"] < 0.9:
                            self.queue_repair("system", "preventive_maintenance", 0.3)
                    except Exception as e:
                        self.logger.warning(f"Failed to perform system scan: {e}")
                
            # Update last health check time
            self.health_metrics["last_health_check"] = current_time
            
        # Set fallback level based on failure rate if not already set
        if fallback_level == 0:
            total_repairs = self.health_metrics["repairs_performed"] + self.health_metrics["repairs_failed"]
            if total_repairs > 0:
                failure_rate = self.health_metrics["repairs_failed"] / total_repairs
                if failure_rate > 0.3:
                    fallback_level = 2
                elif failure_rate > 0.1:
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
        Provides multi-stage repair strategies with priority-based scheduling.
        Required for Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error: Error object or string triggering fallback
            context (dict, optional): Error context information
            
        Returns:
            dict: Fallback status and actions taken
        """
        error_type = str(error) if not isinstance(error, str) else error
        self.health_metrics["repairs_failed"] += 1
        
        # Determine fallback action based on error type
        fallback_action = "monitor"
        
        if "timeout" in error_type.lower():
            fallback_action = "retry_with_extended_timeout"
        elif "permission" in error_type.lower():
            fallback_action = "escalate_privileges"
        elif "resource" in error_type.lower():
            fallback_action = "reduce_resource_usage"
        elif "connection" in error_type.lower():
            fallback_action = "retry_with_backoff"
            
        # Create fallback response
        fallback_response = {
            "target": context.get("target", "unknown") if context else "unknown",
            "repair_type": context.get("type", "unknown") if context else "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "fallback",
            "error": error_type,
            "fallback_action": fallback_action,
            "fallback_level": self.fallback_level + 1
        }
        
        # Log the fallback
        self.logger.warning(f"Fallback triggered: {error_type}")
        
        return fallback_response
        
    def resonance_chain_validator(self, result=None):
        """
        Verifies repair operations maintain resonance integrity.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            result (dict, optional): Result to validate
            
        Returns:
            bool or dict: True/valid status if result maintains resonance integrity
        """
        # If no result provided, return validation capabilities
        if result is None:
            return {
                "valid": True,
                "message": "Test validation successful",
                "validator_type": "self_repair"
            }
            
        # Validate result structure
        if not isinstance(result, dict):
            return {
                "valid": False,
                "message": "Result must be a dictionary",
                "validator_type": "self_repair"
            }
            
        # Check for required fields based on result type
        if "target" in result and "success" in result:
            # Repair result
            required_fields = ["target", "issue", "success", "timestamp"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                return {
                    "valid": False,
                    "message": f"Missing required fields: {missing_fields}",
                    "validator_type": "self_repair"
                }
                
        elif "queue_length" in result:
            # Status result
            required_fields = ["queue_length", "repairs_performed", "repairs_failed"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                return {
                    "valid": False,
                    "message": f"Missing required fields: {missing_fields}",
                    "validator_type": "self_repair"
                }
                
        else:
            # Unknown result type
            return {
                "valid": False,
                "message": "Unknown result type",
                "validator_type": "self_repair"
            }
            
        # All validations passed
        return {
            "valid": True,
            "message": "Result is valid",
            "validator_type": "self_repair"
        }
