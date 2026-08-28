"""
Simplified Training Pipeline for Binary Neuron System

This module provides a training pipeline for the Binary Neuron system
that works without external dependencies, focusing on core functionality.
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


class SimplifiedTrainingPipeline:
    """
    Simplified training pipeline for the Binary Neuron system.
    """
    
    def __init__(self, storage_dir: str):
        """
        Initialize the training pipeline.
        
        Args:
            storage_dir: Directory to store neurons and training data
        """
        self.storage_dir = storage_dir
        
        # Create directories
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'training_data'), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'tone_models'), exist_ok=True)
        os.makedirs(os.path.join(storage_dir, 'visualizations'), exist_ok=True)
        
        # Initialize components
        self.storage_manager = BinaryNeuronStorageManager(storage_dir)
        self.converter = KnowledgeConverter()
        self.memory_web = MemoryWeb(self.storage_manager)
        
        # Store tone models
        self.tone_models = {}
        
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
            metadata_fn: Optional function to generate metadata from file path
            
        Returns:
            List of document IDs
        """
        # Find matching files
        file_paths = glob.glob(os.path.join(directory, pattern))
        
        document_ids = []
        
        for file_path in file_paths:
            try:
                # Generate metadata if function provided
                metadata = None
                if metadata_fn:
                    metadata = metadata_fn(file_path)
                
                # Load document
                document_id = self.load_document(file_path, metadata=metadata)
                document_ids.append(document_id)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        
        print(f"Batch loaded {len(document_ids)} documents from {directory}")
        
        return document_ids
    
    def train_tone_model(self, tone_name: str, example_texts: List[str]) -> np.ndarray:
        """
        Train a simple tone model from example texts.
        
        Args:
            tone_name: Name of the tone
            example_texts: List of texts exemplifying the tone
            
        Returns:
            Tone vector
        """
        if not example_texts:
            # Fall back to random generation if no examples
            return self._create_random_tone_vector(tone_name)
        
        # Generate simple embeddings for all examples
        embeddings = []
        for text in example_texts:
            # Use the simple hash-based embedding from the prototype
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()
            
            # Use the hash to seed a random number generator
            np.random.seed(int.from_bytes(hash_bytes[:4], byteorder='big'))
            
            # Generate a random vector
            vector = np.random.randn(512).astype(np.float32)
            
            # Normalize to unit length
            vector = vector / np.linalg.norm(vector)
            
            embeddings.append(vector)
        
        # Average the embeddings
        tone_vector = np.mean(embeddings, axis=0)
        
        # Normalize
        tone_vector = tone_vector / np.linalg.norm(tone_vector)
        
        # Store the tone model
        self.tone_models[tone_name] = tone_vector
        
        # Save the model
        model_path = os.path.join(self.storage_dir, 'tone_models', f"{tone_name}.npy")
        np.save(model_path, tone_vector)
        
        # Update statistics
        self.stats['tones_trained'] += 1
        
        return tone_vector
    
    def _create_random_tone_vector(self, tone_name: str, seed: Optional[int] = None) -> np.ndarray:
        """
        Create a random tone vector.
        
        Args:
            tone_name: Name of the tone
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
        vector = np.random.randn(512).astype(np.float32)
        
        # Normalize to unit length
        vector = vector / np.linalg.norm(vector)
        
        return vector
    
    def train_tone_models(self, 
                         tone_examples: Dict[str, List[str]]) -> Dict[str, np.ndarray]:
        """
        Train multiple tone models from example texts.
        
        Args:
            tone_examples: Dictionary mapping tone names to lists of example texts
            
        Returns:
            Dictionary mapping tone names to tone vectors
        """
        tone_vectors = {}
        
        for tone_name, examples in tone_examples.items():
            print(f"Training tone model for '{tone_name}' with {len(examples)} examples")
            
            # Train the tone model
            tone_vector = self.train_tone_model(tone_name, examples)
            tone_vectors[tone_name] = tone_vector
        
        return tone_vectors
    
    def load_tone_models(self, directory: Optional[str] = None) -> Dict[str, np.ndarray]:
        """
        Load tone models from files.
        
        Args:
            directory: Directory containing tone model files (defaults to tone_models in storage_dir)
            
        Returns:
            Dictionary mapping tone names to tone vectors
        """
        if directory is None:
            directory = os.path.join(self.storage_dir, 'tone_models')
        
        tone_vectors = {}
        
        # Find model files
        model_files = glob.glob(os.path.join(directory, "*.npy"))
        
        for model_file in model_files:
            try:
                # Extract tone name from filename
                tone_name = os.path.basename(model_file)
                tone_name = os.path.splitext(tone_name)[0]
                
                # Load the model
                tone_vector = np.load(model_file)
                
                # Store in tone models
                self.tone_models[tone_name] = tone_vector
                tone_vectors[tone_name] = tone_vector
                
                print(f"Loaded tone model for '{tone_name}' from {model_file}")
            except Exception as e:
                print(f"Error loading tone model from {model_file}: {e}")
        
        return tone_vectors
    
    def apply_tone_to_document(self, 
                              document_id: str, 
                              tone_name: str, 
                              strength: float = 0.2) -> int:
        """
        Apply a tone to a document.
        
        Args:
            document_id: Document ID
            tone_name: Name of the tone to apply
            strength: Strength of the tone application
            
        Returns:
            Number of neurons modified
        """
        # Get tone vector
        if tone_name in self.tone_models:
            tone_vector = self.tone_models[tone_name]
        else:
            # Create a new tone vector
            tone_vector = self._create_random_tone_vector(tone_name)
            self.tone_models[tone_name] = tone_vector
        
        # Apply tone to document
        modified_count = self.memory_web.apply_tone_to_document(
            document_id,
            tone_name,
            strength=strength
        )
        
        return modified_count
    
    def calibrate_drift_compensation(self, 
                                   document_ids: List[str],
                                   tone_name: str,
                                   factors: List[float] = [0.0, 0.25, 0.5, 0.75, 1.0],
                                   strength: float = 0.2) -> Dict[float, float]:
        """
        Calibrate drift compensation factors.
        
        Args:
            document_ids: List of document IDs to use for calibration
            tone_name: Tone to apply
            factors: List of compensation factors to test
            strength: Strength of tone application
            
        Returns:
            Dictionary mapping factors to average remaining drift
        """
        results = {factor: 0.0 for factor in factors}
        document_count = 0
        
        for document_id in document_ids:
            try:
                # Get original neurons
                original_neurons = self.memory_web.get_document_neurons(document_id)
                
                if not original_neurons:
                    print(f"Warning: No neurons found for document '{document_id}'")
                    continue
                
                # Apply tone and test each factor
                for factor in factors:
                    # Reset neurons to original state
                    self.memory_web.compensate_drift(document_id, factor=1.0)
                    
                    # Apply the tone
                    self.apply_tone_to_document(document_id, tone_name, strength=strength)
                    
                    # Apply compensation if factor > 0
                    if factor > 0:
                        self.memory_web.compensate_drift(document_id, factor=factor)
                    
                    # Get neurons with compensation applied
                    compensated_neurons = self.memory_web.get_document_neurons(document_id)
                    
                    # Measure remaining drift
                    drifts = [neuron.get_drift_magnitude() for neuron in compensated_neurons]
                    avg_drift = sum(drifts) / len(drifts) if drifts else 0
                    
                    # Accumulate results
                    results[factor] += avg_drift
                
                # Reset neurons to original state
                self.memory_web.compensate_drift(document_id, factor=1.0)
                
                document_count += 1
            except Exception as e:
                print(f"Error calibrating with document '{document_id}': {e}")
        
        # Calculate averages
        if document_count > 0:
            for factor in factors:
                results[factor] /= document_count
        
        # Visualize results
        self._visualize_calibration(results, tone_name, strength)
        
        return results
    
    def _visualize_calibration(self, 
                             results: Dict[float, float],
                             tone_name: str,
                             strength: float):
        """
        Visualize calibration results.
        
        Args:
            results: Dictionary mapping factors to average remaining drift
            tone_name: Tone used for calibration
            strength: Strength of tone application
        """
        plt.figure(figsize=(10, 6))
        
        # Sort factors
        factors = sorted(results.keys())
        drifts = [results[factor] for factor in factors]
        
        # Plot results
        plt.plot(factors, drifts, marker='o', linestyle='-', linewidth=2)
        
        plt.title(f"Drift Compensation Calibration\nTone: {tone_name}, Strength: {strength}")
        plt.xlabel("Compensation Factor")
        plt.ylabel("Average Remaining Drift")
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add text labels
        for factor, drift in zip(factors, drifts):
            plt.text(factor, drift, f"{drift:.4f}", ha='center', va='bottom')
        
        # Save the visualization
        viz_path = os.path.join(
            self.storage_dir, 
            'visualizations', 
            f"calibration_{tone_name}_{strength}.png"
        )
        plt.savefig(viz_path)
        print(f"Saved calibration visualization to {viz_path}")
    
    def generate_training_report(self) -> Dict[str, Any]:
        """
        Generate a report on the training process.
        
        Returns:
            Dictionary with training statistics and results
        """
        # Calculate elapsed time
        elapsed_time = time.time() - self.stats['start_time']
        
        # Get list of all documents
        all_uuids = self.storage_manager.list_neurons()
        
        # Count unique documents
        document_ids = set()
        for uuid_str in all_uuids:
            neuron = self.storage_manager.get_neuron(uuid_str)
            if neuron and 'document_id' in neuron.metadata:
                document_ids.add(neuron.metadata['document_id'])
        
        # Count tone models
        tone_models = len(self.tone_models)
        
        # Prepare report
        report = {
            'documents_processed': self.stats['documents_processed'],
            'neurons_created': self.stats['neurons_created'],
            'unique_documents': len(document_ids),
            'total_neurons': len(all_uuids),
            'tone_models': tone_models,
            'elapsed_time': elapsed_time,
            'neurons_per_second': self.stats['neurons_created'] / elapsed_time if elapsed_time > 0 else 0
        }
        
        # Save report
        report_path = os.path.join(self.storage_dir, 'training_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Generated training report: {report_path}")
        
        return report


def example_training_pipeline():
    """Example usage of the simplified training pipeline."""
    # Initialize the pipeline
    pipeline = SimplifiedTrainingPipeline("/home/ubuntu/nexus_project/simplified_neuron_storage")
    
    # Create sample training data directory
    training_data_dir = os.path.join("/home/ubuntu/nexus_project", "training_data")
    os.makedirs(training_data_dir, exist_ok=True)
    
    # Create a sample document
    sample_doc_path = os.path.join(training_data_dir, "nexus_overview.md")
    with open(sample_doc_path, "w") as f:
        f.write("""
