"""
Symbolic Translator module for CortexOS.
Provides bidirectional translation between language and symbolic representations.
Fully compliant with Agharmonic Law.
"""

import time
import logging
import threading
import json
import numpy as np
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agharmonic_compliant import AgharmonicCompliant
from phase4.cortex_vectorizer import CortexVectorizer

class SymbolicTranslator(AgharmonicCompliant):
    """
    Provides bidirectional translation between language and symbolic representations.
    Implements all seven Agharmonic Law interfaces for full compliance.
    """
    
    def __init__(self, global_sync_manager=None, vector_dimensions=128):
        # Core translation parameters
        self.translation_confidence_threshold = 0.7
        self.max_translation_depth = 3
        self.translation_history = []
        self.max_history_size = 100
        self.symbol_registry = {}
        
        # Initialize vectorizer
        self.vectorizer = CortexVectorizer()
        
        # Agharmonic Law compliance components
        self.global_sync_manager = global_sync_manager
        self.frequency_range = [0.1, 1.0]  # Default frequency range
        self.phase_alignment = 0.2  # Default phase alignment
        self.resonance_threshold = 0.75  # Default resonance threshold
        self.last_sync_time = time.time()
        self.sync_interval = 90  # Default sync interval in seconds
        self.health_metrics = {
            "translations_performed": 0,
            "translations_failed": 0,
            "last_health_check": time.time()
        }
        self.fallback_level = 0
        self.validation_lock = threading.RLock()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.info("SymbolicTranslator module initialized successfully")
        
    def register_symbol(self, symbol, meaning, vector=None):
        """
        Register a symbol in the symbol registry.
        
        Args:
            symbol (str): Symbol to register
            meaning (str): Meaning of the symbol
            vector (list, optional): Vector representation of the symbol
            
        Returns:
            dict: Registration result
        """
        # Validate inputs
        if not symbol or not meaning:
            return {"status": "error", "message": "Invalid symbol or meaning"}
               # Generate vector if not provided
            if vector is None:
                try:
                    vector = self.vectorizer.vectorize(meaning, input_type="meaning")
                except Exception as e:
                    self.logger.error(f"Failed to vectorize meaning: {e}")
                    return {"status": "error", "message": f"Failed to vectorize meaning: {e}"}        # Register symbol
        self.symbol_registry[symbol] = {
            "meaning": meaning,
            "vector": vector,
            "created": datetime.utcnow().isoformat(),
            "usage_count": 0
        }
        
        return {
            "status": "success",
            "symbol": symbol,
            "vector_dimensions": len(vector)
        }
        
    def translate_to_symbol(self, text):
        """
        Translate text to symbolic representation.
        
        Args:
            text (str): Text to translate
            
        Returns:
            dict: Translation result
        """
        # Validate input
        if not text:
            return {"status": "error", "message": "Invalid text"}
            
        try:
            # Vectorize text
            text_vector = self.vectorizer.vectorize(text)
            
            # Find closest symbols
            closest_symbols = []
            for symbol, data in self.symbol_registry.items():
                similarity = self._calculate_similarity(text_vector, data["vector"])
                if similarity >= self.translation_confidence_threshold:
                    closest_symbols.append({
                        "symbol": symbol,
                        "similarity": similarity,
                        "meaning": data["meaning"]
                    })
                    
            # Sort by similarity
            closest_symbols.sort(key=lambda x: x["similarity"], reverse=True)
            
            # Update usage count for used symbols
            for symbol_data in closest_symbols[:3]:
                symbol = symbol_data["symbol"]
                if symbol in self.symbol_registry:
                    self.symbol_registry[symbol]["usage_count"] += 1
                    
            # Record translation
            translation_result = {
                "timestamp": datetime.utcnow().isoformat(),
                "input_text": text,
                "symbols": closest_symbols[:5],
                "confidence": closest_symbols[0]["similarity"] if closest_symbols else 0
            }
            
            # Update metrics
            self.health_metrics["translations_performed"] += 1
            
            # Add to history
            self.translation_history.append(translation_result)
            
            # Trim history if needed
            if len(self.translation_history) > self.max_history_size:
                self.translation_history = self.translation_history[-self.max_history_size:]
                
            return {
                "status": "success",
                "symbols": closest_symbols[:5],
                "confidence": closest_symbols[0]["similarity"] if closest_symbols else 0,
                "result": closest_symbols[0]["symbol"] if closest_symbols else None
            }
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            self.health_metrics["translations_failed"] += 1
            
            # Use graceful fallback
            return self.graceful_fallback(e, {"context": "translate_to_symbol", "text": text})
            
    def translate_from_symbol(self, symbol):
        """
        Translate symbol to textual representation.
        
        Args:
            symbol (str): Symbol to translate
            
        Returns:
            dict: Translation result
        """
        # Validate input
        if not symbol:
            return {"status": "error", "message": "Invalid symbol"}
            
        # Check if symbol exists in registry
        if symbol not in self.symbol_registry:
            # Try to find similar symbols
            similar_symbols = []
            for reg_symbol, data in self.symbol_registry.items():
                # Simple string similarity for demonstration
                similarity = self._string_similarity(symbol, reg_symbol)
                if similarity >= 0.5:
                    similar_symbols.append({
                        "symbol": reg_symbol,
                        "similarity": similarity,
                        "meaning": data["meaning"]
                    })
                    
            # Sort by similarity
            similar_symbols.sort(key=lambda x: x["similarity"], reverse=True)
            
            if similar_symbols:
                return {
                    "status": "not_found",
                    "message": f"Symbol '{symbol}' not found in registry",
                    "similar_symbols": similar_symbols[:3],
                    "result": None
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"Symbol '{symbol}' not found in registry",
                    "result": None
                }
                
        # Get symbol data
        symbol_data = self.symbol_registry[symbol]
        
        # Update usage count
        symbol_data["usage_count"] += 1
        
        # Record translation
        translation_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "input_symbol": symbol,
            "meaning": symbol_data["meaning"],
            "confidence": 1.0
        }
        
        # Update metrics
        self.health_metrics["translations_performed"] += 1
        
        # Add to history
        self.translation_history.append(translation_result)
        
        # Trim history if needed
        if len(self.translation_history) > self.max_history_size:
            self.translation_history = self.translation_history[-self.max_history_size:]
            
        return {
            "status": "success",
            "meaning": symbol_data["meaning"],
            "confidence": 1.0,
            "usage_count": symbol_data["usage_count"],
            "result": symbol_data["meaning"]
        }
        
    def _calculate_similarity(self, vector1, vector2):
        """Calculate cosine similarity between two vectors."""
        # Convert to numpy arrays
        v1 = np.array(vector1)
        v2 = np.array(vector2)
        
        # Calculate cosine similarity
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0
            
        return dot_product / (norm_v1 * norm_v2)
        
    def _string_similarity(self, str1, str2):
        """Calculate simple string similarity."""
        # Simple Levenshtein distance-based similarity
        distance = self._levenshtein_distance(str1, str2)
        max_len = max(len(str1), len(str2))
        
        if max_len == 0:
            return 1.0
            
        return 1.0 - (distance / max_len)
        
    def _levenshtein_distance(self, str1, str2):
        """Calculate Levenshtein distance between two strings."""
        m, n = len(str1), len(str2)
        
        # Create distance matrix
        dp = [[0 for _ in range(n + 1)] for _ in range(m + 1)]
        
        # Initialize first row and column
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
            
        # Fill the matrix
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if str1[i-1] == str2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # Deletion
                    dp[i][j-1] + 1,      # Insertion
                    dp[i-1][j-1] + cost  # Substitution
                )
                
        return dp[m][n]
        
    # === Agharmonic Law Compliance Methods ===
    
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for translation operations.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "symbolic_translator",
            "threshold": self.resonance_threshold,
            "input_frequency_range": self.frequency_range,
            "output_phase_alignment": self.phase_alignment
        }
        
    def interface_contract(self, operation=None, payload=None):
        """
        Validates operations against the expected interface contract.
        Required for Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            operation (str, optional): Requested operation
            payload (dict, optional): Operation parameters
            
        Returns:
            bool or dict: True if data meets contract requirements, or contract specification if no data
        """
        # Define allowed operations and their required parameters
        allowed_operations = {
            "register_symbol": ["symbol", "meaning"],
            "translate_to_symbol": ["text"],
            "translate_from_symbol": ["symbol"]
        }
        
        # If no operation specified, return the contract
        if operation is None:
            return {
                "allowed_operations": allowed_operations,
                "status": "contract_provided"
            }
            
        # Validate operation
        if operation not in allowed_operations:
            return {
                "status": "invalid_operation",
                "message": f"Operation '{operation}' not allowed. Valid operations: {list(allowed_operations.keys())}"
            }
            
        # Validate payload for operation
        if payload is None:
            payload = {}
            
        # Check required parameters
        missing_params = []
        for param in allowed_operations[operation]:
            if param not in payload:
                missing_params.append(param)
                
        if missing_params:
            return {
                "status": "invalid_payload",
                "message": f"Missing required parameters: {missing_params}"
            }
            
        return True
        
    def cognitive_energy_flow(self, translation_request=None):
        """
        Normalizes translation complexity and energy allocation.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            translation_request (dict, optional): Translation request
            
        Returns:
            dict: Normalized translation parameters
        """
        # If no request specified, return current energy flow parameters
        if translation_request is None:
            return {
                "translation_confidence_threshold": self.translation_confidence_threshold,
                "max_translation_depth": self.max_translation_depth,
                "energy_budget": 1.0
            }
            
        # Extract request complexity if available
        request_complexity = translation_request.get("complexity", 0.5)
        
        # Normalize translation parameters based on complexity
        normalized_params = {
            "confidence_threshold": max(0.5, self.translation_confidence_threshold - 0.1 * request_complexity),
            "max_depth": min(5, int(self.max_translation_depth * (1.0 + 0.5 * request_complexity))),
            "energy_allocation": min(1.0, request_complexity * 1.5)
        }
        
        return normalized_params
        
    def sync_clock(self, global_sync_manager=None):
        """
        Aligns with GlobalSyncManager for coordinated translation operations.
        Required for Agharmonic Law Tenet 4: Temporal Synchronization.
        
        Args:
            global_sync_manager: Optional external sync manager to use
            
        Returns:
            dict: Synchronization status
        """
        current_time = time.time()
        time_since_last_sync = current_time - self.last_sync_time
        
        # Check if sync is needed
        if time_since_last_sync < self.sync_interval:
            return {
                "status": "skipped",
                "message": f"Sync not needed, {self.sync_interval - time_since_last_sync:.2f}s until next sync",
                "last_sync": self.last_sync_time
            }
            
        # Use provided global_sync_manager if available, otherwise use instance one
        sync_manager = global_sync_manager if global_sync_manager else self.global_sync_manager
            
        # If GlobalSyncManager is available, use it
        if sync_manager:
            try:
                # Get timing policy from GlobalSyncManager
                sync_policy = sync_manager.get_sync_policy()
                
                # Update translation parameters
                if "translation" in sync_policy:
                    translation_policy = sync_policy["translation"]
                    self.translation_confidence_threshold = translation_policy.get(
                        "confidence_threshold", 
                        self.translation_confidence_threshold
                    )
                    self.max_translation_depth = translation_policy.get(
                        "max_depth", 
                        self.max_translation_depth
                    )
                    
                # Update sync interval
                self.sync_interval = sync_policy.get("translation_sync_interval", 90)
                    
            except Exception as e:
                self.logger.warning(f"Failed to sync with GlobalSyncManager: {e}")
                
        # Update last sync time
        self.last_sync_time = current_time
        
        return {
            "status": "synced",
            "message": "Successfully synchronized with temporal framework",
            "sync_interval": self.sync_interval,
            "next_sync": current_time + self.sync_interval
        }
        
    def self_regulate(self):
        """
        Implements adaptive translation parameters based on performance metrics.
        Required for Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            dict: Self-regulation metrics and actions taken
        """
        # Initialize regulation actions and fallback level
        regulation_actions = []
        fallback_level = 0
        
        # Update health metrics
        current_time = time.time()
        time_since_health_check = current_time - self.health_metrics["last_health_check"]
        
        # Perform health check every 5 minutes
        if time_since_health_check >= 300:  # 5 minutes
            # Check for excessive failed translations
            if self.health_metrics["translations_failed"] > 5:
                self.logger.warning(f"High translation failure count: {self.health_metrics['translations_failed']}")
                regulation_actions.append("lower_confidence_threshold")
                
                # Lower confidence threshold to be more permissive
                self.translation_confidence_threshold = max(0.5, self.translation_confidence_threshold - 0.05)
                fallback_level = 1
                
            # Check for symbol registry size
            if len(self.symbol_registry) > 1000:
                self.logger.warning(f"Symbol registry size exceeds 1000: {len(self.symbol_registry)}")
                regulation_actions.append("prune_symbol_registry")
                
                # Prune rarely used symbols
                self._prune_symbol_registry()
                fallback_level = 1
                
            # Update last health check time
            self.health_metrics["last_health_check"] = current_time
            
        # Set fallback level based on failure rate if not already set
        if fallback_level == 0:
            total_translations = self.health_metrics["translations_performed"] + self.health_metrics["translations_failed"]
            if total_translations > 0:
                failure_rate = self.health_metrics["translations_failed"] / total_translations
                if failure_rate > 0.3:
                    fallback_level = 2
                elif failure_rate > 0.1:
                    fallback_level = 1
            
        # Store current fallback level
        self.fallback_level = fallback_level
            
        return {
            "status": "healthy" if fallback_level == 0 else "regulated",
            "metrics": self.health_metrics,
            "actions": regulation_actions,
            "fallback_level": fallback_level
        }
        
    def _prune_symbol_registry(self):
        """Prune rarely used symbols from the registry."""
        # Sort symbols by usage count
        sorted_symbols = sorted(
            self.symbol_registry.items(), 
            key=lambda x: x[1]["usage_count"]
        )
        
        # Remove bottom 10%
        symbols_to_remove = sorted_symbols[:int(len(sorted_symbols) * 0.1)]
        for symbol, _ in symbols_to_remove:
            del self.symbol_registry[symbol]
            
        self.logger.info(f"Pruned {len(symbols_to_remove)} symbols from registry")
        
    def graceful_fallback(self, error, context=None):
        """
        Provides fallback translation mechanisms for error conditions.
        Required for Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error: Error object or string triggering fallback
            context (dict, optional): Error context information
            
        Returns:
            dict: Fallback status and actions taken
        """
        error_type = str(error) if not isinstance(error, str) else error
        self.health_metrics["translations_failed"] += 1
        
        # Determine fallback action based on context
        fallback_action = "return_empty_result"
        
        if context and "context" in context:
            if context["context"] == "translate_to_symbol":
                fallback_action = "use_direct_mapping"
                
                # Try direct character mapping as fallback
                if "text" in context and context["text"]:
                    text = context["text"]
                    direct_symbol = "".join([c[0] if c.strip() else " " for c in text.split()])
                    
                    return {
                        "status": "fallback",
                        "message": f"Used direct mapping fallback due to: {error_type}",
                        "symbols": [{
                            "symbol": direct_symbol,
                            "similarity": 0.5,
                            "meaning": "Fallback direct mapping"
                        }],
                        "confidence": 0.5,
                        "fallback_action": fallback_action,
                        "result": direct_symbol
                    }
            elif context["context"] == "translate_from_symbol":
                fallback_action = "return_symbol_as_meaning"
                
                # Return the symbol itself as the meaning
                if "symbol" in context and context["symbol"]:
                    return {
                        "status": "fallback",
                        "message": f"Used symbol-as-meaning fallback due to: {error_type}",
                        "meaning": f"Symbol: {context['symbol']}",
                        "confidence": 0.5,
                        "fallback_action": fallback_action,
                        "result": f"Symbol: {context['symbol']}"
                    }
                    
        # Create generic fallback response
        fallback_response = {
            "status": "fallback",
            "message": f"Translation failed: {error_type}",
            "confidence": 0.0,
            "fallback_action": fallback_action,
            "result": None
        }
        
        # Log the fallback
        self.logger.warning(f"Fallback triggered: {error_type}")
        
        return fallback_response
        
    def resonance_chain_validator(self, result=None):
        """
        Verifies translation results maintain semantic integrity.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            result (dict, optional): Result to validate
            
        Returns:
            bool or dict: True/valid status if result maintains resonance integrity
        """
        # If no result provided, return validation capabilities
        if result is None:
            return {
                "valid": True,
                "message": "Test validation successful",
                "validator_type": "symbolic_translator"
            }
            
        # Validate result structure
        if not isinstance(result, dict):
            return {
                "valid": False,
                "message": "Result must be a dictionary",
                "validator_type": "symbolic_translator"
            }
            
        # Check for required fields based on result type
        if "symbols" in result:
            # To-symbol translation result
            required_fields = ["status", "symbols", "confidence"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                return {
                    "valid": False,
                    "message": f"Missing required fields: {missing_fields}",
                    "validator_type": "symbolic_translator"
                }
                
            # Validate symbols structure
            symbols = result.get("symbols", [])
            if not symbols:
                return {
                    "valid": False,
                    "message": "Symbols list cannot be empty",
                    "validator_type": "symbolic_translator"
                }
                
            # Check first symbol has required fields
            first_symbol = symbols[0]
            if not isinstance(first_symbol, dict) or "symbol" not in first_symbol or "similarity" not in first_symbol:
                return {
                    "valid": False,
                    "message": "Symbol entries must have 'symbol' and 'similarity' fields",
                    "validator_type": "symbolic_translator"
                }
                
        elif "meaning" in result:
            # From-symbol translation result
            required_fields = ["status", "meaning", "confidence"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                return {
                    "valid": False,
                    "message": f"Missing required fields: {missing_fields}",
                    "validator_type": "symbolic_translator"
                }
                
        else:
            # Unknown result type
            return {
                "valid": False,
                "message": "Unknown result type",
                "validator_type": "symbolic_translator"
            }
            
        # All validations passed
        return {
            "valid": True,
            "message": "Result is valid",
            "validator_type": "symbolic_translator"
        }
