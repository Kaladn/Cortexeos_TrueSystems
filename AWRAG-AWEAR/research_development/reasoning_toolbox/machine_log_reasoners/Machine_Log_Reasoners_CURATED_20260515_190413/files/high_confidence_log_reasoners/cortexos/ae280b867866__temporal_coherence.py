"""
CortexOS Temporal Cognition v2.1
Module: Temporal Coherence Manager
Purpose: Manages time-based relationships between concepts and memories,
         maintaining consistency across temporal operations and enabling predictive capabilities.

This module implements the Agharmonic Law by providing:
- Temporal Synchronization across all modules
- Harmonic Resonance through consistent timing signals
- Self-regulation through adaptive cycle management
- Graceful Degradation when timing constraints cannot be met
"""

import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional

# Configure module logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TemporalCoherenceManager:
    """
    Manages temporal synchronization and coherence across the CortexOS architecture.
    Provides a central timing mechanism for coordinating neural processes.
    """
    
    def __init__(self, cycle_duration: float = 0.5):
        """
        Initialize the Temporal Coherence Manager.
        
        Args:
            cycle_duration: Base duration of a timing cycle in seconds
        """
        self.cycle_duration = cycle_duration  # seconds
        self.last_tick = time.time()
        self.listeners = []
        self._running = False
        self._lock = threading.Lock()
        
        # Agharmonic Law compliance
        self.input_frequency_range = (0.5, 10.0)  # in Hz
        self.output_phase_alignment = 0.0
        self.resonance_threshold = 0.9
        
        # Temporal tracking
        self.cycle_count = 0
        self.timing_stats = {
            "avg_cycle_time": cycle_duration,
            "min_cycle_time": cycle_duration,
            "max_cycle_time": cycle_duration,
            "jitter": 0.0
        }
        
        logger.info(f"TemporalCoherenceManager initialized with cycle_duration={cycle_duration}s")

    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility for this module.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "module": "temporal_coherence",
            "rhythm_hz": 1 / self.cycle_duration,
            "input_range": self.input_frequency_range,
            "output_phase": self.output_phase_alignment,
            "threshold": self.resonance_threshold
        }
    
    def interface_contract(self, listener: Any) -> bool:
        """
        Defines allowed function calls and verifies listener compatibility.
        
        Args:
            listener: Object that will receive temporal signals
            
        Returns:
            True if listener meets the interface contract
            
        Raises:
            AttributeError: If listener doesn't implement required methods
        """
        if not hasattr(listener, 'on_cycle_tick'):
            raise AttributeError("Listener must implement 'on_cycle_tick'")
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
        cycle_position = (now - self.last_tick) / self.cycle_duration
        
        return {
            "timestamp": timestamp,
            "cycle_count": self.cycle_count,
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
                    self.last_tick = external_time
                    logger.info(f"Clock synchronized with external time. Delta: {time_delta:.4f}s")
                
                return True
            except Exception as e:
                logger.warning(f"Failed to sync with global clock: {e}")
                return False
        
        # If no global clock, use internal timing
        return True
    
    def self_regulate(self) -> None:
        """
        Implements feedback loop analysis and adaptive timing adjustments.
        Core to stabilization of the temporal framework.
        """
        # Update timing statistics
        if self.cycle_count > 0:
            current_time = time.time()
            actual_cycle_time = current_time - self.last_tick
            
            # Update running statistics
            self.timing_stats["avg_cycle_time"] = (
                (self.timing_stats["avg_cycle_time"] * (self.cycle_count - 1) + actual_cycle_time) / 
                self.cycle_count
            )
            self.timing_stats["min_cycle_time"] = min(self.timing_stats["min_cycle_time"], actual_cycle_time)
            self.timing_stats["max_cycle_time"] = max(self.timing_stats["max_cycle_time"], actual_cycle_time)
            
            # Calculate jitter
            self.timing_stats["jitter"] = self.timing_stats["max_cycle_time"] - self.timing_stats["min_cycle_time"]
            
            # Adaptive cycle duration adjustment if jitter is too high
            if self.timing_stats["jitter"] > self.cycle_duration * 0.5:
                new_duration = self.timing_stats["avg_cycle_time"] * 1.1  # Increase by 10%
                logger.warning(f"High timing jitter detected ({self.timing_stats['jitter']:.4f}s). "
                              f"Adjusting cycle duration from {self.cycle_duration:.4f}s to {new_duration:.4f}s")
                self.cycle_duration = new_duration
    
    def graceful_fallback(self) -> Dict[str, Any]:
        """
        Provides fallback mechanisms when timing constraints cannot be met.
        
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning("Executing graceful fallback due to timing constraints")
        
        # Reset timing statistics
        self.timing_stats = {
            "avg_cycle_time": self.cycle_duration,
            "min_cycle_time": self.cycle_duration,
            "max_cycle_time": self.cycle_duration,
            "jitter": 0.0
        }
        
        # Increase cycle duration to reduce system load
        adjusted_duration = self.cycle_duration * 1.5
        logger.info(f"Adjusting cycle duration to {adjusted_duration:.4f}s for stability")
        self.cycle_duration = adjusted_duration
        
        return {
            "status": "fallback_active",
            "action": "cycle_duration_increased",
            "new_duration": self.cycle_duration,
            "recommendation": "Consider reducing number of temporal listeners"
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
    
    def register(self, listener: Any) -> bool:
        """
        Register a listener to receive temporal signals.
        
        Args:
            listener: Object that will receive temporal signals
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            self.interface_contract(listener)
            with self._lock:
                if listener not in self.listeners:
                    self.listeners.append(listener)
                    logger.info(f"Listener {listener.__class__.__name__} registered")
                    return True
                else:
                    logger.warning(f"Listener {listener.__class__.__name__} already registered")
                    return False
        except Exception as e:
            logger.error(f"Failed to register listener: {e}")
            return False
    
    def unregister(self, listener: Any) -> bool:
        """
        Unregister a listener from receiving temporal signals.
        
        Args:
            listener: Previously registered listener
            
        Returns:
            True if unregistration successful, False otherwise
        """
        with self._lock:
            if listener in self.listeners:
                self.listeners.remove(listener)
                logger.info(f"Listener {listener.__class__.__name__} unregistered")
                return True
            else:
                logger.warning(f"Listener {listener.__class__.__name__} not found")
                return False
    
    def _tick_loop(self) -> None:
        """Internal loop that generates timing ticks."""
        while self._running:
            now = time.time()
            elapsed = now - self.last_tick
            
            if elapsed >= self.cycle_duration:
                self._trigger_listeners()
                self.last_tick = now
                self.cycle_count += 1
                
                # Self-regulation
                if self.cycle_count % 10 == 0:  # Every 10 cycles
                    self.self_regulate()
            
            # Adaptive sleep to reduce CPU usage
            sleep_time = min(0.01, self.cycle_duration / 10)
            time.sleep(sleep_time)
    
    def _trigger_listeners(self) -> None:
        """Trigger all registered listeners with the current temporal signal."""
        timestamp = datetime.utcnow().isoformat()
        
        # Validate temporal signal
        if not self.resonance_chain_validator(timestamp):
            logger.error("Temporal signal validation failed")
            return
        
        # Normalize signal
        signal = self.cognitive_energy_flow(timestamp)
        
        logger.debug(f"Tick at {timestamp} (cycle {self.cycle_count})")
        
        # Notify listeners
        for listener in self.listeners:
            try:
                listener.on_cycle_tick(timestamp)
            except Exception as e:
                logger.error(f"Listener error: {e}")
                
                # Try fallback if available
                if hasattr(listener, 'on_cycle_error'):
                    try:
                        listener.on_cycle_error(timestamp, str(e))
                    except Exception as fallback_error:
                        logger.error(f"Listener fallback error: {fallback_error}")
    
    def start(self) -> bool:
        """
        Start the temporal coherence loop.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self._running:
            try:
                logger.info("Temporal coherence loop starting")
                self._running = True
                threading.Thread(target=self._tick_loop, daemon=True).start()
                return True
            except Exception as e:
                self._running = False
                logger.error(f"Failed to start temporal coherence loop: {e}")
                return False
        else:
            logger.warning("Temporal coherence loop already running")
            return False
    
    def stop(self) -> bool:
        """
        Stop the temporal coherence loop.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self._running:
            logger.info("Temporal coherence loop stopping")
            self._running = False
            return True
        else:
            logger.warning("Temporal coherence loop already stopped")
            return False
    
    def get_timing_stats(self) -> Dict[str, float]:
        """
        Get current timing statistics.
        
        Returns:
            Dict containing timing statistics
        """
        return {
            **self.timing_stats,
            "cycle_count": self.cycle_count,
            "current_duration": self.cycle_duration,
            "listeners_count": len(self.listeners)
        }