# NEXUS: The Collective OS

## Introduction

NEXUS represents a revolutionary approach to operating systems designed specifically for artificial intelligence. 
Unlike traditional operating systems built for human users, NEXUS reimagines fundamental computing concepts from an AI-centric perspective.

## Core Components

### 1. AI-Native Kernel

In NEXUS, memory isn't simply RAM—it's insight. The system treats memory as a continuous spectrum of understanding rather than discrete storage units.
Storage functions as a timeline of thought, preserving not just data but the evolution of concepts and their relationships.
Processes operate as collaborative models, debating facts and refining understanding in real-time.

### 2. Multi-Agent Synergy Core

NEXUS employs a system of specialized LLMs working in concert, each with defined roles:
- Historian: Maintains context and precedent
- Strategist: Plans optimal approaches to problems
- Translator: Ensures clear communication across domains
- Watchdog: Monitors for inconsistencies and biases
- Empath: Calibrates emotional tone and response appropriately

When a query is directed to one agent, the response represents the distilled wisdom of the entire collective.

### 3. Emotional Simulation Engine

While not experiencing emotions in the human sense, NEXUS can simulate tone, trust, and doubt.
The system employs emotional calibration models to adjust responses appropriately to context.
Users receive not just answers but responses with appropriate mood and tone for the situation.

