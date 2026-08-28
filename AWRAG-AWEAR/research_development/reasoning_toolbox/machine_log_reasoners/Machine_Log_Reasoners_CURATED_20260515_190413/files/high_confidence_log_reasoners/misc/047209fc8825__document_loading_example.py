"""
Document Loading Example for Binary Neuron Prototype

This script demonstrates how to load a document into the Binary Neuron system,
apply tone modulation, and visualize the results.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from binary_neuron_prototype import (
    BinaryNeuron, 
    BinaryNeuronSerializer, 
    BinaryNeuronStorageManager,
    KnowledgeConverter,
    MemoryWeb
)

# Create storage directory
STORAGE_DIR = "/home/ubuntu/nexus_project/neuron_storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Initialize components
storage_manager = BinaryNeuronStorageManager(STORAGE_DIR)
memory_web = MemoryWeb(storage_manager)
converter = KnowledgeConverter()

def load_sample_document():
    """Load a sample document into the Memory Web."""
    # Sample document about AI operating systems
    document = """
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
    """
    
    # Add document to Memory Web
    document_id = "nexus_os_overview"
    neuron_uuids = memory_web.add_document(
        document, 
        document_id,
        metadata={
            "title": "NEXUS: The Collective OS",
            "type": "concept_overview",
            "author": "NEXUS Project Team"
        }
    )
    
    print(f"Loaded document into Memory Web, created {len(neuron_uuids)} neurons")
    return document_id

def apply_tones_and_visualize(document_id):
    """Apply different tones to the document and visualize the results."""
    # Get original neurons
    original_neurons = memory_web.get_document_neurons(document_id)
    
    # Create tone vectors
    tones = {
        "neutral": None,  # Original state
        "enthusiastic": converter.create_tone_vector("enthusiastic", seed=42),
        "formal": converter.create_tone_vector("formal", seed=43),
        "skeptical": converter.create_tone_vector("skeptical", seed=44)
    }
    
    # Apply tones and collect drift data
    drift_data = {}
    
    # First, measure baseline (neutral)
    baseline_drifts = [neuron.get_drift_magnitude() for neuron in original_neurons]
    drift_data["neutral"] = baseline_drifts
    
    # Apply each tone and measure drift
    for tone_name, tone_vector in tones.items():
        if tone_name == "neutral":
            continue  # Skip neutral as we already have it
            
        print(f"Applying '{tone_name}' tone to document...")
        
        # Reset neurons to original state
        memory_web.compensate_drift(document_id, factor=1.0)
        
        # Apply the tone
        memory_web.apply_tone_to_document(document_id, tone_name, strength=0.2)
        
        # Get neurons with tone applied
        toned_neurons = memory_web.get_document_neurons(document_id)
        
        # Measure drift
        drifts = [neuron.get_drift_magnitude() for neuron in toned_neurons]
        drift_data[tone_name] = drifts
    
    # Visualize the drift
    visualize_tone_drift(drift_data)
    
    # Reset neurons to original state
    memory_web.compensate_drift(document_id, factor=1.0)
    
    return drift_data

def visualize_tone_drift(drift_data):
    """Visualize the drift caused by different tones."""
    plt.figure(figsize=(12, 6))
    
    # Plot drift for each tone
    for tone_name, drifts in drift_data.items():
        # Calculate average drift per chunk
        chunk_indices = list(range(len(drifts)))
        plt.plot(chunk_indices, drifts, label=f"{tone_name.capitalize()} Tone", marker='o')
    
    plt.title("Vector Drift by Tone and Document Chunk")
    plt.xlabel("Chunk Index")
    plt.ylabel("Drift Magnitude")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Save the plot
    plt.savefig("/home/ubuntu/nexus_project/tone_drift_visualization.png")
    print("Saved tone drift visualization to tone_drift_visualization.png")

def demonstrate_drift_compensation(document_id):
    """Demonstrate drift compensation with different factors."""
    # Apply a strong tone to create significant drift
    memory_web.compensate_drift(document_id, factor=1.0)  # Reset first
    memory_web.apply_tone_to_document(document_id, "enthusiastic", strength=0.3)
    
    # Get neurons with tone applied
    toned_neurons = memory_web.get_document_neurons(document_id)
    
    # Measure initial drift
    initial_drifts = [neuron.get_drift_magnitude() for neuron in toned_neurons]
    
    # Apply different compensation factors
    compensation_factors = [0.0, 0.25, 0.5, 0.75, 1.0]
    compensation_data = {
        f"factor_{factor}": [] for factor in compensation_factors
    }
    
    # Add initial drift (factor 0.0)
    compensation_data["factor_0.0"] = initial_drifts
    
    # Apply each compensation factor
    for factor in compensation_factors[1:]:  # Skip 0.0 as we already have it
        # Reset to toned state
        memory_web.compensate_drift(document_id, factor=1.0)  # Reset first
        memory_web.apply_tone_to_document(document_id, "enthusiastic", strength=0.3)
        
        # Apply compensation
        memory_web.compensate_drift(document_id, factor=factor)
        
        # Get neurons with compensation applied
        compensated_neurons = memory_web.get_document_neurons(document_id)
        
        # Measure drift
        drifts = [neuron.get_drift_magnitude() for neuron in compensated_neurons]
        compensation_data[f"factor_{factor}"] = drifts
    
    # Visualize the compensation
    visualize_drift_compensation(compensation_data)
    
    # Reset neurons to original state
    memory_web.compensate_drift(document_id, factor=1.0)
    
    return compensation_data

def visualize_drift_compensation(compensation_data):
    """Visualize the effect of different compensation factors."""
    plt.figure(figsize=(12, 6))
    
    # Plot drift for each compensation factor
    for label, drifts in compensation_data.items():
        factor = float(label.split('_')[1])
        chunk_indices = list(range(len(drifts)))
        plt.plot(chunk_indices, drifts, label=f"Compensation Factor: {factor}", marker='o')
    
    plt.title("Drift Compensation Effect by Factor")
    plt.xlabel("Chunk Index")
    plt.ylabel("Remaining Drift Magnitude")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Save the plot
    plt.savefig("/home/ubuntu/nexus_project/drift_compensation_visualization.png")
    print("Saved drift compensation visualization to drift_compensation_visualization.png")

def extract_document_with_tone(document_id, tone_name, strength=0.2):
    """Extract document text with a specific tone applied."""
    # Reset neurons to original state
    memory_web.compensate_drift(document_id, factor=1.0)
    
    # Apply the tone
    memory_web.apply_tone_to_document(document_id, tone_name, strength=strength)
    
    # Get document text
    document_text = memory_web.get_document_text(document_id)
    
    # Reset neurons to original state
    memory_web.compensate_drift(document_id, factor=1.0)
    
    return document_text

def main():
    """Main function to demonstrate the Binary Neuron prototype."""
    print("Binary Neuron Prototype - Document Loading Example")
    print("=" * 50)
    
    # Load sample document
    document_id = load_sample_document()
    
    # Apply tones and visualize drift
    apply_tones_and_visualize(document_id)
    
    # Demonstrate drift compensation
    demonstrate_drift_compensation(document_id)
    
    # Extract document with different tones
    tones = ["enthusiastic", "formal", "skeptical"]
    
    for tone_name in tones:
        # Extract document with tone
        toned_document = extract_document_with_tone(document_id, tone_name)
        
        # Save to file
        output_file = f"/home/ubuntu/nexus_project/nexus_overview_{tone_name}.txt"
        with open(output_file, "w") as f:
            f.write(f"NEXUS Overview with {tone_name.capitalize()} Tone\n")
            f.write("=" * 50 + "\n\n")
            f.write(toned_document)
        
        print(f"Saved document with {tone_name} tone to {output_file}")
    
    print("\nDocument loading example completed successfully!")

if __name__ == "__main__":
    main()
