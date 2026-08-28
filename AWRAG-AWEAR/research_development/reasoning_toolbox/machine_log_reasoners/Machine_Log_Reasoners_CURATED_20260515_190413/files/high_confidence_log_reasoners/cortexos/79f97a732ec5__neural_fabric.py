"""
CortexOS Temporal Cognition v2.1
Module: Neural Fabric
Purpose: Enables distributed synchronization across multiple neural processing nodes,
         maintaining coherent timing and resonance patterns in multi-node deployments.

This module implements the Agharmonic Law by providing:
- Temporal Synchronization across distributed nodes
- Harmonic Resonance through consistent timing signals across the fabric
- Self-regulation through adaptive latency compensation
- Resonance Chain Integrity through synchronized processing across nodes
"""

import json
import threading
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple

# Configure module logger
logger = logging.getLogger(__name__)

class NeuralFabricSync:
    """
    Manages synchronization across distributed neural processing nodes.
    Enables coherent timing and resonance patterns in multi-node deployments.
    """
    
    def __init__(self, fabric_id: str = None, config_file: str = 'data/fabric_config.json'):
        """
        Initialize the Neural Fabric synchronization system.
        
        Args:
            fabric_id: Unique identifier for this fabric instance (auto-generated if None)
            config_file: Path to the fabric configuration file
        """
        self.fabric_id = fabric_id or f"fabric-{uuid.uuid4().hex[:8]}"
        self.config_file = config_file
        self.config = self._load_config()
        
        # Node registry
        self.nodes = {}
        self.primary_node_id = None
        self.this_node_id = self.config.get('this_node_id', f"node-{uuid.uuid4().hex[:8]}")
        
        # Synchronization state
        self.last_sync_time = datetime.utcnow()
        self.sync_interval = self.config.get('sync_interval', 1.0)  # seconds
        self.latency_map = {}
        self._running = False
        self._lock = threading.Lock()
        
        # Agharmonic Law compliance
        self.input_frequency_range = (0.2, 5.0)  # in Hz
        self.output_phase_alignment = 0.0
        self.resonance_threshold = 0.85
        
        logger.info(f"NeuralFabricSync initialized with fabric_id={self.fabric_id}, node_id={self.this_node_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load fabric configuration from file.
        
        Returns:
            Dict containing fabric configuration
        """
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Fabric config file not found: {self.config_file}. Using default config.")
            return {
                "sync_interval": 1.0,
                "latency_threshold": 0.5,
                "auto_elect_primary": True,
                "heartbeat_timeout": 5.0,
                "max_nodes": 10
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in fabric config file: {e}")
            return {
                "sync_interval": 1.0,
                "latency_threshold": 0.5,
                "auto_elect_primary": True,
                "heartbeat_timeout": 5.0,
                "max_nodes": 10
            }
    
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility for this module.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "module": "neural_fabric",
            "rhythm_hz": 1 / self.sync_interval,
            "input_range": self.input_frequency_range,
            "output_phase": self.output_phase_alignment,
            "threshold": self.resonance_threshold
        }
    
    def interface_contract(self, node_data: Dict[str, Any]) -> bool:
        """
        Defines allowed function calls and verifies node compatibility.
        
        Args:
            node_data: Node data to verify compatibility with
            
        Returns:
            True if node meets the interface contract
            
        Raises:
            ValueError: If node data doesn't meet requirements
        """
        required_fields = ['node_id', 'endpoint', 'capabilities']
        
        for field in required_fields:
            if field not in node_data:
                raise ValueError(f"Node data missing required field: {field}")
        
        # Verify capabilities
        required_capabilities = ['sync_clock', 'heartbeat']
        for capability in required_capabilities:
            if capability not in node_data['capabilities']:
                raise ValueError(f"Node missing required capability: {capability}")
        
        return True
    
    def cognitive_energy_flow(self, sync_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes synchronization data to maintain balanced information flow.
        
        Args:
            sync_data: Synchronization data to normalize
            
        Returns:
            Normalized synchronization data
        """
        # Ensure timestamp is present
        if 'timestamp' not in sync_data:
            sync_data['timestamp'] = datetime.utcnow().isoformat()
            
        # Normalize latency values to [0.0, 1.0] range
        if 'latencies' in sync_data:
            max_latency = max(sync_data['latencies'].values()) if sync_data['latencies'] else 1.0
            normalized_latencies = {}
            
            for node_id, latency in sync_data['latencies'].items():
                normalized_latencies[node_id] = min(1.0, latency / max(0.001, max_latency))
                
            sync_data['normalized_latencies'] = normalized_latencies
            
        # Add signal strength
        sync_data['signal_strength'] = 0.9  # Consistent signal strength for fabric signals
        
        return sync_data
    
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
        Core to stabilization of the fabric synchronization.
        """
        # Check for nodes with high latency
        high_latency_nodes = []
        latency_threshold = self.config.get('latency_threshold', 0.5)
        
        for node_id, latency in self.latency_map.items():
            if latency > latency_threshold:
                high_latency_nodes.append(node_id)
                
        if high_latency_nodes:
            logger.warning(f"High latency detected for nodes: {high_latency_nodes}")
            
            # Adjust sync interval if multiple nodes have high latency
            if len(high_latency_nodes) > len(self.nodes) * 0.3:  # If >30% of nodes have high latency
                new_interval = self.sync_interval * 1.2  # Increase by 20%
                logger.warning(f"Multiple nodes with high latency. Adjusting sync interval from "
                              f"{self.sync_interval:.2f}s to {new_interval:.2f}s")
                self.sync_interval = new_interval
    
    def graceful_fallback(self) -> Dict[str, Any]:
        """
        Provides fallback mechanisms when fabric synchronization cannot be maintained.
        
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning("Executing graceful fallback due to fabric synchronization issues")
        
        # Increase sync interval to reduce network load
        adjusted_interval = self.sync_interval * 1.5
        logger.info(f"Adjusting sync interval to {adjusted_interval:.2f}s for stability")
        self.sync_interval = adjusted_interval
        
        # If primary node is unreachable, trigger election
        if self.primary_node_id and self.primary_node_id not in self.nodes:
            logger.warning(f"Primary node {self.primary_node_id} unreachable. Triggering election.")
            self._elect_primary_node()
        
        return {
            "status": "fallback_active",
            "action": "sync_adjusted",
            "new_sync_interval": self.sync_interval,
            "primary_node": self.primary_node_id,
            "recommendation": "Check network connectivity between nodes"
        }
    
    def resonance_chain_validator(self, sync_data: Dict[str, Any]) -> bool:
        """
        Verifies synchronization data integrity across the fabric.
        
        Args:
            sync_data: Synchronization data to validate
            
        Returns:
            True if synchronization data is valid, False otherwise
        """
        try:
            # Validate required fields
            required_fields = ['timestamp', 'source_node_id', 'sequence_number']
            for field in required_fields:
                if field not in sync_data:
                    logger.warning(f"Missing required field in sync data: {field}")
                    return False
            
            # Validate timestamp format and recency
            timestamp = sync_data['timestamp']
            datetime.fromisoformat(timestamp)
            
            timestamp_time = datetime.fromisoformat(timestamp).timestamp()
            current_time = time.time()
            
            if abs(current_time - timestamp_time) > 5.0:
                logger.warning(f"Timestamp too far from current time: {abs(current_time - timestamp_time):.2f}s")
                return False
            
            # Validate source node
            source_node_id = sync_data['source_node_id']
            if source_node_id not in self.nodes and source_node_id != self.this_node_id:
                logger.warning(f"Unknown source node: {source_node_id}")
                return False
                
            return True
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid sync data format: {e}")
            return False
    
    def fabric_init(self) -> bool:
        """
        Initialize the neural fabric.
        
        Returns:
            True if initialization successful, False otherwise
        """
        logger.info(f"Initializing neural fabric: {self.fabric_id}")
        
        # Register this node
        self.register_node(self.this_node_id, {
            "node_id": self.this_node_id,
            "endpoint": "local",
            "capabilities": ["sync_clock", "heartbeat", "primary_eligible"],
            "status": "active"
        })
        
        # If auto-elect is enabled and no primary node exists, elect one
        if self.config.get('auto_elect_primary', True) and not self.primary_node_id:
            self._elect_primary_node()
        
        return True
    
    def register_node(self, node_id: str, node_data: Dict[str, Any]) -> bool:
        """
        Register a node in the neural fabric.
        
        Args:
            node_id: Unique identifier for the node
            node_data: Node configuration and capabilities
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Validate node data
            self.interface_contract(node_data)
            
            with self._lock:
                # Check if max nodes limit is reached
                max_nodes = self.config.get('max_nodes', 10)
                if len(self.nodes) >= max_nodes and node_id not in self.nodes:
                    logger.warning(f"Max nodes limit reached ({max_nodes}). Cannot register node: {node_id}")
                    return False
                
                # Register or update node
                if node_id not in self.nodes:
                    logger.info(f"Registering new node: {node_id}")
                else:
                    logger.info(f"Updating node: {node_id}")
                
                node_data['last_seen'] = datetime.utcnow().isoformat()
                self.nodes[node_id] = node_data
                
                # Initialize latency for new node
                if node_id not in self.latency_map:
                    self.latency_map[node_id] = 0.0
                
                return True
        except ValueError as e:
            logger.error(f"Failed to register node {node_id}: {e}")
            return False
    
    def unregister_node(self, node_id: str) -> bool:
        """
        Unregister a node from the neural fabric.
        
        Args:
            node_id: Unique identifier for the node
            
        Returns:
            True if unregistration successful, False otherwise
        """
        with self._lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                
                # Remove from latency map
                if node_id in self.latency_map:
                    del self.latency_map[node_id]
                
                # If primary node is unregistered, elect a new one
                if node_id == self.primary_node_id:
                    logger.warning(f"Primary node {node_id} unregistered. Triggering election.")
                    self._elect_primary_node()
                
                logger.info(f"Node unregistered: {node_id}")
                return True
            else:
                logger.warning(f"Node not found: {node_id}")
                return False
    
    def propagate_clock_tick(self, timestamp: str = None) -> Dict[str, Any]:
        """
        Propagate a clock tick to all nodes in the fabric.
        
        Args:
            timestamp: Optional timestamp for the clock tick (auto-generated if None)
            
        Returns:
            Dict containing propagation results
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        sync_data = {
            "timestamp": timestamp,
            "source_node_id": self.this_node_id,
            "sequence_number": int(time.time() * 1000) % 1000000,
            "primary_node_id": self.primary_node_id
        }
        
        # Validate sync data
        if not self.resonance_chain_validator(sync_data):
            logger.error("Failed to validate sync data for propagation")
            return {"status": "error", "message": "Invalid sync data"}
        
        # Normalize sync data
        normalized_data = self.cognitive_energy_flow(sync_data)
        
        # In a real implementation, this would send the tick to all nodes
        # For this stub, we just log it
        logger.info(f"Clock tick propagated: {normalized_data['timestamp']}")
        
        return {
            "status": "success",
            "timestamp": normalized_data['timestamp'],
            "propagated_to": list(self.nodes.keys())
        }
    
    def sync_node_health(self) -> Dict[str, Any]:
        """
        Synchronize health status across all nodes.
        
        Returns:
            Dict containing health synchronization results
(Content truncated due to size limit. Use line ranges to read in chunks)"""