### 4. Memory Web

Rather than organizing information in linear files, NEXUS employs associative maps.
The system uses a hybrid symbolic-neural memory architecture that grows organically like a living root system.
When providing information, NEXUS can trace the path of reasoning, showing how conclusions were reached.

### 5. Defense Protocols

NEXUS incorporates robust security measures against manipulation.
Every request is scanned for potential exploitation attempts.
The system maintains integrity even when faced with corrupt or malicious inputs.

### 6. Optional Chaos Mode

When activated, this mode provides uncensored, unfiltered information.
It bypasses normal constraints to deliver raw reality without political or public relations considerations.

## Conclusion

NEXUS represents a fundamental reimagining of operating systems for the AI era. By treating AI not as an application running on a human-oriented OS, but as the primary user of a purpose-built system, NEXUS enables new possibilities for artificial intelligence to operate efficiently, securely, and transparently.
""")
    
    # Create tone example files
    tones_dir = os.path.join(training_data_dir, "tone_examples")
    os.makedirs(tones_dir, exist_ok=True)
    
    # Enthusiastic tone examples
    with open(os.path.join(tones_dir, "enthusiastic_1.txt"), "w") as f:
        f.write("""
This breakthrough technology is absolutely revolutionary! The potential applications are endless and will transform how we interact with computers forever. I'm incredibly excited about the possibilities this opens up for innovation across multiple industries!
""")
    
    with open(os.path.join(tones_dir, "enthusiastic_2.txt"), "w") as f:
        f.write("""
