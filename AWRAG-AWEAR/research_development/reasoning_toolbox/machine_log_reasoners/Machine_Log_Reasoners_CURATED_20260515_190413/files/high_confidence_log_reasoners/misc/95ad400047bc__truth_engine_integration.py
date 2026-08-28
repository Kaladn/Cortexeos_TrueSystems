"""
Truth Engine Integration for Kali Ka

This module integrates a Truth Verification Engine with the Kali Ka system,
enhancing the Binary Neuron and Dynamic Lexicon components with truth verification capabilities.
"""

import os
import json
import numpy as np
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from collections import defaultdict, Counter

# Try to import NLTK components
try:
    import nltk
    from nltk.corpus import words as nltk_words
    from nltk.tokenize import word_tokenize
    from nltk.stem.snowball import SnowballStemmer
    
    # Download necessary NLTK data
    try:
        nltk.data.find('corpora/words')
    except LookupError:
        print("Downloading NLTK words corpus...")
        nltk.download('words', quiet=True)
    
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Downloading NLTK punkt tokenizer...")
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        print("Downloading NLTK POS tagger...")
        nltk.download('averaged_perceptron_tagger', quiet=True)
    
    HAVE_NLTK = True
    
    # Load NLTK's verified word list
    verified_word_list = set(nltk_words.words())
    
    # Initialize stemmer for morpheme extraction
    stemmer = SnowballStemmer("english")
    
except ImportError:
    HAVE_NLTK = False
    print("NLTK not found. Using simplified word verification.")
    print("To install: pip install nltk")
    
    # Create empty placeholders if NLTK is not available
    verified_word_list = set()
    stemmer = None

# Import the Binary Neuron and Dynamic Lexicon components
try:
    from binary_neuron_prototype import (
        BinaryNeuron, 
        BinaryNeuronSerializer, 
        BinaryNeuronStorageManager,
        KnowledgeConverter,
        MemoryWeb
    )
    
    from dynamic_lexicon_builder import (
        WordNeuron,
        WordNeuronSerializer,
        DynamicLexiconBuilder,
        ContextWindowRelationship
    )
    
    HAVE_KALI_KA_COMPONENTS = True
except ImportError:
    HAVE_KALI_KA_COMPONENTS = False
    print("Kali Ka components not found. Running in standalone mode.")


