"""
Enhanced Training Pipeline for Binary Neuron System

This module provides an improved training pipeline for the Binary Neuron system,
including better embedding generation, semantic chunking, and tone model training.
"""

import os
import json
import glob
import numpy as np
import time
import hashlib
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import defaultdict

# Import the Binary Neuron prototype components
from binary_neuron_prototype import (
    BinaryNeuron, 
    BinaryNeuronSerializer, 
    BinaryNeuronStorageManager,
    KnowledgeConverter,
    MemoryWeb
)

try:
    # Try to import sentence-transformers for better embeddings
    from sentence_transformers import SentenceTransformer
    HAVE_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAVE_SENTENCE_TRANSFORMERS = False
    print("sentence-transformers not found. Using simplified embeddings.")
    print("To install: pip install sentence-transformers")

try:
    # Try to import nltk for better text processing
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    HAVE_NLTK = True
    
    # Download necessary NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Downloading NLTK punkt tokenizer...")
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("Downloading NLTK stopwords...")
        nltk.download('stopwords', quiet=True)
        
except ImportError:
    HAVE_NLTK = False
    print("NLTK not found. Using simplified text processing.")
    print("To install: pip install nltk")


class EnhancedKnowledgeConverter(KnowledgeConverter):
    """
    Enhanced knowledge converter with better embedding generation and semantic chunking.
    """
    
    def __init__(self, vector_size: int = 512, use_sentence_transformer: bool = True):
        """
        Initialize the enhanced knowledge converter.
        
        Args:
            vector_size: Size of the embedding vectors
            use_sentence_transformer: Whether to use sentence-transformers for embeddings
        """
        super().__init__(vector_size)
        
        self.use_sentence_transformer = use_sentence_transformer and HAVE_SENTENCE_TRANSFORMERS
        
        # Initialize sentence transformer if available
        if self.use_sentence_transformer:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                # Update vector size to match model
                self.vector_size = self.model.get_sentence_embedding_dimension()
                print(f"Using sentence-transformers with dimension: {self.vector_size}")
            except Exception as e:
                print(f"Error initializing sentence-transformer: {e}")
                self.use_sentence_transformer = False
        
        # Initialize tone models
        self.tone_models = {}
        
    def text_to_embedding(self, text: str) -> np.ndarray:
        """
        Convert text to an embedding vector using better models when available.
        
        Args:
            text: Text to convert
            
        Returns:
            Embedding vector
        """
        if self.use_sentence_transformer:
            # Use sentence-transformer for better embeddings
            try:
                embedding = self.model.encode(text)
                # Ensure correct shape
                if len(embedding) != self.vector_size:
                    print(f"Warning: Embedding dimension mismatch. Expected {self.vector_size}, got {len(embedding)}")
                    # Resize if necessary
                    if len(embedding) > self.vector_size:
                        embedding = embedding[:self.vector_size]
                    else:
                        # Pad with zeros
                        embedding = np.pad(embedding, (0, self.vector_size - len(embedding)))
                
                # Convert to float32 and normalize
                embedding = embedding.astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)
                return embedding
            except Exception as e:
                print(f"Error generating embedding with sentence-transformer: {e}")
                print("Falling back to simplified embedding method")
        
        # Fall back to the simplified method from the prototype
        return super().text_to_embedding(text)
    
    def _chunk_document(self, document: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Split a document into semantically meaningful chunks.
        
        Args:
            document: Document text
            chunk_size: Target size of chunks in characters
            overlap: Target overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        if HAVE_NLTK:
            # Use NLTK for better sentence-based chunking
            try:
                # Split into sentences
                sentences = sent_tokenize(document)
                
                chunks = []
                current_chunk = []
                current_size = 0
                
                for sentence in sentences:
                    sentence_size = len(sentence)
                    
                    # If adding this sentence would exceed chunk size and we already have content,
                    # finish the current chunk
                    if current_size + sentence_size > chunk_size and current_chunk:
                        chunks.append(' '.join(current_chunk))
                        
                        # Keep some sentences for overlap
                        overlap_size = 0
                        overlap_sentences = []
                        
                        # Work backwards through current_chunk to create overlap
                        for s in reversed(current_chunk):
                            if overlap_size + len(s) <= overlap:
                                overlap_sentences.insert(0, s)
                                overlap_size += len(s)
                            else:
                                break
                        
                        # Start new chunk with overlap sentences
                        current_chunk = overlap_sentences
                        current_size = overlap_size
                    
                    # Add the current sentence
                    current_chunk.append(sentence)
                    current_size += sentence_size
                
                # Add the last chunk if it has content
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                
                return chunks
            except Exception as e:
                print(f"Error in semantic chunking: {e}")
                print("Falling back to simplified chunking method")
        
        # Fall back to the simplified method from the prototype
        return super()._chunk_document(document, chunk_size, overlap)
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if HAVE_NLTK:
            try:
                # Tokenize
                tokens = word_tokenize(text)
                
                # Remove stopwords (optional, may want to keep for some applications)
                # stop_words = set(stopwords.words('english'))
                # tokens = [token for token in tokens if token.lower() not in stop_words]
                
                # Rejoin
                cleaned_text = ' '.join(tokens)
                return cleaned_text
            except Exception as e:
                print(f"Error in text cleaning: {e}")
                print("Returning original text")
        
        # Return original if NLTK not available or error occurs
        return text
    
    def document_to_neurons(self, 
                           document: str, 
                           chunk_size: int = 1000, 
                           overlap: int = 200,
                           metadata: Optional[Dict[str, Any]] = None,
                           clean: bool = True) -> List[BinaryNeuron]:
        """
        Convert a document to a list of Binary Neurons with improved processing.
        
        Args:
            document: Document text
            chunk_size: Size of text chunks in characters
            overlap: Overlap between chunks in characters
            metadata: Optional metadata to include in all neurons
            clean: Whether to clean the text before processing
            
        Returns:
            List of BinaryNeurons
        """
        # Clean text if requested
        if clean:
            document = self.clean_text(document)
        
        # Use the enhanced chunking method
        chunks = self._chunk_document(document, chunk_size, overlap)
        
        # Create neurons for each chunk
        neurons = []
        
        base_metadata = metadata or {}
        
        for i, chunk in enumerate(chunks):
            # Create embedding for the chunk
            embedding = self.text_to_embedding(chunk)
            
            # Create metadata for this chunk
            chunk_metadata = base_metadata.copy()
            chunk_metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks),
                'text': chunk,
                'created_at': time.time()
            })
            
            # Create neuron
            neuron = BinaryNeuron(
                vector=embedding,
                metadata=chunk_metadata
            )
            
            # Link to previous chunk if not the first
            if i > 0 and neurons:
                neuron.link_to(neurons[-1].uuid, weight=1.0)
                # Also link previous to this one
                neurons[-1].link_to(neuron.uuid, weight=1.0)
            
            neurons.append(neuron)
        
        return neurons
    
    def train_tone_model(self, tone_name: str, example_texts: List[str]) -> np.ndarray:
        """
        Train a tone model from example texts.
        
        Args:
            tone_name: Name of the tone
            example_texts: List of texts exemplifying the tone
            
        Returns:
            Tone vector
        """
        if not example_texts:
            # Fall back to random generation if no examples
            return self.create_tone_vector(tone_name)
        
        # Generate embeddings for all examples
        embeddings = []
        for text in example_texts:
            embedding = self.text_to_embedding(text)
            embeddings.append(embedding)
        
        # Average the embeddings
        tone_vector = np.mean(embeddings, axis=0)
        
        # Normalize
        tone_vector = tone_vector / np.linalg.norm(tone_vector)
        
        # Store the tone model
        self.tone_models[tone_name] = tone_vector
        
        return tone_vector
    
    def create_tone_vector(self, tone_name: str, seed: Optional[int] = None) -> np.ndarray:
        """
        Create or retrieve a tone vector.
        
        Args:
            tone_name: Name of the tone
            seed: Optional seed for reproducibility
            
        Returns:
            Tone vector
        """
        # Check if we have a trained model
        if tone_name in self.tone_models:
            return self.tone_models[tone_name]
        
        # Fall back to the simplified method from the prototype
        return super().create_tone_vector(tone_name, seed)