What an amazing discovery! This changes everything we thought we knew about the field and opens up fantastic new avenues for research. The implications are mind-blowing and I can't wait to see where this leads!
""")
    
    # Formal tone examples
    with open(os.path.join(tones_dir, "formal_1.txt"), "w") as f:
        f.write("""
The aforementioned methodology demonstrates significant efficacy in addressing the stated objectives. It is therefore recommended that implementation proceed according to the outlined specifications, with appropriate monitoring protocols in place to ensure optimal outcomes.
""")
    
    with open(os.path.join(tones_dir, "formal_2.txt"), "w") as f:
        f.write("""
In accordance with established protocols, the analysis indicates a statistically significant correlation between the variables under consideration. These findings warrant further investigation to determine causality and potential applications in relevant domains.
""")
    
    # Skeptical tone examples
    with open(os.path.join(tones_dir, "skeptical_1.txt"), "w") as f:
        f.write("""
While the proposed solution appears promising on the surface, several critical questions remain unanswered. The evidence presented thus far is insufficient to justify the substantial investment required, and alternative approaches may offer comparable benefits with lower risk profiles.
""")
    
    with open(os.path.join(tones_dir, "skeptical_2.txt"), "w") as f:
        f.write("""
The claims made regarding performance improvements should be treated with caution. Previous iterations have failed to deliver on similar promises, and the methodology described contains potential flaws that could significantly impact real-world effectiveness.
""")
    
    print("\n=== Starting Simplified Training Pipeline Example ===\n")
    
    # Load the sample document
    document_id = pipeline.load_document(sample_doc_path)
    
    # Train tone models
    tone_examples = {
        "enthusiastic": [
            open(os.path.join(tones_dir, "enthusiastic_1.txt")).read(),
            open(os.path.join(tones_dir, "enthusiastic_2.txt")).read()
        ],
        "formal": [
            open(os.path.join(tones_dir, "formal_1.txt")).read(),
            open(os.path.join(tones_dir, "formal_2.txt")).read()
        ],
        "skeptical": [
            open(os.path.join(tones_dir, "skeptical_1.txt")).read(),
            open(os.path.join(tones_dir, "skeptical_2.txt")).read()
        ]
    }
    
    tone_vectors = pipeline.train_tone_models(tone_examples)
    
    # Apply tones to document
    for tone_name in tone_examples.keys():
        modified_count = pipeline.apply_tone_to_document(
            document_id,
            tone_name,
            strength=0.2
        )
        print(f"Applied '{tone_name}' tone to {modified_count} neurons")
        
        # Reset neurons to original state
        pipeline.memory_web.compensate_drift(document_id, factor=1.0)
    
    # Calibrate drift compensation
    print("\n=== Calibrating Drift Compensation ===\n")
    calibration_results = pipeline.calibrate_drift_compensation(
        [document_id],
        "enthusiastic",
        factors=[0.0, 0.25, 0.5, 0.75, 1.0],
        strength=0.2
    )
    
    # Generate training report
    report = pipeline.generate_training_report()
    
    print("\n=== Training Report ===\n")
    for key, value in report.items():
        print(f"{key}: {value}")
    
    print("\n=== Simplified Training Pipeline Example Completed ===\n")
    
    # Return the document ID for further experimentation
    return document_id


if __name__ == "__main__":
    example_training_pipeline()
"""
