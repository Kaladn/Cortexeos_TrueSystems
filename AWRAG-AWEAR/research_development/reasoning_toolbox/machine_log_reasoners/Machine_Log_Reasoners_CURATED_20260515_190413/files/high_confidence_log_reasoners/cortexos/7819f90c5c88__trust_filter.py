"""
Trust Filter module for CortexOS.
Evaluates and scores data reliability for neural processing.

This module implements the Agharmonic Law by providing:
- Harmonic Resonance through consistent trust evaluation
- Cognitive Isolation with well-defined interfaces
- Balanced Information Flow through trust-based signal modulation
- Temporal Synchronization with the Global Sync Manager
- Self-Regulation through adaptive trust thresholds and learning
- Graceful Degradation with review protocols for rejected inputs
- Resonance Chain Integrity through trust validation
"""

import json
import logging
import hashlib
import threading
import time
import queue
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

# Configure module logger
logger = logging.getLogger(__name__)

class TrustFilter:
    """
    Evaluates and scores data reliability for CortexOS neural processing.
    Implements multi-factor trust scoring with source reputation, content analysis, and temporal decay.
    Fully compliant with all seven Agharmonic Law interfaces.
    """
    def __init__(self, source_reputation_file=None, global_sync_manager=None):
        self.source_reputations = self._load_source_reputations(source_reputation_file)
        self.trust_cache = {}
        self.trust_history = []
        self.false_positives = {}  # Track false positives for learning
        self.false_negatives = {}  # Track false negatives for learning
        self.review_queue = queue.Queue()  # Queue for review protocols
        self.global_sync_manager = global_sync_manager
        self._lock = threading.Lock()
        self._last_sync = datetime.utcnow()
        self._health_metrics = {
            "evaluations_count": 0,
            "rejected_count": 0,
            "review_count": 0,
            "avg_processing_time": 0.0,
            "last_error": None,
            "learning_events": 0
        }
        
        # Agharmonic Law compliance parameters
        self.trust_threshold = 0.6
        self.learning_rate = 0.05
        self.review_threshold = 0.4
        
        # Start review processor thread
        self._start_review_processor()
        
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes the frequency compatibility parameters for this module.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            "module": "trust_filter",
            "rhythm_hz": 0.5,  # 2 seconds per cycle
            "input_range": (0.2, 2.0),  # in Hz
            "output_phase": 0.0,
            "threshold": 0.85,
            "trust_threshold": self.trust_threshold,
            "learning_enabled": True
        }
    
    def interface_contract(self, data: Any, data_type: str, metadata: Dict[str, Any]) -> bool:
        """
        Defines allowed function calls and data structures.
        Validates incoming data formats and metadata requirements.
        
        Args:
            data: Data to validate
            data_type: Type of data ('text', 'image', 'structured')
            metadata: Metadata associated with the data
            
        Returns:
            True if data meets the interface contract
            
        Raises:
            ValueError: If data doesn't meet the interface contract
        """
        if data is None:
            raise ValueError(f"Data cannot be None for type {data_type}")
            
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary")
            
        # Validate required metadata fields
        required_fields = ["source"]
        missing_fields = [field for field in required_fields if field not in metadata]
        if missing_fields:
            raise ValueError(f"Missing required metadata fields: {', '.join(missing_fields)}")
            
        # Validate data type
        valid_types = ["text", "image", "structured"]
        if data_type not in valid_types:
            raise ValueError(f"Invalid data type: {data_type}. Must be one of {valid_types}")
            
        # Type-specific validation
        if data_type == "text" and not isinstance(data, str):
            raise ValueError("Text data must be a string")
            
        if data_type == "structured" and not isinstance(data, dict):
            raise ValueError("Structured data must be a dictionary")
            
        return True
    
    def cognitive_energy_flow(self, trust_score: float, content_type: str) -> Dict[str, Any]:
        """
        Normalizes signal amplitude based on trust score.
        
        Args:
            trust_score: Trust/reliability score (0-1)
            content_type: Type of content ('text', 'image', 'structured')
            
        Returns:
            Dict containing normalized signal data
        """
        # Base signal strength is directly proportional to trust score
        base_signal = trust_score
        
        # Apply content type modifiers
        type_modifiers = {
            "text": 1.0,
            "image": 0.9,  # Images slightly less trusted by default
            "structured": 1.1  # Structured data slightly more trusted by default
        }
        
        modifier = type_modifiers.get(content_type, 1.0)
        
        # Calculate final signal strength (capped at 1.0)
        signal_strength = min(1.0, base_signal * modifier)
        
        # Calculate energy consumption based on trust evaluation complexity
        energy_consumption = 0.3 + (0.7 * trust_score)  # Higher trust requires more validation
        
        return {
            "signal_strength": signal_strength,
            "energy_consumption": energy_consumption,
            "trust_factor": trust_score,
            "content_type": content_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def sync_clock(self, global_clock: Any = None) -> bool:
        """
        Connects to the master temporal framework.
        Synchronizes trust thresholds and learning parameters.
        
        Args:
            global_clock: Optional reference to a global clock object
            
        Returns:
            True if synchronization successful, False otherwise
        """
        try:
            if global_clock:
                if hasattr(global_clock, 'get_sync_stats'):
                    stats = global_clock.get_sync_stats()
                    # Adjust trust parameters based on system state
                    if stats.get('cycle_time', 5) > 5:  # System under load
                        # Under load, be more strict with trust to reduce processing
                        self.trust_threshold = min(0.8, self.trust_threshold + 0.05)
                        self.review_threshold = max(0.5, self.review_threshold + 0.05)
                    else:  # Normal load
                        # Reset to default values
                        self.trust_threshold = 0.6
                        self.review_threshold = 0.4
                        
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
        Implements feedback loop analysis and learning from false positives/negatives.
        
        Returns:
            Dict containing self-regulation metrics
        """
        with self._lock:
            total_evaluations = self._health_metrics["evaluations_count"]
            rejected = self._health_metrics["rejected_count"]
            review = self._health_metrics["review_count"]
            learning_events = self._health_metrics["learning_events"]
            
        if total_evaluations > 0:
            rejection_rate = rejected / total_evaluations
            review_rate = review / total_evaluations
            
            # Adjust trust threshold based on rejection rate
            if rejection_rate > 0.4:  # Too many rejections
                new_threshold = max(0.4, self.trust_threshold - 0.05)
                logger.info(f"Adjusting trust threshold from {self.trust_threshold} to {new_threshold} due to high rejection rate")
                self.trust_threshold = new_threshold
            elif rejection_rate < 0.1 and review_rate < 0.1:  # Too few rejections
                new_threshold = min(0.8, self.trust_threshold + 0.05)
                logger.info(f"Adjusting trust threshold from {self.trust_threshold} to {new_threshold} due to low rejection rate")
                self.trust_threshold = new_threshold
                
        # Learn from false positives and negatives
        if self.false_positives or self.false_negatives:
            self._learn_from_feedback()
            
        # Clear old history entries if too many
        if len(self.trust_history) > 200:
            self.trust_history = self.trust_history[-100:]
            
        return {
            "trust_threshold": self.trust_threshold,
            "review_threshold": self.review_threshold,
            "history_size": len(self.trust_history),
            "review_queue_size": self.review_queue.qsize(),
            "false_positives": len(self.false_positives),
            "false_negatives": len(self.false_negatives),
            "learning_rate": self.learning_rate,
            "learning_events": learning_events,
            "last_sync": self._last_sync.isoformat(),
            "health_metrics": self._health_metrics
        }
    
    def graceful_fallback(self, content: Any, content_type: str, metadata: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """
        Provides mechanisms for partial operation under suboptimal conditions.
        Triggers review protocols instead of failing silently.
        
        Args:
            content: The content that failed processing
            content_type: Type of content ('text', 'image', 'structured')
            metadata: Content metadata
            error: The exception that occurred
            
        Returns:
            Dict containing fallback status and actions
        """
        logger.warning(f"Executing graceful fallback for {content_type} content: {error}")
        
        # Create fallback record
        fallback_record = {
            "content_type": content_type,
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata,
            "retry_count": 0
        }
        
        # Add content to fallback record based on type
        if content_type == "text" and isinstance(content, str):
            # Store text directly if not too large
            if len(content) <= 10000:
                fallback_record["content"] = content
            else:
                # Store hash and first/last parts for large text
                fallback_record["content_hash"] = hashlib.md5(content.encode()).hexdigest()
                fallback_record["content_sample"] = content[:500] + "..." + content[-500:]
                
        elif content_type == "structured" and isinstance(content, dict):
            try:
                # Store structured data as JSON string
                fallback_record["content"] = json.dumps(content)
            except Exception as e:
                logger.error(f"Failed to serialize structured data: {e}")
                fallback_record["content_error"] = str(e)
                
        # Queue for review
        self.review_queue.put(fallback_record)
        
        with self._lock:
            self._health_metrics["review_count"] += 1
            self._health_metrics["last_error"] = str(error)
            
        # Generate default trust score for fallback
        default_trust = {
            "content_hash": self._generate_content_hash(content, content_type),
            "content_type": content_type,
            "trust_score": 0.3,  # Conservative default
            "factors": {
                "source_reputation": 0.3,
                "content_analysis": 0.3,
                "metadata_completeness": 0.3,
                "citation_quality": 0.3,
                "temporal_freshness": 0.3
            },
            "fallback_generated": True,
            "timestamp": datetime.utcnow().isoformat()
        }
            
        return {
            "status": "fallback_active",
            "action": "queued_for_review",
            "queue_size": self.review_queue.qsize(),
            "error": str(error),
            "trust_evaluation": default_trust,
            "recommendation": "Check review queue later"
        }
    
    def resonance_chain_validator(self, content: Any, metadata: Dict[str, Any], trust_score: float) -> bool:
        """
        Verifies trust evaluation integrity across the resonance chain.
        
        Args:
            content: Content being evaluated
            metadata: Content metadata
            trust_score: Calculated trust score
            
        Returns:
            True if trust evaluation is valid, False otherwise
        """
        # Validate trust score range
        if not 0 <= trust_score <= 1:
            logger.warning(f"Invalid trust score: {trust_score}")
            return False
            
        # Validate timestamp if present
        if "timestamp" in metadata:
            try:
                timestamp = datetime.fromisoformat(metadata["timestamp"])
                # Check if timestamp is reasonably current (within 1 day)
                time_diff = abs((datetime.utcnow() - timestamp).total_seconds())
                if time_diff > 86400:  # More than 1 day old
                    logger.warning(f"Content timestamp too old: {time_diff:.2f}s")
                    # Don't fail validation, but log warning
            except (ValueError, TypeError):
                logger.warning("Invalid timestamp format in metadata")
                # Don't fail validation, but log warning
                
        # Validate source reputation consistency
        if "source" in metadata:
            source = metadata["source"].lower()
            if source in self.source_reputations:
                source_rep = self.source_reputations[source]
                # If trust score is significantly higher than source reputation, flag as suspicious
                if trust_score > source_rep + 0.3:
                    logger.warning(f"Trust score ({trust_score}) significantly higher than source reputation ({source_rep})")
                    return False
                    
        # All validations passed
        return True
    
    def _load_source_reputations(self, source_reputation_file):
        """Load source reputation scores from JSON file."""
        default_reputations = {
            "verified_academic": 0.95,
            "peer_reviewed": 0.90,
            "official_source": 0.85,
            "established_news": 0.75,
            "expert_opinion": 0.70,
            "curated_collection": 0.65,
            "specialized_blog": 0.60,
            "general_web": 0.50,
            "social_media": 0.40,
            "anonymous_source": 0.30,
            "untrusted_source": 0.20,
            "known_misinformation": 0.10
        }
        
        if source_reputation_file:
            try:
                with open(source_reputation_file, 'r') as f:
                    loaded_reputations = json.load(f)
                    # Merge with defaults, keeping loaded values
                    return {**default_reputations, **loaded_reputations}
            except Exception as e:
                logger.warning(f"Failed to load source reputations from {source_reputation_file}: {e}")
                
        return default_reputations
        
    def evaluate_trust(self, content: Any, metadata: Dict[str, Any], content_type: str = "text") -> Dict[str, Any]:
        """
        Evaluate trust score for content based on multiple factors.
        
        Args:
            content: Content to evaluate (text, image data, or structured data)
            metadata (dict): Content metadata including source, author, timestamp, etc.
            content_type (str): Type of content ('text', 'image', 'structured')
            
        Returns:
            dict: Trust evaluation result with overall score and factor breakdown
        """
        start_time = time.time()
        
        try:
            # Validate input through interface contract
            self.interface_contract(content, content_type, metadata)
            
            # Generate content hash for caching
            content_hash = self._generate_content_hash(content, content_type)
            
            # Check cache for existing evaluation
            if content_hash in self.trust_cache:
                cached = self.trust_cache[content_hash]
                # Apply temporal decay to cached score
                if "timestamp" in cached:
                    cached_time = datetime.fromisoformat(cached["timestamp"])
                    current_time = datetime.now()
                    days_elapsed = (current_time - cached_time).days
                    decay_factor = max(0.0, 1.0 - (days_elapsed * 0.01))  # 1% decay per day
                    cached["trust_score"] *= decay_factor
                    cached["factors"]["temporal_decay"] = decay_factor
                    
                return cached
                
            # Initialize factors dictionary
            factors = {}
            
            # 1. Source reputation factor
            source_factor = self._evaluate_source_reputation(metadata)
            factors["source_reputation"] = source_factor
            
            # 2. Content analysis factor
            content_factor = self._analyze_content(content, content_type)
            factors["content_analysis"] = content_factor
            
            # 3. Metadata completeness factor
            metadata_factor = self._evaluate_metadata_completeness(metadata)
            factors["metadata_completeness"] = metadata_factor
            
            # 4. Citation factor
            citation_factor = self._evaluate_citations(metadata)
            factors["citation_quality"] = citation_factor
            
            # 5. Temporal factor (freshness)
            temporal_factor = self._evaluate_temporal_factor(metadata)
            factors["temporal_freshness"] = temporal_factor
            
            # Calculate weighted trust score
            weights = {
                "source_reputation": 0.35,
                "content_analysis": 0.25,
                "metadata_completeness": 0.15,
                "citation_quality": 0.15,
                "temporal_freshness": 0.10
            }
            
            trust_score = sum(factors[k] * weights[k] for k in factors.keys())
            
            # Apply cognitive energy flow
            energy_data = self.cognitive_energy_flow(trust_score, content_type)
            
            # Create evaluation result
            result = {
                "content_hash": content_hash,
                "content_type": content_type,
                "trust_score": round(trust_score, 3),
                "factors": factors,
                "energy_data": energy_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Validate through resonance chain
            if not self.resonance_chain_validator(content, metadata, trust_score):
                logger.warning(f"Resonance chain validation failed for {content_type} content")
                # Adjust trust score downward
                result["trust_score"] *= 0.8
                result["resonance_validation_failed"] = True
                
            # Cache the result
            self.trust_cache[content_hash] = result
            
            # Add to history
            self.trust_history.append({
                "content_hash": content_hash,
                "trust_score": result["trust_score"],
                "timestamp": result["timestamp"]
            })
            
            # Limit history size
            if len(self.trust_history) > 100:
                self.trust_history = self.trust_history[-100:]
                
            # Update processing metrics
            processing_time = time.time() - start_time
            with self._lock:
                self._health_metrics["evaluations_count"] += 1
                # Update average processing time with exponential moving average
                self._health_metrics["avg_processing_time"] = 0.9 * self._health_metrics["avg_processing_time"] + 0.1 * processing_time
                
                # Track rejection if below threshold
                if result["trust_score"] < self.trust_threshold:
                    self._health_metrics["rejected_count"] += 1
                    
            return result
            
        except Exception as e:
            logger.error(f"Error in trust evaluation: {e}")
            return self.graceful_fallback(content, content_type, metadata, e)
            
    def _generate_content_hash(self, content, content_type):
        """Generate hash for content based on type."""
        if content_type == "text":
            return hashlib.md5(str(content).encode()).hexdigest()
        elif content_type == "structured":
            return hashlib.md5(json.dumps(content, sort_keys=True).encode()).hexdigest()
        elif content_type == "image":
            # For image data, hash a string representation of the data
            return hashlib.md5(str(content).encode()).hexdigest()
        else:
            return hashlib.md5(str(content).encode()).hexdigest()
            
    def _evaluate_source_reputation(self, metadata):
        """Evaluate source reputation factor."""
        if "source" not in metadata:
            return 0.5  # Default for unknown source
            
        source = metadata["source"].lower()
        
        # Check for exact match in reputation dictionary
        if source in self.source_reputations:
            return self.source_reputations[source]
            
        # Check for partial matches
        for known_source, reputation in self.source_reputations.items():
            if known_source in source:
                return reputation
                
        return 0.5  # Default for unknown source
        
    def _analyze_content(self, content, content_type):
        """Analyze content for quality indicators."""
        if content_type == "text":
            # Simple text analysis heuristics
            if not content:
                return 0.0
                
            # Length-based heuristic
            length = len(content)
            if length < 10:
                return 0.3
            elif length < 100:
                return 0.5
            elif length < 1000:
                return 0.7
            else:
                return 0.8
                
        elif content_type == "structured":
            # Structured data completeness
            if not content:
                return 0.0
                
            # Check for empty or sparse data
            if isinstance(content, dict):
                filled_ratio = sum(1 for v in content.values() if v) / max(1, len(content))
                return min(0.9, filled_ratio)
            else:
                return 0.5
                
        elif content_type == "image":
            # Image analysis would require more complex logic
            # This is a placeholder for future enhancement
            return 0.6
            
        return 0.5  # Default for unknown content type
        
    def _evaluate_metadata_completeness(self, metadata):
        """Evaluate metadata completeness factor."""
        if not metadata:
            return 0.0
            
        # Key metadata fields
        key_fields = ["source", "author", "timestamp", "title", "description"]
        
        # Calculate completeness ratio
        present_fields = sum(1 for field in key_fields if field in metadata and metadata[field])
        completeness = present_fields / len(key_fields)
        
        return completeness
        
    def _evaluate_citations(self, metadata):
        """Evaluate citation quality factor."""
        if "citations" not in metadata or not metadata["citations"]:
            return 0.4  # Default for no citations
            
        citations = metadata["citations"]
        
        if isinstance(citations, list):
            # Number of citations factor
            count_factor = min(1.0, len(citations) / 10)  # Max out at 10 citations
            
            # Citation quality factor (placeholder)
            # In a real implementation, would evaluate each citation
            quality_factor = 0.7  # Default quality assumption
            
            return (count_factor + quality_factor) / 2
        else:
            return 0.5  # Default for non-list citations
            
    def _evaluate_temporal_factor(self, metadata):
        """Evaluate temporal freshness factor."""
        if "timestamp" not in metadata or not metadata["timestamp"]:
            return 0.5  # Default for unknown timestamp
            
        try:
            # Parse timestamp
            if isinstance(metadata["timestamp"], str):
                timestamp = datetime.fromisoformat(metadata["timestamp"])
            else:
                timestamp = datetime.fromtimestamp(metadata["timestamp"])
                
            # Calculate age in days
            age_days = (datetime.now() - timestamp).days
            
            # Freshness factor (1.0 for today, decreasing with age)
            if age_days <= 0:
                return 1.0
            elif age_days <= 7:
                return 0.9  # Within a week
            elif age_days <= 30:
                return 0.8  # Within a month
            elif age_days <= 90:
                return 0.7  # Within a quarter
            elif age_days <= 365:
                return 0.6  # Within a year
            else:
                return 0.5  # Older than a year
        except Exception:
            return 0.5  # Default for parsing errors
            
    def update_source_reputation(self, source: str, reputation_score: float) -> bool:
        """
        Update reputation score for a source.
        
        Args:
            source (str): Source identifier
            reputation_score (float): New reputation score (0-1)
            
        Returns:
            bool: Success status
        """
        if not 0 <= reputation_score <= 1:
            logger.warning(f"Invalid reputation score: {reputation_score}")
            return False
            
        self.source_reputations[source.lower()] = reputation_score
        return True
        
    def report_false_positive(self, content_hash: str, feedback: Dict[str, Any]) -> bool:
        """
        Report a false positive (content incorrectly trusted).
        
        Args:
            content_hash: Hash of the content
            feedback: Feedback information
            
        Returns:
            bool: Success status
        """
        if content_hash not in self.trust_cache:
            logger.warning(f"Content hash not found in trust cache: {content_hash}")
            return False
            
        with self._lock:
            self.false_positives[content_hash] = {
                "original_evaluation": self.trust_cache[content_hash],
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            }
            self._health_metrics["learning_events"] += 1
            
        return True
        
    def report_false_negative(self, content_hash: str, feedback: Dict[str, Any]) -> bool:
        """
        Report a false negative (content incorrectly distrusted).
        
        Args:
            content_hash: Hash of the content
            feedback: Feedback information
            
        Returns:
            bool: Success status
        """
        if content_hash not in self.trust_cache:
            logger.warning(f"Content hash not found in trust cache: {content_hash}")
            return False
            
        with self._lock:
            self.false_negatives[content_hash] = {
                "original_evaluation": self.trust_cache[content_hash],
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            }
            self._health_metrics["learning_events"] += 1
            
        return True
        
    def _learn_from_feedback(self) -> None:
        """Learn from false positives and negatives to improve trust evaluation."""
        with self._lock:
            fp_count = len(self.false_positives)
            fn_count = len(self.false_negatives)
            
            if fp_count + fn_count == 0:
                return
                
            logger.info(f"Learning from feedback: {fp_count} false positives, {fn_count} false negatives")
            
            # Adjust source reputations based on feedback
            source_adjustments = {}
            
            # Process false positives (trusted content that shouldn't have been)
            for content_hash, data in self.false_positives.items():
                eval_data = data["original_evaluation"]
                if "source" in eval_data.get("metadata", {}):
                    source = eval_data["metadata"]["source"].lower()
                    # Decrease reputation for sources with false positives
                    adjustment = source_adjustments.get(source, 0) - self.learning_rate
                    source_adjustments[source] = adjustment
                    
            # Process false negatives (distrusted content that should have been trusted)
            for content_hash, data in self.false_negatives.items():
                eval_data = data["original_evaluation"]
                if "source" in eval_data.get("metadata", {}):
                    source = eval_data["metadata"]["source"].lower()
                    # Increase reputation for sources with false negatives
                    adjustment = source_adjustments.get(source, 0) + self.learning_rate
                    source_adjustments[source] = adjustment
                    
            # Apply adjustments to source reputations
            for source, adjustment in source_adjustments.items():
                if source in self.source_reputations:
                    current = self.source_reputations[source]
                    new_value = max(0.0, min(1.0, current + adjustment))
                    logger.info(f"Adjusting reputation for {source}: {current:.2f} -> {new_value:.2f}")
                    self.source_reputations[source] = new_value
                    
            # Clear processed feedback
            self.false_positives.clear()
            self.false_negatives.clear()
            
    def _start_review_processor(self) -> None:
        """Start the review processing thread."""
        def process_review_queue():
            while True:
                try:
                    # Process items from the review queue
                    if not self.review_queue.empty():
                        item = self.review_queue.get(block=False)
                        
                        # Increment retry count
                        item["retry_count"] += 1
                        
                        logger.info(f"Processing review item: {item['content_type']}, retry #{item['retry_count']}")
                        
                        # TODO: Implement actual review logic
                        # For now, just log the review attempt
                        
                        # If retry count exceeds limit, log and discard
                        if item["retry_count"] >= 3:
                            logger.warning(f"Discarding review item after {item['retry_count']} retries: {item['content_type']}")
                        else:
                            # Re-queue for another attempt later
                            self.review_queue.put(item)
                            
                except queue.Empty:
                    pass
                except Exception as e:
                    logger.error(f"Error in review processor: {e}")
                    
                # Sleep before next processing attempt
                time.sleep(5)
                
        # Start the processing thread
        threading.Thread(target=process_review_queue, daemon=True).start()
            
    def get_trust_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent trust evaluation history.
        
        Args:
            limit (int): Maximum number of history entries to return
            
        Returns:
            list: Recent trust evaluation history
        """
        return self.trust_history[-limit:]
        
    def export_source_reputations(self, output_file: str) -> bool:
        """
        Export source reputation data to JSON file.
        
        Args:
            output_file (str): Output file path
            
        Returns:
            bool: Success status
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(self.source_reputations, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export source reputations: {e}")
            return False
            
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status of the trust filter.
        
        Returns:
            Dict containing health status metrics
        """
        with self._lock:
            metrics = self._health_metrics.copy()
            
        # Add additional status information
        status = {
            **metrics,
            "trust_threshold": self.trust_threshold,
            "review_threshold": self.review_threshold,
            "history_size": len(self.trust_history),
            "review_queue_size": self.review_queue.qsize(),
            "false_positives": len(self.false_positives),
            "false_negatives": len(self.false_negatives),
            "learning_rate": self.learning_rate,
            "last_sync": self._last_sync.isoformat()
        }
        
        return status
