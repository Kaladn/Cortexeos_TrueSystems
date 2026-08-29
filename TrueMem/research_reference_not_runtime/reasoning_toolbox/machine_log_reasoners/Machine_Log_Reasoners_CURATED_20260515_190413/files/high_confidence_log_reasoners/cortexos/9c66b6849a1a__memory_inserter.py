"""
Memory Inserter module for CortexOS Temporal Cognition v2.1

This module controls memory insertion operations with trust score gating,
retry logic, and robust fallback mechanisms. It implements all seven
Agharmonic Law interfaces for full compliance.

Author: Manus
Date: May 18, 2025
"""

import json
import os
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Import required modules
from cortexos_cognitive_bridge import CortexOSCognitiveBridge
from neuron_mapper import NeuronMapper
from expandable_cortex_cube import ExpandableCortexCube
from global_sync_manager import GlobalSyncManager
from resonance_monitor import ResonanceMonitor

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("memory_inserter")

class MemoryInserter:
    """
    Controls memory insertion operations with trust score gating,
    retry logic, and robust fallback mechanisms.
    """
    
    def __init__(self, 
                 bridge: CortexOSCognitiveBridge,
                 sync_manager: Optional[GlobalSyncManager] = None,
                 resonance_monitor: Optional[ResonanceMonitor] = None):
        """
        Initialize the memory inserter with required components.
        
        Args:
            bridge: CortexOS cognitive bridge for memory operations
            sync_manager: Global synchronization manager (optional)
            resonance_monitor: Resonance stability monitor (optional)
        """
        self.bridge = bridge
        self.sync_manager = sync_manager
        self.resonance_monitor = resonance_monitor
        
        # Trust and coherence thresholds
        self.trust_threshold = 0.65
        self.coherence_threshold = 0.75
        
        # Retry configuration
        self.max_retries = 3
        self.retry_backoff = 1.5  # seconds
        
        # Memory insertion metrics
        self.metrics = {
            "total_attempted": 0,
            "successful": 0,
            "rejected_trust": 0,
            "rejected_coherence": 0,
            "failed_after_retry": 0,
            "recovered_by_retry": 0
        }
        
        # Memory insertion registry
        self.insertion_registry = {}
        
        # Last synchronization timestamp
        self.last_sync = datetime.utcnow()
        
        # Thread lock for concurrent operations
        self._lock = threading.Lock()
        
        logger.info("Memory Inserter initialized with trust threshold: %.2f, coherence threshold: %.2f", 
                   self.trust_threshold, self.coherence_threshold)

    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes frequency compatibility parameters for the memory inserter.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "module": "memory_inserter",
            "input_frequency_range": [0.4, 1.1],
            "output_phase_alignment": 0.1,
            "resonance_threshold": 0.7,
            "version": "2.1.0"
        }
    
    def interface_contract(self, memory_data: Dict[str, Any]) -> bool:
        """
        Validates input data against the interface contract.
        
        Args:
            memory_data: Memory data to validate
            
        Returns:
            True if valid, raises exception otherwise
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Required fields
        required_fields = ["id", "harmonics_vector", "trust_score", "coherence_score"]
        
        # Check for missing fields
        missing = [field for field in required_fields if field not in memory_data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        
        # Validate field types
        if not isinstance(memory_data["id"], str):
            raise ValueError("Field 'id' must be a string")
        
        if not isinstance(memory_data["harmonics_vector"], list):
            raise ValueError("Field 'harmonics_vector' must be a list")
        
        if not isinstance(memory_data["trust_score"], (int, float)) or not 0 <= memory_data["trust_score"] <= 1:
            raise ValueError("Field 'trust_score' must be a float between 0 and 1")
        
        if not isinstance(memory_data["coherence_score"], (int, float)) or not 0 <= memory_data["coherence_score"] <= 1:
            raise ValueError("Field 'coherence_score' must be a float between 0 and 1")
        
        return True
    
    def cognitive_energy_flow(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes signal amplitude and information flow.
        
        Args:
            memory_data: Memory data to normalize
            
        Returns:
            Normalized memory data
        """
        # Create a copy to avoid modifying the original
        normalized = memory_data.copy()
        
        # Normalize trust and coherence scores to prevent extreme values
        normalized["trust_score"] = max(min(normalized["trust_score"], 1.0), 0.0)
        normalized["coherence_score"] = max(min(normalized["coherence_score"], 1.0), 0.0)
        
        # Calculate energy level based on trust and coherence
        energy_level = (normalized["trust_score"] * 0.6) + (normalized["coherence_score"] * 0.4)
        normalized["energy_level"] = energy_level
        
        # Add timestamp for temporal tracking
        normalized["timestamp"] = datetime.utcnow().isoformat()
        
        return normalized
    
    def sync_clock(self) -> bool:
        """
        Synchronizes with the global temporal framework.
        
        Returns:
            True if synchronized, False otherwise
        """
        # If sync manager is available, use it
        if self.sync_manager:
            try:
                sync_state = self.sync_manager.get_sync_state()
                self.last_sync = datetime.utcnow()
                
                # Update thresholds based on system state if needed
                if "memory_thresholds" in sync_state:
                    self.trust_threshold = sync_state["memory_thresholds"].get("trust", self.trust_threshold)
                    self.coherence_threshold = sync_state["memory_thresholds"].get("coherence", self.coherence_threshold)
                
                logger.debug("Synchronized with GlobalSyncManager. Updated thresholds: trust=%.2f, coherence=%.2f", 
                           self.trust_threshold, self.coherence_threshold)
                return True
            except Exception as e:
                logger.warning("Failed to synchronize with GlobalSyncManager: %s", str(e))
                return False
        
        # If no sync manager, use internal clock
        now = datetime.utcnow()
        if (now - self.last_sync).total_seconds() > 60:  # 1 minute sync interval
            self.last_sync = now
            logger.debug("Internal clock synchronized")
            return True
        
        return False
    
    def self_regulate(self) -> None:
        """
        Implements feedback loops for stability.
        """
        # Check insertion metrics for anomalies
        with self._lock:
            total = self.metrics["total_attempted"]
            if total == 0:
                return
            
            # Calculate rejection rates
            trust_rejection_rate = self.metrics["rejected_trust"] / total
            coherence_rejection_rate = self.metrics["rejected_coherence"] / total
            failure_rate = self.metrics["failed_after_retry"] / total
            
            # Adjust thresholds if rejection rates are too high or too low
            if trust_rejection_rate > 0.5:  # More than 50% rejected due to trust
                self.trust_threshold = max(0.5, self.trust_threshold - 0.05)
                logger.info("Self-regulation: Lowered trust threshold to %.2f due to high rejection rate", 
                           self.trust_threshold)
            elif trust_rejection_rate < 0.05:  # Less than 5% rejected due to trust
                self.trust_threshold = min(0.9, self.trust_threshold + 0.05)
                logger.info("Self-regulation: Raised trust threshold to %.2f due to low rejection rate", 
                           self.trust_threshold)
            
            # Similar for coherence threshold
            if coherence_rejection_rate > 0.5:
                self.coherence_threshold = max(0.5, self.coherence_threshold - 0.05)
                logger.info("Self-regulation: Lowered coherence threshold to %.2f due to high rejection rate", 
                           self.coherence_threshold)
            elif coherence_rejection_rate < 0.05:
                self.coherence_threshold = min(0.9, self.coherence_threshold + 0.05)
                logger.info("Self-regulation: Raised coherence threshold to %.2f due to low rejection rate", 
                           self.coherence_threshold)
            
            # Adjust retry parameters if failure rate is high
            if failure_rate > 0.3:  # More than 30% fail even after retries
                self.max_retries = min(5, self.max_retries + 1)
                logger.info("Self-regulation: Increased max retries to %d due to high failure rate", 
                           self.max_retries)
            
            # Periodically reset metrics to avoid long-term bias
            if total > 10000:
                logger.info("Self-regulation: Resetting metrics after %d operations", total)
                self.metrics = {key: 0 for key in self.metrics}
    
    def graceful_fallback(self, memory_data: Dict[str, Any], error: Exception) -> Tuple[bool, Dict[str, Any]]:
        """
        Provides mechanisms for partial operation during failures.
        
        Args:
            memory_data: Memory data that failed to insert
            error: Exception that occurred
            
        Returns:
            Tuple of (success, result_data)
        """
        logger.warning("Initiating graceful fallback for memory ID %s: %s", 
                      memory_data.get("id", "unknown"), str(error))
        
        # Strategy 1: Reduce vector dimensionality if too complex
        if "harmonics_vector" in memory_data and len(memory_data["harmonics_vector"]) > 100:
            try:
                # Simplify by taking only the strongest dimensions
                vector = memory_data["harmonics_vector"]
                indexed_vector = [(i, v) for i, v in enumerate(vector)]
                sorted_vector = sorted(indexed_vector, key=lambda x: abs(x[1]), reverse=True)
                top_indices = [idx for idx, _ in sorted_vector[:100]]
                
                simplified_vector = [0.0] * len(vector)
                for idx in top_indices:
                    simplified_vector[idx] = vector[idx]
                
                fallback_data = memory_data.copy()
                fallback_data["harmonics_vector"] = simplified_vector
                fallback_data["_fallback_applied"] = "dimensionality_reduction"
                
                logger.info("Fallback: Applied dimensionality reduction for memory ID %s", 
                           memory_data.get("id", "unknown"))
                return True, fallback_data
            except Exception as e:
                logger.warning("Fallback strategy 1 failed: %s", str(e))
        
        # Strategy 2: Store in temporary buffer if bridge is unavailable
        try:
            fallback_file = f"fallback_memory_{int(time.time())}.json"
            fallback_path = os.path.join(os.path.dirname(__file__), "..", "data", "fallbacks", fallback_file)
            os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
            
            with open(fallback_path, 'w') as f:
                json.dump(memory_data, f)
            
            logger.info("Fallback: Stored memory ID %s in fallback file %s", 
                       memory_data.get("id", "unknown"), fallback_path)
            
            fallback_data = memory_data.copy()
            fallback_data["_fallback_applied"] = "temporary_storage"
            fallback_data["_fallback_path"] = fallback_path
            
            return True, fallback_data
        except Exception as e:
            logger.error("All fallback strategies failed for memory ID %s: %s", 
                        memory_data.get("id", "unknown"), str(e))
            
            # Last resort: Return minimal success with error info
            minimal_data = {
                "id": memory_data.get("id", "unknown"),
                "_fallback_applied": "minimal_record",
                "_error": str(error),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return False, minimal_data
    
    def resonance_chain_validator(self, memory_data: Dict[str, Any]) -> bool:
        """
        Verifies resonance integrity across the chain.
        
        Args:
            memory_data: Memory data to validate
            
        Returns:
            True if valid, False otherwise
        """
        # If resonance monitor is available, use it
        if self.resonance_monitor:
            try:
                # Check if this memory insertion would disrupt resonance stability
                stability_check = self.resonance_monitor.check_insertion_impact(
                    memory_data.get("harmonics_vector", []),
                    memory_data.get("energy_level", 0.5)
                )
                
                if not stability_check["stable"]:
                    logger.warning("Resonance chain validation failed: %s", stability_check["reason"])
                    return False
                
                logger.debug("Resonance chain validation passed with stability score: %.2f", 
                           stability_check.get("stability_score", 0))
                return True
            except Exception as e:
                logger.warning("Failed to validate resonance chain: %s", str(e))
                # Fall through to basic validation
        
        # Basic validation if no resonance monitor
        try:
            # Check for extreme values in vector that might cause resonance disruption
            vector = memory_data.get("harmonics_vector", [])
            if not vector:
                return True
            
            # Check for NaN or infinity
            if any(not isinstance(v, (int, float)) or v != v or abs(v) == float('inf') for v in vector):
                logger.warning("Resonance chain validation failed: Vector contains invalid values")
                return False
            
            # Check for extreme amplitudes
            max_amplitude = max(abs(v) for v in vector)
            if max_amplitude > 10.0:  # Arbitrary threshold
                logger.warning("Resonance chain validation failed: Vector contains extreme amplitude: %.2f", 
                             max_amplitude)
                return False
            
            return True
        except Exception as e:
            logger.error("Error in basic resonance validation: %s", str(e))
            return False
    
    def insert_vectorized_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserts a single memory vector with trust score gating and retry logic.
        
        Args:
            memory_data: Memory data to insert
            
        Returns:
            Result of the insertion operation
        """
        # Update metrics
        with self._lock:
            self.metrics["total_attempted"] += 1
        
        # Validate interface contract
        try:
            self.interface_contract(memory_data)
        except ValueError as e:
            logger.warning("Interface contract validation failed: %s", str(e))
            with self._lock:
                self.metrics["failed_after_retry"] += 1
            return {"success": False, "error": str(e), "stage": "validation"}
        
        # Normalize data through cognitive energy flow
        try:
            normalized_data = self.cognitive_energy_flow(memory_data)
        except Exception as e:
            logger.warning("Cognitive energy flow normalization failed: %s", str(e))
            with self._lock:
                self.metrics["failed_after_retry"] += 1
            return {"success": False, "error": str(e), "stage": "normalization"}
        
        # Apply trust score gating
        if normalized_data["trust_score"] < self.trust_threshold:
            logger.info("Memory rejected due to low trust score: %.2f < %.2f (threshold)", 
                       normalized_data["trust_score"], self.trust_threshold)
            with self._lock:
                self.metrics["rejected_trust"] += 1
            return {"success": False, "reason": "trust_score_below_threshold", 
                    "score": normalized_data["trust_score"], "threshold": self.trust_threshold}
        
        # Apply coherence score gating
        if normalized_data["coherence_score"] < self.coherence_threshold:
            logger.info("Memory rejected due to low coherence score: %.2f < %.2f (threshold)", 
                       normalized_data["coherence_score"], self.coherence_threshold)
            with self._lock:
                self.metrics["rejected_coherence"] += 1
            return {"success": False, "reason": "coherence_score_below_threshold", 
                    "score": normalized_data["coherence_score"], "threshold": self.coherence_threshold}
        
        # Validate resonance chain integrity
        if not self.resonance_chain_validator(normalized_data):
            logger.warning("Memory rejected due to resonance chain validation failure")
            with self._lock:
                self.metrics["rejected_coherence"] += 1  # Using coherence metric for resonance failures
            return {"success": False, "reason": "resonance_chain_validation_failed"}
        
        # Attempt insertion with retry logic
        memory_id = normalized_data.get("id", "unknown")
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                # Synchronize with global clock before insertion
                self.sync_clock()
                
                # Attempt to insert memory
                self.bridge.submit_memory(memory_id, normalized_data["harmonics_vector"])
                
                # Record successful insertion
                with self._lock:
                    self.metrics["successful"] += 1
                    if retry_count > 0:
                        self.metrics["recovered_by_retry"] += 1
                
                # Update insertion registry
                self.insertion_registry[memory_id] = {
                    "timestamp": normalized_data["timestamp"],
                    "trust_score": normalized_data["trust_score"],
                    "coherence_score": normalized_data["coherence_score"],
                    "retries": retry_count
                }
                
                logger.info("Successfully inserted memory ID %s (retries: %d)", memory_id, retry_count)
                
                # Self-regulate after successful insertion
                self.self_regulate()
                
                return {
                    "success": True, 
                    "memory_id": memory_id,
                    "retries": retry_count,
                    "timestamp": normalized_data["timestamp"]
                }
            
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_count <= self.max_retries:
                    # Calculate backoff time with exponential increase
                    backoff_time = self.retry_backoff * (2 ** (retry_count - 1))
                    logger.warning("Insertion failed for memory ID %s, retrying in %.1f seconds (attempt %d/%d): %s", 
                                  memory_id, backoff_time, retry_count, self.max_retries, str(e))
                    time.sleep(backoff_time)
                    
                    # Rebalance resonance for retry if resonance monitor is available
                    if self.resonance_monitor:
                        try:
                            self.resonance_monitor.rebalance_for_insertion(
                                normalized_data.get("harmonics_vector", [])
                            )
                            logger.info("Rebalanced resonance for retry")
                        except Exception as re:
                            logger.warning("Failed to rebalance resonance: %s", str(re))
                else:
                    logger.error("Insertion failed for memory ID %s after %d retries: %s", 
                                memory_id, self.max_retries, str(e))
                    with self._lock:
                        self.metrics["failed_after_retry"] += 1
        
        # All retries failed, attempt graceful fallback
        success, fallback_data = self.graceful_fallback(normalized_data, last_error)
        
        if success:
            logger.info("Applied graceful fallback for memory ID %s: %s", 
                       memory_id, fallback_data.get("_fallback_applied", "unknown"))
            return {
                "success": True,
                "memory_id": memory_id,
                "fallback_applied": fallback_data.get("_fallback_applied"),
                "fallback_path": fallback_data.get("_fallback_path"),
                "timestamp": normalized_data["timestamp"]
            }
        else:
            logger.error("All insertion attempts and fallbacks failed for memory ID %s", memory_id)
            return {
                "success": False,
                "memory_id": memory_id,
                "error": str(last_error),
                "stage": "insertion_and_fallback"
            }
    
    def insert_from_file(self, input_jsonl_path: str, flush_every: int = 1000) -> Dict[str, Any]:
        """
        Batch inserts from a vectorized JSONL file with comprehensive error handling.
        
        Args:
            input_jsonl_path: Path to the JSONL file containing memory vectors
            flush_every: Number of entries after which to flush the memory cube
            
        Returns:
            Summary of the batch insertion operation
        """
        if not os.path.exists(input_jsonl_path):
            logger.error("Input file not found: %s", input_jsonl_path)
            return {"success": False, "error": "Input file not found"}
        
        start_time = time.time()
        results = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "rejected_trust": 0,
            "rejected_coherence": 0,
            "fallbacks_applied": 0,
            "errors": []
        }
        
        try:
            with open(input_jsonl_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        # Parse JSON entry
                        entry = json.loads(line.strip())
                        
                        # Insert memory
                        result = self.insert_vectorized_memory(entry)
                        results["total_processed"] += 1
                        
                        # Process result
                        if result["success"]:
                            results["successful"] += 1
                            if "fallback_applied" in result:
                                results["fallbacks_applied"] += 1
                        else:
                            results["failed"] += 1
                            if result.get("reason") == "trust_score_below_threshold":
                                results["rejected_trust"] += 1
                            elif result.get("reason") == "coherence_score_below_threshold":
                                results["rejected_coherence"] += 1
                            
                            # Record error (limit to prevent excessive logging)
                            if len(results["errors"]) < 100:
                                results["errors"].append({
                                    "line": line_num,
                                    "memory_id": entry.get("id", "unknown"),
                                    "error": result.get("error", "Unknown error"),
                                    "stage": result.get("stage", "unknown")
                                })
                        
                        # Flush periodically
                        if results["total_processed"] % flush_every == 0:
                            if hasattr(self.bridge.cube, 'flush'):
                                self.bridge.cube.flush()
                            logger.info("Processed %d entries. Cube flushed (if applicable).", 
                                       results["total_processed"])
                            
                            # Self-regulate periodically
                            self.self_regulate()
                    
                    except json.JSONDecodeError as e:
                        logger.warning("Skipping line %d due to JSONDecodeError: %s", line_num, str(e))
                        results["failed"] += 1
                        if len(results["errors"]) < 100:
                            results["errors"].append({
                                "line": line_num,
                                "error": f"JSONDecodeError: {str(e)}",
                                "stage": "parsing"
                            })
                    except Exception as e:
                        logger.warning("Error processing entry at line %d: %s", line_num, str(e))
                        results["failed"] += 1
                        if len(results["errors"]) < 100:
                            results["errors"].append({
                                "line": line_num,
                                "error": str(e),
                                "stage": "processing"
                            })
            
            # Final flush
            if hasattr(self.bridge.cube, 'flush'):
                self.bridge.cube.flush()
            
            # Calculate statistics
            elapsed_time = time.time() - start_time
            results["elapsed_seconds"] = elapsed_time
            results["entries_per_second"] = results["total_processed"] / elapsed_time if elapsed_time > 0 else 0
            
            # Get cube statistics if available
            if hasattr(self.bridge.cube, 'get_stats'):
                try:
                    cube_stats = self.bridge.cube.get_stats()
                    results["cube_stats"] = cube_stats
                except Exception as e:
                    logger.warning("Failed to get cube statistics: %s", str(e))
            
            # Log summary
            logger.info("\n--- Memory Insertion Summary ---")
            logger.info("Total entries processed: %d", results["total_processed"])
            logger.info("Successful insertions: %d (%.1f%%)", 
                       results["successful"], 
                       (results["successful"] / results["total_processed"] * 100) if results["total_processed"] > 0 else 0)
            logger.info("Failed insertions: %d (%.1f%%)", 
                       results["failed"], 
                       (results["failed"] / results["total_processed"] * 100) if results["total_processed"] > 0 else 0)
            logger.info("Rejected due to trust threshold: %d", results["rejected_trust"])
            logger.info("Rejected due to coherence threshold: %d", results["rejected_coherence"])
            logger.info("Fallbacks applied: %d", results["fallbacks_applied"])
            logger.info("Processing time: %.2f seconds (%.2f entries/sec)", 
                       results["elapsed_seconds"], results["entries_per_second"])
            
            return results
        
        except Exception as e:
            logger.error("Fatal error during batch insertion: %s", str(e))
            results["success"] = False
            results["fatal_error"] = str(e)
            return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Returns current memory insertion metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            return self.metrics.copy()
    
    def recover_fallbacks(self) -> Dict[str, Any]:
        """
        Attempts to recover and process memories from fallback storage.
        
        Returns:
            Summary of recovery operation
        """
        fallback_dir = os.path.join(os.path.dirname(__file__), "..", "data", "fallbacks")
        if not os.path.exists(fallback_dir):
            logger.info("No fallback directory found at %s", fallback_dir)
            return {"success": True, "recovered": 0, "failed": 0}
        
        results = {
            "recovered": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            fallback_files = [f for f in os.listdir(fallback_dir) if f.startswith("fallback_memory_") and f.endswith(".json")]
            logger.info("Found %d fallback files to recover", len(fallback_files))
            
            for file_name in fallback_files:
                file_path = os.path.join(fallback_dir, file_name)
                try:
                    with open(file_path, 'r') as f:
                        memory_data = json.load(f)
                    
                    # Attempt to reinsert
                    result = self.insert_vectorized_memory(memory_data)
                    
                    if result["success"]:
                        # Remove fallback file after successful recovery
                        os.remove(file_path)
                        results["recovered"] += 1
                        logger.info("Successfully recovered memory from %s", file_path)
                    else:
                        results["failed"] += 1
                        if len(results["errors"]) < 100:
                            results["errors"].append({
                                "file": file_path,
                                "memory_id": memory_data.get("id", "unknown"),
                                "error": result.get("error", "Unknown error"),
                                "stage": result.get("stage", "unknown")
                            })
                        logger.warning("Failed to recover memory from %s: %s", 
                                      file_path, result.get("error", "Unknown error"))
                
                except Exception as e:
                    results["failed"] += 1
                    if len(results["errors"]) < 100:
                        results["errors"].append({
                            "file": file_path,
                            "error": str(e),
                            "stage": "recovery"
                        })
                    logger.warning("Error recovering memory from %s: %s", file_path, str(e))
            
            logger.info("Fallback recovery complete. Recovered: %d, Failed: %d", 
                       results["recovered"], results["failed"])
            results["success"] = True
            return results
        
        except Exception as e:
            logger.error("Fatal error during fallback recovery: %s", str(e))
            results["success"] = False
            results["fatal_error"] = str(e)
            return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Insert harmonic memory vectors using CortexOS Cognitive Bridge.")
    parser.add_argument('--input', required=True, help='Path to vectorized JSONL file')
    parser.add_argument('--trust-threshold', type=float, default=0.65, help='Trust score threshold (0-1)')
    parser.add_argument('--coherence-threshold', type=float, default=0.75, help='Coherence score threshold (0-1)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum retry attempts')
    parser.add_argument('--recover-fallbacks', action='store_true', help='Recover memories from fallback storage')
    parser.add_argument('--flush-every', type=int, default=1000, help='Flush cube after this many insertions')
    args = parser.parse_args()

    # Initialize components
    cube = ExpandableCortexCube(chunk_size=64)
    mapper = NeuronMapper(cube_shape=(1024, 1024, 1024), spacing=16)
    bridge = CortexOSCognitiveBridge(cube, mapper)
    
    # Try to import optional components
    try:
        from global_sync_manager import GlobalSyncManager
        sync_manager = GlobalSyncManager()
        logger.info("GlobalSyncManager initialized")
    except ImportError:
        logger.warning("GlobalSyncManager not available, running without global synchronization")
        sync_manager = None
    
    try:
        from resonance_monitor import ResonanceMonitor
        resonance_monitor = ResonanceMonitor()
        logger.info("ResonanceMonitor initialized")
    except ImportError:
        logger.warning("ResonanceMonitor not available, running without resonance monitoring")
        resonance_monitor = None
    
    # Initialize memory inserter
    inserter = MemoryInserter(bridge, sync_manager, resonance_monitor)
    inserter.trust_threshold = args.trust_threshold
    inserter.coherence_threshold = args.coherence_threshold
    inserter.max_retries = args.max_retries
    
    # Recover fallbacks if requested
    if args.recover_fallbacks:
        recovery_results = inserter.recover_fallbacks()
        print(f"Fallback recovery: {recovery_results['recovered']} recovered, {recovery_results['failed']} failed")
    
    # Process input file
    results = inserter.insert_from_file(args.input, flush_every=args.flush_every)
    
    # Print summary
    print("\n=== Memory Insertion Complete ===")
    print(f"Total processed: {results['total_processed']}")
    print(f"Successful: {results['successful']} ({results['successful']/results['total_processed']*100:.1f}% if results['total_processed'] > 0 else 0)")
    print(f"Failed: {results['failed']}")
    print(f"Processing time: {results['elapsed_seconds']:.2f} seconds ({results['entries_per_second']:.2f} entries/sec)")
    
    if "cube_stats" in results:
        print("\n=== Cube Statistics ===")
        stats = results["cube_stats"]
        print(f"Chunks created: {stats.get('chunks_created', 'N/A')}")
        print(f"Active voxels: {stats.get('active_voxels_in_chunks', 'N/A')}")
        if "activations_by_chunk" in stats:
            print(f"Activations by chunk: {stats['activations_by_chunk']}")
