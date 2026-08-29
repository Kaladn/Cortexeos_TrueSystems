"""
Knowledge Reinforcer module for CortexOS Temporal Cognition v2.1.
Strengthens neural connections based on activation patterns and temporal context.
Implements Hebbian-inspired learning with decay and temporal weighting.
Fully compliant with Agharmonic Law.
"""

import numpy as np
import time
import logging
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeReinforcer:
    """
    Reinforces neural connections based on activation patterns and temporal context.
    Implements Hebbian-inspired learning with decay and temporal weighting.
    Fully compliant with all seven Agharmonic Law interfaces.
    """
    def __init__(self, 
                 decay_rate: float = 0.05, 
                 learning_rate: float = 0.1, 
                 temporal_window: int = 5,
                 resonance_threshold: float = 0.65,
                 max_registry_size: int = 10000):
        """
        Initialize the Knowledge Reinforcer.
        
        Args:
            decay_rate: Rate at which connections decay over time (0-1)
            learning_rate: Rate at which connections strengthen (0-1)
            temporal_window: Time window in minutes for temporal correlation
            resonance_threshold: Minimum resonance required for validation
            max_registry_size: Maximum size of reinforcement registry
        """
        # Core parameters
        self.decay_rate = decay_rate
        self.learning_rate = learning_rate
        self.temporal_window = temporal_window
        self.resonance_threshold = resonance_threshold
        self.max_registry_size = max_registry_size
        
        # State tracking
        self.activation_history = {}
        self.connection_strengths = {}
        self.last_reinforcement = {}
        self.reinforcement_registry = []  # [(symbol, timestamp, score, tags)]
        self.last_sync = datetime.utcnow()
        self.last_regulation = datetime.utcnow()
        self.last_validation = datetime.utcnow()
        
        # Performance metrics
        self.metrics = {
            'reinforcements_processed': 0,
            'connections_created': 0,
            'connections_strengthened': 0,
            'connections_decayed': 0,
            'rejected_reinforcements': 0,
            'total_registry_entries': 0
        }
        
        # Operational state
        self.operational_state = 'normal'  # normal, degraded, minimal
        self.error_count = 0
        self.last_error_time = None
        
        logger.info("Knowledge Reinforcer initialized with decay_rate=%f, learning_rate=%f, temporal_window=%d",
                   decay_rate, learning_rate, temporal_window)
    
    def harmonic_signature(self) -> Dict[str, Any]:
        """
        Establishes frequency compatibility parameters for the module.
        Required by Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            Dict containing harmonic signature parameters
        """
        return {
            'module': 'knowledge_reinforcer',
            'version': '2.1.0',
            'input_frequency_range': [0.5, 1.2],
            'output_phase_alignment': 0.2,
            'resonance_threshold': self.resonance_threshold,
            'temporal_sensitivity': self.temporal_window,
            'decay_curve_coefficient': self.decay_rate,
            'reinforcement_coefficient': self.learning_rate
        }
    
    def interface_contract(self, input_data: Dict[str, Any]) -> bool:
        """
        Validates input data against the expected interface.
        Required by Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            input_data: Dictionary containing input parameters
            
        Returns:
            True if input is valid, raises exception otherwise
            
        Raises:
            ValueError: If input data does not meet requirements
        """
        # Check for required fields based on operation type
        if 'operation' not in input_data:
            raise ValueError("Missing required field: 'operation'")
            
        operation = input_data['operation']
        
        if operation == 'record_activation':
            required = ['neuron_id', 'activation_strength']
        elif operation == 'reinforce_connections':
            required = ['active_neurons']
        elif operation == 'get_connections':
            required = ['neuron_id']
        elif operation == 'register_symbol':
            required = ['symbol', 'score']
        else:
            raise ValueError(f"Unknown operation: {operation}")
            
        # Validate required fields
        missing = [field for field in required if field not in input_data]
        if missing:
            raise ValueError(f"Missing required fields for {operation}: {missing}")
            
        # Validate data types and ranges
        if operation == 'record_activation':
            if not isinstance(input_data['neuron_id'], str):
                raise ValueError("neuron_id must be a string")
            if not (0 <= input_data['activation_strength'] <= 1):
                raise ValueError("activation_strength must be between 0 and 1")
                
        elif operation == 'register_symbol':
            if not isinstance(input_data['symbol'], str):
                raise ValueError("symbol must be a string")
            if not (0 <= input_data['score'] <= 1):
                raise ValueError("score must be between 0 and 1")
                
        return True
    
    def cognitive_energy_flow(self, input_energy: float, operation_type: str) -> float:
        """
        Normalizes signal amplitude and information flow.
        Required by Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            input_energy: Input energy level (0-1)
            operation_type: Type of operation being performed
            
        Returns:
            Normalized energy level (0-1)
        """
        # Base normalization - clamp to valid range
        energy = max(0.0, min(1.0, input_energy))
        
        # Apply operation-specific normalization
        if operation_type == 'reinforcement':
            # Scale reinforcement energy based on current system state
            if self.operational_state == 'degraded':
                energy *= 0.7  # Reduce energy in degraded state
            elif self.operational_state == 'minimal':
                energy *= 0.4  # Significantly reduce energy in minimal state
                
            # Apply logarithmic scaling to prevent runaway reinforcement
            if energy > 0.8:
                # Logarithmically scale high energy values to prevent spikes
                energy = 0.8 + (0.2 * np.log10(1 + 10 * (energy - 0.8)))
                
        elif operation_type == 'decay':
            # Ensure decay energy is proportional to system state
            if self.operational_state == 'degraded':
                energy *= 1.2  # Increase decay in degraded state
            elif self.operational_state == 'minimal':
                energy *= 1.5  # Significantly increase decay in minimal state
                
        elif operation_type == 'query':
            # Query energy is less affected by system state
            if self.operational_state == 'minimal':
                energy *= 0.9  # Slight reduction in minimal state
                
        # Log significant energy adjustments
        if abs(energy - input_energy) > 0.3:
            logger.info(f"Significant energy adjustment for {operation_type}: {input_energy:.2f} -> {energy:.2f}")
            
        return energy
    
    def sync_clock(self) -> bool:
        """
        Synchronizes with the global temporal framework.
        Required by Agharmonic Law Tenet 4: Temporal Synchronization.
        
        Returns:
            True if synchronization is needed, False otherwise
        """
        now = datetime.utcnow()
        time_since_sync = (now - self.last_sync).total_seconds()
        
        # Determine if sync is needed (every 30 seconds)
        sync_needed = time_since_sync >= 30
        
        if sync_needed:
            logger.debug(f"Clock sync triggered after {time_since_sync:.1f}s")
            self.last_sync = now
            
            # Apply time-based decay to all connections
            self._apply_connection_decay(now.timestamp())
            
            # Prune old entries from reinforcement registry
            self._prune_reinforcement_registry()
            
        return sync_needed
    
    def self_regulate(self) -> Dict[str, Any]:
        """
        Implements internal feedback loops for stability.
        Required by Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            Dict containing regulation metrics
        """
        now = datetime.utcnow()
        time_since_regulation = (now - self.last_regulation).total_seconds()
        
        # Only regulate periodically (every 2 minutes)
        if time_since_regulation < 120:
            return {'status': 'skipped', 'reason': 'too_soon'}
            
        self.last_regulation = now
        
        # Check for registry size limits
        registry_size = len(self.reinforcement_registry)
        registry_utilization = registry_size / self.max_registry_size
        
        # Check for connection count limits
        connection_count = len(self.connection_strengths)
        
        # Determine if any regulation actions are needed
        actions_taken = []
        
        # Regulate registry size if needed
        if registry_utilization > 0.9:
            # Aggressive pruning needed
            self._prune_reinforcement_registry(force_ratio=0.7)
            actions_taken.append('aggressive_registry_pruning')
        elif registry_utilization > 0.7:
            # Moderate pruning
            self._prune_reinforcement_registry(force_ratio=0.85)
            actions_taken.append('moderate_registry_pruning')
            
        # Regulate connection strengths if needed
        if connection_count > 100000:
            # Prune weak connections
            pruned = self._prune_weak_connections(threshold=0.2)
            actions_taken.append(f'pruned_{pruned}_weak_connections')
            
        # Adjust learning parameters based on system state
        if self.error_count > 5 and self.operational_state == 'normal':
            # Transition to degraded state
            self.operational_state = 'degraded'
            self.learning_rate *= 0.8  # Reduce learning rate
            actions_taken.append('reduced_learning_rate')
            logger.warning("Transitioned to degraded operational state")
            
        elif self.error_count > 10 and self.operational_state == 'degraded':
            # Transition to minimal state
            self.operational_state = 'minimal'
            self.learning_rate *= 0.5  # Significantly reduce learning rate
            actions_taken.append('minimal_learning_rate')
            logger.warning("Transitioned to minimal operational state")
            
        elif self.error_count == 0 and self.operational_state != 'normal':
            # Recover to normal state
            self.operational_state = 'normal'
            self.learning_rate = 0.1  # Reset to default
            actions_taken.append('restored_normal_operation')
            logger.info("Recovered to normal operational state")
            
        # Reset error count periodically
        if (now - self.last_error_time).total_seconds() > 3600 if self.last_error_time else True:
            self.error_count = 0
            
        regulation_metrics = {
            'status': 'regulated' if actions_taken else 'stable',
            'actions_taken': actions_taken,
            'registry_utilization': registry_utilization,
            'connection_count': connection_count,
            'operational_state': self.operational_state,
            'error_count': self.error_count,
            'learning_rate': self.learning_rate
        }
        
        logger.info(f"Self-regulation complete: {regulation_metrics['status']}")
        return regulation_metrics
    
    def graceful_fallback(self, error_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provides mechanisms for partial operation during failures.
        Required by Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error_type: Type of error encountered
            context: Contextual information about the error
            
        Returns:
            Dict containing fallback status and actions
        """
        # Track error occurrence
        self.error_count += 1
        self.last_error_time = datetime.utcnow()
        
        # Log the error
        logger.error(f"Error encountered: {error_type} - Context: {context}")
        
        fallback_actions = []
        
        # Determine appropriate fallback based on error type
        if error_type == 'memory_allocation':
            # Memory issues - aggressive pruning
            pruned_registry = self._prune_reinforcement_registry(force_ratio=0.5)
            pruned_connections = self._prune_weak_connections(threshold=0.3)
            fallback_actions.extend([
                'aggressive_registry_pruning',
                'aggressive_connection_pruning'
            ])
            
        elif error_type == 'data_corruption':
            # Data corruption - reset affected structures
            if 'structure' in context:
                if context['structure'] == 'registry':
                    self.reinforcement_registry = []
                    fallback_actions.append('reset_registry')
                elif context['structure'] == 'connections':
                    self.connection_strengths = {}
                    self.last_reinforcement = {}
                    fallback_actions.append('reset_connections')
                    
        elif error_type == 'synchronization':
            # Sync issues - operate independently
            self.last_sync = datetime.utcnow()
            fallback_actions.append('forced_sync_reset')
            
        elif error_type == 'processing_overload':
            # Processing overload - reduce workload
            self.learning_rate *= 0.7  # Reduce learning rate
            self.temporal_window = max(1, self.temporal_window - 1)  # Reduce temporal window
            fallback_actions.extend([
                'reduced_learning_rate',
                'reduced_temporal_window'
            ])
            
        # Update operational state based on error severity
        if self.error_count > 10:
            self.operational_state = 'minimal'
            fallback_actions.append('transitioned_to_minimal_state')
        elif self.error_count > 5:
            self.operational_state = 'degraded'
            fallback_actions.append('transitioned_to_degraded_state')
            
        fallback_result = {
            'status': 'fallback_engaged',
            'error_type': error_type,
            'actions_taken': fallback_actions,
            'operational_state': self.operational_state,
            'error_count': self.error_count
        }
        
        logger.warning(f"Fallback engaged: {fallback_result}")
        return fallback_result
    
    def resonance_chain_validator(self, 
                                 input_vector: Dict[str, Any], 
                                 output_vector: Dict[str, Any]) -> bool:
        """
        Verifies resonance integrity across the chain.
        Required by Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            input_vector: Input data vector
            output_vector: Output data vector
            
        Returns:
            True if resonance is valid, False otherwise
        """
        now = datetime.utcnow()
        self.last_validation = now
        
        # Extract key validation parameters
        operation = input_vector.get('operation', '')
        
        # Skip validation for certain operations
        if operation in ['get_connections', 'export_graph']:
            return True
            
        # Validate reinforcement operations
        if operation == 'reinforce_connections':
            # Check for resonance spikes (abnormally high reinforcement)
            if 'reinforcement_strength' in input_vector:
                strength = input_vector['reinforcement_strength']
                if strength > 0.9:  # Suspiciously high reinforcement
                    # Check if this is part of a pattern (multiple high reinforcements)
                    recent_high_count = sum(1 for entry in self.reinforcement_registry[-10:] 
                                          if entry[2] > 0.9)  # Count recent high scores
                    
                    if recent_high_count > 3:  # Multiple high reinforcements detected
                        logger.warning(f"Resonance spike detected: {recent_high_count} high reinforcements recently")
                        return False
                        
        # Validate symbol registration
        if operation == 'register_symbol':
            symbol = input_vector.get('symbol', '')
            score = input_vector.get('score', 0)
            
            # Check for duplicate symbols with conflicting scores
            recent_entries = [entry for entry in self.reinforcement_registry[-50:] 
                             if entry[0] == symbol]
            
            if recent_entries:
                # Calculate average recent score
                avg_score = sum(entry[2] for entry in recent_entries) / len(recent_entries)
                
                # Check for significant deviation
                if abs(score - avg_score) > 0.4:  # Significant deviation
                    logger.warning(f"Conflicting symbol scores detected for '{symbol}': new={score:.2f}, avg={avg_score:.2f}")
                    return False
                    
        # Validate activation recording
        if operation == 'record_activation':
            neuron_id = input_vector.get('neuron_id', '')
            strength = input_vector.get('activation_strength', 0)
            
            # Check activation history for this neuron
            if neuron_id in self.activation_history:
                recent_activations = self.activation_history[neuron_id][-5:]
                
                # Check for oscillatory pattern (sign of resonance instability)
                if len(recent_activations) >= 3:
                    strengths = [a['strength'] for a in recent_activations]
                    
                    # Check for alternating high-low pattern
                    is_oscillating = all(
                        abs(strengths[i] - strengths[i-1]) > 0.5
                        for i in range(1, len(strengths))
                    )
                    
                    if is_oscillating:
                        logger.warning(f"Oscillatory activation pattern detected for neuron {neuron_id}")
                        return False
                        
        # Validate output vector
        if output_vector:
            # Check for NaN or infinity values
            has_invalid = any(
                isinstance(v, (int, float)) and (np.isnan(v) or np.isinf(v))
                for v in output_vector.values()
            )
            
            if has_invalid:
                logger.error("Invalid values (NaN/Inf) detected in output vector")
                return False
                
        return True
    
    def record_activation(self, 
                         neuron_id: str, 
                         activation_strength: float, 
                         timestamp: Optional[float] = None,
                         tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Record neuron activation for reinforcement processing.
        
        Args:
            neuron_id: Unique identifier for the neuron
            activation_strength: Strength of activation (0-1)
            timestamp: Activation time (defaults to current time)
            tags: Optional list of tags for this activation
            
        Returns:
            Dict containing operation status
        """
        try:
            # Validate input
            input_data = {
                'operation': 'record_activation',
                'neuron_id': neuron_id,
                'activation_strength': activation_strength
            }
            self.interface_contract(input_data)
            
            # Normalize energy
            activation_strength = self.cognitive_energy_flow(activation_strength, 'activation')
            
            if timestamp is None:
                timestamp = time.time()
                
            if tags is None:
                tags = []
                
            if neuron_id not in self.activation_history:
                self.activation_history[neuron_id] = []
                
            # Add new activation record
            self.activation_history[neuron_id].append({
                'strength': activation_strength,
                'timestamp': timestamp,
                'tags': tags
            })
            
            # Prune old activations outside temporal window
            self._prune_activation_history(neuron_id, timestamp)
            
            # Register as symbol if neuron_id looks like a symbol
            if len(neuron_id) < 50 and not neuron_id.startswith('neuron_'):
                self.register_symbol(neuron_id, activation_strength, tags)
                
            # Validate resonance
            validation_result = self.resonance_chain_validator(
                input_data,
                {'status': 'activation_recorded', 'neuron_id': neuron_id}
            )
            
            return {
                'status': 'success' if validation_result else 'warning',
                'message': 'Activation recorded successfully' if validation_result else 'Activation recorded with resonance warning',
                'neuron_id': neuron_id,
                'normalized_strength': activation_strength
            }
            
        except Exception as e:
            logger.error(f"Error recording activation: {str(e)}")
            return self.graceful_fallback('activation_error', {
                'neuron_id': neuron_id,
                'error': str(e)
            })
    
    def _prune_activation_history(self, neuron_id: str, current_time: float) -> None:
        """
        Remove activations outside the temporal window.
        
        Args:
            neuron_id: ID of the neuron to prune
            current_time: Current timestamp
        """
        if neuron_id in self.activation_history:
            cutoff_time = current_time - (self.temporal_window * 60)  # Convert minutes to seconds
            self.activation_history[neuron_id] = [
                a for a in self.activation_history[neuron_id] 
                if a['timestamp'] >= cutoff_time
            ]
    
    def register_symbol(self, 
                       symbol: str, 
                       score: float, 
                       tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Register a symbol in the reinforcement registry.
        
        Args:
            symbol: Symbol to register
            score: Reinforcement score (0-1)
            tags: Optional list of tags for this symbol
            
        Returns:
            Dict containing operation status
        """
        try:
            # Validate input
            input_data = {
                'operation': 'register_symbol',
                'symbol': symbol,
                'score': score
            }
            self.interface_contract(input_data)
            
            # Normalize energy
            score = self.cognitive_energy_flow(score, 'reinforcement')
            
            if tags is None:
                tags = []
                
            timestamp = datetime.utcnow().timestamp()
            
            # Add to registry
            self.reinforcement_registry.append((symbol, timestamp, score, tags))
            self.metrics['total_registry_entries'] += 1
            
            # Prune if needed
            if len(self.reinforcement_registry) > self.max_registry_size:
                self._prune_reinforcement_registry()
                
            # Validate resonance
            validation_result = self.resonance_chain_validator(
                input_data,
                {'status': 'symbol_registered', 'symbol': symbol, 'score': score}
            )
            
            return {
                'status': 'success' if validation_result else 'warning',
                'message': 'Symbol registered successfully' if validation_result else 'Symbol registered with resonance warning',
                'symbol': symbol,
                'normalized_score': score
            }
            
        except Exception as e:
            logger.error(f"Error registering symbol: {str(e)}")
            return self.graceful_fallback('symbol_registration_error', {
                'symbol': symbol,
                'error': str(e)
            })
    
    def _prune_reinforcement_registry(self, force_ratio: Optional[float] = None) -> int:
        """
        Prune old or low-score entries from the reinforcement registry.
        
        Args:
            force_ratio: If provided, force pruning to this ratio of max size
            
        Returns:
            Number of entries pruned
        """
        if not self.reinforcement_registry:
            return 0
            
        original_size = len(self.reinforcement_registry)
        
        # Determine target size
        if force_ratio is not None:
            target_size = int(self.max_registry_size * force_ratio)
        else:
            # Default to 90% of max size
            target_size = int(self.max_registry_size * 0.9)
            
        if original_size <= target_size:
            return 0
            
        # Sort by score and recency (weighted combination)
        now = datetime.utcnow().timestamp()
        
        def entry_priority(entry):
            symbol, timestamp, score, _ = entry
            recency = 1.0 - min(1.0, (now - timestamp) / (30 * 24 * 3600))  # 30 days max
            return (score * 0.7) + (recency * 0.3)  # 70% score, 30% recency
            
        sorted_entries = sorted(self.reinforcement_registry, key=entry_priority, reverse=True)
        
        # Keep only the highest priority entries
        self.reinforcement_registry = sorted_entries[:target_size]
        
        pruned_count = original_size - len(self.reinforcement_registry)
        logger.info(f"Pruned {pruned_count} entries from reinforcement registry")
        
        return pruned_count
    
    def reinforce_connections(self, 
                             active_neurons: Optional[List[str]] = None, 
                             current_time: Optional[float] = None,
                             reinforcement_strength: Optional[float] = None) -> Dict[str, Any]:
        """
        Reinforce connections between recently active neurons.
        
        Args:
            active_neurons: List of currently active neuron IDs
                          (defaults to all neurons with recent activity)
            current_time: Current timestamp (defaults to current time)
            reinforcement_strength: Optional override for reinforcement strength
            
        Returns:
            Dict containing reinforcement operation summary
        """
        try:
            # Validate input
            input_data = {
                'operation': 'reinforce_connections',
                'active_neurons': active_neurons or list(self.activation_history.keys()),
                'reinforcement_strength': reinforcement_strength
            }
            self.interface_contract(input_data)
            
            if current_time is None:
                current_time = time.time()
                
            # If no specific neurons provided, use all with recent activity
            if active_neurons is None:
                active_neurons = list(self.activation_history.keys())
                
            # Check if sync is needed
            self.sync_clock()
            
            # Apply decay to all existing connections
            self._apply_connection_decay(current_time)
            
            # Track reinforcement operations for logging
            reinforcement_ops = {
                'connections_reinforced': 0,
                'new_connections': 0,
                'total_strength_delta': 0.0,
                'neurons_processed': len(active_neurons),
                'timestamp': current_time
            }
            
            # Process each pair of active neurons
            for i, neuron1 in enumerate(active_neurons):
                if neuron1 not in self.activation_history:
                    continue
                    
                for neuron2 in active_neurons[i+1:]:
                    if neuron2 not in self.activation_history:
                        continue
                        
                    # Skip self-connections
                    if neuron1 == neuron2:
                        continue
                        
                    # Calculate temporal correlation between neuron activations
                    correlation = self._calculate_temporal_correlation(neuron1, neuron2, current_time)
                    
                    if correlation > 0:
                        # Create connection key (alphabetically sorted for consistency)
                        conn_key = tuple(sorted([neuron1, neuron2]))
                        
                        # Get current connection strength or initialize
                        current_strength = self.connection_strengths.get(conn_key, 0.0)
                        
                        # Calculate reinforcement amount
                        base_reinforcement = correlation * self.learning_rate
                        
                        # Apply custom reinforcement strength if provided
                        if reinforcement_strength is not None:
                            base_reinforcement *= reinforcement_strength
                            
                        # Normalize through cognitive energy flow
                        reinforcement = self.cognitive_energy_flow(base_reinforcement, 'reinforcement')
                        
                        # Apply reinforcement
                        new_strength = min(1.0, current_strength + reinforcement)
                        self.connection_strengths[conn_key] = new_strength
                        
                        # Update last reinforcement time
                        self.last_reinforcement[conn_key] = current_time
                        
                        # Track operation for logging
                        if current_strength == 0:
                            reinforcement_ops['new_connections'] += 1
                            self.metrics['connections_created'] += 1
                        else:
                            reinforcement_ops['connections_reinforced'] += 1
                            self.metrics['connections_strengthened'] += 1
                            
                        reinforcement_ops['total_strength_delta'] += (new_strength - current_strength)
                        
                        # Register symbols if both neurons look like symbols
                        if (len(neuron1) < 50 and not neuron1.startswith('neuron_') and
                            len(neuron2) < 50 and not neuron2.startswith('neuron_')):
                            # Register connection as a symbol pair
                            symbol_pair = f"{neuron1}:{neuron2}"
                            self.register_symbol(
                                symbol_pair, 
                                new_strength,
                                ['connection', 'pair']
                            )
            
            # Update metrics
            self.metrics['reinforcements_processed'] += 1
            
            # Self-regulate periodically
            self.self_regulate()
            
            # Validate resonance
            validation_result = self.resonance_chain_validator(
                input_data,
                reinforcement_ops
            )
            
            # Log reinforcement summary
            logger.info(
                f"Reinforced {reinforcement_ops['connections_reinforced']} connections, "
                f"created {reinforcement_ops['new_connections']} new connections, "
                f"total strength delta: {reinforcement_ops['total_strength_delta']:.4f}"
            )
            
            reinforcement_ops['status'] = 'success' if validation_result else 'warning'
            reinforcement_ops['message'] = 'Reinforcement completed successfully' if validation_result else 'Reinforcement completed with resonance warning'
            
            return reinforcement_ops
            
        except Exception as e:
            logger.error(f"Error reinforcing connections: {str(e)}")
            return self.graceful_fallback('reinforcement_error', {
                'active_neurons_count': len(active_neurons) if active_neurons else 0,
                'error': str(e)
            })
    
    def _apply_connection_decay(self, current_time: float) -> int:
        """
        Apply time-based decay to all connections.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            Number of connections decayed
        """
        decayed_count = 0
        
        for conn_key, strength in list(self.connection_strengths.items()):
            # Skip if no last reinforcement record
            if conn_key not in self.last_reinforcement:
                continue
                
            # Calculate time since last reinforcement
            last_time = self.last_reinforcement[conn_key]
            time_delta = current_time - last_time
            
            # Convert to hours for decay calculation
            hours_elapsed = time_delta / 3600
            
            # Calculate decay factor using decay curve
            decay_factor = self._calculate_decay_curve(hours_elapsed)
            
            # Normalize through cognitive energy flow
            decay_energy = self.cognitive_energy_flow(1.0 - decay_factor, 'decay')
            adjusted_decay_factor = 1.0 - decay_energy
            
            # Apply decay
            new_strength = strength * adjusted_decay_factor
            
            # Update or remove if below threshold
            if new_strength < 0.01:
                del self.connection_strengths[conn_key]
                del self.last_reinforcement[conn_key]
            else:
                self.connection_strengths[conn_key] = new_strength
                
            decayed_count += 1
            
        self.metrics['connections_decayed'] += decayed_count
        return decayed_count
    
    def _calculate_decay_curve(self, hours_elapsed: float) -> float:
        """
        Calculate decay factor using a natural decay curve.
        
        Args:
            hours_elapsed: Hours since last reinforcement
            
        Returns:
            Decay factor (0-1, where 1 means no decay)
        """
        # Base exponential decay
        base_decay = np.exp(-self.decay_rate * hours_elapsed)
        
        # Apply sigmoid curve to create more natural forgetting
        # Fast initial decay, then slower long-term decay
        if hours_elapsed > 24:  # After 24 hours, use different curve
            days_elapsed = hours_elapsed / 24
            long_term_decay = 1.0 / (1.0 + 0.1 * np.sqrt(days_elapsed))
            decay_factor = base_decay * long_term_decay
        else:
            decay_factor = base_decay
            
        # Ensure bounds
        return max(0.0, min(1.0, decay_factor))
    
    def _calculate_temporal_correlation(self, neuron1: str, neuron2: str, current_time: float) -> float:
        """
        Calculate temporal correlation between two neurons' activation patterns.
        
        Args:
            neuron1: First neuron ID
            neuron2: Second neuron ID
            current_time: Current timestamp
            
        Returns:
            Correlation strength (0-1)
        """
        # Get activation histories
        activations1 = self.activation_history.get(neuron1, [])
        activations2 = self.activation_history.get(neuron2, [])
        
        if not activations1 or not activations2:
            return 0.0
            
        # Calculate correlation based on temporal proximity and activation strengths
        correlation = 0.0
        
        for act1 in activations1:
            for act2 in activations2:
                # Calculate temporal proximity (0-1, higher for closer in time)
                time_diff = abs(act1['timestamp'] - act2['timestamp'])
                max_time_diff = self.temporal_window * 60  # Convert minutes to seconds
                temporal_proximity = max(0.0, 1.0 - (time_diff / max_time_diff))
                
                # Check for shared tags (increases correlation)
                tag_overlap = len(set(act1.get('tags', [])) & set(act2.get('tags', [])))
                tag_bonus = min(0.2, 0.05 * tag_overlap)  # Up to 0.2 bonus for shared tags
                
                # Weight by activation strengths and temporal proximity
                weight = act1['strength'] * act2['strength'] * (temporal_proximity + tag_bonus)
                correlation += weight
                
        # Normalize by number of comparisons
        total_comparisons = len(activations1) * len(activations2)
        normalized_correlation = correlation / total_comparisons if total_comparisons > 0 else 0.0
        
        return normalized_correlation
    
    def _prune_weak_connections(self, threshold: float = 0.1) -> int:
        """
        Prune connections below specified strength threshold.
        
        Args:
            threshold: Minimum strength to retain
            
        Returns:
            Number of connections pruned
        """
        original_count = len(self.connection_strengths)
        
        # Remove weak connections
        weak_keys = [k for k, v in self.connection_strengths.items() if v < threshold]
        
        for key in weak_keys:
            del self.connection_strengths[key]
            if key in self.last_reinforcement:
                del self.last_reinforcement[key]
                
        pruned_count = len(weak_keys)
        
        if pruned_count > 0:
            logger.info(f"Pruned {pruned_count} weak connections below threshold {threshold}")
            
        return pruned_count
    
    def get_strongest_connections(self, 
                                 neuron_id: Optional[str] = None, 
                                 top_k: int = 10) -> List[Tuple[str, str, float]]:
        """
        Get strongest connections for a neuron or across all neurons.
        
        Args:
            neuron_id: Specific neuron to query (None for all)
            top_k: Maximum number of connections to return
            
        Returns:
            List of (neuron1, neuron2, strength) tuples sorted by strength
        """
        try:
            # Validate input
            input_data = {
                'operation': 'get_connections',
                'neuron_id': neuron_id or '',
                'top_k': top_k
            }
            self.interface_contract(input_data)
            
            connections = []
            
            for conn_key, strength in self.connection_strengths.items():
                neuron1, neuron2 = conn_key
                
                # Filter by neuron_id if specified
                if neuron_id is not None and neuron_id not in conn_key:
                    continue
                    
                connections.append((neuron1, neuron2, strength))
                
            # Sort by strength (descending)
            connections.sort(key=lambda x: x[2], reverse=True)
            
            # Validate resonance
            self.resonance_chain_validator(
                input_data,
                {'connections_count': len(connections[:top_k])}
            )
            
            return connections[:top_k]
            
        except Exception as e:
            logger.error(f"Error getting strongest connections: {str(e)}")
            self.graceful_fallback('query_error', {
                'neuron_id': neuron_id,
                'error': str(e)
            })
            return []  # Return empty list on error
    
    def get_symbol_reinforcements(self, 
                                symbol: Optional[str] = None, 
                                tag: Optional[str] = None,
                                limit: int = 50) -> List[Tuple[str, float, float, List[str]]]:
        """
        Get reinforcement history for symbols.
        
        Args:
            symbol: Specific symbol to query (None for all)
            tag: Filter by specific tag (None for all)
            limit: Maximum number of entries to return
            
        Returns:
            List of (symbol, timestamp, score, tags) tuples
        """
        try:
            results = []
            
            for entry in reversed(self.reinforcement_registry):  # Most recent first
                entry_symbol, timestamp, score, tags = entry
                
                # Filter by symbol if specified
                if symbol is not None and entry_symbol != symbol:
                    continue
                    
                # Filter by tag if specified
                if tag is not None and tag not in tags:
                    continue
                    
                results.append(entry)
                
                if len(results) >= limit:
                    break
                    
            return results
            
        except Exception as e:
            logger.error(f"Error getting symbol reinforcements: {str(e)}")
            self.graceful_fallback('query_error', {
                'symbol': symbol,
                'error': str(e)
            })
            return []  # Return empty list on error
    
    def export_connection_graph(self, min_strength: float = 0.1) -> Dict[str, Any]:
        """
        Export connection graph for visualization.
        
        Args:
            min_strength: Minimum connection strength to include
            
        Returns:
            Dict containing graph representation with nodes and edges
        """
        try:
            # Validate input
            input_data = {
                'operation': 'export_graph',
                'min_strength': min_strength
            }
            
            nodes = set()
            edges = []
            
            for conn_key, strength in self.connection_strengths.items():
                if strength >= min_strength:
                    neuron1, neuron2 = conn_key
                    nodes.add(neuron1)
                    nodes.add(neuron2)
                    edges.append({
                        'source': neuron1,
                        'target': neuron2,
                        'strength': strength,
                        'last_reinforced': self.last_reinforcement.get(conn_key, 0)
                    })
                    
            # Validate resonance
            self.resonance_chain_validator(
                input_data,
                {'nodes_count': len(nodes), 'edges_count': len(edges)}
            )
            
            return {
                'nodes': list(nodes),
                'edges': edges,
                'metadata': {
                    'min_strength': min_strength,
                    'timestamp': datetime.utcnow().isoformat(),
                    'total_connections': len(self.connection_strengths),
                    'operational_state': self.operational_state
                }
            }
            
        except Exception as e:
            logger.error(f"Error exporting connection graph: {str(e)}")
            self.graceful_fallback('export_error', {
                'min_strength': min_strength,
                'error': str(e)
            })
            return {'nodes': [], 'edges': [], 'error': str(e)}
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get operational metrics for the knowledge reinforcer.
        
        Returns:
            Dict containing operational metrics
        """
        return {
            'metrics': self.metrics,
            'operational_state': self.operational_state,
            'registry_size': len(self.reinforcement_registry),
            'connections_count': len(self.connection_strengths),
            'error_count': self.error_count,
            'last_sync': self.last_sync.isoformat(),
            'last_regulation': self.last_regulation.isoformat(),
            'last_validation': self.last_validation.isoformat(),
            'harmonic_signature': self.harmonic_signature()
        }
    
    def decay_curve(self, hours: float) -> float:
        """
        Public interface to the decay curve calculation.
        
        Args:
            hours: Hours elapsed
            
        Returns:
            Decay factor (0-1)
        """
        return self._calculate_decay_curve(hours)