class TruthVerifier:
    """
    Verifies the truth of words, statements, and relationships.
    """
    
    def __init__(self, 
                 verified_truth_dir: str = None, 
                 unconfirmed_data_dir: str = None,
                 custom_dictionary: Optional[Set[str]] = None):
        """
        Initialize the Truth Verifier.
        
        Args:
            verified_truth_dir: Directory to store verified truth data
            unconfirmed_data_dir: Directory to store unconfirmed data
            custom_dictionary: Optional custom dictionary of verified words
        """
        # Set up directories
        base_dir = os.getcwd()
        self.verified_truth_dir = verified_truth_dir or os.path.join(base_dir, "Verified_Truth")
        self.unconfirmed_data_dir = unconfirmed_data_dir or os.path.join(base_dir, "Unconfirmed_Data")
        
        # Ensure directories exist
        os.makedirs(self.verified_truth_dir, exist_ok=True)
        os.makedirs(self.unconfirmed_data_dir, exist_ok=True)
        
        # Set up verification sources
        self.verified_word_list = verified_word_list
        
        # Add custom dictionary if provided
        if custom_dictionary:
            self.verified_word_list.update(custom_dictionary)
        
        # Statistics
        self.stats = {
            'total_words_checked': 0,
            'verified_words': 0,
            'unverified_words': 0,
            'total_statements_checked': 0,
            'verified_statements': 0,
            'unverified_statements': 0,
            'total_relationships_checked': 0,
            'verified_relationships': 0,
            'unverified_relationships': 0
        }
    
    def verify_word(self, word: str) -> bool:
        """
        Verify if a word exists in the verified word list.
        
        Args:
            word: Word to verify
            
        Returns:
            True if verified, False otherwise
        """
        # Update statistics
        self.stats['total_words_checked'] += 1
        
        # Check if word is in verified list
        is_verified = word.lower() in self.verified_word_list
        
        # Update verification statistics
        if is_verified:
            self.stats['verified_words'] += 1
        else:
            self.stats['unverified_words'] += 1
        
        return is_verified
    
    def verify_statement(self, statement: str) -> Tuple[bool, float, Dict[str, bool]]:
        """
        Verify a statement by checking the validity of its component words.
        
        Args:
            statement: Statement to verify
            
        Returns:
            Tuple of (overall_verification, confidence_score, word_verification_dict)
        """
        # Update statistics
        self.stats['total_statements_checked'] += 1
        
        # Tokenize statement
        if HAVE_NLTK:
            words = word_tokenize(statement.lower())
        else:
            # Simple tokenization
            words = statement.lower().split()
        
        # Remove punctuation and non-alphabetic tokens
        words = [word for word in words if word.isalpha()]
        
        # Verify each word
        word_verification = {}
        verified_count = 0
        
        for word in words:
            is_verified = self.verify_word(word)
            word_verification[word] = is_verified
            
            if is_verified:
                verified_count += 1
        
        # Calculate confidence score
        if words:
            confidence_score = verified_count / len(words)
        else:
            confidence_score = 0.0
        
        # Determine overall verification
        # A statement is considered verified if at least 80% of its words are verified
        overall_verification = confidence_score >= 0.8
        
        # Update verification statistics
        if overall_verification:
            self.stats['verified_statements'] += 1
        else:
            self.stats['unverified_statements'] += 1
        
        return overall_verification, confidence_score, word_verification
    
    def verify_relationship(self, 
                           target_word: str, 
                           related_words: Dict[int, List[Tuple[str, int]]]) -> Dict[int, List[Tuple[str, int, bool]]]:
        """
        Verify relationships between words in a context window.
        
        Args:
            target_word: Target word
            related_words: Dictionary mapping positions to lists of (word, count) tuples
            
        Returns:
            Dictionary mapping positions to lists of (word, count, is_verified) tuples
        """
        # Update statistics
        self.stats['total_relationships_checked'] += 1
        
        # Verify target word
        target_verified = self.verify_word(target_word)
        
        # Verify related words
        verified_relationships = {}
        verified_count = 0
        total_relationships = 0
        
        for position, words in related_words.items():
            verified_relationships[position] = []
            
            for word, count in words:
                is_verified = self.verify_word(word)
                verified_relationships[position].append((word, count, is_verified))
                
                if is_verified:
                    verified_count += 1
                
                total_relationships += 1
        
        # Calculate verification ratio
        if total_relationships > 0:
            verification_ratio = verified_count / total_relationships
        else:
            verification_ratio = 0.0
        
        # Update verification statistics
        if verification_ratio >= 0.8:
            self.stats['verified_relationships'] += 1
        else:
            self.stats['unverified_relationships'] += 1
        
        return verified_relationships
    
    def process_lexicon_file(self, input_file: str) -> Tuple[str, str]:
        """
        Process a lexicon file, separating verified and unverified words.
        
        Args:
            input_file: Path to input lexicon file (JSON)
            
        Returns:
            Tuple of (verified_output_file, unverified_output_file)
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                lexicon = json.load(f)
        except Exception as e:
            print(f"Error: Could not open file {input_file}: {str(e)}")
            return None, None
        
        if not lexicon:
            print(f"Warning: Empty lexicon in {input_file}")
            return None, None
        
        verified_data = {}
        unverified_data = {}
        
        for word, entry in lexicon.items():
            if self.verify_word(word):
                verified_data[word] = entry
            else:
                unverified_data[word] = entry
        
        # Generate output filenames
        filename = os.path.basename(input_file)
        verified_output_file = os.path.join(self.verified_truth_dir, filename)
        unverified_output_file = os.path.join(self.unconfirmed_data_dir, filename)
        
        # Save verified words
        with open(verified_output_file, 'w', encoding='utf-8') as f:
            json.dump(verified_data, f, indent=4)
        print(f"Verified data saved to {verified_output_file}")
        
        # Save unverified words
        with open(unverified_output_file, 'w', encoding='utf-8') as f:
            json.dump(unverified_data, f, indent=4)
        print(f"Unverified data saved to {unverified_output_file}")
        
        return verified_output_file, unverified_output_file
    
    def process_lexicon_directory(self, lexicon_dir: str) -> Dict[str, Any]:
        """
        Process all lexicon files in a directory.
        
        Args:
            lexicon_dir: Directory containing lexicon files (JSON)
            
        Returns:
            Dictionary with processing statistics
        """
        source_files = [f for f in os.listdir(lexicon_dir) if f.endswith(".json")]
        processed_files = 0
        
        for filename in source_files:
            input_file = os.path.join(lexicon_dir, filename)
            verified_file, unverified_file = self.process_lexicon_file(input_file)
            
            if verified_file and unverified_file:
                processed_files += 1
        
        # Generate report
        report = {
            'total_files_processed': processed_files,
            'verified_words': self.stats['verified_words'],
            'unverified_words': self.stats['unverified_words'],
            'verification_rate': self.stats['verified_words'] / self.stats['total_words_checked'] if self.stats['total_words_checked'] > 0 else 0
        }
        
        # Print report
        print("\n--- Truth Engine Report ---")
        print(f"Total files processed: {report['total_files_processed']}")
        print(f"Verified words: {report['verified_words']}")
        print(f"Unverified words: {report['unverified_words']}")
        print(f"Verification success rate: {report['verification_rate'] * 100:.2f}%")
        
        return report
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive report on verification activities.
        
        Returns:
            Dictionary with verification statistics
        """
        report = {
            'words': {
                'total_checked': self.stats['total_words_checked'],
                'verified': self.stats['verified_words'],
                'unverified': self.stats['unverified_words'],
                'verification_rate': self.stats['verified_words'] / self.stats['total_words_checked'] if self.stats['total_words_checked'] > 0 else 0
            },
            'statements': {
                'total_checked': self.stats['total_statements_checked'],
                'verified': self.stats['verified_statements'],
                'unverified': self.stats['unverified_statements'],
                'verification_rate': self.stats['verified_statements'] / self.stats['total_statements_checked'] if self.stats['total_statements_checked'] > 0 else 0
            },
            'relationships': {
                'total_checked': self.stats['total_relationships_checked'],
                'verified': self.stats['verified_relationships'],
                'unverified': self.stats['unverified_relationships'],
                'verification_rate': self.stats['verified_relationships'] / self.stats['total_relationships_checked'] if self.stats['total_relationships_checked'] > 0 else 0
            }
        }
        
        # Print report
        print("\n=== Comprehensive Truth Verification Report ===\n")
        
        print("Word Verification:")
        print(f"  Total checked: {report['words']['total_checked']}")
        print(f"  Verified: {report['words']['verified']}")
        print(f"  Unverified: {report['words']['unverified']}")
        print(f"  Verification rate: {report['words']['verification_rate'] * 100:.2f}%")
        
        print("\nStatement Verification:")
        print(f"  Total checked: {report['statements']['total_checked']}")
        print(f"  Verified: {report['statements']['verified']}")
        print(f"  Unverified: {report['statements']['unverified']}")
        print(f"  Verification rate: {report['statements']['verification_rate'] * 100:.2f}%")
        
        print("\nRelationship Verification:")
        print(f"  Total checked: {report['relationships']['total_checked']}")
        print(f"  Verified: {report['relationships']['verified']}")
        print(f"  Unverified: {report['relationships']['unverified']}")
        print(f"  Verification rate: {report['relationships']['verification_rate'] * 100:.2f}%")
        
        return report


