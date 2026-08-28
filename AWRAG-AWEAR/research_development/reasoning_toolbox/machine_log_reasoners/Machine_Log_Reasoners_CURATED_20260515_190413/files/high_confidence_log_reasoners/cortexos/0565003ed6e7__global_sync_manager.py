"""
CortexOS Temporal Cognition v2.1
Module: Global Sync Manager
Purpose: Centralizes temporal coordination across all neural modules,
         ensuring synchronized processing cycles and resonance alignment.

This module implements the Agharmonic Law by providing:
- Temporal Synchronization across all modules
- Harmonic Resonance through consistent timing signals
- Self-regulation through adaptive cycle management
- Resonance Chain Integrity through synchronized processing
"""

import json
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure module logger
logger = logging.getLogger(__name__)

class GlobalSyncManager:
    """
    Manages global synchronization across the CortexOS architecture.
    Provides centralized timing control and ensures temporal coherence.
    """
    
    def __init__(self, policy_file: str = 'data/sync_policy.json', environment: str = 'dev'):
        """
        Initialize the Global Sync Manager.
        
        Args:
            policy_file: Path to the sync policy configuration file
            environment: Environment setting ('dev', 'realtime', 'research')
        """
        self.policy_file = policy_file
        self.environment = environment
        self.policy = self._load_policy()
        
        # Initialize timing parameters
        self.cycle_time = self.policy['timing'][self.environment]['cycle_time']
        self.learning_cycle = self.policy['timing'][self.environment]['learning_cycle']
        self.resonance_check_interval = self.policy['timing'][self.environment]['resonance_check_interval']
        self.fabric_sync_enabled = self.policy['timing'][self.environment].get('fabric_sync_enabled', False)
        
        # Registered modules
        self.modules = {}
        self.last_sync_time = datetime.utcnow()
        self._running = False
        self._lock = threading.Lock()
        
        # Agharmonic Law compliance
        self.input_frequency_range = (0.1, 10.0)  # in Hz
        self.output_phase_alignment = 0.0
        self.resonance_threshold = 0.9
        
        logger.info(f"GlobalSyncManager initialized with environment={environment}, cycle_time={self.cycle_time}s")
    
    def _load_policy(self) -> Dict[str, Any]:
        """
        Load sync policy from configuration file.
        
        Returns:
            Dict containing sync policy configuration
            
        Raises:
            FileNotFoundError: If policy file doesn't exist
            json.JSONDecodeError: If policy file contains invalid JSON
        """
        try:
            with open(self.policy_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Sync policy file not found: {self.policy_file}. Using default policy.")
            return {
                "timing": {
                    "dev": {
                        "cycle_time": 5,
                        "learning_cycle": 60,
                        "resonance_check_interval": 30,
                        "fabric_sync_enabled": False
                    },
                    "realtime": {
                        "cycle_time": 1,
                        "learning_cycle": 5,
                        "resonance_check_interval": 2,
                        "fabric_sync_enabled": True
                    },
                    "research": {
                        "cycle_time": 10,
                        "learning_cycle": 300,
                        "resonance_check_interval": 120,
                        "fabric_sync_enabled": False
                    }
                },
                "module_overrides": {}
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in sync policy file: {e}")
            raise
    
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility for this module.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "module": "global_sync_manager",
            "rhythm_hz": 1 / self.cycle_time,
            "input_range": self.input_frequency_range,
            "output_phase": self.output_phase_alignment,
            "threshold": self.resonance_threshold
        }
    
    def interface_contract(self, module: Any) -> bool:
        """
        Defines allowed function calls and verifies module compatibility.
        
        Args:
            module: Module to verify compatibility with
            
        Returns:
            True if module meets the interface contract
            
        Raises:
            AttributeError: If module doesn't implement required methods
        """
        required_methods = ['sync_clock']
        
        for method in required_methods:
            if not hasattr(module, method) or not callable(getattr(module, method)):
                raise AttributeError(f"Module must implement '{method}' method")
        
        return True
    
    def cognitive_energy_flow(self, timestamp: str) -> Dict[str, Any]:
        """
        Normalizes temporal signal information to maintain balanced information flow.
        
        Args:
            timestamp: Current timestamp string
            
        Returns:
            Normalized temporal signal data
        """
        now = time.time()
        cycle_position = (now - self.last_sync_time.timestamp()) / self.cycle_time
        
        return {
            "timestamp": timestamp,
            "cycle_position": min(1.0, max(0.0, cycle_position)),  # Normalized to [0.0, 1.0]
            "signal_strength": 0.9  # Consistent signal strength for temporal signals
        }
    
    def sync_clock(self, global_clock: Any = None) -> bool:
        """
        Synchronizes with the master temporal framework or external clock.
        
        Args:
            global_clock: Optional reference to a global clock object
            
        Returns:
            True if synchronization successful, False otherwise
        """
        if global_clock and hasattr(global_clock, 'get_time'):
            try:
                external_time = global_clock.get_time()
                time_delta = abs(time.time() - external_time)
                
                # Only adjust if drift is significant
                if time_delta > 0.1:
                    self.last_sync_time = datetime.fromtimestamp(external_time)
                    logger.info(f"Clock synchronized with external time. Delta: {time_delta:.4f}s")
                
                return True
            except Exception as e:
                logger.warning(f"Failed to sync with global clock: {e}")
                return False
        
        # If no global clock, use internal timing
        self.last_sync_time = datetime.utcnow()
        return True
    
    def self_regulate(self) -> None:
        """
        Implements feedback loop analysis and adaptive timing adjustments.
        Core to stabilization of the temporal framework.
        """
        # Check if any modules are consistently missing sync cycles
        missed_syncs = {}
        
        for module_id, module_data in self.modules.items():
            if module_data.get('missed_syncs', 0) > 3:
                missed_syncs[module_id] = module_data['missed_syncs']
                
        if missed_syncs:
            # Adjust cycle time if modules are consistently missing syncs
            if len(missed_syncs) > len(self.modules) * 0.3:  # If >30% of modules are missing syncs
                new_cycle_time = self.cycle_time * 1.2  # Increase by 20%
                logger.warning(f"Multiple modules missing sync cycles. Adjusting cycle time from "
                              f"{self.cycle_time:.2f}s to {new_cycle_time:.2f}s")
                self.cycle_time = new_cycle_time
                
                # Reset missed syncs counter
                for module_id in missed_syncs:
                    self.modules[module_id]['missed_syncs'] = 0
    
    def graceful_fallback(self) -> Dict[str, Any]:
        """
        Provides fallback mechanisms when timing constraints cannot be met.
        
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning("Executing graceful fallback due to timing constraints")
        
        # Increase cycle time to reduce system load
        adjusted_cycle_time = self.cycle_time * 1.5
        logger.info(f"Adjusting cycle time to {adjusted_cycle_time:.2f}s for stability")
        self.cycle_time = adjusted_cycle_time
        
        # Reduce frequency of non-critical operations
        adjusted_learning_cycle = self.learning_cycle * 2
        adjusted_resonance_check = self.resonance_check_interval * 2
        
        logger.info(f"Adjusting learning cycle to {adjusted_learning_cycle}s")
        logger.info(f"Adjusting resonance check interval to {adjusted_resonance_check}s")
        
        self.learning_cycle = adjusted_learning_cycle
        self.resonance_check_interval = adjusted_resonance_check
        
        return {
            "status": "fallback_active",
            "action": "timing_adjusted",
            "new_cycle_time": self.cycle_time,
            "new_learning_cycle": self.learning_cycle,
            "new_resonance_check": self.resonance_check_interval,
            "recommendation": "Consider reducing number of synchronized modules"
        }
    
    def resonance_chain_validator(self, timestamp: str) -> bool:
        """
        Verifies temporal signal integrity across the resonance chain.
        
        Args:
            timestamp: Timestamp to validate
            
        Returns:
            True if temporal signal is valid, False otherwise
        """
        try:
            # Validate timestamp format
            datetime.fromisoformat(timestamp)
            
            # Check if timestamp is reasonably current (within 5 seconds)
            timestamp_time = datetime.fromisoformat(timestamp).timestamp()
            current_time = time.time()
            
            if abs(current_time - timestamp_time) > 5.0:
                logger.warning(f"Timestamp too far from current time: {abs(current_time - timestamp_time):.2f}s")
                return False
                
            return True
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid timestamp format: {e}")
            return False
    
    def register_module(self, module_id: str, module: Any) -> bool:
        """
        Register a module for synchronization.
        
        Args:
            module_id: Unique identifier for the module
            module: Module object to register
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            self.interface_contract(module)
            
            with self._lock:
                if module_id not in self.modules:
                    self.modules[module_id] = {
                        'module': module,
                        'last_sync': datetime.utcnow(),
                        'missed_syncs': 0
                    }
                    logger.info(f"Module {module_id} registered for synchronization")
                    return True
                else:
                    logger.warning(f"Module {module_id} already registered")
                    return False
        except Exception as e:
            logger.error(f"Failed to register module {module_id}: {e}")
            return False
    
    def unregister_module(self, module_id: str) -> bool:
        """
        Unregister a module from synchronization.
        
        Args:
            module_id: Unique identifier for the module
            
        Returns:
            True if unregistration successful, False otherwise
        """
        with self._lock:
            if module_id in self.modules:
                del self.modules[module_id]
                logger.info(f"Module {module_id} unregistered")
                return True
            else:
                logger.warning(f"Module {module_id} not found")
                return False
    
    def _sync_loop(self) -> None:
        """Internal loop that synchronizes all registered modules."""
        while self._running:
            cycle_start = time.time()
            timestamp = datetime.utcnow().isoformat()
            
            # Validate temporal signal
            if not self.resonance_chain_validator(timestamp):
                logger.error("Temporal signal validation failed")
                time.sleep(0.1)
                continue
            
            # Normalize signal
            signal = self.cognitive_energy_flow(timestamp)
            
            # Synchronize all modules
            with self._lock:
                for module_id, module_data in self.modules.items():
                    try:
                        module = module_data['module']
                        module.sync_clock(self)
                        self.modules[module_id]['last_sync'] = datetime.utcnow()
                        self.modules[module_id]['missed_syncs'] = 0
                    except Exception as e:
                        logger.error(f"Failed to synchronize module {module_id}: {e}")
                        self.modules[module_id]['missed_syncs'] += 1
            
            # Self-regulation
            self.self_regulate()
            
            # Calculate sleep time to maintain consistent cycle time
            cycle_end = time.time()
            cycle_duration = cycle_end - cycle_start
            sleep_time = max(0.001, self.cycle_time - cycle_duration)
            
            time.sleep(sleep_time)
    
    def start(self) -> bool:
        """
        Start the global synchronization loop.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self._running:
            try:
                logger.info("Global synchronization loop starting")
                self._running = True
                threading.Thread(target=self._sync_loop, daemon=True).start()
                return True
            except Exception as e:
                self._running = False
                logger.error(f"Failed to start global synchronization loop: {e}")
                return False
        else:
            logger.warning("Global synchronization loop already running")
            return False
    
    def stop(self) -> bool:
        """
        Stop the global synchronization loop.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self._running:
            logger.info("Global synchronization loop stopping")
            self._running = False
            return True
        else:
            logger.warning("Global synchronization loop already stopped")
            return False
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """
        Get current synchronization statistics.
        
        Returns:
            Dict containing synchronization statistics
        """
        return {
            "environment": self.environment,
            "cycle_time": self.cycle_time,
            "learning_cycle": self.learning_cycle,
            "resonance_check_interval": self.resonance_check_interval,
            "fabric_sync_enabled": self.fabric_sync_enabled,
            "registered_modules": len(self.modules),
            "module_ids": list(self.modules.keys())
        }
