"""
Swarm Resonance module for CortexOS Temporal Cognition v2.1.
Enables collective resonance for neural agents, prioritizing swarm patterns with mood-driven and phase-aware coordination.
Fully compliant with Agharmonic Law for resonance stability and coherence.
"""
logger = logging.getLogger(__name__)
# [NOTE] Class 'SwarmResonance' structure visible, implementation withheld
class SwarmResonance:
    """
    Manages swarm-based resonance for CortexOS neural agents.
    Uses mood-driven and phase-aware resonance to simulate collective behavior (e.g., flocking, exploration).
    Implements all Agharmonic Law interfaces for system-wide resonance stability.
    """
    def __init__(self):
        self.neuromod = Neuromodulator()
        self.phase_harmonics = PhaseHarmonics()
        self.sync_manager = GlobalSyncManager.get_instance()
        # Agharmonic compliance parameters
        self.input_frequency_range = [0.7, 1.5]
        self.output_phase_alignment = 0.0
        self.resonance_threshold = 0.85
        self.last_sync = datetime.utcnow()
        self.stability_metrics = {
            "collective_coherence": 0.0,
            "phase_stability": 0.0,
            "swarm_density": 0.0,
            "resonance_strength": 0.0
        }
        self.fallback_levels = ["normal", "reduced_swarm", "minimal_agents", "emergency"]
        self.current_fallback_level = "normal"
        self.resonance_chain_status = "stable"
        self.experience_buffer = []
        self.max_buffer_size = 1000
        logger.info("SwarmResonance initialized with Agharmonic Law compliance")
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for resonance with other modules.
        Returns:
            dict: Harmonic signature parameters for frequency compatibility
        """
        return {
            "module": "swarm_resonance",
            "input_frequency_range": self.input_frequency_range,
            "output_phase_alignment": self.output_phase_alignment,
            "resonance_threshold": self.resonance_threshold,
            "timestamp": datetime.utcnow().isoformat()
        }
    def interface_contract(self, agent_vectors, voxel_field, mood="curious", time_step=0, swarm_threshold=0.65):
        """
        Validates input parameters against expected contract.
        Args:
            agent_vectors (list): List of harmonic vectors for agents
            voxel_field (dict): Voxel field data
            mood (str): Mood state
            time_step (int): Current time step
            swarm_threshold (float): Minimum collective similarity
        Returns:
            bool: True if contract is valid, raises exception otherwise
        """
        # Validate agent_vectors
        if not isinstance(agent_vectors, list) or len(agent_vectors) == 0:
            raise ValueError("agent_vectors must be a non-empty list")
        for agent in agent_vectors:
            if not isinstance(agent, list) or len(agent) < 6:
                raise ValueError("Each agent vector must be a list with at least 6 elements [R,G,B,intensity,freq1,freq2]")
        # Validate voxel_field
        if not isinstance(voxel_field, dict) or len(voxel_field) == 0:
            raise ValueError("voxel_field must be a non-empty dictionary")
        # Validate mood
        valid_moods = ["curious", "playful", "imaginative", "focused", "exploratory"]
        if mood not in valid_moods:
            logger.warning(f"Mood '{mood}' not in standard set {valid_moods}, using default parameters")
        # Validate time_step
        if not isinstance(time_step, (int, float)) or time_step < 0:
            raise ValueError("time_step must be a non-negative number")
        # Validate swarm_threshold
        if not isinstance(swarm_threshold, float) or not (0.0 <= swarm_threshold <= 1.0):
            raise ValueError("swarm_threshold must be a float between 0.0 and 1.0")
        return True
    def cognitive_energy_flow(self, collective_similarities):
        """
        Normalizes signal amplitude and information flow for resonance patterns.
        Args:
            collective_similarities (list): List of collective similarity scores
        Returns:
            dict: Normalized energy metrics
        """
        if not collective_similarities:
            return {
                "mean_energy": 0.0,
                "peak_energy": 0.0,
                "energy_distribution": [],
                "energy_coherence": 0.0
            }
        # Normalize similarities to energy values (0.0-1.0)
        energies = [min(max(sim, 0.0), 1.0) for sim in collective_similarities]
        # Calculate energy metrics
        mean_energy = sum(energies) / len(energies) if energies else 0.0
        peak_energy = max(energies) if energies else 0.0
        # Calculate energy distribution (histogram)
        bins = np.linspace(0, 1, 10)
        hist, _ = np.histogram(energies, bins=bins, density=True)
        energy_distribution = hist.tolist()
        # Calculate energy coherence (inverse of standard deviation)
        std_dev = np.std(energies) if len(energies) > 1 else 0.0
        energy_coherence = 1.0 - min(std_dev, 1.0)
        return {
            "mean_energy": mean_energy,
            "peak_energy": peak_energy,
            "energy_distribution": energy_distribution,
            "energy_coherence": energy_coherence
        }
    def sync_clock(self):
        """
        Connects to the master temporal framework for synchronization.
        Returns:
            bool: True if sync is needed, False otherwise
        """
        current_time = datetime.utcnow()
        time_delta = (current_time - self.last_sync).total_seconds()
        # Get sync policy from GlobalSyncManager
        sync_policy = self.sync_manager.get_sync_policy("swarm_resonance")
        sync_interval = sync_policy.get("sync_interval", 5.0)  # Default 5 seconds
        # Check if sync is needed
        if time_delta >= sync_interval:
            self.last_sync = current_time
            logger.debug(f"SwarmResonance sync triggered after {time_delta:.2f}s")
            return True
        return False
    def self_regulate(self, swarm_log):
        """
        Implements feedback loops for stability and performance optimization.
        Args:
            swarm_log (dict): Log of swarm activity
        Returns:
            dict: Updated stability metrics
        """
        # Extract metrics from swarm_log
        agent_activations = swarm_log.get("agent_activations", [])
        collective_similarities = [
            item.get("collective_similarity", 0.0) 
            for item in swarm_log.get("collective_similarities", [])
        ]
        # Calculate stability metrics
        num_agents = len(agent_activations)
        if num_agents == 0 or not collective_similarities:
            # No data to regulate
            return self.stability_metrics
        # Calculate collective coherence (agreement between agents)
        activation_matrix = []
        for activations in agent_activations:
            if activations:
                activation_matrix.append(activations)
        if activation_matrix:
            # Calculate pairwise correlations between agent activations
            correlations = []
            for i in range(len(activation_matrix)):
                for j in range(i+1, len(activation_matrix)):
                    if activation_matrix[i] and activation_matrix[j]:
                        corr = np.corrcoef(activation_matrix[i], activation_matrix[j])[0, 1]
                        if not np.isnan(corr):
                            correlations.append(corr)
            collective_coherence = np.mean(correlations) if correlations else 0.0
        else:
            collective_coherence = 0.0
        # Calculate phase stability from phase steps
        phase_steps = [
            item.get("phase_step", 0.0) 
            for item in swarm_log.get("collective_similarities", [])
        ]
        phase_stability = 1.0 - (np.std(phase_steps) / np.pi if phase_steps else 0.0)
        # Calculate swarm density (proportion of agents that agree)
        swarm_density = len(collective_similarities) / max(num_agents, 1)
        # Calculate resonance strength (average collective similarity)
        resonance_strength = np.mean(collective_similarities) if collective_similarities else 0.0
        # Update stability metrics
        self.stability_metrics = {
            "collective_coherence": collective_coherence,
            "phase_stability": phase_stability,
            "swarm_density": swarm_density,
            "resonance_strength": resonance_strength
        }
        # Store experience for adaptive learning
        if len(self.experience_buffer) >= self.max_buffer_size:
            self.experience_buffer = self.experience_buffer[-(self.max_buffer_size // 2):]
        self.experience_buffer.append({
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self.stability_metrics,
            "num_agents": num_agents,
            "num_similarities": len(collective_similarities)
        })
        # Log stability status
        logger.info(f"SwarmResonance stability metrics: {json.dumps(self.stability_metrics)}")
        return self.stability_metrics
    def graceful_fallback(self, error_type=None, severity=0.5):
        """
        Provides mechanisms for partial operation during degraded conditions.
        Args:
            error_type (str): Type of error or degradation
            severity (float): Severity level from 0.0 to 1.0
        Returns:
            dict: Fallback configuration
        """
        # Determine fallback level based on severity
        if severity >= 0.9:
            fallback_level = "emergency"
        elif severity >= 0.7:
            fallback_level = "minimal_agents"
        elif severity >= 0.4:
            fallback_level = "reduced_swarm"
        else:
            fallback_level = "normal"
        self.current_fallback_level = fallback_level
        # Define fallback configurations
        fallback_configs = {
            "normal": {
                "max_agents": 100,
                "swarm_threshold": 0.65,
                "use_phase_harmonics": True,
                "use_neuromodulation": True
            },
            "reduced_swarm": {
                "max_agents": 50,
                "swarm_threshold": 0.7,
                "use_phase_harmonics": True,
                "use_neuromodulation": True
            },
            "minimal_agents": {
                "max_agents": 10,
                "swarm_threshold": 0.8,
                "use_phase_harmonics": False,
                "use_neuromodulation": True
            },
            "emergency": {
                "max_agents": 3,
                "swarm_threshold": 0.9,
                "use_phase_harmonics": False,
                "use_neuromodulation": False
            }
        }
        # Log fallback activation
        if fallback_level != "normal":
            logger.warning(f"SwarmResonance activating fallback level: {fallback_level}, error: {error_type}, severity: {severity}")
        return fallback_configs[fallback_level]
    def resonance_chain_validator(self, resonance_chain):
        """
        Verifies resonance integrity across the chain of modules.
        Args:
            resonance_chain (list): Chain of resonance modules and their states
        Returns:
            dict: Validation results
        """
        # Default validation result
        validation = {
            "valid": True,
            "issues": [],
            "chain_coherence": 1.0,
            "phase_alignment": 1.0
        }
        if not resonance_chain:
            validation["valid"] = False
            validation["issues"].append("Empty resonance chain")
            validation["chain_coherence"] = 0.0
            validation["phase_alignment"] = 0.0
            return validation
        # Check for required modules in the chain
        required_modules = ["neuroengine", "resonance_field", "phase_harmonics"]
        chain_modules = [module.get("name") for module in resonance_chain]
        for module in required_modules:
            if module not in chain_modules:
                validation["valid"] = False
                validation["issues"].append(f"Missing required module: {module}")
        # Check phase alignment across chain
        phase_alignments = [
            module.get("phase_alignment", 0.0) for module in resonance_chain
        ]
        phase_variance = np.var(phase_alignments) if phase_alignments else 0.0
        phase_alignment_score = np.exp(-phase_variance * 10)  # Exponential decay with variance
        # Check frequency compatibility across chain
        frequency_ranges = [
            module.get("frequency_range", [0, 0]) for module in resonance_chain
        ]
        # Check for frequency range overlaps
        frequency_compatibility = 1.0
        if len(frequency_ranges) > 1:
            compatibility_scores = []
            for i in range(len(frequency_ranges)):
                for j in range(i+1, len(frequency_ranges)):
                    min1, max1 = frequency_ranges[i]
                    min2, max2 = frequency_ranges[j]
                    # Calculate overlap
                    overlap_min = max(min1, min2)
                    overlap_max = min(max1, max2)
                    if overlap_max > overlap_min:
                        # Ranges overlap
                        overlap_size = overlap_max - overlap_min
                        range1_size = max1 - min1
                        range2_size = max2 - min2
                        # Normalize overlap to the smaller range
                        compatibility = overlap_size / min(range1_size, range2_size)
                        compatibility_scores.append(compatibility)
                    else:
                        # No overlap
                        compatibility_scores.append(0.0)
            frequency_compatibility = np.mean(compatibility_scores) if compatibility_scores else 0.0
        # Calculate overall chain coherence
        chain_coherence = (frequency_compatibility + phase_alignment_score) / 2.0
        # Update validation results
        validation["chain_coherence"] = chain_coherence
        validation["phase_alignment"] = phase_alignment_score
        if chain_coherence < 0.6:
            validation["valid"] = False
            validation["issues"].append(f"Low chain coherence: {chain_coherence:.2f}")
        # Update resonance chain status
        self.resonance_chain_status = "stable" if validation["valid"] else "unstable"
        return validation
    def assess_swarm_resonance(self, agent_vectors, voxel_field, mood="curious", time_step=0, swarm_threshold=0.65):
        """
        Perform swarm-based resonance across neural agents with Agharmonic Law compliance.
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
        try:
            # Validate inputs through interface contract
            self.interface_contract(agent_vectors, voxel_field, mood, time_step, swarm_threshold)
            # Check for fallback conditions
            fallback_config = None
            if self.stability_metrics["collective_coherence"] < 0.3 or self.stability_metrics["phase_stability"] < 0.3:
                severity = 1.0 - min(self.stability_metrics["collective_coherence"], self.stability_metrics["phase_stability"])
                fallback_config = self.graceful_fallback("low_stability", severity)
            # Apply fallback configuration if needed
            if fallback_config:
                # Limit number of agents
                agent_vectors = agent_vectors[:fallback_config["max_agents"]]
                # Update threshold
                swarm_threshold = fallback_config["swarm_threshold"]
            # Get neuromodulation parameters
            params = self.neuromod.adjust_resonance_params(mood)
            k, threshold, decay, phase_step, base_frequency = (
                params["k"],
                params["threshold"],
                params["decay"],
                params["phase_step"],
                params["base_frequency"]
            )
            # Apply phase harmonics if not in fallback or if fallback allows
            if not fallback_config or fallback_config.get("use_phase_harmonics", True):
                self.phase_harmonics.phase_step = phase_step
                self.phase_harmonics.base_frequency = base_frequency
            swarm_matches = []
            swarm_log = {"agent_activations": [], "collective_similarities": [], "time_steps": []}
            # Individual agent resonance
            agent_results = []
            for agent_vector in agent_vectors:
                # Apply phase offset if not in fallback or if fallback allows
                if not fallback_config or fallback_config.get("use_phase_harmonics", True):
                    phased_vector = self.phase_harmonics.add_phase_offset(agent_vector, time_step)
                else:
                    phased_vector = agent_vector
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
            collective_similarities = []
            for voxel_id, similarities in voxel_scores.items():
                collective_similarity = sum(similarities) / len(similarities) # Average similarity
                collective_similarities.append(collective_similarity)
                if collective_similarity >= swarm_threshold:
                    collective_strength = collective_similarity ** 2
                    swarm_matches.append((voxel_id, collective_similarity, collective_strength))
                    swarm_log["collective_similarities"].append({
                        "voxel_id": voxel_id,
                        "collective_similarity": collective_similarity,
                        "collective_strength": collective_strength,
                        "phase_step": phase_step
                    })
            # Add time step to log
            swarm_log["time_steps"].append(time_step)
            # Apply cognitive energy flow normalization
            energy_metrics = self.cognitive_energy_flow(collective_similarities)
            swarm_log["energy_metrics"] = energy_metrics
            # Self-regulate based on swarm log
            self.self_regulate(swarm_log)
            # Check if sync is needed
            if self.sync_clock():
                # Perform synchronization tasks
                logger.debug("SwarmResonance performing sync tasks")
                # Validate resonance chain if we have data
                if len(self.experience_buffer) > 0:
                    # Construct a simple resonance chain for validation
                    resonance_chain = [
                        {
                            "name": "swarm_resonance",
                            "phase_alignment": self.output_phase_alignment,
                            "frequency_range": self.input_frequency_range
                        },
                        {
                            "name": "neuroengine",
                            "phase_alignment": 0.0,
                            "frequency_range": [0.8, 1.5]
                        },
                        {
                            "name": "resonance_field",
                            "phase_alignment": 0.15,
                            "frequency_range": [0.6, 1.4]
                        },
                        {
                            "name": "phase_harmonics",
                            "phase_alignment": 0.05,
                            "frequency_range": [0.7, 1.3]
                        }
                    ]
                    validation_results = self.resonance_chain_validator(resonance_chain)
                    swarm_log["resonance_validation"] = validation_results
            return swarm_matches, swarm_log
        except Exception as e:
            logger.error(f"SwarmResonance error: {str(e)}")
            # Activate emergency fallback
            fallback_config = self.graceful_fallback("exception", 0.9)
            # Return minimal results
            return [], {"agent_activations": [], "collective_similarities": [], "time_steps": [time_step], "error": str(e)}