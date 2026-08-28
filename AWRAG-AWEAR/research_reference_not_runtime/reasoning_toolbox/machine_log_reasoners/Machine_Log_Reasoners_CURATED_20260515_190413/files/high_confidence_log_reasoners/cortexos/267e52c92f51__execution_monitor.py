"""
CortexOS Temporal Cognition v2.1
Module: Execution Monitor
Purpose: Monitors neuron firing patterns, execution performance, and detects anomalies
         in the neural processing flow. Acts as a watchdog for performance issues,
         failures, or rogue patterns.

This module implements the Agharmonic Law by providing:
- Harmonic Resonance monitoring across execution chains
- Temporal synchronization verification
- Self-regulation through anomaly detection
- Graceful degradation recommendations when performance issues are detected
"""

import logging
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Configure module logger
logger = logging.getLogger(__name__)

class ExecutionMonitor:
    """
    Monitors the execution of neural processes across the CortexOS architecture.
    Tracks performance metrics, detects anomalies, and ensures Agharmonic compliance.
    """
    
    def __init__(self, sampling_rate: float = 0.1, 
                 alert_threshold: float = 0.85,
                 history_length: int = 1000):
        """
        Initialize the ExecutionMonitor with monitoring parameters.
        
        Args:
            sampling_rate: Frequency of monitoring samples (0-1.0)
            alert_threshold: Threshold for triggering alerts (0-1.0)
            history_length: Number of execution records to maintain
        """
        self.sampling_rate = sampling_rate
        self.alert_threshold = alert_threshold
        self.history_length = history_length
        
        # Execution tracking
        self.execution_history = []
        self.anomaly_log = []
        self.performance_metrics = {}
        self.last_sync_time = datetime.utcnow()
        
        # Resonance tracking
        self.input_frequency_range = (0.5, 2.0)  # in GHz cognitive equivalent
        self.output_phase_alignment = 0.25
        self.resonance_threshold = 0.75
        
        logger.info("ExecutionMonitor initialized with sampling_rate=%.2f, alert_threshold=%.2f",
                   sampling_rate, alert_threshold)
    
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility for this module.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "input_range": self.input_frequency_range,
            "output_phase": self.output_phase_alignment,
            "threshold": self.resonance_threshold,
        }
    
    def interface_contract(self) -> Dict[str, List[str]]:
        """
        Defines all allowed function calls, accepted data structures, and outbound schema.
        
        Returns:
            Dict containing input and output interface specifications
        """
        return {
            "inputs": ["module_id", "execution_data", "performance_metrics", "resonance_pattern"],
            "outputs": ["execution_status", "anomaly_report", "performance_summary"]
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
        time_delta = (current_time - self.last_sync_time).total_seconds()
        
        if global_clock:
            self.timestep = global_clock.get_time()
        else:
            self.timestep = time_delta
            
        self.last_sync_time = current_time
        logger.debug("Clock synchronized. Timestep: %.4f", self.timestep)
        return True
    
    def self_regulate(self) -> None:
        """
        Implements feedback loop analysis, jitter buffer, and pattern anticipation.
        Core to stabilization of the monitoring system itself.
        """
        # Trim history if it exceeds the maximum length
        if len(self.execution_history) > self.history_length:
            self.execution_history = self.execution_history[-self.history_length:]
            
        # Check for internal anomalies
        if len(self.anomaly_log) > self.history_length * 0.5:
            logger.warning("High anomaly rate detected in monitoring system")
            self.anomaly_log = self.anomaly_log[-int(self.history_length * 0.3):]
            self.alert_threshold *= 1.1  # Temporarily increase threshold
            
        # Reset alert threshold if it was previously adjusted
        if self.alert_threshold > 0.85 and len(self.anomaly_log) < self.history_length * 0.1:
            self.alert_threshold = 0.85
            logger.info("Alert threshold normalized to %.2f", self.alert_threshold)
    
    def graceful_fallback(self) -> Dict[str, Any]:
        """
        Fallback to partial operation templates when upstream data is unavailable or corrupted.
        
        Returns:
            Dict containing fallback status and recommendations
        """
        logger.warning("Executing graceful fallback due to data corruption or unavailability")
        
        # Generate fallback metrics based on historical data
        if self.execution_history:
            recent_history = self.execution_history[-min(10, len(self.execution_history)):]
            avg_metrics = {
                "execution_time": np.mean([h.get("execution_time", 0) for h in recent_history]),
                "memory_usage": np.mean([h.get("memory_usage", 0) for h in recent_history]),
                "cpu_load": np.mean([h.get("cpu_load", 0) for h in recent_history]),
            }
        else:
            avg_metrics = {
                "execution_time": 0,
                "memory_usage": 0,
                "cpu_load": 0,
            }
            
        return {
            "status": "fallback_active",
            "estimated_metrics": avg_metrics,
            "confidence": 0.4,
            "recommendation": "Consider reducing sampling rate or disabling non-critical modules"
        }
    
    def resonance_chain_validator(self, output: Dict[str, Any]) -> bool:
        """
        Verifies resonance fingerprint when modules pass output to others.
        
        Args:
            output: Output data to validate
            
        Returns:
            True if resonance is valid, False otherwise
        """
        if "resonance_fingerprint" not in output:
            logger.warning("Missing resonance fingerprint in output")
            return False
            
        fingerprint = output["resonance_fingerprint"]
        
        # Validate fingerprint against expected patterns
        if not isinstance(fingerprint, dict):
            return False
            
        required_keys = ["source_id", "timestamp", "frequency", "phase"]
        if not all(k in fingerprint for k in required_keys):
            return False
            
        # Check if frequency is within acceptable range
        if not (self.input_frequency_range[0] <= fingerprint["frequency"] <= self.input_frequency_range[1]):
            logger.warning("Frequency out of range: %.2f", fingerprint["frequency"])
            return False
            
        return True
    
    def record_execution(self, module_id: str, execution_data: Dict[str, Any]) -> None:
        """
        Records execution metrics for a module.
        
        Args:
            module_id: Identifier of the module being monitored
            execution_data: Dictionary containing execution metrics
        """
        if not isinstance(execution_data, dict):
            logger.error("Invalid execution data format for module %s", module_id)
            return
            
        # Add timestamp and module identifier
        execution_data["timestamp"] = time.time()
        execution_data["module_id"] = module_id
        
        # Apply sampling based on configured rate
        if np.random.random() <= self.sampling_rate:
            self.execution_history.append(execution_data)
            
            # Update performance metrics
            if module_id not in self.performance_metrics:
                self.performance_metrics[module_id] = []
                
            self.performance_metrics[module_id].append({
                "execution_time": execution_data.get("execution_time", 0),
                "memory_usage": execution_data.get("memory_usage", 0),
                "timestamp": execution_data["timestamp"]
            })
            
            # Trim module-specific metrics
            if len(self.performance_metrics[module_id]) > 100:
                self.performance_metrics[module_id] = self.performance_metrics[module_id][-100:]
                
        # Self-regulation
        self.self_regulate()
    
    def detect_anomalies(self, module_id: str = None) -> List[Dict[str, Any]]:
        """
        Detects anomalies in execution patterns.
        
        Args:
            module_id: Optional module identifier to filter anomalies
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Filter history by module if specified
        if module_id:
            history = [h for h in self.execution_history if h.get("module_id") == module_id]
        else:
            history = self.execution_history
            
        if len(history) < 5:
            return anomalies  # Not enough data for anomaly detection
            
        # Extract execution times
        exec_times = np.array([h.get("execution_time", 0) for h in history])
        if exec_times.size > 0 and exec_times.std() > 0:
            # Detect execution time anomalies (Z-score)
            z_scores = np.abs((exec_times - exec_times.mean()) / exec_times.std())
            anomaly_indices = np.where(z_scores > 3)[0]  # Z-score > 3 indicates anomaly
            
            for idx in anomaly_indices:
                if idx < len(history):
                    anomaly = {
                        "type": "execution_time_anomaly",
                        "module_id": history[idx].get("module_id", "unknown"),
                        "timestamp": history[idx].get("timestamp", 0),
                        "value": history[idx].get("execution_time", 0),
                        "z_score": z_scores[idx],
                        "severity": min(1.0, z_scores[idx] / 10)
                    }
                    anomalies.append(anomaly)
                    
        # Log anomalies
        for anomaly in anomalies:
            if anomaly not in self.anomaly_log:
                self.anomaly_log.append(anomaly)
                logger.warning("Anomaly detected: %s (severity: %.2f)", 
                              anomaly["type"], anomaly["severity"])
                
        return anomalies
    
    def get_performance_summary(self, module_id: str = None) -> Dict[str, Any]:
        """
        Generates a performance summary for specified module or all modules.
        
        Args:
            module_id: Optional module identifier to filter metrics
            
        Returns:
            Dict containing performance summary
        """
        if module_id and module_id in self.performance_metrics:
            modules = {module_id: self.performance_metrics[module_id]}
        else:
            modules = self.performance_metrics
            
        summary = {}
        for mod_id, metrics in modules.items():
            if not metrics:
                continue
                
            exec_times = [m.get("execution_time", 0) for m in metrics]
            memory_usage = [m.get("memory_usage", 0) for m in metrics]
            
            summary[mod_id] = {
                "avg_execution_time": np.mean(exec_times) if exec_times else 0,
                "max_execution_time": np.max(exec_times) if exec_times else 0,
                "min_execution_time": np.min(exec_times) if exec_times else 0,
                "std_execution_time": np.std(exec_times) if exec_times else 0,
                "avg_memory_usage": np.mean(memory_usage) if memory_usage else 0,
                "sample_count": len(metrics),
                "last_execution": metrics[-1] if metrics else None
            }
            
        return {
            "timestamp": time.time(),
            "module_summaries": summary,
            "total_modules_monitored": len(modules),
            "anomaly_count": len(self.anomaly_log)
        }
    
    def monitor_resonance_field(self, resonance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitors resonance field stability and coherence.
        
        Args:
            resonance_data: Dictionary containing resonance field data
            
        Returns:
            Dict containing resonance monitoring results
        """
        if not isinstance(resonance_data, dict):
            logger.error("Invalid resonance data format")
            return {"status": "error", "message": "Invalid data format"}
            
        # Extract resonance patterns
        patterns = resonance_data.get("patterns", [])
        if not patterns:
            return {"status": "warning", "message": "No resonance patterns found"}
            
        # Analyze coherence
        coherence_scores = []
        for pattern in patterns:
            if "coherence" in pattern:
                coherence_scores.append(pattern["coherence"])
                
        if not coherence_scores:
            return {"status": "warning", "message": "No coherence scores found"}
            
        avg_coherence = np.mean(coherence_scores)
        min_coherence = np.min(coherence_scores)
        
        # Check for resonance instability
        if min_coherence < self.resonance_threshold:
            logger.warning("Resonance instability detected. Min coherence: %.2f", min_coherence)
            return {
                "status": "alert",
                "message": f"Resonance instability detected",
                "avg_coherence": avg_coherence,
                "min_coherence": min_coherence,
                "threshold": self.resonance_threshold,
                "recommendation": "Adjust phase harmonics or reduce cognitive load"
            }
            
        return {
            "status": "stable",
            "avg_coherence": avg_coherence,
            "min_coherence": min_coherence,
            "pattern_count": len(patterns)
        }
    
    def generate_execution_report(self) -> Dict[str, Any]:
        """
        Generates a comprehensive execution report across all monitored modules.
        
        Returns:
            Dict containing execution report
        """
        # Detect anomalies
        anomalies = self.detect_anomalies()
        
        # Get performance summary
        performance = self.get_performance_summary()
        
        # Generate report
        report = {
            "timestamp": time.time(),
            "report_id": f"exec_report_{int(time.time())}",
            "performance_summary": performance,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "modules_monitored": list(self.performance_metrics.keys()),
            "execution_samples": len(self.execution_history),
            "status": "healthy" if len(anomalies) == 0 else "anomalies_detected"
        }
        
      
(Content truncated due to size limit. Use line ranges to read in chunks)