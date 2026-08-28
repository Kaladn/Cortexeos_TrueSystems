Data Ingestor module for CortexOS.
Processes and vectorizes input data from various sources for neural storage.

This module implements the Agharmonic Law by providing:
- Harmonic Resonance through consistent input processing
- Cognitive Isolation with well-defined interfaces
- Balanced Information Flow through source credibility scaling
- Temporal Synchronization with the Global Sync Manager
- Self-Regulation through adaptive trust thresholds
- Graceful Degradation with input queuing for delayed processing
- Resonance Chain Integrity through input validation
"""

import os
import json
import logging
import hashlib
import threading
import time
import queue
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from phase4.cortex_vectorizer import CortexVectorizer

# Configure module logger
logger = logging.getLogger(__name__)

class DataIngestor:
    """
    Processes and vectorizes input data from various sources for CortexOS.
    Handles text, images, structured data, and mixed content with trust scoring.
    Implements all seven Agharmonic Law interfaces for full compliance.
    """
    def __init__(self, vector_dimensions=10, trust_threshold=0.5, global_sync_manager=None):
        self.vectorizer = CortexVectorizer(vector_dimensions)
        self.trust_threshold = trust_threshold
        self.ingest_history = []
        self.cache_dir = "data/cache"
        self.scored_dir = "data/scored"
        self.delayed_queue = queue.Queue()  # Queue for delayed processing
        self.compression_policy = {"text": True, "image": True, "structured": False}
        self.global_sync_manager = global_sync_manager
        self._lock = threading.Lock()
        self._processing = False
        self._last_sync = datetime.utcnow()
        self._health_metrics = {
            "processed_count": 0,
            "rejected_count": 0,
            "delayed_count": 0,
            "avg_processing_time": 0.0,
            "last_error": None
        }
        
        # Ensure cache directories exist
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.scored_dir, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Start delayed processing thread
        self._start_delayed_processor()
        
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility parameters for this module.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "module": "data_ingestor",
            "rhythm_hz": 0.2,  # 5 seconds per cycle
            "input_range": (0.1, 10.0),  # in Hz
            "output_phase": 0.0,
            "threshold": 0.85,
            "vector_dimensions": self.vectorizer.dimensions,
            "compression_enabled": any(self.compression_policy.values())
        }
    
    def interface_contract(self, data: Any, data_type: str) -> bool:
        """
        Defines allowed function calls and data structures.
        Validates incoming data formats and rejects malformed payloads.
        
        Args:
            data: Data to validate
            data_type: Type of data ('text', 'image', 'structured', 'mixed')
            
        Returns:
            True if data meets the interface contract
            
        Raises:
            ValueError: If data doesn't meet the interface contract
        """
        if data is None:
            raise ValueError(f"Data cannot be None for type {data_type}")
            
        if data_type == "text":
            if not isinstance(data, str):
                raise ValueError("Text data must be a string")
            if len(data) == 0:
                raise ValueError("Text data cannot be empty")
                
        elif data_type == "image":
            # Check if it's a numpy array with shape and size
            if not hasattr(data, 'shape') or not hasattr(data, 'size'):
                raise ValueError("Image data must be a numpy array")
            if data.size == 0:
                raise ValueError("Image data cannot be empty")
                
        elif data_type == "structured":
            if not isinstance(data, dict):
                raise ValueError("Structured data must be a dictionary")
            if len(data) == 0:
                raise ValueError("Structured data cannot be empty")
                
        elif data_type == "mixed":
            if not isinstance(data, list):
                raise ValueError("Mixed content must be a list")
            if len(data) == 0:
                raise ValueError("Mixed content list cannot be empty")
            for item in data:
                if not isinstance(item, dict) or "type" not in item or "data" not in item:
                    raise ValueError("Each mixed content item must be a dict with 'type' and 'data' keys")
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
            
        return True
    
    def cognitive_energy_flow(self, data: Any, trust_score: float) -> Dict[str, Any]:
        """
        Normalizes signal amplitude and scales by source credibility.
        
        Args:
            data: Input data
            trust_score: Trust/reliability score (0-1)
            
        Returns:
            Dict containing normalized signal data
        """
        # Calculate data complexity/size
        if isinstance(data, str):
            size = len(data)
            complexity = len(set(data)) / max(1, len(data))  # Unique char ratio
        elif hasattr(data, 'size'):  # numpy array
            size = data.size
            complexity = 0.8  # Default complexity for images
        elif isinstance(data, dict):
            size = len(json.dumps(data))
            complexity = len(data.keys()) / 10  # Normalize by expected avg keys
        elif isinstance(data, list):
            size = sum(len(json.dumps(item)) for item in data)
            complexity = len(data) / 5  # Normalize by expected avg items
        else:
            size = 100  # Default size
            complexity = 0.5  # Default complexity
            
        # Scale signal strength by trust score and complexity
        signal_strength = min(1.0, trust_score * (0.5 + 0.5 * complexity))
        
        # Calculate energy consumption based on size
        energy_consumption = min(1.0, size / 10000)  # Normalize to 0-1 range
        
        return {
            "signal_strength": signal_strength,
            "energy_consumption": energy_consumption,
            "trust_factor": trust_score,
            "complexity": complexity,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def sync_clock(self, global_clock: Any = None) -> bool:
        """
        Connects to the master temporal framework.
        Synchronizes compression and preprocessing policy.
        
        Args:
            global_clock: Optional reference to a global clock object
            
        Returns:
            True if synchronization successful, False otherwise
        """
        try:
            if global_clock:
                if hasattr(global_clock, 'get_sync_stats'):
                    stats = global_clock.get_sync_stats()
                    # Adjust compression policy based on system load
                    if stats.get('cycle_time', 5) > 5:  # System under load
                        self.compression_policy = {"text": True, "image": True, "structured": True}
                    else:  # Normal load
                        self.compression_policy = {"text": True, "image": True, "structured": False}
                        
                self._last_sync = datetime.utcnow()
                return True
            elif self.global_sync_manager:
                return self.sync_clock(self.global_sync_manager)
            else: