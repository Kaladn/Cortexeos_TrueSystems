"""
Lexicon Seeder module for CortexOS Temporal Cognition v2.1

This module seeds the neural network with language primitives, creating word-neurons
with 6-1-6 context maps (before-word-after) and part-of-speech influence on connection strength.
Each word is represented as a neuron with its own context map and resonance properties.

The module implements all seven required Agharmonic Law interfaces:
- harmonic_signature(): Establishes frequency compatibility parameters
- interface_contract(): Defines allowed function calls and data structures
- cognitive_energy_flow(): Normalizes signal amplitude and information flow
- sync_clock(): Connects to the master temporal framework
- self_regulate(): Implements feedback loops for stability
- graceful_fallback(): Provides mechanisms for partial operation
- resonance_chain_validator(): Verifies resonance integrity
"""

import json
import logging
import time
import random
import hashlib
from datetime import datetime
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LexiconSeeder:
    """
    Seeds the neural network with language primitives, creating word-neurons
    with 6-1-6 context maps and POS tag influence on connection strength.
    """
    
    def __init__(self, lexicon_path, cortex_cube=None, global_sync_manager=None):
        """
        Initialize the LexiconSeeder with paths and dependencies.
        
        Args:
            lexicon_path (str): Path to the lexicon file
            cortex_cube (object, optional): Reference to CortexCubeNVME instance
            global_sync_manager (object, optional): Reference to GlobalSyncManager
        """
        self.lexicon_path = lexicon_path
        self.lexicon = {}
        self.cortex_cube = cortex_cube
        self.global_sync_manager = global_sync_manager
        self.last_sync = datetime.utcnow()
        self.seeding_buffer = deque(maxlen=1000)
        self.seeding_metrics = {
            'total_seeded': 0,
            'successful_seeds': 0,
            'failed_seeds': 0,
            'last_seeding_time': None,
            'pos_distribution': defaultdict(int)
        }
        self.pos_weights = {
            'NOUN': 1.0,
            'VERB': 0.9,
            'ADJ': 0.8,
            'ADV': 0.7,
            'PRON': 0.6,
            'DET': 0.5,
            'PREP': 0.5,
            'CONJ': 0.4,
            'PART': 0.3,
            'NUM': 0.7,
            'INTJ': 0.6,
            'SYM': 0.5,
            'X': 0.3  # Unknown
        }
        self.context_array_size = 13  # 6-1-6 context map + word itself
        self.resonance_threshold = 0.75
        self.is_initialized = False
        self.fallback_mode = False
        self.health_status = 1.0  # 1.0 = fully healthy
        
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for the lexicon seeder.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            'module': 'lexicon_seeder',
            'input_frequency_range': [0.4, 1.2],
            'output_phase_alignment': 0.05,
            'resonance_threshold': self.resonance_threshold,
            'pos_influence_enabled': True,
            'context_array_dimensions': self.context_array_size,
            'binary_cell_compatible': True
        }
        
    def interface_contract(self, params):
        """
        Validates input parameters against the expected interface.
        
        Args:
            params (dict): Input parameters to validate
            
        Returns:
            bool: True if valid, raises exception otherwise
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not isinstance(params, dict):
            raise ValueError("Parameters must be provided as a dictionary")
            
        required_keys = ['word_list']
        if not all(key in params for key in required_keys):
            missing = [k for k in required_keys if k not in params]
            raise ValueError(f"Missing required parameters: {missing}")
            
        # Validate word_list format
        if not isinstance(params['word_list'], list):
            raise ValueError("word_list must be a list of words")
            
        # Validate optional parameters
        if 'pos_tags' in params and len(params['pos_tags']) != len(params['word_list']):
            raise ValueError("pos_tags length must match word_list length")
            
        if 'frequency_data' in params and len(params['frequency_data']) != len(params['word_list']):
            raise ValueError("frequency_data length must match word_list length")
            
        return True
        
    def cognitive_energy_flow(self, signal_strength, pos_tag=None):
        """
        Normalizes signal amplitude based on part-of-speech and other factors.
        
        Args:
            signal_strength (float): Raw signal strength
            pos_tag (str, optional): Part of speech tag
            
        Returns:
            float: Normalized signal strength
        """
        # Base normalization to 0.0-1.0 range
        normalized = max(0.0, min(1.0, signal_strength))
        
        # Apply POS tag weighting if available
        if pos_tag and pos_tag in self.pos_weights:
            normalized *= self.pos_weights[pos_tag]
            
        # Apply health status modifier
        normalized *= self.health_status
        
        return normalized
        
    def sync_clock(self):
        """
        Synchronizes with the global temporal framework.
        
        Returns:
            bool: True if sync successful, False otherwise
        """
        if self.global_sync_manager is None:
            # Fallback to internal timing if no global sync manager
            current_time = datetime.utcnow()
            time_delta = (current_time - self.last_sync).total_seconds()
            is_time_to_sync = time_delta > 5.0  # 5-second cycle
            
            if is_time_to_sync:
                self.last_sync = current_time
                return True
            return False
            
        try:
            # Attempt to sync with global manager
            sync_result = self.global_sync_manager.request_sync('lexicon_seeder')
            if sync_result.get('status') == 'success':
                self.last_sync = datetime.utcnow()
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to sync with global manager: {e}")
            # Fallback to internal timing
            return self.sync_clock()
            
    def self_regulate(self):
        """
        Implements internal feedback loops for stability.
        
        Returns:
            dict: Self-regulation metrics
        """
        metrics = {
            'buffer_size': len(self.seeding_buffer),
            'buffer_capacity': self.seeding_buffer.maxlen,
            'buffer_utilization': len(self.seeding_buffer) / self.seeding_buffer.maxlen if self.seeding_buffer.maxlen else 0,
            'health_status': self.health_status,
            'fallback_mode': self.fallback_mode
        }
        
        # Check buffer health
        if metrics['buffer_utilization'] > 0.9:
            logger.warning("Seeding buffer near capacity, applying backpressure")
            # Apply backpressure by slowing down
            time.sleep(0.1)
            
        # Check success rate
        if self.seeding_metrics['total_seeded'] > 0:
            success_rate = self.seeding_metrics['successful_seeds'] / self.seeding_metrics['total_seeded']
            metrics['success_rate'] = success_rate
            
            # Adjust health status based on success rate
            if success_rate < 0.5:
                self.health_status = max(0.5, self.health_status - 0.1)
                logger.warning(f"Low seeding success rate ({success_rate:.2f}), health status adjusted to {self.health_status}")
            elif success_rate > 0.9 and self.health_status < 1.0:
                self.health_status = min(1.0, self.health_status + 0.05)
                logger.info(f"Good seeding success rate ({success_rate:.2f}), health status improved to {self.health_status}")
                
        return metrics
        
    def graceful_fallback(self, error_type, context=None):
        """
        Provides mechanisms for partial operation during failures.
        
        Args:
            error_type (str): Type of error triggering fallback
            context (dict, optional): Additional context about the error
            
        Returns:
            dict: Fallback status and actions taken
        """
        fallback_actions = {
            'status': 'fallback_activated',
            'error_type': error_type,
            'actions_taken': []
        }
        
        if error_type == 'lexicon_file_not_found':
            # Create an empty lexicon and continue
            logger.warning(f"Lexicon file not found: {self.lexicon_path}, operating with empty lexicon")
            self.lexicon = {}
            self.fallback_mode = True
            fallback_actions['actions_taken'].append('created_empty_lexicon')
            
        elif error_type == 'cortex_cube_unavailable':
            # Buffer seeds for later processing
            logger.warning("CortexCube unavailable, buffering seeds for later processing")
            self.fallback_mode = True
            fallback_actions['actions_taken'].append('enabled_seed_buffering')
            
        elif error_type == 'json_decode_error':
            # Skip problematic entries and continue
            logger.warning(f"JSON decode error in lexicon file, skipping problematic entries")
            problematic_line = context.get('line', 'unknown') if context else 'unknown'
            logger.debug(f"Problematic line: {problematic_line}")
            fallback_actions['actions_taken'].append('skipped_problematic_entries')
            
        elif error_type == 'memory_allocation_failure':
            # Reduce buffer size and continue with minimal operation
            logger.warning("Memory allocation failure, reducing buffer size")
            self.seeding_buffer = deque(maxlen=100)  # Reduce buffer size
            self.fallback_mode = True
            fallback_actions['actions_taken'].append('reduced_buffer_size')
            
        else:
            # Generic fallback
            logger.warning(f"Unknown error type: {error_type}, activating generic fallback")
            self.fallback_mode = True
            fallback_actions['actions_taken'].append('generic_fallback_activated')
            
        # Adjust health status
        self.health_status = max(0.3, self.health_status - 0.2)
        fallback_actions['health_status'] = self.health_status
        
        return fallback_actions
        
    def resonance_chain_validator(self, seed_operation=None):
        """
        Verifies resonance integrity across the chain.
        
        Args:
            seed_operation (dict, optional): Details of the seed operation to validate
            
        Returns:
            dict: Validation results
        """
        validation_result = {
            'status': 'valid',
            'issues': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check if cortex_cube is available
        if self.cortex_cube is None:
            validation_result['status'] = 'warning'
            validation_result['issues'].append('cortex_cube_not_connected')
            
        # Validate specific seed operation if provided
        if seed_operation:
            # Check for required fields
            required_fields = ['word', 'pos', 'context_array']
            missing_fields = [f for f in required_fields if f not in seed_operation]
            if missing_fields:
                validation_result['status'] = 'invalid'
                validation_result['issues'].append(f'missing_required_fields: {missing_fields}')
                
            # Check context array format
            if 'context_array' in seed_operation:
                context_array = seed_operation['context_array']
                if not isinstance(context_array, list) or len(context_array) != self.context_array_size:
                    validation_result['status'] = 'invalid'
                    validation_result['issues'].append(f'invalid_context_array_format: expected list of size {self.context_array_size}')
                    
            # Check POS tag validity
            if 'pos' in seed_operation and seed_operation['pos'] not in self.pos_weights:
                validation_result['status'] = 'warning'
                validation_result['issues'].append(f'unknown_pos_tag: {seed_operation["pos"]}')
                
        # Check overall module health
        if self.fallback_mode:
            validation_result['status'] = 'degraded'
            validation_result['issues'].append('operating_in_fallback_mode')
            
        if self.health_status < 0.8:
            validation_result['status'] = 'degraded'
            validation_result['issues'].append(f'reduced_health_status: {self.health_status}')
            
        return validation_result

    def load_lexicon(self):
        """
        Loads the lexicon from the specified file path.
        
        Returns:
            dict: Loading status and metrics
        """
        result = {
            'status': 'success',
            'entries_loaded': 0,
            'entries_skipped': 0,
            'errors': []
        }
        
        try:
            with open(self.lexicon_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped_line = line.strip()
                    if not stripped_line:  # Skip empty lines
                        continue
                    try:
                        entry = json.loads(stripped_line)
                        if self.validate_entry(entry):
                            self.lexicon[entry['id']] = entry
                            result['entries_loaded'] += 1
                        else:
                            result['entries_skipped'] += 1
                            logger.warning(f"Invalid entry skipped: {entry}")
                    except json.JSONDecodeError as e:
                        result['errors'].append(f"JSON decode error: {e}")
                        result['entries_skipped'] += 1
                        context = {'line': stripped_line}
                        self.graceful_fallback('json_decode_error', context)
                        
            logger.info(f"Loaded {result['entries_loaded']} valid lexicon entries, skipped {result['entries_skipped']}")
            self.is_initialized = True
            
        except FileNotFoundError:
            result['status'] = 'error'
            result['errors'].append(f"Lexicon file not found: {self.lexicon_path}")
            logger.error(f"Lexicon file not found: {self.lexicon_path}")
            self.graceful_fallback('lexicon_file_not_found')
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Unexpected error: {str(e)}")
            logger.error(f"Unexpected error loading lexicon: {e}", exc_info=True)
            self.graceful_fallback('unexpected_error', {'error': str(e)})
            
        return result

    def validate_entry(self, entry):
        """
        Validates a lexicon entry against required schema.
        
        Args:
            entry (dict): Lexicon entry to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_keys = ['id', 'word', 'form', 'pos', 'pitch_range', 'tone_profile', 'resonant_links', 'symbol_tags']
        if not all(key in entry for key in required_keys):
            return False
            
        # Validate POS tag
        if entry['pos'] not in self.pos_weights:
            # Default to 'X' (unknown) if not recognized
            entry['pos'] = 'X'
            
        return True

    def get_entry_by_id(self, neuron_id):
        """
        Retrieves a lexicon entry by its neuron ID.
        
        Args:
            neuron_id (str): ID of the neuron to retrieve
            
        Returns:
            dict: Lexicon entry or None if not found
        """
        return self.lexicon.get(neuron_id)

    def get_all_entries(self):
        """
        Retrieves all lexicon entries.
        
        Returns:
            list: All lexicon entries
        """
        return list(self.lexicon.values())

    def print_summary(self):
        """
        Prints a summary of the loaded lexicon.
        
        Returns:
            dict: Summary metrics
        """
        summary = {
            'total_entries': len(self.lexicon),
            'pos_distribution': defaultdict(int),
            'health_status': self.health_status
        }
        
        if not self.lexicon:
            logger.info("No lexicon entries loaded to summarize.")
            return summary
            
        for eid, data in self.lexicon.items():
            pos = data['pos']
            summary['pos_distribution'][pos] += 1
            logger.debug(f"{eid}: {data['word']} ({pos}) → tags: {', '.join(data['symbol_tags'])}")
            
        # Log summary
        logger.info(f"Lexicon summary: {len(self.lexicon)} entries")
        for pos, count in summary['pos_distribution'].items():
            logger.info(f"  {pos}: {count} entries")
            
        return summary
        
    def create_context_array(self, word, context_before=None, context_after=None):
        """
        Creates a 6-1-6 context array for a word.
        
        Args:
            word (str): The word itself
            context_before (list, optional): Words before (up to 6)
            context_after (list, optional): Words after (up to 6)
            
        Returns:
            list: 13-element context array (6 before, word, 6 after)
        """
        # Initialize empty context array
        context_array = [None] * self.context_array_size
        
        # Set the word at the middle position (index 6)
        middle_index = self.context_array_size // 2
        context_array[middle_index] = word
        
        # Fill in context before
        if context_before:
            before_slice = context_before[-6:] if len(context_before) > 6 else context_before
            for i, ctx_word in enumerate(reversed(before_slice)):
                context_array[middle_index - i - 1] = ctx_word
                
        # Fill in context after
        if context_after:
            after_slice = context_after[:6] if len(context_after) > 6 else context_after
            for i, ctx_word in enumerate(after_slice):
                context_array[middle_index + i + 1] = ctx_word
                
        return context_array
        
    def seed_word(self, word, pos=None, frequency=None, context_before=None, context_after=None):
        """
        Seeds a single word into the neural network.
        
        Args:
            word (str): Word to seed
            pos (str, optional): Part of speech tag
            frequency (float, optional): Word frequency (0.0-1.0)
            context_before (list, optional): Words before (up to 6)
            context_after (list, optional): Words after (up to 6)
            
        Returns:
            dict: Seeding result
        """
        if not self.is_initialized:
            self.load_lexicon()
            
        result = {
            'status': 'pending',
            'word': word,
            'neuron_id': None,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Generate neuron ID from word
        neuron_id = hashlib.md5(word.encode('utf-8')).hexdigest()
        result['neuron_id'] = neuron_id
        
        # Default POS to 'X' if not provided
        if not pos:
            pos = 'X'
            
        # Default frequency to 0.5 if not provided
        if frequency is None:
            frequency = 0.5
            
        # Create context array
        context_array = self.create_context_array(word, context_before, context_after)
        
        # Create seed operation for validation
        seed_operation = {
            'word': word,
            'pos': pos,
            'frequency': frequency,
            'context_array': context_array,
            'neuron_id': neuron_id
        }
        
        # Validate the operation
        validation = self.resonance_chain_validator(seed_operation)
        if validation['status'] == 'invalid':
            result['status'] = 'failed'
            result['errors'] = validation['issues']
            self.seeding_metrics['failed_seeds'] += 1
            self.seeding_metrics['total_seeded'] += 1
            return result
            
        # Apply POS influence on connection strength
        connection_strength = self.cognitive_energy_flow(frequency, pos)
        
        # Create binary cell structure
        binary_cell = {
            'header': {
                'word': word,
                'neuron_id': neuron_id,
                'pos': pos,
                'frequency': frequency,
                'connection_strength': connection_strength,
                'timestamp': datetime.utcnow().timestamp()
            },
            'context_array': context_array,
            'symbol_tags': [],
            'resonant_links': []
        }
        
        # Attempt to write to cortex cube
        if self.cortex_cube:
            try:
                # Calculate coordinates based on word hash
                hash_int = int(neuron_id[:8], 16)
                x = hash_int % 64
                y = (hash_int // 64) % 64
                z = (hash_int // (64 * 64)) % 64
                
                write_result = self.cortex_cube.write(
                    memory_cell=binary_cell,
                    write_coordinates=(x, y, z),
                    source_id='lexicon_seeder',
                    priority_level=self.pos_weights.get(pos, 0.5)
                )
                
                if write_result.get('status') == 'success':
                    result['status'] = 'success'
                    result['coordinates'] = (x, y, z)
                    self.seeding_metrics['successful_seeds'] += 1
                else:
                    result['status'] = 'failed'
                    result['errors'] = [write_result.get('error', 'Unknown write error')]
                    # Buffer for retry
                    self.seeding_buffer.append(seed_operation)
                    self.seeding_metrics['failed_seeds'] += 1
            except Exception as e:
                result['status'] = 'failed'
                result['errors'] = [str(e)]
                # Buffer for retry
                self.seeding_buffer.append(seed_operation)
                self.seeding_metrics['failed_seeds'] += 1
                self.graceful_fallback('cortex_cube_error', {'error': str(e)})
        else:
            # No cortex cube available, buffer the operation
            self.seeding_buffer.append(seed_operation)
            result['status'] = 'buffered'
            self.graceful_fallback('cortex_cube_unavailable')
            
        # Update metrics
        self.seeding_metrics['total_seeded'] += 1
        self.seeding_metrics['last_seeding_time'] = datetime.utcnow().isoformat()
        self.seeding_metrics['pos_distribution'][pos] += 1
        
        # Self-regulate
        self.self_regulate()
        
        return result
        
    def seed_words(self, word_list, pos_tags=None, frequency_data=None):
        """
        Seeds multiple words into the neural network.
        
        Args:
            word_list (list): List of words to seed
            pos_tags (list, optional): Corresponding POS tags
            frequency_data (list, optional): Corresponding frequency data
            
        Returns:
            dict: Seeding results
        """
        # Validate input parameters
        try:
            self.interface_contract({
                'word_list': word_list,
                'pos_tags': pos_tags,
                'frequency_data': frequency_data
            })
        except ValueError as e:
            return {
                'status': 'error',
                'error': str(e),
                'words_processed': 0,
                'successful_seeds': 0,
                'failed_seeds': 0
            }
            
        results = {
            'status': 'success',
            'words_processed': 0,
            'successful_seeds': 0,
            'failed_seeds': 0,
            'buffered_seeds': 0,
            'word_results': []
        }
        
        # Process each word
        for i, word in enumerate(word_list):
            pos = pos_tags[i] if pos_tags and i < len(pos_tags) else None
            freq = frequency_data[i] if frequency_data and i < len(frequency_data) else None
            
            # Get context words (if available)
            context_before = word_list[max(0, i-6):i] if i > 0 else []
            context_after = word_list[i+1:i+7] if i < len(word_list)-1 else []
            
            # Seed the word
            word_result = self.seed_word(word, pos, freq, context_before, context_after)
            results['words_processed'] += 1
            
            if word_result['status'] == 'success':
                results['successful_seeds'] += 1
            elif word_result['status'] == 'buffered':
                results['buffered_seeds'] += 1
            else:
                results['failed_seeds'] += 1
                
            results['word_results'].append(word_result)
            
            # Check if we should sync
            if self.sync_clock():
                # Process any buffered seeds if cortex cube is available
                self.process_buffer()
                
        # Final metrics
        if results['words_processed'] > 0:
            success_rate = results['successful_seeds'] / results['words_processed']
            results['success_rate'] = success_rate
            
        return results
        
    def process_buffer(self):
        """
        Processes any buffered seed operations.
        
        Returns:
            dict: Buffer processing results
        """
        if not self.cortex_cube or not self.seeding_buffer:
            return {
                'status': 'skipped',
                'reason': 'cortex_cube_unavailable' if not self.cortex_cube else 'buffer_empty',
                'buffer_size': len(self.seeding_buffer)
            }
            
        results = {
            'status': 'success',
            'operations_processed': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'remaining_buffer_size': len(self.seeding_buffer)
        }
        
        # Process up to 100 buffered operations
        operations_to_process = min(100, len(self.seeding_buffer))
        for _ in range(operations_to_process):
            if not self.seeding_buffer:
                break
                
            seed_operation = self.seeding_buffer.popleft()
            results['operations_processed'] += 1
            
            try:
                # Calculate coordinates based on word hash
                neuron_id = seed_operation['neuron_id']
                hash_int = int(neuron_id[:8], 16)
                x = hash_int % 64
                y = (hash_int // 64) % 64
                z = (hash_int // (64 * 64)) % 64
                
                # Create binary cell structure
                binary_cell = {
                    'header': {
                        'word': seed_operation['word'],
                        'neuron_id': neuron_id,
                        'pos': seed_operation['pos'],
                        'frequency': seed_operation['frequency'],
                        'connection_strength': self.cognitive_energy_flow(
                            seed_operation['frequency'], 
                            seed_operation['pos']
                        ),
                        'timestamp': datetime.utcnow().timestamp()
                    },
                    'context_array': seed_operation['context_array'],
                    'symbol_tags': [],
                    'resonant_links': []
                }
                
                write_result = self.cortex_cube.write(
                    memory_cell=binary_cell,
                    write_coordinates=(x, y, z),
                    source_id='lexicon_seeder_buffer',
                    priority_level=self.pos_weights.get(seed_operation['pos'], 0.5)
                )
                
                if write_result.get('status') == 'success':
                    results['successful_operations'] += 1
                    self.seeding_metrics['successful_seeds'] += 1
                    self.seeding_metrics['failed_seeds'] -= 1  # Adjust previous failure
                else:
                    results['failed_operations'] += 1
                    # Re-buffer for later retry with reduced priority
                    seed_operation['retry_count'] = seed_operation.get('retry_count', 0) + 1
                    if seed_operation['retry_count'] < 3:  # Limit retries
                        self.seeding_buffer.append(seed_operation)
            except Exception as e:
                results['failed_operations'] += 1
                logger.error(f"Error processing buffered seed: {e}")
                # Re-buffer for later retry with reduced priority
                seed_operation['retry_count'] = seed_operation.get('retry_count', 0) + 1
                if seed_operation['retry_count'] < 3:  # Limit retries
                    self.seeding_buffer.append(seed_operation)
                    
        results['remaining_buffer_size'] = len(self.seeding_buffer)
        
        # Self-regulate after buffer processing
        self.self_regulate()
        
        return results
        
    def get_seeding_metrics(self):
        """
        Returns current seeding metrics.
        
        Returns:
            dict: Seeding metrics
        """
        metrics = self.seeding_metrics.copy()
        metrics['buffer_size'] = len(self.seeding_buffer)
        metrics['buffer_capacity'] = self.seeding_buffer.maxlen
        metrics['health_status'] = self.health_status
        metrics['fallback_mode'] = self.fallback_mode
        
        # Convert defaultdict to regular dict for serialization
        metrics['pos_distribution'] = dict(metrics['pos_distribution'])
        
        return metrics
