"""
Swarm Resonance module for CortexOS.
Enables collective resonance for neural agents, prioritizing swarm patterns with mood-driven and phase-aware coordination.
"""

from topk_sparse_resonance import assess_resonance, cosine_similarity
from neuromodulation import Neuromodulator
from phase_harmonics import PhaseHarmonics

class SwarmResonance:
    """
    Manages swarm-based resonance for CortexOS neural agents.
    Uses mood-driven and phase-aware resonance to simulate collective behavior (e.g., flocking, exploration).
    """
    def __init__(self):
        self.neuromod = Neuromodulator()
        self.phase_harmonics = PhaseHarmonics()

    def assess_swarm_resonance(self, agent_vectors, voxel_field, mood="curious", time_step=0, swarm_threshold=0.65):
        """
        Perform swarm-based resonance across neural agents.
        
        Args:
            agent_vectors (list): List of harmonic vectors for agents [[R, G, B, intensity, freq1, freq2], ...]
            voxel_field (dict): {voxel_id: (harmonic_vector, time_step), ...}
            mood (str): Mood state (e.g., 'curious', 'playful', 'imaginative')
            time_step (int): Current time step for phase harmonics
            swarm_threshold (float): Minimum collective similarity for swarm resonance
        
        Returns:
            swarm_matches (list): [(voxel_id, collective_similarity, collective_strength), ...]
            swarm_log (dict): Log of agent activations, collective similarities, and time steps
        """
        params = self.neuromod.adjust_resonance_params(mood)
        k, threshold, decay, phase_step, base_frequency = (
            params["k"],
            params["threshold"],
            params["decay"],
            params["phase_step"],
            params["base_frequency"]
        )
        
        self.phase_harmonics.phase_step = phase_step
        self.phase_harmonics.base_frequency = base_frequency
        
        swarm_matches = []
        swarm_log = {"agent_activations": [], "collective_similarities": [], "time_steps": []}
        
        # Individual agent resonance
        agent_results = []
        for agent_vector in agent_vectors:
            phased_vector = self.phase_harmonics.add_phase_offset(agent_vector, time_step)
            top_k_matches, resonance_log = assess_resonance(
                phased_vector, voxel_field, mood, time_step
            )
            agent_results.append((top_k_matches, resonance_log))
            swarm_log["agent_activations"].append(resonance_log["activations"])
        
        # Compute collective resonance
        voxel_scores = {}
        for top_k_matches, _ in agent_results:
            for voxel_id, similarity in top_k_matches:
                if voxel_id not in voxel_scores:
                    voxel_scores[voxel_id] = []
                voxel_scores[voxel_id].append(similarity)
        
        # Aggregate collective similarities
        for voxel_id, similarities in voxel_scores.items():
            collective_similarity = sum(similarities) / len(similarities) # Average similarity
            if collective_similarity >= swarm_threshold:
                collective_strength = collective_similarity ** 2
                swarm_matches.append((voxel_id, collective_similarity, collective_strength))
                swarm_log["collective_similarities"].append({
                    "voxel_id": voxel_id,
                    "collective_similarity": collective_similarity,
                    "collective_strength": collective_strength,
                    "phase_step": phase_step
                })
                
        return swarm_matches, swarm_log
