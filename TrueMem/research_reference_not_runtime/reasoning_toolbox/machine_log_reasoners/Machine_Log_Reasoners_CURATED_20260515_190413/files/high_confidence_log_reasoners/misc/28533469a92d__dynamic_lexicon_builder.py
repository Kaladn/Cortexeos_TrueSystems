"""
Dynamic Lexicon Builder for Binary Neuron System

This module implements a dynamic lexicon builder that starts with NLTK words
and builds 6-1-6 context window relationships incrementally as text is processed.
"""

import os
import json
import numpy as np
import time
import hashlib
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from collections import defaultdict, Counter

# Import the Binary Neuron prototype components
from binary_neuron_prototype import (
    BinaryNeuron, 
    BinaryNeuronSerializer, 
    BinaryNeuronStorageManager,
    KnowledgeConverter,
    MemoryWeb
)

try:
    # Try to import nltk for word tokenization and base vocabulary
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import words as nltk_words
    HAVE_NLTK = True
    
    # Download necessary NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Downloading NLTK punkt tokenizer...")
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/words')
    except LookupError:
        print("Downloading NLTK words corpus...")
        nltk.download('words', quiet=True)
        
except ImportError:
    HAVE_NLTK = False
    print("NLTK not found. Using simplified word processing.")
    print("To install: pip install nltk")


