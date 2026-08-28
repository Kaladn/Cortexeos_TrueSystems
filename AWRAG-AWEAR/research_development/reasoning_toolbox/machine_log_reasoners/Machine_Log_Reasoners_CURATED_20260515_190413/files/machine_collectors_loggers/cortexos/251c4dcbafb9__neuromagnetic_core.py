import json
import os
from collections import defaultdict, deque

class NeuroMagneticCore:
    def __init__(self, cube, mapper, max_history=1000):
        self.cube = cube
        self.mapper = mapper
        self.link_map = defaultdict(dict)  # neuron_id -> {linked_id: strength}
        self.resonance_history = deque(maxlen=max_history)
        self.signal_profiles = {}  # neuron_id -> last known signal profile

    def observe_resonance_event(self, neuron_id, signal_profile):
        """
        Records a resonance event for a neuron, storing the signal profile and updating history.
        signal_profile is expected to be a dict with fields like:
        {
            'intensity': float,
            'timestamp': float,
            'frequency': float,
            'tags': list[str]
        }
        """
        self.signal_profiles[neuron_id] = signal_profile
        self.resonance_history.append((neuron_id, signal_profile))

    def update_links(self):
        """
        Builds or strengthens links between neurons that have appeared in close temporal proximity.
        A simple rule: if two neurons fire within the same short window, increase their mutual link strength.
        """
        coactivation_window = 5  # Number of recent events to consider
        recent_ids = [neuron_id for neuron_id, _ in list(self.resonance_history)[-coactivation_window:]]

        for i, nid1 in enumerate(recent_ids):
            for nid2 in recent_ids[i + 1:]:
                if nid1 == nid2:
                    continue
                self.link_map[nid1][nid2] = self.link_map[nid1].get(nid2, 0.0) + 0.05
                self.link_map[nid2][nid1] = self.link_map[nid2].get(nid1, 0.0) + 0.05

                # Cap strength
                self.link_map[nid1][nid2] = min(self.link_map[nid1][nid2], 1.0)
                self.link_map[nid2][nid1] = min(self.link_map[nid2][nid1], 1.0)

    def activate_links(self, neuron_id, threshold=0.3, flush=False):
        """
        Activates linked neurons with strength above the threshold.
        Each linked neuron's coordinate is resolved and a proportional activation is applied.
        """
        if neuron_id not in self.link_map:
            return

        for linked_id, strength in self.link_map[neuron_id].items():
            if strength >= threshold:
                coords = self.mapper.id_to_coords(linked_id)
                if coords:
                    x, y, z = coords
                    self.cube.activate_voxel(x, y, z, strength)
        if flush:
            self.cube.flush()

    def signal_chaining(self, origin_id, max_hops=3, decay=0.8, threshold=0.3, _visited=None, _depth=0):
        """
        Recursively propagates activation through resonance links.

        Parameters:
        - origin_id (int): The neuron to start propagation from.
        - max_hops (int): Maximum number of hops to chain.
        - decay (float): Strength decay per hop.
        - threshold (float): Minimum strength after decay to trigger activation.
        - _visited (set): Internal set to track visited neurons.
        - _depth (int): Current recursion depth.
        """
        if _visited is None:
            _visited = set()

        if origin_id in _visited or _depth > max_hops:
            return

        _visited.add(origin_id)

        # The intensity for activating the current node in the chain.
        # For the initial origin_id (depth 0), this will be 1.0 (decay**0).
        # This assumes the initial signal has an intensity of 1.0 before any decay.
        current_node_activation_intensity = decay ** _depth

        if current_node_activation_intensity < threshold:
            return

        coords = self.mapper.id_to_coords(origin_id)
        if coords:
            x, y, z = coords
            self.cube.activate_voxel(x, y, z, current_node_activation_intensity)

        if origin_id not in self.link_map:
            return
            
        for linked_id, link_strength in self.link_map[origin_id].items():
            # The intensity propagated to the next node is the current node's activation intensity modulated by the link strength.
            propagated_intensity = current_node_activation_intensity * link_strength 
            
            # Note: The original algorithm sketch was "strength × decay^depth ≥ threshold"
            # where 'strength' was link strength and 'decay^depth' applied to the *next* hop.
            # The current implementation applies decay to the current node's activation, then modulates by link strength.
            # This seems fine, as long as it's consistent. The key is that `propagated_intensity` is what's checked against `threshold` for the *next* step.
            # However, the recursive call does not pass `propagated_intensity`. It passes `decay` which is then used to calculate `decay ** (_depth + 1)`.
            # This means the `propagated_intensity` is effectively `(decay ** _depth) * link_strength` for the *current* link, and the *next* node will be activated with `decay ** (_depth + 1)`.
            # The condition to recurse should be based on whether the *next* node would activate.
            # The intensity for the *next* node (linked_id) if it activates at _depth + 1 would be decay ** (_depth + 1).
            # This should be compared against the threshold. The link_strength acts as a gate or modulator.
            
            # Let's stick to the user's provided code's logic for now:
            # The `current_node_activation_intensity` is what the current node fires with.
            # The signal passed to the next link is this intensity * link_strength.
            # The next node in the chain will then be activated with `decay ** (_depth + 1)` if this propagated signal is strong enough.
            # The `threshold` in the recursive call will be compared against `decay ** (_depth + 1)`.
            # So, the condition `propagated_intensity >= threshold` is to decide if we even bother to recurse.
            
            if propagated_intensity >= threshold: # Check if the signal is strong enough to potentially activate the next node above threshold.
                self.signal_chaining(
                    linked_id,
                    max_hops=max_hops,
                    decay=decay,
                    threshold=threshold,
                    _visited=_visited,
                    _depth=_depth + 1
                )

    def save_state(self, filepath):
        """
        Saves the current resonance link map to disk.
        """
        with open(filepath, 'w') as f:
            json.dump(self.link_map, f)

    def load_state(self, filepath):
        """
        Loads a previously saved link map.
        """
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r') as f:
            self.link_map = json.load(f)

