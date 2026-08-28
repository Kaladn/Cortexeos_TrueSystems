"""
Binary Neuron Prototype Implementation

This module implements a simplified version of the Binary Neuron system
for early knowledge injection testing. It includes:

1. BinaryNeuron class with core structure
2. Basic serializer with UUID tracking
3. Minimal storage manager
4. Knowledge conversion utilities
"""

import os
import uuid
import json
import pickle
import hashlib
import numpy as np
import time
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple, Union

class BinaryNeuron:
    """
    Simplified Binary Neuron implementation for prototype testing.
    
    Attributes:
        uuid (str): 256-bit UUID as a string
        vector (np.ndarray): 512-dimensional embedding vector
        metadata (dict): Dictionary containing metadata about the neuron
        binary_ref (int): Binary reference for indexing
        links (dict): Dictionary of connected neurons and weights
    """
    
    def __init__(self, 
                 uuid_str: Optional[str] = None, 
                 vector: Optional[np.ndarray] = None, 
                 metadata: Optional[Dict[str, Any]] = None, 
                 binary_ref: Optional[int] = None):
        """
        Initialize a Binary Neuron.
        
        Args:
            uuid_str: Optional UUID string. If None, a new UUID is generated.
            vector: Optional 512-dimensional embedding vector. If None, a zero vector is created.
            metadata: Optional metadata dictionary. If None, an empty dict is created.
            binary_ref: Optional binary reference. If None, a hash of the UUID is used.
        """
        # Generate UUID if not provided
        self.uuid = uuid_str if uuid_str else str(uuid.uuid4())
        
        # Create embedding vector if not provided
        if vector is not None:
            self.vector = np.array(vector, dtype=np.float32)
        else:
            self.vector = np.zeros(512, dtype=np.float32)
        
        # Set metadata if provided, otherwise empty dict
        self.metadata = metadata if metadata else {}
        
        # Set binary reference if provided, otherwise hash the UUID
        if binary_ref is not None:
            self.binary_ref = binary_ref
        else:
            # Create a deterministic binary reference from the UUID
            self.binary_ref = int(hashlib.md5(self.uuid.encode()).hexdigest(), 16) % (2**64)
        
        # Initialize empty links dictionary
        self.links = {}
        
        # Track original vector for drift calculations
        self._original_vector = self.vector.copy()
        
        # Track tone applications
        self._tone_history = []
    
    def link_to(self, other_neuron_uuid: str, weight: float = 1.0) -> None:
        """
        Link this neuron to another neuron with a specified weight.
        
        Args:
            other_neuron_uuid: UUID of the neuron to link to
            weight: Weight of the link (default: 1.0)
        """
        self.links[other_neuron_uuid] = weight
    
    def apply_tone(self, tone_vector: np.ndarray, strength: float = 0.1) -> None:
        """
        Apply a tone vector to this neuron's embedding.
        
        Args:
            tone_vector: Vector representing the tone to apply
            strength: Strength of the tone application (0.0 to 1.0)
        """
        # Ensure tone vector has the right shape
        if tone_vector.shape != self.vector.shape:
            raise ValueError(f"Tone vector shape {tone_vector.shape} does not match neuron vector shape {self.vector.shape}")
        
        # Apply tone with specified strength
        self.vector = self.vector * (1 - strength) + tone_vector * strength
        
        # Record tone application for drift tracking
        self._tone_history.append({
            'tone_vector': tone_vector.copy(),
            'strength': strength,
            'timestamp': time.time()
        })
    
    def reset_to_original(self) -> None:
        """Reset the vector to its original state, removing all tone modifications."""
        self.vector = self._original_vector.copy()
        self._tone_history = []
    
    def get_drift_vector(self) -> np.ndarray:
        """
        Calculate the current drift vector from the original.
        
        Returns:
            Drift vector (current - original)
        """
        return self.vector - self._original_vector
    
    def get_drift_magnitude(self) -> float:
        """
        Calculate the magnitude of drift from the original vector.
        
        Returns:
            Euclidean distance between current and original vectors
        """
        return np.linalg.norm(self.get_drift_vector())
    
    def compensate_drift(self, factor: float = 0.5) -> None:
        """
        Compensate for drift by moving partially back toward the original vector.
        
        Args:
            factor: Compensation factor (0.0 to 1.0)
                   0.0 = no compensation, 1.0 = full reset to original
        """
        if factor <= 0.0:
            return
        elif factor >= 1.0:
            self.reset_to_original()
            return
        
        drift = self.get_drift_vector()
        self.vector = self.vector - (drift * factor)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the neuron to a dictionary representation.
        
        Returns:
            Dictionary representation of the neuron
        """
        return {
            'uuid': self.uuid,
            'vector': self.vector.tolist(),
            'metadata': self.metadata,
            'binary_ref': self.binary_ref,
            'links': self.links,
            '_original_vector': self._original_vector.tolist(),
            '_tone_history': [
                {
                    'tone_vector': th['tone_vector'].tolist(),
                    'strength': th['strength'],
                    'timestamp': th['timestamp']
                }
                for th in self._tone_history
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BinaryNeuron':
        """
        Create a neuron from a dictionary representation.
        
        Args:
            data: Dictionary representation of a neuron
            
        Returns:
            BinaryNeuron instance
        """
        neuron = cls(
            uuid_str=data['uuid'],
            vector=np.array(data['vector'], dtype=np.float32),
            metadata=data['metadata'],
            binary_ref=data['binary_ref']
        )
        
        neuron.links = data['links']
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
        
        return neuron


class BinaryNeuronSerializer:
    """
    Basic serializer for Binary Neurons with UUID tracking.
    """
    
    def serialize(self, neuron: BinaryNeuron) -> bytes:
        """
        Serialize a neuron to binary format.
        
        Args:
            neuron: BinaryNeuron to serialize
            
        Returns:
            Binary representation of the neuron
        """
        # Convert neuron to dictionary
        neuron_dict = neuron.to_dict()
        
        # Use pickle for simplicity in the prototype
        # In production, would use a more efficient binary format
        return pickle.dumps(neuron_dict)
    
    def deserialize(self, data: bytes) -> BinaryNeuron:
        """
        Deserialize binary data to a neuron.
        
        Args:
            data: Binary data to deserialize
            
        Returns:
            Deserialized BinaryNeuron
        """
        # Unpickle the dictionary
        neuron_dict = pickle.loads(data)
        
        # Create neuron from dictionary
        return BinaryNeuron.from_dict(neuron_dict)
    
    def serialize_to_json(self, neuron: BinaryNeuron) -> str:
        """
        Serialize a neuron to JSON format for human readability.
        
        Args:
            neuron: BinaryNeuron to serialize
            
        Returns:
            JSON string representation of the neuron
        """
        return json.dumps(neuron.to_dict(), indent=2)
    
    def deserialize_from_json(self, json_str: str) -> BinaryNeuron:
        """
        Deserialize a neuron from JSON format.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Deserialized BinaryNeuron
        """
        neuron_dict = json.loads(json_str)
        return BinaryNeuron.from_dict(neuron_dict)


class BinaryNeuronStorageManager:
    """
    Minimal storage manager for Binary Neurons.
    """
    
    def __init__(self, storage_dir: str):
        """
        Initialize the storage manager.
        
        Args:
            storage_dir: Directory to store neurons
        """
        self.storage_dir = storage_dir
        self.serializer = BinaryNeuronSerializer()
        self.index = {}  # UUID to filename mapping
        
        # Create storage directory if it doesn't exist
        os.makedirs(storage_dir, exist_ok=True)
        
        # Create subdirectories for better organization
        os.makedirs(os.path.join(storage_dir, 'neurons'), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'index'), exist_ok=True)
        
        # Load existing index if available
        self._load_index()
    
    def _get_neuron_path(self, uuid_str: str) -> str:
        """
        Get the file path for a neuron.
        
        Args:
            uuid_str: UUID of the neuron
            
        Returns:
            File path for the neuron
        """
        # Use first 2 characters of UUID for subdirectory to avoid too many files in one directory
        subdir = uuid_str[:2]
        neuron_dir = os.path.join(self.storage_dir, 'neurons', subdir)
        os.makedirs(neuron_dir, exist_ok=True)
        
        return os.path.join(neuron_dir, f"{uuid_str}.bin")
    
    def _load_index(self) -> None:
        """Load the UUID index from disk."""
        index_path = os.path.join(self.storage_dir, 'index', 'uuid_index.json')
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                self.index = json.load(f)
    
    def _save_index(self) -> None:
        """Save the UUID index to disk."""
        index_path = os.path.join(self.storage_dir, 'index', 'uuid_index.json')
        with open(index_path, 'w') as f:
            json.dump(self.index, f)
    
    def store_neuron(self, neuron: BinaryNeuron) -> str:
        """
        Store a neuron.
        
        Args:
            neuron: BinaryNeuron to store
            
        Returns:
            UUID of the stored neuron
        """
        # Serialize the neuron
        data = self.serializer.serialize(neuron)
        
        # Get the file path
        file_path = self._get_neuron_path(neuron.uuid)
        
        # Write to file
        with open(file_path, 'wb') as f:
            f.write(data)
        
        # Update index
        self.index[neuron.uuid] = file_path
        self._save_index()
        
        return neuron.uuid
    
    def get_neuron(self, uuid_str: str) -> Optional[BinaryNeuron]:
        """
        Retrieve a neuron by UUID.
        
        Args:
            uuid_str: UUID of the neuron to retrieve
            
        Returns:
            Retrieved BinaryNeuron or None if not found
        """
        # Check if UUID exists in index
        if uuid_str not in self.index:
            return None
        
        file_path = self.index[uuid_str]
        
        # Check if file exists
        if not os.path.exists(file_path):
            # Remove from index if file doesn't exist
            del self.index[uuid_str]
            self._save_index()
            return None
        
        # Read and deserialize
        with open(file_path, 'rb') as f:
            data = f.read()
        
        return self.serializer.deserialize(data)
    
    def delete_neuron(self, uuid_str: str) -> bool:
        """
        Delete a neuron.
        
        Args:
            uuid_str: UUID of the neuron to delete
            
        Returns:
            True if deleted, False if not found
        """
        if uuid_str not in self.index:
            return False
        
        file_path = self.index[uuid_str]
        
        # Delete file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove from index
        del self.index[uuid_str]
        self._save_index()
        
        return True
    
    def list_neurons(self) -> List[str]:
        """
        List all stored neuron UUIDs.
        
        Returns:
            List of UUIDs
        """
        return list(self.index.keys())
    
    def store_batch(self, neurons: List[BinaryNeuron]) -> List[str]:
        """
        Store multiple neurons.
        
        Args:
            neurons: List of BinaryNeurons to store
            
        Returns:
            List of stored UUIDs
        """
        uuids = []
        for neuron in neurons:
            uuid_str = self.store_neuron(neuron)
            uuids.append(uuid_str)
        
        return uuids
    
    def get_batch(self, uuid_list: List[str]) -> List[Optional[BinaryNeuron]]:
        """
        Retrieve multiple neurons.
        
        Args:
            uuid_list: List of UUIDs to retrieve
            
        Returns:
            List of retrieved neurons (None for not found)
        """
        return [self.get_neuron(uuid_str) for uuid_str in uuid_list]


class KnowledgeConverter:
    """
    Utilities for converting documents to Binary Neurons.
    """
    
    def __init__(self, vector_size: int = 512):
        """
        Initialize the knowledge converter.
        
        Args:
            vector_size: Size of the embedding vectors
        """
        self.vector_size = vector_size
    
    def text_to_embedding(self, text: str) -> np.ndarray:
        """
        Convert text to an embedding vector.
        
        In a real implementation, this would use a proper embedding model.
        For the prototype, we use a simple hash-based approach.
        
        Args:
            text: Text to convert
            
        Returns:
            Embedding vector
        """
        # Create a deterministic but simplified embedding
        # In production, would use a proper embedding model
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Use the hash to seed a random number generator
        np.random.seed(int.from_bytes(hash_bytes[:4], byteorder='big'))
        
        # Generate a random vector
        vector = np.random.randn(self.vector_size).astype(np.float32)
        
        # Normalize to unit length
        vector = vector / np.linalg.norm(vector)
        
        return vector
    
    def document_to_neurons(self, 
                           document: str, 
                           chunk_size: int = 1000, 
                           overlap: int = 200,
                           metadata: Optional[Dict[str, Any]] = None) -> List[BinaryNeuron]:
        """
        Convert a document to a list of Binary Neurons.
        
        Args:
            document: Document text
            chunk_size: Size of text chunks in characters
            overlap: Overlap between chunks in characters
            metadata: Optional metadata to include in all neurons
            
        Returns:
            List of BinaryNeurons
        """
        # Split document into chunks
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
    
    def _chunk_document(self, document: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Split a document into overlapping chunks.
        
        Args:
            document: Document text
            chunk_size: Size of chunks in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        # Simple character-based chunking for the prototype
        # In production, would use more sophisticated chunking based on semantics
        
        pos = 0
        while pos < len(document):
            end = min(pos + chunk_size, len(document))
            chunks.append(document[pos:end])
            pos += chunk_size - overlap
        
        return chunks
    
    def json_to_neurons(self, 
                       json_data: Union[Dict, List], 
                       metadata: Optional[Dict[str, Any]] = None) -> List[BinaryNeuron]:
        """
        Convert JSON data to Binary Neurons.
        
        Args:
            json_data: JSON data (dict or list)
            metadata: Optional metadata to include in all neurons
            
        Returns:
            List of BinaryNeurons
        """
        # Convert JSON to string for simple processing
        json_str = json.dumps(json_data, indent=2)
        
        # Use document conversion
        base_metadata = metadata or {}
        base_metadata['data_type'] = 'json'
        
        return self.document_to_neurons(json_str, metadata=base_metadata)
    
    def create_tone_vector(self, tone_name: str, seed: Optional[int] = None) -> np.ndarray:
        """
        Create a tone vector for emotional modulation.
        
        Args:
            tone_name: Name of the tone (e.g., 'happy', 'sad', 'formal')
            seed: Optional seed for reproducibility
            
        Returns:
            Tone vector
        """
        # Set seed if provided
        if seed is not None:
            np.random.seed(seed)
        else:
            # Use tone name as seed
            np.random.seed(int(hashlib.md5(tone_name.encode()).hexdigest(), 16) % (2**32))
        
        # Create a random vector
        vector = np.random.randn(self.vector_size).astype(np.float32)
        
        # Normalize to unit length
        vector = vector / np.linalg.norm(vector)
        
        return vector


class MemoryWeb:
    """
    Simple Memory Web implementation for the prototype.
    """
    
    def __init__(self, storage_manager: BinaryNeuronStorageManager):
        """
        Initialize the Memory Web.
        
        Args:
            storage_manager: Storage manager for neurons
        """
        self.storage_manager = storage_manager
        self.knowledge_converter = KnowledgeConverter()
        
        # Cache for frequently accessed neurons
        self.cache = {}
        self.max_cache_size = 1000
    
    def add_document(self, 
                    document: str, 
                    document_id: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Add a document to the Memory Web.
        
        Args:
            document: Document text
            document_id: Unique identifier for the document
            metadata: Optional metadata
            
        Returns:
            List of neuron UUIDs
        """
        # Prepare metadata
        meta = metadata or {}
        meta['document_id'] = document_id
        
        # Convert document to neurons
        neurons = self.knowledge_converter.document_to_neurons(document, metadata=meta)
        
        # Store neurons
        return self.storage_manager.store_batch(neurons)
    
    def add_json_data(self, 
                     json_data: Union[Dict, List], 
                     data_id: str, 
                     metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Add JSON data to the Memory Web.
        
        Args:
            json_data: JSON data (dict or list)
            data_id: Unique identifier for the data
            metadata: Optional metadata
            
        Returns:
            List of neuron UUIDs
        """
        # Prepare metadata
        meta = metadata or {}
        meta['data_id'] = data_id
        
        # Convert JSON to neurons
        neurons = self.knowledge_converter.json_to_neurons(json_data, metadata=meta)
        
        # Store neurons
        return self.storage_manager.store_batch(neurons)
    
    def get_neuron(self, uuid_str: str) -> Optional[BinaryNeuron]:
        """
        Get a neuron by UUID.
        
        Args:
            uuid_str: UUID of the neuron
            
        Returns:
            BinaryNeuron or None if not found
        """
        # Check cache first
        if uuid_str in self.cache:
            return self.cache[uuid_str]
        
        # Get from storage
        neuron = self.storage_manager.get_neuron(uuid_str)
        
        # Update cache if found
        if neuron:
            self._update_cache(uuid_str, neuron)
        
        return neuron
    
    def _update_cache(self, uuid_str: str, neuron: BinaryNeuron) -> None:
        """
        Update the neuron cache.
        
        Args:
            uuid_str: UUID of the neuron
            neuron: BinaryNeuron to cache
        """
        # Add to cache
        self.cache[uuid_str] = neuron
        
        # Evict if cache is too large
        if len(self.cache) > self.max_cache_size:
            # Simple LRU: remove a random item
            # In production, would use a proper LRU cache
            key_to_remove = next(iter(self.cache))
            del self.cache[key_to_remove]
    
    def apply_tone_to_document(self, 
                              document_id: str, 
                              tone_name: str, 
                              strength: float = 0.1) -> int:
        """
        Apply a tone to all neurons from a document.
        
        Args:
            document_id: Document identifier
            tone_name: Name of the tone to apply
            strength: Strength of the tone application
            
        Returns:
            Number of neurons modified
        """
        # Get all neurons
        all_uuids = self.storage_manager.list_neurons()
        
        # Create tone vector
        tone_vector = self.knowledge_converter.create_tone_vector(tone_name)
        
        count = 0
        
        # Apply tone to matching neurons
        for uuid_str in all_uuids:
            neuron = self.get_neuron(uuid_str)
            
            if neuron and neuron.metadata.get('document_id') == document_id:
                # Apply tone
                neuron.apply_tone(tone_vector, strength)
                
                # Store updated neuron
                self.storage_manager.store_neuron(neuron)
                
                # Update cache
                self._update_cache(uuid_str, neuron)
                
                count += 1
        
        return count
    
    def compensate_drift(self, 
                        document_id: str, 
                        factor: float = 0.5) -> int:
        """
        Compensate for drift in neurons from a document.
        
        Args:
            document_id: Document identifier
            factor: Compensation factor
            
        Returns:
            Number of neurons modified
        """
        # Get all neurons
        all_uuids = self.storage_manager.list_neurons()
        
        count = 0
        
        # Compensate matching neurons
        for uuid_str in all_uuids:
            neuron = self.get_neuron(uuid_str)
            
            if neuron and neuron.metadata.get('document_id') == document_id:
                # Compensate drift
                neuron.compensate_drift(factor)
                
                # Store updated neuron
                self.storage_manager.store_neuron(neuron)
                
                # Update cache
                self._update_cache(uuid_str, neuron)
                
                count += 1
        
        return count
    
    def get_document_neurons(self, document_id: str) -> List[BinaryNeuron]:
        """
        Get all neurons for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of neurons
        """
        # Get all neurons
        all_uuids = self.storage_manager.list_neurons()
        
        # Filter by document ID
        document_neurons = []
        
        for uuid_str in all_uuids:
            neuron = self.get_neuron(uuid_str)
            
            if neuron and neuron.metadata.get('document_id') == document_id:
                document_neurons.append(neuron)
        
        # Sort by chunk index if available
        document_neurons.sort(key=lambda n: n.metadata.get('chunk_index', 0))
        
        return document_neurons
    
    def get_document_text(self, document_id: str) -> str:
        """
        Reconstruct document text from neurons.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Reconstructed document text
        """
        # Get document neurons
        neurons = self.get_document_neurons(document_id)
        
        # Extract text from each neuron
        text_chunks = [n.metadata.get('text', '') for n in neurons]
        
        # Join chunks
        return ''.join(text_chunks)


def test_binary_neuron_prototype():
    """Test the Binary Neuron prototype implementation."""
    print("Testing Binary Neuron prototype...")
    
    # Create a test neuron
    test_neuron = BinaryNeuron(
        vector=np.random.randn(512),
        metadata={"test": "value", "source": "test_function"}
    )
    
    print(f"Created test neuron with UUID: {test_neuron.uuid}")
    
    # Test serialization
    serializer = BinaryNeuronSerializer()
    binary_data = serializer.serialize(test_neuron)
    
    print(f"Serialized neuron size: {len(binary_data)} bytes")
    
    # Test deserialization
    deserialized_neuron = serializer.deserialize(binary_data)
    
    print(f"Deserialized neuron UUID: {deserialized_neuron.uuid}")
    
    # Verify data integrity
    assert test_neuron.uuid == deserialized_neuron.uuid
    assert np.array_equal(test_neuron.vector, deserialized_neuron.vector)
    assert test_neuron.metadata == deserialized_neuron.metadata
    assert test_neuron.binary_ref == deserialized_neuron.binary_ref
    
    print("Serialization/deserialization test passed!")
    
    # Test storage manager
    storage_dir = "/tmp/binary_neuron_test"
    storage_manager = BinaryNeuronStorageManager(storage_dir)
    
    # Store the neuron
    stored_uuid = storage_manager.store_neuron(test_neuron)
    
    print(f"Stored neuron with UUID: {stored_uuid}")
    
    # Retrieve the neuron
    retrieved_neuron = storage_manager.get_neuron(stored_uuid)
    
    print(f"Retrieved neuron UUID: {retrieved_neuron.uuid}")
    
    # Verify data integrity
    assert test_neuron.uuid == retrieved_neuron.uuid
    assert np.array_equal(test_neuron.vector, retrieved_neuron.vector)
    assert test_neuron.metadata == retrieved_neuron.metadata
    assert test_neuron.binary_ref == retrieved_neuron.binary_ref
    
    print("Storage/retrieval test passed!")
    
    # Test tone application
    tone_vector = np.random.randn(512)
    tone_vector = tone_vector / np.linalg.norm(tone_vector)
    
    print(f"Original vector norm: {np.linalg.norm(test_neuron.vector)}")
    
    test_neuron.apply_tone(tone_vector, strength=0.2)
    
    print(f"After tone application, vector norm: {np.linalg.norm(test_neuron.vector)}")
    print(f"Drift magnitude: {test_neuron.get_drift_magnitude()}")
    
    # Test drift compensation
    test_neuron.compensate_drift(factor=0.5)
    
    print(f"After compensation, drift magnitude: {test_neuron.get_drift_magnitude()}")
    
    # Test knowledge conversion
    converter = KnowledgeConverter()
    
    test_document = """
    This is a test document for the Binary Neuron prototype.
    It contains multiple sentences that will be converted into neurons.
    Each sentence or chunk will become a neuron in the Memory Web.
    The neurons will be linked together to form a connected graph.
    """
    
    neurons = converter.document_to_neurons(
        test_document,
        chunk_size=100,
        overlap=20,
        metadata={"source": "test_document"}
    )
    
    print(f"Converted document to {len(neurons)} neurons")
    
    # Test Memory Web
    memory_web = MemoryWeb(storage_manager)
    
    document_id = "test_doc_001"
    neuron_uuids = memory_web.add_document(test_document, document_id)
    
    print(f"Added document to Memory Web, created {len(neuron_uuids)} neurons")
    
    # Test tone application to document
    modified_count = memory_web.apply_tone_to_document(
        document_id,
        "happy",
        strength=0.15
    )
    
    print(f"Applied 'happy' tone to {modified_count} neurons")
    
    # Test drift compensation
    compensated_count = memory_web.compensate_drift(document_id, factor=0.3)
    
    print(f"Compensated drift in {compensated_count} neurons")
    
    # Test document reconstruction
    reconstructed_text = memory_web.get_document_text(document_id)
    
    print(f"Reconstructed document length: {len(reconstructed_text)} characters")
    print("Test completed successfully!")


if __name__ == "__main__":
    test_binary_neuron_prototype()