class ContextWindowRelationship:
    """
    Represents the 6-1-6 context window relationship for a word.
    
    Tracks the top 10 words for each position in the context window.
    """
    
    def __init__(self, target_word: str):
        """
        Initialize the context window relationship.
        
        Args:
            target_word: The target word at the center of the context window
        """
        self.target_word = target_word
        
        # Initialize position counters (-6 to +6, excluding 0 which is the target word)
        self.position_counters = {
            pos: Counter() for pos in range(-6, 7) if pos != 0
        }
        
        # Track total occurrences
        self.total_occurrences = 0
        
        # Track when this was last updated
        self.last_updated = time.time()
    
    def update(self, context_words: List[str], positions: List[int]) -> None:
        """
        Update the context window with new occurrences.
        
        Args:
            context_words: List of words in the context
            positions: List of positions corresponding to each word (-6 to +6, excluding 0)
        """
        if len(context_words) != len(positions):
            raise ValueError("context_words and positions must have the same length")
        
        # Update counters for each position
        for word, pos in zip(context_words, positions):
            if pos != 0:  # Skip the target word position
                self.position_counters[pos][word] += 1
        
        # Increment total occurrences
        self.total_occurrences += 1
        
        # Update timestamp
        self.last_updated = time.time()
    
    def get_top_words(self, position: int, n: int = 10) -> List[Tuple[str, int]]:
        """
        Get the top N words for a specific position.
        
        Args:
            position: Position in the context window (-6 to +6, excluding 0)
            n: Number of top words to return
            
        Returns:
            List of (word, count) tuples for the top N words
        """
        if position == 0:
            raise ValueError("Position 0 is the target word position")
        
        if position not in self.position_counters:
            raise ValueError(f"Invalid position: {position}")
        
        return self.position_counters[position].most_common(n)
    
    def get_all_top_words(self, n: int = 10) -> Dict[int, List[Tuple[str, int]]]:
        """
        Get the top N words for all positions.
        
        Args:
            n: Number of top words to return for each position
            
        Returns:
            Dictionary mapping positions to lists of (word, count) tuples
        """
        return {
            pos: self.get_top_words(pos, n)
            for pos in self.position_counters.keys()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            'target_word': self.target_word,
            'position_counters': {
                str(pos): dict(counter)
                for pos, counter in self.position_counters.items()
            },
            'total_occurrences': self.total_occurrences,
            'last_updated': self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextWindowRelationship':
        """
        Create from dictionary representation.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ContextWindowRelationship instance
        """
        relationship = cls(data['target_word'])
        
        # Restore position counters
        for pos_str, counter_dict in data['position_counters'].items():
            pos = int(pos_str)
            relationship.position_counters[pos] = Counter(counter_dict)
        
        # Restore other attributes
        relationship.total_occurrences = data['total_occurrences']
        relationship.last_updated = data['last_updated']
        
        return relationship


class WordNeuron(BinaryNeuron):
    """
    Specialized Binary Neuron for representing words with context relationships.
    """
    
    def __init__(self, 
                 word: str,
                 uuid_str: Optional[str] = None,
                 vector: Optional[np.ndarray] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 binary_ref: Optional[int] = None):
        """
        Initialize a Word Neuron.
        
        Args:
            word: The word this neuron represents
            uuid_str: Optional UUID string
            vector: Optional embedding vector
            metadata: Optional metadata
            binary_ref: Optional binary reference
        """
        # Initialize base neuron
        super().__init__(uuid_str, vector, metadata, binary_ref)
        
        # Set word as the primary identifier
        self.word = word
        if metadata is None:
            self.metadata = {}
        self.metadata['word'] = word
        
        # Initialize context relationship
        self.context_relationship = ContextWindowRelationship(word)
    
    def update_context(self, context_words: List[str], positions: List[int]) -> None:
        """
        Update the context relationship with new occurrences.
        
        Args:
            context_words: List of words in the context
            positions: List of positions corresponding to each word
        """
        self.context_relationship.update(context_words, positions)
    
    def get_top_context_words(self, position: int, n: int = 10) -> List[Tuple[str, int]]:
        """
        Get the top N words for a specific position.
        
        Args:
            position: Position in the context window
            n: Number of top words to return
            
        Returns:
            List of (word, count) tuples for the top N words
        """
        return self.context_relationship.get_top_words(position, n)
    
    def get_all_top_context_words(self, n: int = 10) -> Dict[int, List[Tuple[str, int]]]:
        """
        Get the top N words for all positions.
        
        Args:
            n: Number of top words to return for each position
            
        Returns:
            Dictionary mapping positions to lists of (word, count) tuples
        """
        return self.context_relationship.get_all_top_words(n)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        # Get base neuron representation
        data = super().to_dict()
        
        # Add context relationship
        data['context_relationship'] = self.context_relationship.to_dict()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WordNeuron':
        """
        Create from dictionary representation.
        
        Args:
            data: Dictionary representation
            
        Returns:
            WordNeuron instance
        """
        # Extract word from metadata
        word = data['metadata'].get('word')
        if not word:
            raise ValueError("Word not found in metadata")
        
        # Create base neuron
        neuron = cls(
            word=word,
            uuid_str=data['uuid'],
            vector=np.array(data['vector'], dtype=np.float32),
            metadata=data['metadata'],
            binary_ref=data['binary_ref']
        )
        
        # Restore links
        neuron.links = data['links']
        
        # Restore original vector
        neuron._original_vector = np.array(data['_original_vector'], dtype=np.float32)
        
        # Restore tone history if present
        if '_tone_history' in data:
            neuron._tone_history = [
                {
                    'tone_vector': np.array(th['tone_vector'], dtype=np.float32),
                    'strength': th['strength'],
                    'timestamp': th['timestamp']
                }
                for th in data['_tone_history']
            ]
        
        # Restore context relationship if present
        if 'context_relationship' in data:
            neuron.context_relationship = ContextWindowRelationship.from_dict(
                data['context_relationship']
            )
        
        return neuron


class WordNeuronSerializer(BinaryNeuronSerializer):
    """
    Specialized serializer for Word Neurons.
    """
    
    def deserialize(self, data: bytes) -> WordNeuron:
        """
        Deserialize binary data to a Word Neuron.
        
        Args:
            data: Binary data to deserialize
            
        Returns:
            Deserialized WordNeuron
        """
        # Unpickle the dictionary
        neuron_dict = super().deserialize(data).to_dict()
        
        # Create Word Neuron from dictionary
        return WordNeuron.from_dict(neuron_dict)


class DynamicLexiconBuilder:
    """
    Builds a lexicon of words with 6-1-6 context window relationships dynamically.
    """
    
    def __init__(self, storage_dir: str, use_nltk_base: bool = True):
        """
        Initialize the dynamic lexicon builder.
        
        Args:
            storage_dir: Directory to store word neurons
            use_nltk_base: Whether to initialize with NLTK words
        """
        self.storage_dir = storage_dir
        
        # Create directories
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'lexicon_data'), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'visualizations'), exist_ok=True)
        
        # Initialize components
        self.storage_manager = BinaryNeuronStorageManager(storage_dir)
        self.serializer = WordNeuronSerializer()
        
        # Track processed words
        self.word_uuids = {}  # word -> uuid mapping
        self._load_word_index()
        
        # Statistics
        self.stats = {
            'total_words': 0,
            'total_updates': 0,
            'texts_processed': 0,
            'start_time': time.time()
        }
        
        # Initialize with NLTK words if requested
        if use_nltk_base and HAVE_NLTK:
            self._initialize_nltk_base()
    
    def _load_word_index(self) -> None:
        """Load the word to UUID index from disk."""
        index_path = os.path.join(self.storage_dir, 'lexicon_data', 'word_index.json')
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                self.word_uuids = json.load(f)
    
    def _save_word_index(self) -> None:
        """Save the word to UUID index to disk."""
        index_path = os.path.join(self.storage_dir, 'lexicon_data', 'word_index.json')
        with open(index_path, 'w') as f:
            json.dump(self.word_uuids, f)
    
    def _initialize_nltk_base(self) -> None:
        """Initialize with base vocabulary from NLTK."""
        print("Initializing with NLTK words...")
        
        # Get NLTK words
        nltk_word_list = set(w.lower() for w in nltk_words.words())
        
        # Filter out very short words and non-alphabetic words
        filtered_words = [w for w in nltk_word_list if len(w) > 1 and w.isalpha()]
        
        # Limit to a reasonable number for initial testing
        # In production, you might want to use the full list
        initial_words = filtered_words[:10000]  # Adjust as needed
        
        # Create word neurons for each word
        for word in initial_words:
            if word not in self.word_uuids:
                self._create_word_neuron(word)
        
        print(f"Initialized with {len(self.word_uuids)} NLTK words")
    
    def _create_word_neuron(self, word: str) -> str:
        """
        Create a new Word Neuron for a word.
        
        Args:
            word: Word to create a neuron for
            
        Returns:
            UUID of the created neuron
        """
        # Create embedding for the word
        embedding = self._create_word_embedding(word)
        
        # Create metadata
        metadata = {
            'word': word,
            'created_at': time.time()
        }
        
        # Create neuron
        neuron = WordNeuron(
            word=word,
            vector=embedding,
            metadata=metadata
        )
        
        # Store neuron
        uuid_str = self.storage_manager.store_neuron(neuron)
        
        # Update word index
        self.word_uuids[word] = uuid_str
        self._save_word_index()
        
        # Update statistics
        self.stats['total_words'] += 1
        
        return uuid_str
    
    def _create_word_embedding(self, word: str) -> np.ndarray:
        """
        Create an embedding vector for a word.
        
        Args:
            word: Word to create embedding for
            
        Returns:
            Embedding vector
        """
        # Use a simple hash-based approach for the prototype
        # In production, would use a proper word embedding model
        
        hash_obj = hashlib.sha256(word.encode())
        hash_bytes = hash_obj.digest()
        
        # Use the hash to seed a random number generator
        np.random.seed(int.from_bytes(hash_bytes[:4], byteorder='big'))
        
        # Generate a random vector
        vector = np.random.randn(512).astype(np.float32)
        
        # Normalize to unit length
        vector = vector / np.linalg.norm(vector)
        
        return vector
    
    def _get_word_neuron(self, word: str) -> Optional[WordNeuron]:
        """
        Get the Word Neuron for a word.
        
        Args:
            word: Word to get neuron for
            
        Returns:
            WordNeuron or None if not found
        """
        # Check if word exists in index
        if word not in self.word_uuids:
            return None
        
        # Get UUID
        uuid_str = self.word_uuids[word]
        
        # Get neuron from storage
        neuron = self.storage_manager.get_neuron(uuid_str)
        
        # Convert to WordNeuron if necessary
        if neuron and not isinstance(neuron, WordNeuron):
            neuron = WordNeuron.from_dict(neuron.to_dict())
        
        return neuron
    
    def _ensure_word_exists(self, word: str) -> str:
        """
        Ensure a word exists in the lexicon, creating it if necessary.
        
        Args:
            word: Word to ensure exists
            
        Returns:
            UUID of the word neuron
        """
        # Check if word exists
        if word in self.word_uuids:
            return self.word_uuids[word]
        
        # Create new word neuron
        return self._create_word_neuron(word)
    
    def process_text(self, text: str) -> int:
        """
        Process text to update context window relationships.
        
        Args:
            text: Text to process
            
        Returns:
            Number of context window updates performed
        """
        # Tokenize text
        if HAVE_NLTK:
            tokens = word_tokenize(text.lower())
        else:
            # Simple tokenization
            tokens = text.lower().split()
        
        # Clean tokens (remove punctuation, etc.)
        tokens = [token for token in tokens if token.isalpha()]
        
        # Process context windows
        updates = 0
        
        for i in range(len(tokens)):
            # Get target word
            target_word = tokens[i]
            
            # Ensure target word exists
            self._ensure_word_exists(target_word)
            
            # Get context window
            context_start = max(0, i - 6)
            context_end = min(len(tokens), i + 7)
            
            context_words = []
            positions = []
            
            for j in range(context_start, context_end):
                if j != i:  # Skip the target word
                    context_word = tokens[j]
                    
                    # Ensure context word exists
                    self._ensure_word_exists(context_word)
                    
                    # Calculate position relative to target
                    position = j - i
                    
                    context_words.append(context_word)
                    positions.append(position)
            
            # Get target word neuron
            target_neuron = self._get_word_neuron(target_word)
            
            if target_neuron:
                # Update context relationship
                target_neuron.update_context(context_words, positions)
                
                # Store updated neuron
                self.storage_manager.store_neuron(target_neuron)
                
                updates += 1
        
        # Update statistics
        self.stats['total_updates'] += updates
        self.stats['texts_processed'] += 1
        
        return updates
    
    def process_file(self, file_path: str) -> int:
        """
        Process a text file to update context window relationships.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Number of context window updates performed
        """
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Process text
        updates = self.process_text(text)
        
        print(f"Processed {file_path}, performed {updates} context window updates")
        
        return updates
    
    def process_directory(self, directory: str, pattern: str = "*.txt") -> int:
        """
        Process all text files in a directory.
        
        Args:
            directory: Directory containing text files
            pattern: Glob pattern for matching files
            
        Returns:
            Total number of context window updates performed
        """
        import glob
        
        # Find matching files
        file_paths = glob.glob(os.path.join(directory, pattern))
        
        total_updates = 0
        
        for file_path in file_paths:
            try:
                updates = self.process_file(file_path)
                total_updates += updates
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        print(f"Processed {len(file_paths)} files, performed {total_updates} context window updates")
        
        return total_updates
    
    def get_word_context(self, word: str) -> Optional[Dict[int, List[Tuple[str, int]]]]:
        """
        Get the context window relationship for a word.
        
        Args:
            word: Word to get context for
            
        Returns:
            Dictionary mapping positions to lists of (word, count) tuples,
            or None if word not found
        """
        # Get word neuron
        neuron = self._get_word_neuron(word)
        
        if not neuron:
            return None
        
        # Get all top context words
        return neuron.get_all_top_context_words()
    
    def visualize_word_context(self, word: str, n: int = 10) -> str:
        """
        Visualize the context window relationship for a word.
        
        Args:
            word: Word to visualize context for
            n: Number of top words to include
            
        Returns:
            Path to the saved visualization, or None if word not found
        """
        # Get word context
        context = self.get_word_context(word)
        
        if not context:
            print(f"Word '{word}' not found in lexicon")
            return None
        
        # Create visualization
        plt.figure(figsize=(15, 8))
        
        # Set up positions and colors
        positions = sorted(context.keys())
        colors = plt.cm.viridis(np.linspace(0, 1, len(positions)))
        
        # Create subplots for each position
        for i, pos in enumerate(positions):
            # Get top words for this position
            top_words = context[pos][:n]
            
            if not top_words:
                continue
            
            # Extract words and counts
            words, counts = zip(*top_words) if top_words else ([], [])
            
            # Create subplot
            plt.subplot(2, 6, i + 1)
            plt.barh(range(len(words)), counts, color=colors[i])
            plt.yticks(range(len(words)), words)
            plt.title(f"Position {pos}")
            plt.tight_layout()
        
        # Add overall title
        plt.suptitle(f"Context Window for '{word}'", fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # Save visualization
        viz_path = os.path.join(
            self.storage_dir,
            'visualizations',
            f"context_{word}.png"
        )
        plt.savefig(viz_path)
        plt.close()
        
        print(f"Saved context visualization to {viz_path}")
        
        return viz_path
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a report on the lexicon.
        
        Returns:
            Dictionary with lexicon statistics
        """
        # Calculate elapsed time
        elapsed_time = time.time() - self.stats['start_time']
        
        # Get all word neurons
        all_uuids = self.storage_manager.list_neurons()
        
        # Count words with context relationships
        words_with_context = 0
        total_context_occurrences = 0
        
        for uuid_str in all_uuids:
            neuron = self.storage_manager.get_neuron(uuid_str)
            
            if isinstance(neuron, WordNeuron) and hasattr(neuron, 'context_relationship'):
                if neuron.context_relationship.total_occurrences > 0:
                    words_with_context += 1
                    total_context_occurrences += neuron.context_relationship.total_occurrences
        
        # Prepare report
        report = {
            'total_words': self.stats['total_words'],
            'words_with_context': words_with_context,
            'total_context_occurrences': total_context_occurrences,
            'texts_processed': self.stats['texts_processed'],
            'total_updates': self.stats['total_updates'],
            'elapsed_time': elapsed_time,
            'updates_per_second': self.stats['total_updates'] / elapsed_time if elapsed_time > 0 else 0
        }
        
        # Save report
        report_path = os.path.join(self.storage_dir, 'lexicon_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Generated lexicon report: {report_path}")
        
        return report
    
    def export_lexicon(self, output_path: str) -> None:
        """
        Export the lexicon to a JSON file.
        
        Args:
            output_path: Path to save the exported lexicon
        """
        # Get all word neurons
        all_uuids = self.storage_manager.list_neurons()
        
        # Prepare export data
        export_data = {}
        
        for uuid_str in all_uuids:
            neuron = self.storage_manager.get_neuron(uuid_str)
            
            if isinstance(neuron, WordNeuron) and hasattr(neuron, 'context_relationship'):
                word = neuron.word
                
                # Get context relationship
                context = neuron.get_all_top_context_words()
                
                # Add to export data
                export_data[word] = {
                    'uuid': uuid_str,
                    'context': {
                        str(pos): top_words
                        for pos, top_words in context.items()
                    },
                    'total_occurrences': neuron.context_relationship.total_occurrences,
                    'last_updated': neuron.context_relationship.last_updated
                }
        
        # Save export data
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Exported lexicon to {output_path}")


def example_dynamic_lexicon():
    """Example usage of the dynamic lexicon builder."""
    # Initialize the lexicon builder
    lexicon_builder = DynamicLexiconBuilder("/home/ubuntu/nexus_project/lexicon_storage")
    
    # Create sample text directory
    text_dir = os.path.join("/home/ubuntu/nexus_project", "sample_texts")
    os.makedirs(text_dir, exist_ok=True)
    
    # Create sample texts
    sample_texts = [
        """
        Artificial intelligence is transforming how we interact with technology.
        Machine learning algorithms can now recognize patterns in data that humans might miss.
        Neural networks are inspired by the structure of the human brain.
        Deep learning has revolutionized fields like computer vision and natural language processing.
        Reinforcement learning enables AI systems to learn through trial and error.
        """,
        
        """
        The NEXUS operating system represents a new paradigm in computing.
        Unlike traditional operating systems, NEXUS is designed specifically for AI.
        Memory in NEXUS functions as insight rather than simple storage.
        The multi-agent synergy core allows specialized AI models to work together.
        Emotional simulation enables NEXUS to adjust its tone appropriately.
        """,
        
        """
        Binary neurons form the foundation of the NEXUS memory system.
        Each neuron contains a 256-bit UUID and a 512-dimensional embedding vector.
        Neurons are linked together to form an associative memory web.
        The system can apply different emotional tones to neurons.
        Drift compensation ensures semantic integrity over time.
        """
    ]
    
    # Write sample texts to files
    for i, text in enumerate(sample_texts):
        file_path = os.path.join(text_dir, f"sample_{i+1}.txt")
        with open(file_path, "w") as f:
            f.write(text)
    
    print("\n=== Starting Dynamic Lexicon Builder Example ===\n")
    
    # Process the sample texts
    lexicon_builder.process_directory(text_dir)
    
    # Visualize context for some interesting words
    for word in ["ai", "nexus", "memory", "neurons", "system"]:
        lexicon_builder.visualize_word_context(word)
    
    # Generate report
    report = lexicon_builder.generate_report()
    
    print("\n=== Lexicon Report ===\n")
    for key, value in report.items():
        print(f"{key}: {value}")
    
    # Export lexicon
    export_path = os.path.join("/home/ubuntu/nexus_project", "lexicon_export.json")
    lexicon_builder.export_lexicon(export_path)
    
    print("\n=== Dynamic Lexicon Builder Example Completed ===\n")
    
    return lexicon_builder


if __name__ == "__main__":
    example_dynamic_lexicon()