class TrainingPipeline:
    """
    Enhanced training pipeline for the Binary Neuron system.
    """
    
    def __init__(self, storage_dir: str, use_sentence_transformer: bool = True):
        """
        Initialize the training pipeline.
        
        Args:
            storage_dir: Directory to store neurons and training data
            use_sentence_transformer: Whether to use sentence-transformers for embeddings
        """
        self.storage_dir = storage_dir
        
        # Create directories
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'training_data'), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'tone_models'), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'visualizations'), exist_ok=True)
        
        # Initialize components
        self.storage_manager = BinaryNeuronStorageManager(storage_dir)
        self.converter = EnhancedKnowledgeConverter(use_sentence_transformer=use_sentence_transformer)
        self.memory_web = MemoryWeb(self.storage_manager)
        
        # Training statistics
        self.stats = {
            'documents_processed': 0,
            'neurons_created': 0,
            'tones_trained': 0,
            'start_time': time.time()
        }
    
    def load_document(self, 
                     file_path: str, 
                     document_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     chunk_size: int = 1000,
                     overlap: int = 200) -> str:
        """
        Load a document from file into the Memory Web.
        
        Args:
            file_path: Path to the document file
            document_id: Optional document ID (defaults to filename)
            metadata: Optional metadata
            chunk_size: Size of text chunks in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            Document ID
        """
        # Generate document ID from filename if not provided
        if document_id is None:
            document_id = os.path.basename(file_path)
            # Remove extension
            document_id = os.path.splitext(document_id)[0]
        
        # Prepare metadata
        meta = metadata or {}
        meta['source_file'] = file_path
        meta['document_id'] = document_id
        
        # Determine file type and load accordingly
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.txt', '.md', '.rst']:
            # Text file
            with open(file_path, 'r', encoding='utf-8') as f:
                document_text = f.read()
            
            # Add document to Memory Web
            neuron_uuids = self.memory_web.add_document(
                document_text, 
                document_id,
                metadata=meta
            )
        
        elif file_ext in ['.json']:
            # JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Add JSON to Memory Web
            neuron_uuids = self.memory_web.add_json_data(
                json_data,
                document_id,
                metadata=meta
            )
        
        else:
            # Unsupported file type
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Update statistics
        self.stats['documents_processed'] += 1
        self.stats['neurons_created'] += len(neuron_uuids)
        
        print(f"Loaded document '{document_id}' from {file_path}, created {len(neuron_uuids)} neurons")
        
        return document_id
    
    def batch_load_documents(self, 
                            directory: str, 
                            pattern: str = "*.*",
                            metadata_fn: Optional[callable] = None) -> List[str]:
        """
        Load multiple documents from a directory.
        
        Args:
            directory: Directory containing documents
            pattern: Glob pattern for matching files
            metadata_fn: Optional function to gene
(Content truncated due to size limit. Use line ranges to read in chunks)