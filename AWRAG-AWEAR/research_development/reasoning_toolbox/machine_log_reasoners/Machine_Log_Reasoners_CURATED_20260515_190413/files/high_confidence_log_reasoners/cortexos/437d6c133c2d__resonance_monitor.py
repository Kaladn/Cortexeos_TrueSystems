"""
CortexOS Temporal Cognition v2.1
Module: Resonance Monitor
Purpose: Monitors resonance stability and phase coherence across the neural architecture,
         detecting and alerting on phase drift or resonance instability.

This module implements the Agharmonic Law by providing:
- Harmonic Resonance monitoring across the neural architecture
- Self-regulation through phase stability checks
- Resonance Chain Integrity verification
"""

import logging
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure module logger
logger = logging.getLogger(__name__)

class ResonanceMonitor:
    """
    Monitors resonance stability and phase coherence across the neural architecture.
    Detects and alerts on phase drift or resonance instability.
    """
    
    def __init__(self, stability_threshold: float = 0.75):
        """
        Initialize the Resonance Monitor.
        
        Args:
            stability_threshold: Threshold for resonance stability (0-1.0)
        """
        self.stability_threshold = stability_threshold
        self.last_check_time = datetime.utcnow()
        self.resonance_history = []
        self.max_history_length = 1000
        
        # Resonance tracking
        self.active_resonances = {}
        self.phase_drift_log = []
        
        # Agharmonic Law compliance
        self.input_frequency_range = (0.5, 2.0)  # in GHz cognitive equivalent
        self.output_phase_alignment = 0.0
        self.resonance_threshold = 0.8
        
        logger.info(f"ResonanceMonitor initialized with stability_threshold={stability_threshold}")
    
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility for this module.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "input_range": self.input_frequency_range,
            "output_phase": self.output_phase_alignment,
            "threshold": self.resonance_threshold
        }
    
    def interface_contract(self) -> Dict[str, List[str]]:
        """
        Defines all allowed function calls, accepted data structures, and outbound schema.
        
        Returns:
            Dict containing input and output interface specifications
        """
        return {
            "inputs": ["resonance_id", "phase", "strength", "check_interval"],
            "outputs": ["stability_report", "phase_drift", "active_resonances"]
        }
    
    def cognitive_energy_flow(self, signal: np.ndarray) -> np.ndarray:
        """
        Normalizes incoming and outgoing signals based on signal amplitude and payload entropy.
        
        Args:
            signal: Input signal to normalize
            
        Returns:
            Normalized signal
        """
        # Normalize signal to maintain balanced information flow
        if signal.size == 0:
            return np.array([])
            
        normalized = (signal - signal.min()) / (signal.max() - signal.min() + 1e-10)
        return normalized * 0.9 + 0.05  # Scale to range [0.05, 0.95]
    
    def sync_clock(self, global_clock: Any = None) -> bool:
        """
        Connects the module to the master temporal framework.
        
        Args:
            global_clock: Reference to the global clock object
            
        Returns:
            True if synchronization successful, False otherwise
        """
        current_time = datetime.utcnow()
        
        if global_clock:
            try:
                self.timestep = global_clock.get_time()
                logger.debug(f"Clock synchronized with global clock. Timestep: {self.timestep}")
                return True
            except Exception as e:
                logger.warning(f"Failed to sync with global clock: {e}")
                return False
        
        # If no global clock, use internal timing
        self.last_check_time = current_time
        return True
    
    def self_regulate(self) -> None:
        """
        Implements feedback loop analysis and pattern anticipation.
        Core to stabilization of the resonance monitoring system.
        """
        # Trim history if it exceeds the maximum length
        if len(self.resonance_history) > self.max_history_length:
            self.resonance_history = self.resonance_history[-self.max_history_length:]
            
        # Check for internal anomalies
        if len(self.phase_drift_log) > self.max_history_length * 0.3:
            logger.warning("High phase drift rate detected in monitoring system")
            self.phase_drift_log = self.phase_drift_log[-int(self.max_history_length * 0.2):]
            
            # Adjust stability threshold if too many drifts are detected
            if self.stability_threshold < 0.9:
                new_threshold = min(0.9, self.stability_threshold * 1.1)
                logger.info(f"Adjusting stability threshold from {self.stability_threshold:.2f} to {new_threshold:.2f}")
                self.stability_threshold = new_threshold
    
    def graceful_fallback(self) -> Dict[str, Any]:
        """
        Fallback to partial operation when monitoring system is compromised.
        
        Returns:
            Dict containing fallback status and recommendations
        """
        logger.warning("Executing graceful fallback due to resonance monitoring issues")
        
        # Reset history and logs
        self.resonance_history = self.resonance_history[-min(100, len(self.resonance_history)):]
        self.phase_drift_log = []
        
        # Adjust threshold to be more permissive
        adjusted_threshold = max(0.6, self.stability_threshold * 0.9)
        logger.info(f"Adjusting stability threshold to {adjusted_threshold:.2f} for stability")
        self.stability_threshold = adjusted_threshold
        
        return {
            "status": "fallback_active",
            "action": "threshold_adjusted",
            "new_threshold": self.stability_threshold,
            "recommendation": "Consider reducing resonance sensitivity temporarily"
        }
    
    def resonance_chain_validator(self, resonance_data: Dict[str, Any]) -> bool:
        """
        Verifies resonance data integrity.
        
        Args:
            resonance_data: Resonance data to validate
            
        Returns:
            True if resonance data is valid, False otherwise
        """
        # Check required fields
        required_fields = ['id', 'phase', 'strength']
        for field in required_fields:
            if field not in resonance_data:
                logger.warning(f"Missing required field in resonance data: {field}")
                return False
        
        # Validate phase and strength ranges
        phase = resonance_data['phase']
        strength = resonance_data['strength']
        
        if not (0 <= phase < 2*np.pi):
            logger.warning(f"Invalid phase value: {phase}")
            return False
            
        if not (0 <= strength <= 1.0):
            logger.warning(f"Invalid strength value: {strength}")
            return False
            
        return True
    
    def activate_resonance(self, resonance_id: str, strength: float, phase: float) -> Dict[str, Any]:
        """
        Activate a resonance in the monitoring system.
        
        Args:
            resonance_id: Unique identifier for the resonance
            strength: Strength of the resonance (0-1.0)
            phase: Phase of the resonance (0-2π)
            
        Returns:
            Dict containing activation status
        """
        # Validate input
        resonance_data = {
            'id': resonance_id,
            'phase': phase,
            'strength': strength
        }
        
        if not self.resonance_chain_validator(resonance_data):
            return {
                "active": False,
                "error": "Invalid resonance data"
            }
        
        # Add to active resonances
        self.active_resonances[resonance_id] = {
            "strength": strength,
            "phase": phase,
            "activated_at": datetime.utcnow().isoformat()
        }
        
        logger.debug(f"Resonance activated: {resonance_id} (strength={strength:.2f}, phase={phase:.2f})")
        
        return {
            "active": True,
            "strength": strength,
            "phase": phase
        }
    
    def deactivate_resonance(self, resonance_id: str) -> bool:
        """
        Deactivate a resonance in the monitoring system.
        
        Args:
            resonance_id: Unique identifier for the resonance
            
        Returns:
            True if deactivation successful, False otherwise
        """
        if resonance_id in self.active_resonances:
            del self.active_resonances[resonance_id]
            logger.debug(f"Resonance deactivated: {resonance_id}")
            return True
        else:
            logger.warning(f"Resonance not found: {resonance_id}")
            return False
    
    def get_active_resonances(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active resonances.
        
        Returns:
            Dict mapping resonance IDs to resonance data
        """
        return self.active_resonances.copy()
    
    def check_alignment(self, check_interval: float = None) -> Dict[str, Any]:
        """
        Check phase alignment and stability across all active resonances.
        
        Args:
            check_interval: Optional interval between checks (in seconds)
            
        Returns:
            Dict containing alignment check results
        """
        current_time = datetime.utcnow()
        
        # If check_interval is provided, only check if enough time has passed
        if check_interval is not None:
            time_delta = (current_time - self.last_check_time).total_seconds()
            if time_delta < check_interval:
                return {
                    "status": "skipped",
                    "message": f"Check interval not reached ({time_delta:.1f}s < {check_interval:.1f}s)"
                }
        
        # Update last check time
        self.last_check_time = current_time
        
        # If no active resonances, return early
        if not self.active_resonances:
            return {
                "status": "stable",
                "message": "No active resonances to check",
                "stability_score": 1.0
            }
        
        # Calculate phase coherence
        phases = np.array([data['phase'] for data in self.active_resonances.values()])
        strengths = np.array([data['strength'] for data in self.active_resonances.values()])
        
        # Calculate weighted phase variance
        if len(phases) > 1:
            # Convert phases to complex numbers for circular statistics
            complex_phases = np.exp(1j * phases)
            
            # Calculate weighted mean phase
            weighted_sum = np.sum(complex_phases * strengths)
            mean_phase = np.angle(weighted_sum)
            
            # Calculate phase coherence (R)
            R = np.abs(weighted_sum) / np.sum(strengths)
            
            # Detect phase drift
            stability_score = R
            phase_drift = 1.0 - R
            
            # Log significant phase drift
            if phase_drift > (1.0 - self.stability_threshold):
                drift_event = {
                    "timestamp": current_time.isoformat(),
                    "phase_drift": phase_drift,
                    "active_resonances": len(self.active_resonances)
                }
                self.phase_drift_log.append(drift_event)
                logger.warning(f"Phase drift detected: {phase_drift:.4f}")
        else:
            # Single resonance is always coherent with itself
            stability_score = 1.0
            phase_drift = 0.0
            mean_phase = phases[0]
        
        # Add to history
        history_entry = {
            "timestamp": current_time.isoformat(),
            "stability_score": stability_score,
            "active_resonances": len(self.active_resonances)
        }
        self.resonance_history.append(history_entry)
        
        # Self-regulation
        self.self_regulate()
        
        # Determine status
        if stability_score >= self.stability_threshold:
            status = "stable"
        else:
            status = "unstable"
            logger.warning(f"Resonance instability detected: {stability_score:.4f} < {self.stability_threshold:.4f}")
        
        return {
            "status": status,
            "stability_score": stability_score,
            "phase_drift": phase_drift,
            "mean_phase": mean_phase,
            "active_resonances": len(self.active_resonances),
            "threshold": self.stability_threshold
        }
    
    def check_phase_stability(self) -> Dict[str, Any]:
        """
        Check phase stability across all active resonances.
        
        Returns:
            Dict containing phase stability check results
        """
        return self.check_alignment()
    
    def get_stability_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get historical stability data.
        
        Args:
            limit: Optional limit on number of history entries to return
            
        Returns:
            List of historical stability entries
        """
        if limit is not None:
            return self.resonance_history[-limit:]
        else:
            return self.resonance_history.copy()
    
    def get_drift_events(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get historical phase drift events.
        
        Args:
            limit: Optional limit on number of drift events to return
            
        Returns:
            List of historical phase drift events
        """
        if limit is not None:
            return self.phase_drift_log[-limit:]
        else:
            return self.phase_drift_log.copy()