class VerifiedWordNeuron(WordNeuron):
    """
    Extends WordNeuron with truth verification capabilities.
    """
    
    def __init__(self, 
                 word: str,
                 uuid_str: Optional[str] = None,
                 vector: Optional[np.ndarray] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 binary_ref: Optional[int] = None,
                 truth_verifier: Optional[TruthVerifier] = None):
        """
        Initialize a Verified Word Neuron.
        
        Args:
            word: The word this neuron represents
            uuid_str: Optional UUID string
            vector: Optional embedding vector
            metadata: Optional metadata
            binary_ref: Optional binary reference
            truth_verifier: Optional TruthVerifier instance
        """
        # Initialize base WordNeuron
        super().__init__(word, uuid_str, vector, metadata, binary_ref)
        
        # Set up truth verification
        self.truth_verifier = truth_verifier or TruthVerifier()
        
        # Verify the word
        self.is_verified = self.truth_verifier.verify_word(word)
        
        # Add verification status to metadata
        self.metadata['is_verified'] = self.is_verified
        
        # Track verified relationships
        self.verified_relationships = {}
    
    def update_context(self, context_words: List[str], positions: List[int]) -> None:
        """
        Update the context relationship with new occurrences and verify relationships.
        
        Args:
            context_words: List of words in the context
            positions: List of positions corresponding to each word
        """
        # Update base context relationship
        super().update_context(context_words, positions)
        
        # Verify relationships
        self._verify_relationships()
    
    def _verify_relationships(self) -> None:
        """Verify all relationships in the context window."""
        # Get all top context words
        all_context_words = self.get_all_top_context_words()
        
        # Verify relationships
        self.verified_relationships = self.truth_verifier.verify_relationship(
            self.word, all_context_words
        )
    
    def get_verified_context_words(self, position: int, n: int = 10) -> List[Tuple[str, int, bool]]:
        """
        Get the top N verified words for a specific position.
        
        Args:
            position: Position in the context window
            n: Number of top words to return
            
        Returns:
            List of (word, count, is_verified) tuples for the top N words
        """
        if position not in self.verified_relationships:
            self._verify_relationships()
            
        return self.verified_relationships.get(position, [])[:n]
    
    def get_all_verified_context_words(self, n: int = 10) -> Dict[int, List[Tuple[str, int, bool]]]:
        """
        Get the top N verified words for all positions.
        
        Args:
            n: Number of top words to return for each position
            
        Returns:
            Dictionary mapping positions to lists of (word, count, is_verified) tuples
        """
        if not self.verified_relationships:
            self._verify_relationships()
            
        return {
            pos: words[:n]
            for pos, words in self.verified_relationships.items()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        # Get base representation
        data = super().to_dict()
        
        # Add verification data
        data['is_verified'] = self.is_verified
        data['verified_relationships'] = {
            str(pos): rel_list
            for pos, rel_list in self.verified_relationships.items()
        }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], truth_verifier: Optional[TruthVerifier] = None) -> 'VerifiedWordNeuron':
        """
        Create from dictionary representation.
        
        Args:
            data: Dictionary representation
            truth_verifier: Optional TruthVerifier instance
            
        Returns:
            VerifiedWordNeuron instance
        """
        # Extract word from metadata
        word = data['metadata'].get('word')
        if not word:
            raise ValueError("Word not found in metadata")
        
        # Create verifier if not provided
        if truth_verifier is None:
            truth_verifier = TruthVerifier()
        
        # Create neuron
        neuron = cls(
            word=word,
            uuid_str=data['uuid'],
            vector=np.array(data['vector'], dtype=np.float32),
            metadata=data['metadata'],
            binary_ref=data['binary_ref'],
            truth_verifier=truth_verifier
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
        
        # Restore verification data if present
        if 'is_verified' in data:
            neuron.is_verified = data['is_verified']
        
        if 'verified_relationships' in data:
            neuron.verified_relationships = {
                int(pos): rel_list
                for pos, rel_list in data['verified_relationships'].items()
            }
        
        return neuron


class VerifiedLexiconBuilder(DynamicLexiconBuilder):
    """
    Extends DynamicLexiconBuilder with truth verification capabilities.
    """
    
    def __init__(self, 
                 storage_dir: str, 
                 use_nltk_base: bool = True,
                 verified_truth_dir: Optional[str] = None,
                 unconfirmed_data_dir: Optional[str] = None):
        """
        Initialize the verified lexicon builder.
        
        Args:
            storage_dir: Directory to store word neurons
            use_nltk_base: Whether to initialize with NLTK words
            verified_truth_dir: Directory to store verified truth data
            unconfirmed_data_dir: Directory to store unconfirmed data
        """
        # Initialize base lexicon builder
        super().__init__(storage_dir, use_nltk_base)
        
        # Set up truth verification
        self.truth_verifier = TruthVerifier(
            verified_truth_dir=verified_truth_dir,
            unconfirmed_data_dir=unconfirmed_data_dir
        )
        
        # Create additional directories
        os.makedirs(os.path.join(storage_dir, 'verified_lexicon'), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'unverified_lexicon'), exist_ok=True)
        
        # Track verification statistics
        self.verification_stats = {
            'total_words': 0,
            'verified_words': 0,
            'unverified_words': 0,
            'verified_relationships': 0,
            'unverified_relationships': 0
        }
    
    def _create_word_neuron(self, word: str) -> str:
        """
        Create a new Verified Word Neuron for a word.
        
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
        
        # Create verified neuron
        neuron = VerifiedWordNeuron(
            word=word,
            vector=embedding,
            metadata=metadata,
            truth_verifier=self.truth_verifier
        )
        
        # Store neuron
        uuid_str = self.storage_manager.store_neuron(neuron)
        
        # Update word index
        self.word_uuids[word] = uuid_str
        self._save_word_index()
        
        # Update statistics
        self.stats['total_words'] += 1
        self.verification_stats['total_words'] += 1
        
        if neuron.is_verified:
            self.verification_stats['verified_words'] += 1
        else:
            self.verification_stats['unverified_words'] += 1
        
        return uuid_str
    
    def process_text(self, text: str, verify: bool = True) -> int:
        """
        Process text to update context window relationships with verification.
        
        Args:
            text: Text to process
            verify: Whether to verify relationships
            
        Returns:
            Number of context window updates performed
        """
        # Process text using base method
        updates = super().process_text(text)
        
        # Verify relationships if requested
        if verify:
            self._verify_all_relationships()
        
        return updates
    
    def _verify_all_relationships(self) -> None:
        """Verify all relationships in the lexicon."""
        # Get all word neurons
        all_uuids = self.storage_manager.list_neurons()
        
        for uuid_str in all_uuids:
            neuron = self.storage_manager.get_neuron(uuid_str)
            
            if isinstance(neuron, VerifiedWordNeuron):
                # Verify relationships
                neuron._verify_relationships()
                
                # Store updated neuron
                self.storage_manager.store_neuron(neuron)
                
                # Update statistics
                for pos, words in neuron.verified_relationships.items():
                    for word, count, is_verified in words:
                        if is_verified:
                            self.verification_stats['verified_relationships'] += 1
                        else:
                            self.verification_stats['unverified_relationships'] += 1
    
    def export_verified_lexicon(self, output_path: str) -> None:
        """
        Export only the verified words and relationships to a JSON file.
        
        Args:
            output_path: Path to save the exported lexicon
        """
        # Get all word neurons
        all_uuids = self.storage_manager.list_neurons()
        
        # Prepare export data
        export_data = {}
        
        for uuid_str in all_uuids:
            neuron = self.storage_manager.get_neuron(uuid_str)
            
            if isinstance(neuron, VerifiedWordNeuron) and neuron.is_verified:
                word = neuron.word
                
                # Get verified relationships
                verified_context = {}
                
                for pos, rel_list in neuron.get_all_verified_context_words().items():
                    # Filter to only include verified words
                    verified_words = [
                        (word, count) for word, count, is_verified in rel_list
                        if is_verified
                    ]
                    
                    if verified_words:
                        verified_context[str(pos)] = verified_words
                
                # Add to export data
                export_data[word] = {
                    'uuid': uuid_str,
                    'verified_context': verified_context,
                    'total_occurrences': neuron.context_relationship.total_occurrences,
                    'last_updated': neuron.context_relationship.last_updated
                }
        
        # Save export data
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=4)
        
        print(f"Exported verified lexicon to {output_path}")
    
    def generate_verification_report(self) -> Dict[str, Any]:
        """
        Generate a report on verification activities.
        
        Returns:
            Dictionary with verification statistics
        """
        # Get truth verifier report
        verifier_report = self.truth_verifier.generate_report()
        
        # Combine with lexicon statistics
        report = {
            'lexicon': {
                'total_words': self.verification_stats['total_words'],
                'verified_words': self.verification_stats['verified_words'],
                'unverified_words': self.verification_stats['unverified_words'],
                'verification_rate': self.verification_stats['verified_words'] / self.verification_stats['total_words'] if self.verification_stats['total_words'] > 0 else 0
            },
            'relationships': {
                'verified_relationships': self.verification_stats['verified_relationships'],
                'unverified_relationships': self.verification_stats['unverified_relationships'],
                'verification_rate': self.verification_stats['verified_relationships'] / (self.verification_stats['verified_relationships'] + self.verification_stats['unverified_relationships']) if (self.verification_stats['verified_relationships'] + self.verification_stats['unverified_relationships']) > 0 else 0
            },
            'verifier': verifier_report
        }
        
        # Print report
        print("\n=== Verified Lexicon Report ===\n")
        
        print("Lexicon Statistics:")
        print(f"  Total words: {report['lexicon']['total_words']}")
        print(f"  Verified words: {report['lexicon']['verified_words']}")
        print(f"  Unverified words: {report['lexicon']['unverified_words']}")
        print(f"  Word verification rate: {report['lexicon']['verification_rate'] * 100:.2f}%")
        
        print("\nRelationship Statistics:")
        print(f"  Verified relationships: {report['relationships']['verified_relationships']}")
        print(f"  Unverified relationships: {report['relationships']['unverified_relationships']}")
        print(f"  Relationship verification rate: {report['relationships']['verification_rate'] * 100:.2f}%")
        
        return report


class TruthEngineIntegration:
    """
    Integrates the Truth Engine with the Kali Ka system.
    """
    
    def __init__(self, 
                 storage_dir: str,
                 verified_truth_dir: Optional[str] = None,
                 unconfirmed_data_dir: Optional[str] = None):
        """
        Initialize the Truth Engine Integration.
        
        Args:
            storage_dir: Directory to store data
            verified_truth_dir: Directory to store verified truth data
            unconfirmed_data_dir: Directory to store unconfirmed data
        """
        self.storage_dir = storage_dir
        
        # Create directories
        os.makedirs(storage_dir, exist_ok=True)
        
        # Initialize components
        self.truth_verifier = TruthVerifier(
            verified_truth_dir=verified_truth_dir,
            unconfirmed_data_dir=unconfirmed_data_dir
        )
        
        self.verified_lexicon_builder = VerifiedLexiconBuilder(
            storage_dir=os.path.join(storage_dir, 'verified_lexicon'),
            use_nltk_base=True,
            verified_truth_dir=verified_truth_dir,
            unconfirmed_data_dir=unconfirmed_data_dir
        )
        
        # Initialize memory web if Kali Ka components are available
        if HAVE_KALI_KA_COMPONENTS:
            self.memory_web = MemoryWeb(
                storage_manager=BinaryNeuronStorageManager(
                    os.path.join(storage_dir, 'memory_web')
                )
            )
        else:
            self.memory_web = None
    
    def process_document(self, 
                        document_text: str, 
                        document_id: str,
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a document with truth verification.
        
        Args:
            document_text: Text of the document
            document_id: Document ID
            metadata: Optional metadata
            
        Returns:
            Dictionary with processing results
        """
        # Verify the document text
        is_verified, confidence_score, word_verification = self.truth_verifier.verify_statement(document_text)
        
        # Process with verified lexicon builder
        update_count = self.verified_lexicon_builder.process_text(document_text)
        
        # Add to memory web if available
        memory_web_uuids = []
        if self.memory_web:
            # Add metadata about verification
            if metadata is None:
                metadata = {}
            
            metadata['truth_verification'] = {
                'is_verified': is_verified,
                'confidence_score': confidence_score,
                'verification_timestamp': time.time()
            }
            
            # Add to memory web
            memory_web_uuids = self.memory_web.add_document(
                document_text,
                document_id,
                metadata=metadata
            )
        
        # Prepare results
        results = {
            'document_id': document_id,
            'verification': {
                'is_verified': is_verified,
                'confidence_score': confidence_score,
                'verified_words': sum(1 for v in word_verification.values() if v),
                'unverified_words': sum(1 for v in word_verification.values() if not v),
                'total_words': len(word_verification)
            },
            'lexicon_updates': update_count,
            'memory_web_neurons': len(memory_web_uuids) if memory_web_uuids else 0
        }
        
        return results
    
    def process_file(self, 
                    file_path: str, 
                    document_id: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a file with truth verification.
        
        Args:
            file_path: Path to the file
            document_id: Optional document ID (defaults to filename)
            metadata: Optional metadata
            
        Returns:
            Dictionary with processing results
        """
        # Generate document ID from filename if not provided
        if document_id is None:
            document_id = os.path.basename(file_path)
            # Remove extension
            document_id = os.path.splitext(document_id)[0]
        
        # Prepare metadata
        meta = metadata or {}
        meta['source_file'] = file_path
        
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            document_text = f.read()
        
        # Process document
        results = self.process_document(document_text, document_id, meta)
        
        print(f"Processed file {file_path} as document '{document_id}'")
        print(f"Verification confidence: {results['verification']['confidence_score'] * 100:.2f}%")
        print(f"Lexicon updates: {results['lexicon_updates']}")
        print(f"Memory web neurons: {results['memory_web_neurons']}")
        
        return results
    
    def process_directory(self, 
                         directory: str, 
                         pattern: str = "*.txt",
                         metadata_fn: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Process all files in a directory with truth verification.
        
        Args:
            directory: Directory containing files
            pattern: Glob pattern for matching files
            metadata_fn: Optional function to generate metadata from file path
            
        Returns:
            List of dictionaries with processing results
        """
        import glob
        
        # Find matching files
        file_paths = glob.glob(os.path.join(directory, pattern))
        
        results = []
        
        for file_path in file_paths:
            try:
                # Generate metadata if function provided
                metadata = None
                if metadata_fn:
                    metadata = metadata_fn(file_path)
                
                # Process file
                result = self.process_file(file_path, metadata=metadata)
                results.append(result)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        print(f"Processed {len(results)} files from {directory}")
        
        return results
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive report on all truth verification activities.
        
        Returns:
            Dictionary with comprehensive statistics
        """
        # Get verification report from lexicon builder
        lexicon_report = self.verified_lexicon_builder.generate_verification_report()
        
        # Get truth verifier report
        verifier_report = self.truth_verifier.generate_report()
        
        # Combine reports
        report = {
            'lexicon': lexicon_report['lexicon'],
            'relationships': lexicon_report['relationships'],
            'words': verifier_report['words'],
            'statements': verifier_report['statements'],
            'overall_verification_rate': (
                lexicon_report['lexicon']['verification_rate'] +
                lexicon_report['relationships']['verification_rate'] +
                verifier_report['words']['verification_rate'] +
                verifier_report['statements']['verification_rate']
            ) / 4
        }
        
        # Print overall summary
        print("\n=== Kali Ka Truth Engine Summary ===\n")
        print(f"Overall verification rate: {report['overall_verification_rate'] * 100:.2f}%")
        print(f"Total words processed: {report['words']['total_checked']}")
        print(f"Total statements verified: {report['statements']['total_checked']}")
        print(f"Lexicon size: {report['lexicon']['total_words']} words")
        print(f"Relationship count: {report['relationships']['verified_relationships'] + report['relationships']['unverified_relationships']}")
        
        return report


def example_truth_engine():
    """Example usage of the Truth Engine Integration."""
    # Initialize the Truth Engine Integration
    truth_engine = TruthEngineIntegration("/home/ubuntu/nexus_project/truth_engine_storage")
    
    # Create sample text directory
    text_dir = os.path.join("/home/ubuntu/nexus_project", "truth_sample_texts")
    os.makedirs(text_dir, exist_ok=True)
    
    # Create sample texts with varying levels of "truth"
    sample_texts = [
        # Highly verified text (all common English words)
        """
        Artificial intelligence is transforming how we interact with technology.
        Machine learning algorithms can now recognize patterns in data that humans might miss.
        Neural networks are inspired by the structure of the human brain.
        Deep learning has revolutionized fields like computer vision and natural language processing.
        Reinforcement learning enables AI systems to learn through trial and error.
        """,
        
        # Partially verified text (mix of common words and specialized terms)
        """
        The NEXUS operating system represents a new paradigm in computing.
        Unlike traditional operating systems, NEXUS is designed specifically for AI.
        Memory in NEXUS functions as insight rather than simple storage.
        The multi-agent synergy core allows specialized AI models to work together.
        Emotional simulation enables NEXUS to adjust its tone appropriately.
        """,
        
        # Text with made-up terms (lower verification rate)
        """
        Hyperquantum neurons form the foundation of the NEXUS memory system.
        Each neuron contains a zeptobyte UUID and a hyperdimensional embedding vector.
        Neurons are linked together to form an associative memoryscape web.
        The system can apply different emotispheric tones to neurons.
        Metacalibration ensures semantic integrity over time.
        """
    ]
    
    # Write sample texts to files
    for i, text in enumerate(sample_texts):
        file_path = os.path.join(text_dir, f"truth_sample_{i+1}.txt")
        with open(file_path, "w") as f:
            f.write(text)
    
    print("\n=== Starting Truth Engine Integration Example ===\n")
    
    # Process the sample texts
    results = truth_engine.process_directory(text_dir)
    
    # Print verification results for each document
    print("\n=== Document Verification Results ===\n")
    for i, result in enumerate(results):
        print(f"Document {i+1}:")
        print(f"  Verified: {'Yes' if result['verification']['is_verified'] else 'No'}")
        print(f"  Confidence: {result['verification']['confidence_score'] * 100:.2f}%")
        print(f"  Verified words: {result['verification']['verified_words']}")
        print(f"  Unverified words: {result['verification']['unverified_words']}")
        print()
    
    # Export verified lexicon
    export_path = os.path.join("/home/ubuntu/nexus_project", "verified_lexicon_export.json")
    truth_engine.verified_lexicon_builder.export_verified_lexicon(export_path)
    
    # Generate comprehensive report
    report = truth_engine.generate_comprehensive_report()
    
    print("\n=== Truth Engine Integration Example Completed ===\n")
    
    return truth_engine


if __name__ == "__main__":
    example_truth_engine()
