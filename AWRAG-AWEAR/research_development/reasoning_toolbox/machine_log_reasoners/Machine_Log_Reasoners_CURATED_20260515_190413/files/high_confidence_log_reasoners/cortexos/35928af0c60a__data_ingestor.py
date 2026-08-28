"""
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
                # No global clock, use internal timing
                self._last_sync = datetime.utcnow()
                return True
        except Exception as e:
            logger.error(f"Failed to sync with global clock: {e}")
            return False
    
    def self_regulate(self) -> Dict[str, Any]:
        """
        Implements feedback loops for stability.
        Adjusts trust threshold based on rejection rates.
        
        Returns:
            Dict containing self-regulation metrics
        """
        with self._lock:
            total_processed = self._health_metrics["processed_count"]
            rejected = self._health_metrics["rejected_count"]
            delayed = self._health_metrics["delayed_count"]
            
        if total_processed > 0:
            rejection_rate = rejected / total_processed
            delay_rate = delayed / total_processed
            
            # Adjust trust threshold based on rejection rate
            if rejection_rate > 0.5:  # Too many rejections
                new_threshold = max(0.3, self.trust_threshold - 0.05)
                logger.info(f"Adjusting trust threshold from {self.trust_threshold} to {new_threshold} due to high rejection rate")
                self.trust_threshold = new_threshold
            elif rejection_rate < 0.1 and delay_rate < 0.1:  # Too few rejections
                new_threshold = min(0.8, self.trust_threshold + 0.05)
                logger.info(f"Adjusting trust threshold from {self.trust_threshold} to {new_threshold} due to low rejection rate")
                self.trust_threshold = new_threshold
                
        # Clear old history entries if too many
        if len(self.ingest_history) > 200:
            self.ingest_history = self.ingest_history[-100:]
            
        return {
            "trust_threshold": self.trust_threshold,
            "history_size": len(self.ingest_history),
            "delayed_queue_size": self.delayed_queue.qsize(),
            "last_sync": self._last_sync.isoformat(),
            "health_metrics": self._health_metrics
        }
    
    def graceful_fallback(self, data: Any, data_type: str, error: Exception) -> Dict[str, Any]:
        """
        Provides mechanisms for partial operation under suboptimal conditions.
        Queues dropped inputs for delayed review.
        
        Args:
            data: The data that failed processing
            data_type: Type of data ('text', 'image', 'structured', 'mixed')
            error: The exception that occurred
            
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning(f"Executing graceful fallback for {data_type} data: {error}")
        
        # Create fallback record
        fallback_record = {
            "data_type": data_type,
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        # Add data to fallback record based on type
        if data_type == "text" and isinstance(data, str):
            # Store text directly if not too large
            if len(data) <= 10000:
                fallback_record["data"] = data
            else:
                # Store hash and first/last parts for large text
                fallback_record["data_hash"] = hashlib.md5(data.encode()).hexdigest()
                fallback_record["data_sample"] = data[:500] + "..." + data[-500:]
                
                # Cache large text to file
                cache_file = os.path.join(self.cache_dir, f"{fallback_record['data_hash']}.txt")
                try:
                    with open(cache_file, 'w') as f:
                        f.write(data)
                    fallback_record["cache_file"] = cache_file
                except Exception as e:
                    logger.error(f"Failed to cache text data: {e}")
                    
        elif data_type == "structured" and isinstance(data, dict):
            try:
                # Store structured data as JSON string
                fallback_record["data"] = json.dumps(data)
            except Exception as e:
                logger.error(f"Failed to serialize structured data: {e}")
                fallback_record["data_error"] = str(e)
                
        elif data_type == "mixed" and isinstance(data, list):
            # Store count and types for mixed content
            fallback_record["item_count"] = len(data)
            fallback_record["item_types"] = [item.get("type") for item in data if isinstance(item, dict)]
            
        # Queue for delayed processing
        self.delayed_queue.put(fallback_record)
        
        with self._lock:
            self._health_metrics["delayed_count"] += 1
            self._health_metrics["last_error"] = str(error)
            
        return {
            "status": "fallback_active",
            "action": "queued_for_delayed_processing",
            "queue_size": self.delayed_queue.qsize(),
            "error": str(error),
            "recommendation": "Check delayed processing queue later"
        }
    
    def resonance_chain_validator(self, data: Any, metadata: Dict[str, Any]) -> bool:
        """
        Verifies resonance integrity across the processing chain.
        
        Args:
            data: Data to validate
            metadata: Metadata associated with the data
            
        Returns:
            True if resonance chain is valid, False otherwise
        """
        # Validate timestamp if present
        if "timestamp" in metadata:
            try:
                timestamp = datetime.fromisoformat(metadata["timestamp"])
                # Check if timestamp is reasonably current (within 1 hour)
                time_diff = abs((datetime.utcnow() - timestamp).total_seconds())
                if time_diff > 3600:  # More than 1 hour old
                    logger.warning(f"Data timestamp too old: {time_diff:.2f}s")
                    return False
            except (ValueError, TypeError):
                logger.warning("Invalid timestamp format in metadata")
                return False
                
        # Validate source if present
        if "source" in metadata:
            source = metadata["source"]
            if not isinstance(source, str) or len(source) == 0:
                logger.warning("Invalid source in metadata")
                return False
                
        # Validate data consistency
        if isinstance(data, str) and len(data) == 0:
            logger.warning("Empty text data")
            return False
            
        if isinstance(data, dict) and len(data) == 0:
            logger.warning("Empty structured data")
            return False
            
        # All validations passed
        return True
    
    def ingest_text(self, text: str, metadata: Optional[Dict[str, Any]] = None, trust_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Ingest and vectorize text data.
        
        Args:
            text (str): Text content to ingest
            metadata (dict, optional): Additional context information
            trust_score (float, optional): Trust/reliability score (0-1)
            
        Returns:
            dict: Ingestion result with vector, metadata, and trust score
        """
        start_time = time.time()
        
        try:
            # Validate input
            self.interface_contract(text, "text")
            
            # Initialize metadata if not provided
            if metadata is None:
                metadata = {}
                
            # Add timestamp if not present
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.utcnow().isoformat()
                
            # Validate resonance chain
            if not self.resonance_chain_validator(text, metadata):
                logger.warning("Resonance chain validation failed for text input")
                with self._lock:
                    self._health_metrics["rejected_count"] += 1
                return None
                
            # Calculate trust score if not provided
            if trust_score is None:
                trust_score = self._calculate_trust_score(text, metadata)
                
            # Apply cognitive energy flow
            energy_data = self.cognitive_energy_flow(text, trust_score)
                
            # Generate content hash for deduplication
            content_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Vectorize the text
            vector = self.vectorizer.vectorize_text(text, metadata)
            
            # Create ingestion record
            ingestion = {
                "type": "text",
                "content_hash": content_hash,
                "vector": vector,
                "metadata": metadata,
                "trust_score": trust_score,
                "timestamp": metadata.get("timestamp"),
                "energy_data": energy_data
            }
            
            # Apply compression if enabled
            if self.compression_policy["text"] and len(text) > 1000:
                ingestion["compressed"] = True
                ingestion["original_length"] = len(text)
                # Store only first and last parts for large texts
                ingestion["text_sample"] = text[:500] + "..." + text[-500:]
            else:
                ingestion["compressed"] = False
                
            # Save to history and cache if above threshold
            if trust_score >= self.trust_threshold:
                self._save_ingestion(ingestion)
            else:
                logger.info(f"Text ingestion rejected due to low trust score: {trust_score}")
                with self._lock:
                    self._health_metrics["rejected_count"] += 1
                    
            # Update processing metrics
            processing_time = time.time() - start_time
            with self._lock:
                self._health_metrics["processed_count"] += 1
                # Update average processing time with exponential moving average
                self._health_metrics["avg_processing_time"] = 0.9 * self._health_metrics["avg_processing_time"] + 0.1 * processing_time
                
            return ingestion
            
        except Exception as e:
            logger.error(f"Error in text ingestion: {e}")
            return self.graceful_fallback(text, "text", e)
        
    def ingest_image(self, image_array, metadata: Optional[Dict[str, Any]] = None, trust_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Ingest and vectorize image data.
        
        Args:
            image_array: Image data as numpy array
            metadata (dict, optional): Additional context information
            trust_score (float, optional): Trust/reliability score (0-1)
            
        Returns:
            dict: Ingestion result with vector, metadata, and trust score
        """
        start_time = time.time()
        
        try:
            # Validate input
            self.interface_contract(image_array, "image")
            
            # Initialize metadata if not provided
            if metadata is None:
                metadata = {}
                
            # Add timestamp if not present
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.utcnow().isoformat()
                
            # Validate resonance chain
            if not self.resonance_chain_validator(image_array, metadata):
                logger.warning("Resonance chain validation failed for image input")
                with self._lock:
                    self._health_metrics["rejected_count"] += 1
                return None
                
            # Calculate trust score if not provided
            if trust_score is None:
                trust_score = self._calculate_trust_score(None, metadata, image=True)
                
            # Apply cognitive energy flow
            energy_data = self.cognitive_energy_flow(image_array, trust_score)
                
            # Vectorize the image
            vector = self.vectorizer.vectorize_image(image_array)
            
            # Create content hash from vector (since image array can't be directly hashed)
            content_hash = hashlib.md5(str(vector).encode()).hexdigest()
            
            # Create ingestion record
            ingestion = {
                "type": "image",
                "content_hash": content_hash,
                "vector": vector,
                "metadata": metadata,
                "trust_score": trust_score,
                "timestamp": metadata.get("timestamp"),
                "energy_data": energy_data,
                "image_shape": image_array.shape if hasattr(image_array, 'shape') else None
            }
            
            # Apply compression if enabled
            if self.compression_policy["image"]:
                ingestion["compressed"] = True
                ingestion["original_size"] = image_array.size if hasattr(image_array, 'size') else 0
            else:
                ingestion["compressed"] = False
                
            # Save to history and cache if above threshold
            if trust_score >= self.trust_threshold:
                self._save_ingestion(ingestion)
            else:
                logger.info(f"Image ingestion rejected due to low trust score: {trust_score}")
                with self._lock:
                    self._health_metrics["rejected_count"] += 1
                    
            # Update processing metrics
            processing_time = time.time() - start_time
            with self._lock:
                self._health_metrics["processed_count"] += 1
                # Update average processing time with exponential moving average
                self._health_metrics["avg_processing_time"] = 0.9 * self._health_metrics["avg_processing_time"] + 0.1 * processing_time
                
            return ingestion
            
        except Exception as e:
            logger.error(f"Error in image ingestion: {e}")
            return self.graceful_fallback(image_array, "image", e)
        
    def ingest_structured_data(self, data_dict: Dict[str, Any], schema: Optional[Dict[str, Any]] = None, 
                              metadata: Optional[Dict[str, Any]] = None, trust_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Ingest and vectorize structured data.
        
        Args:
            data_dict (dict): Key-value pairs of structured data
            schema (dict, optional): Schema defining importance weights
            metadata (dict, optional): Additional context information
            trust_score (float, optional): Trust/reliability score (0-1)
            
        Returns:
            dict: Ingestion result with vector, metadata, and trust score
        """
        start_time = time.time()
        
        try:
            # Validate input
            self.interface_contract(data_dict, "structured")
            
            # Initialize metadata if not provided
            if metadata is None:
                metadata = {}
                
            # Add timestamp if not present
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.utcnow().isoformat()
                
            # Validate resonance chain
            if not self.resonance_chain_validator(data_dict, metadata):
                logger.warning("Resonance chain validation failed for structured data input")
                with self._lock:
                    self._health_metrics["rejected_count"] += 1
                return None
                
            # Calculate trust score if not provided
            if trust_score is None:
                trust_score = self._calculate_trust_score(str(data_dict), metadata)
                
            # Apply cognitive energy flow
            energy_data = self.cognitive_energy_flow(data_dict, trust_score)
                
            # Vectorize the structured data
            vector = self.vectorizer.vectorize_structured_data(data_dict, schema)
            
            # Create content hash
            content_hash = hashlib.md5(json.dumps(data_dict, sort_keys=True).encode()).hexdigest()
            
            # Create ingestion record
            ingestion = {
                "type": "structured",
                "content_hash": content_hash,
                "vector": vector,
                "metadata": metadata,
                "trust_score": trust_score,
                "timestamp": metadata.get("timestamp"),
                "schema": schema,
                "energy_data": energy_data
            }
            
            # Apply compression if enabled
            if self.compression_policy["structured"]:
                ingestion["compressed"] = True
                ingestion["key_count"] = len(data_dict)
                ingestion["keys"] = list(data_dict.keys())
            else:
                ingestion["compressed"] = False
                
            # Save to history and cache if above threshold
            if trust_score >= self.trust_threshold:
                self._save_ingestion(ingestion)
            else:
                logger.info(f"Structured data ingestion rejected due to low trust score: {trust_score}")
                with self._lock:
                    self._health_metrics["rejected_count"] += 1
                    
            # Update processing metrics
            processing_time = time.time() - start_time
            with self._lock:
                self._health_metrics["processed_count"] += 1
                # Update average processing time with exponential moving average
                self._health_metrics["avg_processing_time"] = 0.9 * self._health_metrics["avg_processing_time"] + 0.1 * processing_time
                
            return ingestion
            
        except Exception as e:
            logger.error(f"Error in structured data ingestion: {e}")
            return self.graceful_fallback(data_dict, "structured", e)
        
    def ingest_mixed_content(self, content_items: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Ingest multiple content items of different types.
        
        Args:
            content_items (list): List of content items with type and data
            metadata (dict, optional): Shared metadata for all items
            
        Returns:
            list: List of ingestion results
        """
        try:
            # Validate input
            self.interface_contract(content_items, "mixed")
            
            # Initialize shared metadata if not provided
            if metadata is None:
                metadata = {}
                
            # Add timestamp if not present
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.utcnow().isoformat()
                
            results = []
            
            for item in content_items:
                item_type = item.get("type")
                item_data = item.get("data")
                item_metadata = {**metadata, **item.get("metadata", {})}
                trust_score = item.get("trust_score")
                
                if item_type == "text":
                    result = self.ingest_text(item_data, item_metadata, trust_score)
                elif item_type == "image":
                    result = self.ingest_image(item_data, item_metadata, trust_score)
                elif item_type == "structured":
                    schema = item.get("schema")
                    result = self.ingest_structured_data(item_data, schema, item_metadata, trust_score)
                else:
                    self.logger.warning(f"Unknown content type: {item_type}")
                    result = None
                    
                if result:
                    results.append(result)
                    
            return results
            
        except Exception as e:
            logger.error(f"Error in mixed content ingestion: {e}")
            return self.graceful_fallback(content_items, "mixed", e)
        
    def _calculate_trust_score(self, content: Optional[str], metadata: Dict[str, Any], image: bool = False) -> float:
        """Calculate trust score based on content and metadata."""
        # Default score
        score = 0.5
        
        # Adjust based on metadata
        if "source" in metadata:
            source = metadata["source"].lower()
            if any(trusted in source for trusted in ["official", "verified", "academic"]):
                score += 0.2
            elif any(untrusted in source for trusted in ["unverified", "anonymous"]):
                score -= 0.2
                
        if "author" in metadata and metadata["author"]:
            score += 0.1
            
        if "citation" in metadata and metadata["citation"]:
            score += 0.1
            
        # Content-based adjustments (simple heuristics)
        if not image and content:
            # Text length heuristic
            if len(content) < 10:
                score -= 0.1
            elif len(content) > 1000:
                score += 0.1
                
        # Ensure score is within bounds
        return max(0.0, min(1.0, score))
        
    def _save_ingestion(self, ingestion: Dict[str, Any]) -> None:
        """Save ingestion to history and cache."""
        # Add to history
        with self._lock:
            self.ingest_history.append(ingestion)
            
            # Limit history size
            if len(self.ingest_history) > 100:
                self.ingest_history = self.ingest_history[-100:]
                
        # Save to cache file
        cache_file = os.path.join(self.scored_dir, f"{ingestion['content_hash']}.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(ingestion, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to cache ingestion: {e}")
            
    def _start_delayed_processor(self) -> None:
        """Start the delayed processing thread."""
        def process_delayed_queue():
            while True:
                try:
                    # Process items from the delayed queue
                    if not self.delayed_queue.empty():
                        item = self.delayed_queue.get(block=False)
                        
                        # Increment retry count
                        item["retry_count"] += 1
                        
                        logger.info(f"Processing delayed item: {item['data_type']}, retry #{item['retry_count']}")
                        
                        # TODO: Implement actual retry logic based on data type
                        # For now, just log the retry attempt
                        
                        # If retry count exceeds limit, log and discard
                        if item["retry_count"] >= 3:
                            logger.warning(f"Discarding delayed item after {item['retry_count']} retries: {item['data_type']}")
                        else:
                            # Re-queue for another attempt later
                            self.delayed_queue.put(item)
                            
                except queue.Empty:
                    pass
                except Exception as e:
                    logger.error(f"Error in delayed processor: {e}")
                    
                # Sleep before next processing attempt
                time.sleep(5)
                
        # Start the processing thread
        threading.Thread(target=process_delayed_queue, daemon=True).start()
            
    def get_recent_ingestions(self, limit: int = 10, min_trust: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get recent ingestion records.
        
        Args:
            limit (int): Maximum number of records to return
            min_trust (float, optional): Minimum trust score filter
            
        Returns:
            list: Recent ingestion records
        """
        with self._lock:
            if min_trust is not None:
                filtered = [i for i in self.ingest_history if i["trust_score"] >= min_trust]
                return filtered[-limit:]
            else:
                return self.ingest_history[-limit:]
            
    def get_ingestion_by_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve ingestion record by content hash.
        
        Args:
            content_hash (str): MD5 hash of content
            
        Returns:
            dict: Ingestion record if found, None otherwise
        """
        # Check history first
        with self._lock:
            for ingestion in self.ingest_history:
                if ingestion["content_hash"] == content_hash:
                    return ingestion
                
        # Check cache file
        cache_file = os.path.join(self.scored_dir, f"{content_hash}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load cached ingestion: {e}")
                
        return None
        
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status of the data ingestor.
        
        Returns:
            Dict containing health status metrics
        """
        with self._lock:
            metrics = self._health_metrics.copy()
            
        # Add additional status information
        status = {
            **metrics,
            "trust_threshold": self.trust_threshold,
            "history_size": len(self.ingest_history),
            "delayed_queue_size": self.delayed_queue.qsize(),
            "last_sync": self._last_sync.isoformat(),
            "compression_policy": self.compression_policy
        }
        
        return status
