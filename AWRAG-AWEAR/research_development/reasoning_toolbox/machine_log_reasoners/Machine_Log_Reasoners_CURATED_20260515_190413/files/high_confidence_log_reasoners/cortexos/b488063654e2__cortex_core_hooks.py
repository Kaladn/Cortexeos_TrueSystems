"""
Cortex Core Hooks module for CortexOS.
Provides low-level hooks for neural operations and monitoring.

This module implements the Agharmonic Law by providing:
- Harmonic Resonance through verified module linkage
- Cognitive Isolation with well-defined hook interfaces
- Balanced Information Flow through operation throttling
- Temporal Synchronization with the Global Sync Manager
- Self-Regulation through auto-lockout and alerts
- Graceful Degradation with failover mechanisms
- Resonance Chain Integrity through master validation
"""

import logging
import time
import threading
import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Callable

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CortexCoreHooks:
    """
    Provides low-level hooks for neural operations and monitoring.
    Implements all seven Agharmonic Law interfaces for full compliance.
    Acts as interceptor and failover bridge for the neural architecture.
    """
    def __init__(self, global_sync_manager=None, security_level="high"):
        # Global tracking for neural operations
        self._operation_log = []
        self._chain_log = []
        self._voxel_operations = {}
        self._last_flush_time = time.time()
        self._verified_modules = {}
        self._blocked_modules = {}
        self._alert_callbacks = []
        self._lock = threading.Lock()
        self._last_sync = datetime.utcnow()
        self._global_sync_manager = global_sync_manager
        self._security_level = security_level
        self._health_metrics = {
            "operations_count": 0,
            "chain_events": 0,
            "blocked_operations": 0,
            "alerts_triggered": 0,
            "last_error": None
        }
        
        # Agharmonic Law compliance parameters
        self.operation_threshold = 1000
        self.chain_threshold = 500
        self.alert_threshold = 10
        self.auto_lockout_enabled = (security_level == "high")
        
        # Start monitoring thread
        self._start_monitor_thread()
        
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility parameters for this module.
        Hardened to ensure only verified modules link into core.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "module": "cortex_core_hooks",
            "rhythm_hz": 1.0,  # 1 second per cycle
            "input_range": (0.5, 2.0),  # in Hz
            "output_phase": 0.0,
            "threshold": 0.95,  # High threshold for core components
            "security_level": self._security_level,
            "auto_lockout": self.auto_lockout_enabled,
            "verification_required": True
        }
    
    def interface_contract(self, module_id: str, operation_type: str) -> bool:
        """
        Defines allowed function calls and verifies module access rights.
        
        Args:
            module_id: Identifier of the calling module
            operation_type: Type of operation requested
            
        Returns:
            True if module meets the interface contract
            
        Raises:
            ValueError: If module doesn't meet the interface contract
        """
        if not module_id:
            raise ValueError("Module ID cannot be empty")
            
        # Check if module is blocked
        if module_id in self._blocked_modules:
            block_info = self._blocked_modules[module_id]
            logger.warning(f"Blocked module {module_id} attempted {operation_type} operation. "
                          f"Blocked since: {block_info['timestamp']}, "
                          f"Reason: {block_info['reason']}")
            raise ValueError(f"Module {module_id} is blocked: {block_info['reason']}")
            
        # Check if module is verified
        if module_id not in self._verified_modules:
            # Auto-verify on first use if security level is not high
            if self._security_level != "high":
                self.verify_module(module_id, {"auto_verified": True})
            else:
                raise ValueError(f"Module {module_id} is not verified")
                
        # Check operation type
        valid_operations = ["increment", "chain", "flush", "stats", "reset"]
        if operation_type not in valid_operations:
            raise ValueError(f"Invalid operation type: {operation_type}. Must be one of {valid_operations}")
            
        return True
    
    def cognitive_energy_flow(self, operation_type: str, strength: float = None) -> Dict[str, Any]:
        """
        Normalizes operation signal amplitude and throttles if needed.
        
        Args:
            operation_type: Type of operation
            strength: Operation strength if applicable
            
        Returns:
            Dict containing normalized signal data
        """
        # Base energy consumption by operation type
        energy_map = {
            "increment": 0.2,
            "chain": 0.3,
            "flush": 0.5,
            "stats": 0.1,
            "reset": 0.8
        }
        
        base_energy = energy_map.get(operation_type, 0.5)
        
        # Adjust for strength if provided
        if strength is not None:
            # Cap strength to reasonable range
            capped_strength = max(0.0, min(1.0, strength))
            energy_consumption = base_energy * (0.5 + 0.5 * capped_strength)
        else:
            energy_consumption = base_energy
            
        # Check if system is overloaded
        with self._lock:
            operation_count = len(self._operation_log)
            chain_count = len(self._chain_log)
            
        # Calculate load factor (0-1)
        load_factor = max(
            operation_count / self.operation_threshold,
            chain_count / self.chain_threshold
        ) if self.operation_threshold > 0 and self.chain_threshold > 0 else 0
        
        # Apply throttling if overloaded
        if load_factor > 0.8:
            throttle_factor = 1.0 - (load_factor - 0.8) * 5  # Linear decrease from 1.0 to 0.0
            throttle_factor = max(0.1, throttle_factor)  # Never go below 10%
            energy_consumption *= throttle_factor
            logger.warning(f"Throttling operations to {throttle_factor:.2f} due to high load")
            
        return {
            "operation_type": operation_type,
            "energy_consumption": energy_consumption,
            "load_factor": load_factor,
            "throttled": load_factor > 0.8,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def sync_clock(self, global_clock: Any = None) -> bool:
        """
        Connects to the master temporal framework.
        Synchronizes operation thresholds and security parameters.
        
        Args:
            global_clock: Optional reference to a global clock object
            
        Returns:
            True if synchronization successful, False otherwise
        """
        try:
            if global_clock:
                if hasattr(global_clock, 'get_sync_stats'):
                    stats = global_clock.get_sync_stats()
                    # Adjust thresholds based on system state
                    if stats.get('cycle_time', 5) > 5:  # System under load
                        # Under load, increase thresholds to reduce processing
                        self.operation_threshold = max(500, self.operation_threshold * 0.8)
                        self.chain_threshold = max(250, self.chain_threshold * 0.8)
                    else:  # Normal load
                        # Reset to default values
                        self.operation_threshold = 1000
                        self.chain_threshold = 500
                        
                self._last_sync = datetime.utcnow()
                return True
            elif self._global_sync_manager:
                return self.sync_clock(self._global_sync_manager)
            else:
                # No global clock, use internal timing
                self._last_sync = datetime.utcnow()
                return True
        except Exception as e:
            logger.error(f"Failed to sync with global clock: {e}")
            return False
    
    def self_regulate(self) -> Dict[str, Any]:
        """
        Implements feedback loop analysis and auto-lockout for suspicious activity.
        Provides real-time alerts for security events.
        
        Returns:
            Dict containing self-regulation metrics
        """
        with self._lock:
            operation_count = len(self._operation_log)
            chain_count = len(self._chain_log)
            voxel_count = len(self._voxel_operations)
            
        # Check for suspicious activity
        suspicious_activity = False
        suspicious_reason = None
        
        # Check for operation spikes
        if operation_count > self.operation_threshold * 1.5:
            suspicious_activity = True
            suspicious_reason = f"Operation count ({operation_count}) exceeds threshold ({self.operation_threshold * 1.5})"
            
        # Check for chain spikes
        if chain_count > self.chain_threshold * 1.5:
            suspicious_activity = True
            suspicious_reason = f"Chain count ({chain_count}) exceeds threshold ({self.chain_threshold * 1.5})"
            
        # Check for unusual voxel activity
        if voxel_count > 0:
            # Find max activation
            max_activation = max(self._voxel_operations.values()) if self._voxel_operations else 0
            if max_activation > 10.0:  # Arbitrary threshold for suspicious activation
                suspicious_activity = True
                suspicious_reason = f"Unusually high voxel activation detected: {max_activation}"
                
        # Take action if suspicious activity detected
        if suspicious_activity:
            logger.warning(f"Suspicious activity detected: {suspicious_reason}")
            
            # Trigger alerts
            self._trigger_alert({
                "type": "suspicious_activity",
                "reason": suspicious_reason,
                "timestamp": datetime.utcnow().isoformat(),
                "operation_count": operation_count,
                "chain_count": chain_count,
                "voxel_count": voxel_count
            })
            
            # Auto-lockout if enabled
            if self.auto_lockout_enabled:
                logger.warning("Auto-lockout enabled, flushing logs and resetting state")
                self.flush_operation_log()
                self.flush_chain_log()
                self.reset_voxel_operations()
                
        # Auto-flush if logs are getting large
        if operation_count > self.operation_threshold:
            logger.info(f"Auto-flushing operation log ({operation_count} entries)")
            self.flush_operation_log()
            
        if chain_count > self.chain_threshold:
            logger.info(f"Auto-flushing chain log ({chain_count} entries)")
            self.flush_chain_log()
            
        return {
            "operation_count": operation_count,
            "chain_count": chain_count,
            "voxel_count": voxel_count,
            "suspicious_activity": suspicious_activity,
            "suspicious_reason": suspicious_reason,
            "auto_lockout_enabled": self.auto_lockout_enabled,
            "last_sync": self._last_sync.isoformat(),
            "health_metrics": self._health_metrics
        }
    
    def graceful_fallback(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides failover mechanisms when core operations cannot be completed.
        
        Args:
            error: The exception that occurred
            context: Context information about the operation
            
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning(f"Executing graceful fallback: {error}")
        
        operation_type = context.get("operation_type", "unknown")
        module_id = context.get("module_id", "unknown")
        
        # Record error
        with self._lock:
            self._health_metrics["last_error"] = str(error)
            
        # Different fallback strategies based on operation type
        if operation_type == "increment":
            # For increment operations, use a default minimal increment
            voxel_id = context.get("voxel_id", "unknown")
            logger.info(f"Fallback for increment operation on voxel {voxel_id}")
            
            # Apply minimal increment to avoid breaking chains
            if voxel_id != "unknown":
                with self._lock:
                    if voxel_id not in self._voxel_operations:
                        self._voxel_operations[voxel_id] = 0.0
                    self._voxel_operations[voxel_id] += 0.1  # Minimal increment
                    
                return {
                    "status": "fallback_applied",
                    "action": "minimal_increment",
                    "voxel_id": voxel_id,
                    "new_strength": self._voxel_operations[voxel_id]
                }
                
        elif operation_type == "chain":
            # For chain operations, log a minimal entry
            logger.info("Fallback for chain operation")
            
            # Add minimal chain log entry
            with self._lock:
                self._chain_log.append({
                    "voxel_id": context.get("voxel_id", "unknown"),
                    "strength": context.get("strength", 0.1),
                    "timestamp": time.time(),
                    "fallback": True
                })
                
            return {
                "status": "fallback_applied",
                "action": "minimal_chain_log"
            }
            
        elif operation_type in ["flush", "stats", "reset"]:
            # For management operations, return empty results
            logger.info(f"Fallback for {operation_type} operation")
            
            return {
                "status": "fallback_applied",
                "action": "empty_result",
                "operation_type": operation_type
            }
            
        # Generic fallback for unknown operations
        return {
            "status": "fallback_applied",
            "action": "no_action",
            "error": str(error)
        }
    
    def resonance_chain_validator(self, module_id: str, operation_type: str, params: Dict[str, Any]) -> bool:
        """
        Master validator that watches for broken resonance loops.
        Verifies operation integrity across the resonance chain.
        
        Args:
            module_id: ID of the module performing the operation
            operation_type: Type of operation being performed
            params: Operation parameters
            
        Returns:
            True if operation is valid, False otherwise
        """
        # Verify module is allowed to perform this operation
        if module_id not in self._verified_modules:
            logger.warning(f"Unverified module {module_id} attempted {operation_type} operation")
            return False
            
        # Check operation-specific validations
        if operation_type == "increment":
            voxel_id = params.get("voxel_id")
            strength = params.get("strength")
            
            # Validate voxel_id
            if not voxel_id:
                logger.warning("Missing voxel_id for increment operation")
                return False
                
            # Validate strength is reasonable
            if strength is None or strength < 0 or strength > 5.0:
                logger.warning(f"Invalid strength for increment operation: {strength}")
                return False
                
            # Check for rapid repeated increments to same voxel (potential loop)
            with self._lock:
                recent_ops = [op for op in self._operation_log[-20:] 
                             if op.get("operation") == "increment" and op.get("voxel_id") == voxel_id]
                
            if len(recent_ops) > 10:  # More than 10 recent operations on same voxel
                time_span = recent_ops[-1].get("timestamp", time.time()) - recent_ops[0].get("timestamp", time.time())
                if time_span < 1.0:  # All within 1 second
                    logger.warning(f"Potential resonance loop detected on voxel {voxel_id}: "
                                  f"{len(recent_ops)} operations in {time_span:.2f}s")
                    return False
                    
        elif operation_type == "chain":
            voxel_id = params.get("voxel_id")
            
            # Validate voxel_id
            if not voxel_id:
                logger.warning("Missing voxel_id for chain operation")
                return False
                
            # Check for chain loops
            with self._lock:
                recent_chains = [c for c in self._chain_log[-20:] if c.get("voxel_id") == voxel_id]
                
            if len(recent_chains) > 5:  # More than 5 recent chains on same voxel
                time_span = recent_chains[-1].get("timestamp", time.time()) - recent_chains[0].get("timestamp", time.time())
                if time_span < 0.5:  # All within 0.5 seconds
                    logger.warning(f"Potential chain loop detected on voxel {voxel_id}: "
                                  f"{len(recent_chains)} chains in {time_span:.2f}s")
                    return False
                    
        # All validations passed
        return True
    
    def verify_module(self, module_id: str, verification_data: Dict[str, Any]) -> bool:
        """
        Verify a module for core access.
        
        Args:
            module_id: Module identifier
            verification_data: Data for verification
            
        Returns:
            True if verification successful, False otherwise
        """
        with self._lock:
            # Check if already verified
            if module_id in self._verified_modules:
                logger.info(f"Module {module_id} already verified")
                return True
                
            # Check if blocked
            if module_id in self._blocked_modules:
                logger.warning(f"Cannot verify blocked module {module_id}")
                return False
                
            # Store verification data
            self._verified_modules[module_id] = {
                "verification_data": verification_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Module {module_id} verified for core access")
            return True
    
    def block_module(self, module_id: str, reason: str) -> bool:
        """
        Block a module from core access.
        
        Args:
            module_id: Module identifier
            reason: Reason for blocking
            
        Returns:
            True if blocking successful, False otherwise
        """
        with self._lock:
            # Remove from verified modules if present
            if module_id in self._verified_modules:
                del self._verified_modules[module_id]
                
            # Add to blocked modules
            self._blocked_modules[module_id] = {
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.warning(f"Module {module_id} blocked from core access: {reason}")
            
            # Trigger alert
            self._trigger_alert({
                "type": "module_blocked",
                "module_id": module_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return True
    
    def register_alert_callback(self, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Register a callback for real-time alerts.
        
        Args:
            callback: Function to call when alert is triggered
            
        Returns:
            True if registration successful, False otherwise
        """
        if not callable(callback):
            logger.warning("Alert callback must be callable")
            return False
            
        with self._lock:
            self._alert_callbacks.append(callback)
            
        logger.info(f"Alert callback registered, total callbacks: {len(self._alert_callbacks)}")
        return True
    
    def _trigger_alert(self, alert_data: Dict[str, Any]) -> None:
        """Trigger all registered alert callbacks."""
        with self._lock:
            callbacks = self._alert_callbacks.copy()
            self._health_metrics["alerts_triggered"] += 1
            
        for callback in callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def _start_monitor_thread(self) -> None:
        """Start the monitoring thread."""
        def monitor_loop():
            while True:
                try:
                    # Perform self-regulation
                    self.self_regulate()
                except Exception as e:
                    logger.error(f"Error in monitor thread: {e}")
                    
                # Sleep before next check
                time.sleep(5)
                
        # Start the monitoring thread
        threading.Thread(target=monitor_loop, daemon=True).start()
        logger.info("Core hooks monitoring thread started")
    
    def increment_voxel(self, module_id: str, voxel_id: str, strength: float) -> float:
        """
        Increment voxel activation strength.
        
        Args:
            module_id: ID of the calling module
            voxel_id: Unique identifier for the voxel
            strength: Activation strength to apply
            
        Returns:
            float: New voxel strength
        """
        try:
            # Validate through interface contract
            self.interface_contract(module_id, "increment")
            
            # Validate through resonance chain
            params = {"voxel_id": voxel_id, "strength": strength}
            if not self.resonance_chain_validator(module_id, "increment", params):
                logger.warning(f"Resonance chain validation failed for increment operation from {module_id}")
                raise ValueError("Resonance chain validation failed")
                
            # Apply cognitive energy flow
            energy_data = self.cognitive_energy_flow("increment", strength)
            
            # Throttle if needed
            if energy_data.get("throttled", False):
                strength *= 0.5  # Reduce strength when throttled
                
            with self._lock:
                if voxel_id not in self._voxel_operations:
                    self._voxel_operations[voxel_id] = 0.0
                    
                self._voxel_operations[voxel_id] += strength
                
                # Log operation
                self._operation_log.append({
                    "operation": "increment",
                    "module_id": module_id,
                    "voxel_id": voxel_id,
                    "strength": strength,
                    "timestamp": time.time()
                })
                
                self._health_metrics["operations_count"] += 1
                
                return self._voxel_operations[voxel_id]
                
        except Exception as e:
            logger.error(f"Error in increment_voxel: {e}")
            context = {
                "operation_type": "increment",
                "module_id": module_id,
                "voxel_id": voxel_id,
                "strength": strength
            }
            fallback_result = self.graceful_fallback(e, context)
            
            # Return voxel strength from fallback if available
            return fallback_result.get("new_strength", 0.0)
    
    def log_chain(self, module_id: str, voxel_id: str, strength: float) -> bool:
        """
        Log neural chain activation.
        
        Args:
            module_id: ID of the calling module
            voxel_id: Voxel identifier in the chain
            strength: Activation strength
            
        Returns:
            bool: Success status
        """
        try:
            # Validate through interface contract
            self.interface_contract(module_id, "chain")
            
            # Validate through resonance chain
            params = {"voxel_id": voxel_id, "strength": strength}
            if not self.resonance_chain_validator(module_id, "chain", params):
                logger.warning(f"Resonance chain validation failed for chain operation from {module_id}")
                raise ValueError("Resonance chain validation failed")
                
            # Apply cognitive energy flow
            energy_data = self.cognitive_energy_flow("chain", strength)
            
            with self._lock:
                self._chain_log.append({
                    "module_id": module_id,
                    "voxel_id": voxel_id,
                    "strength": strength,
                    "timestamp": time.time()
                })
                
                self._health_metrics["chain_events"] += 1
                
            return True
            
        except Exception as e:
            logger.error(f"Error in log_chain: {e}")
            context = {
                "operation_type": "chain",
                "module_id": module_id,
                "voxel_id": voxel_id,
                "strength": strength
            }
            self.graceful_fallback(e, context)
            return False
    
    def flush_operation_log(self, module_id: str = "system", output_file: str = None) -> List[Dict[str, Any]]:
        """
        Flush operation log to file or memory.
        
        Args:
            module_id: ID of the calling module
            output_file: Output file path
            
        Returns:
            list: Operation log entries
        """
        try:
            # Validate through interface contract
            self.interface_contract(module_id, "flush")
            
            # Validate through resonance chain
            params = {"output_file": output_file}
            if not self.resonance_chain_validator(module_id, "flush", params):
                logger.warning(f"Resonance chain validation failed for flush operation from {module_id}")
                raise ValueError("Resonance chain validation failed")
                
            # Apply cognitive energy flow
            self.cognitive_energy_flow("flush")
            
            with self._lock:
                if not self._operation_log:
                    return []
                    
                # Copy log for return
                log_copy = self._operation_log.copy()
                
                # Write to file if specified
                if output_file:
                    try:
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, 'a') as f:
                            for entry in self._operation_log:
                                f.write(f"{datetime.fromtimestamp(entry['timestamp']).isoformat()} - "
                                       f"{entry.get('module_id', 'unknown')} - "
                                       f"{entry['operation']} - {entry['voxel_id']} - {entry['strength']}\n")
                    except Exception as e:
                        logger.error(f"Failed to write operation log to {output_file}: {e}")
                
                # Clear log
                self._operation_log = []
                self._last_flush_time = time.time()
                
                return log_copy
                
        except Exception as e:
            logger.error(f"Error in flush_operation_log: {e}")
            context = {
                "operation_type": "flush",
                "module_id": module_id,
                "output_file": output_file
            }
            self.graceful_fallback(e, context)
            return []
    
    def flush_chain_log(self, module_id: str = "system", output_file: str = None) -> List[Dict[str, Any]]:
        """
        Flush chain log to file or memory.
        
        Args:
            module_id: ID of the calling module
            output_file: Output file path
            
        Returns:
            list: Chain log entries
        """
        try:
            # Validate through interface contract
            self.interface_contract(module_id, "flush")
            
            # Validate through resonance chain
            params = {"output_file": output_file}
            if not self.resonance_chain_validator(module_id, "flush", params):
                logger.warning(f"Resonance chain validation failed for flush operation from {module_id}")
                raise ValueError("Resonance chain validation failed")
                
            # Apply cognitive energy flow
            self.cognitive_energy_flow("flush")
            
            with self._lock:
                if not self._chain_log:
                    return []
                    
                # Copy log for return
                log_copy = self._chain_log.copy()
                
                # Write to file if specified
                if output_file:
                    try:
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, 'a') as f:
                            for entry in self._chain_log:
                                f.write(f"{datetime.fromtimestamp(entry['timestamp']).isoformat()} - "
                                       f"{entry.get('module_id', 'unknown')} - "
                                       f"chain - {entry['voxel_id']} - {entry['strength']}\n")
                    except Exception as e:
                        logger.error(f"Failed to write chain log to {output_file}: {e}")
                
                # Clear log
                self._chain_log = []
                
                return log_copy
                
        except Exception as e:
            logger.error(f"Error in flush_chain_log: {e}")
            context = {
                "operation_type": "flush",
                "module_id": module_id,
                "output_file": output_file
            }
            self.graceful_fallback(e, context)
            return []
    
    def get_voxel_operations(self, module_id: str = "system") -> Dict[str, float]:
        """
        Get current voxel operations.
        
        Args:
            module_id: ID of the calling module
            
        Returns:
            dict: Voxel operations {voxel_id: strength}
        """
        try:
            # Validate through interface contract
            self.interface_contract(module_id, "stats")
            
            # Validate through resonance chain
            if not self.resonance_chain_validator(module_id, "stats", {}):
                logger.warning(f"Resonance chain validation failed for stats operation from {module_id}")
                raise ValueError("Resonance chain validation failed")
                
            # Apply cognitive energy flow
            self.cognitive_energy_flow("stats")
            
            with self._lock:
                return self._voxel_operations.copy()
                
        except Exception as e:
            logger.error(f"Error in get_voxel_operations: {e}")
            context = {
                "operation_type": "stats",
                "module_id": module_id
            }
            self.graceful_fallback(e, context)
            return {}
    
    def reset_voxel_operations(self, module_id: str = "system") -> Dict[str, float]:
        """
        Reset voxel operations tracking.
        
        Args:
            module_id: ID of the calling module
            
        Returns:
            dict: Previous voxel operations
        """
        try:
            # Validate through interface contract
            self.interface_contract(module_id, "reset")
            
            # Validate through resonance chain
            if not self.resonance_chain_validator(module_id, "reset", {}):
                logger.warning(f"Resonance chain validation failed for reset operation from {module_id}")
                raise ValueError("Resonance chain validation failed")
                
            # Apply cognitive energy flow
            self.cognitive_energy_flow("reset")
            
            with self._lock:
                previous = self._voxel_operations.copy()
                self._voxel_operations = {}
                
                return previous
                
        except Exception as e:
            logger.error(f"Error in reset_voxel_operations: {e}")
            context = {
                "operation_type": "reset",
                "module_id": module_id
            }
            self.graceful_fallback(e, context)
            return {}
    
    def get_operation_stats(self, module_id: str = "system") -> Dict[str, Any]:
        """
        Get operation statistics.
        
        Args:
            module_id: ID of the calling module
            
        Returns:
            dict: Operation statistics
        """
        try:
            # Validate through interface contract
            self.interface_contract(module_id, "stats")
            
            # Validate through resonance chain
            if not self.resonance_chain_validator(module_id, "stats", {}):
                logger.warning(f"Resonance chain validation failed for stats operation from {module_id}")
                raise ValueError("Resonance chain validation failed")
                
            # Apply cognitive energy flow
            self.cognitive_energy_flow("stats")
            
            with self._lock:
                stats = {
                    "operation_log_size": len(self._operation_log),
                    "chain_log_size": len(self._chain_log),
                    "voxel_count": len(self._voxel_operations),
                    "verified_modules": len(self._verified_modules),
                    "blocked_modules": len(self._blocked_modules),
                    "last_flush_time": self._last_flush_time,
                    "time_since_flush": time.time() - self._last_flush_time,
                    "security_level": self._security_level,
                    "auto_lockout_enabled": self.auto_lockout_enabled,
                    "health_metrics": self._health_metrics
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Error in get_operation_stats: {e}")
            context = {
                "operation_type": "stats",
                "module_id": module_id
            }
            self.graceful_fallback(e, context)
            return {}
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status of the core hooks.
        
        Returns:
            Dict containing health status metrics
        """
        with self._lock:
            metrics = self._health_metrics.copy()
            
        # Add additional status information
        status = {
            **metrics,
            "operation_log_size": len(self._operation_log),
            "chain_log_size": len(self._chain_log),
            "voxel_count": len(self._voxel_operations),
            "verified_modules": len(self._verified_modules),
            "blocked_modules": len(self._blocked_modules),
            "security_level": self._security_level,
            "auto_lockout_enabled": self.auto_lockout_enabled,
            "last_sync": self._last_sync.isoformat()
        }
        
        return status

# Create a global instance for backward compatibility with procedural code
_core_hooks = CortexCoreHooks()

# Procedural API for backward compatibility
def increment_voxel(voxel_id, strength):
    """
    Increment voxel activation strength.
    
    Args:
        voxel_id (str): Unique identifier for the voxel
        strength (float): Activation strength to apply
        
    Returns:
        float: New voxel strength
    """
    return _core_hooks.increment_voxel("legacy", voxel_id, strength)

def log_chain(voxel_id, strength):
    """
    Log neural chain activation.
    
    Args:
        voxel_id (str): Voxel identifier in the chain
        strength (float): Activation strength
    """
    _core_hooks.log_chain("legacy", voxel_id, strength)

def flush_operation_log(output_file=None):
    """
    Flush operation log to file or memory.
    
    Args:
        output_file (str, optional): Output file path
        
    Returns:
        list: Operation log entries
    """
    return _core_hooks.flush_operation_log("legacy", output_file)

def flush_chain_log(output_file=None):
    """
    Flush chain log to file or memory.
    
    Args:
        output_file (str, optional): Output file path
        
    Returns:
        list: Chain log entries
    """
    return _core_hooks.flush_chain_log("legacy", output_file)

def get_voxel_operations():
    """
    Get current voxel operations.
    
    Returns:
        dict: Voxel operations {voxel_id: strength}
    """
    return _core_hooks.get_voxel_operations("legacy")

def reset_voxel_operations():
    """
    Reset voxel operations tracking.
    
    Returns:
        dict: Previous voxel operations
    """
    return _core_hooks.reset_voxel_operations("legacy")

def get_operation_stats():
    """
    Get operation statistics.
    
    Returns:
        dict: Operation statistics
    """
    return _core_hooks.get_operation_stats("legacy")
