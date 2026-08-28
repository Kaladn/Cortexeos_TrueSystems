import json
import random
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from neurons.neuron_model import Neuron # Assuming neuron_model.py is in a 'neurons' subdir
from neuromappers.neuromapper_model import Neuromapper # Assuming neuromapper_model.py is in a 'neuromappers' subdir

class CHRM:
    def __init__(self, base_data_path, cube_dimensions=(100, 100, 100)):
        """
        Initializes the Cortex Hyper Resource Manager.

        Args:
            base_data_path (str): The root directory where neuron and neuromapper data will be stored.
            cube_dimensions (tuple): (max_x, max_y, max_z) defining the conceptual size of the cube for coordinate allocation.
        """
        self.base_data_path = base_data_path
        self.neurons_path = os.path.join(base_data_path, "neurons")
        self.neuromappers_path = os.path.join(base_data_path, "neuromappers")
        os.makedirs(self.neurons_path, exist_ok=True)
        os.makedirs(self.neuromappers_path, exist_ok=True)

        self.cube_dimensions = cube_dimensions
        self.occupied_coordinates = set() # To keep track of allocated neuron coordinates (X,Y,Z)
        self.neuron_registry = {} # neuron_id -> { "path": file_path, "coordinates": (x,y,z) }
        self.neuromapper_registry = {} # mapper_id -> { "path": file_path }

        # For a prototype, "free block pool" is simplified to finding an empty coordinate.
        # A more complex system would manage actual file blocks.
        self._load_registries() # Load existing state if any

    def _get_neuron_filepath(self, neuron_id):
        return os.path.join(self.neurons_path, f"{neuron_id}.bin")

    def _get_neuromapper_filepath(self, mapper_id):
        return os.path.join(self.neuromappers_path, f"{mapper_id}.bin")

    def _load_registries(self):
        """Loads registries from a metadata file if it exists."""
        registry_file = os.path.join(self.base_data_path, "chrm_registry.json")
        if os.path.exists(registry_file):
            try:
                with open(registry_file, "r") as f:
                    data = json.load(f)
                    self.neuron_registry = data.get("neuron_registry", {})
                    self.neuromapper_registry = data.get("neuromapper_registry", {})
                    # Populate occupied_coordinates from loaded neuron_registry
                    for neuron_id, meta in self.neuron_registry.items():
                        if "coordinates" in meta:
                            self.occupied_coordinates.add(tuple(meta["coordinates"]))
                # print(f"CHRM registries loaded from {registry_file}")
            except json.JSONDecodeError:
                print(f"Error: Could not decode CHRM registry file: {registry_file}. Starting fresh.")
            except Exception as e:
                print(f"Error loading CHRM registries: {e}. Starting fresh.")
        else:
            # print("No CHRM registry file found. Starting with empty registries.")
            pass 

    def _save_registries(self):
        """Saves the current state of registries to a metadata file."""
        registry_file = os.path.join(self.base_data_path, "chrm_registry.json")
        data = {
            "neuron_registry": self.neuron_registry,
            "neuromapper_registry": self.neuromapper_registry
        }
        with open(registry_file, "w") as f:
            json.dump(data, f, indent=4)
        # print(f"CHRM registries saved to {registry_file}")

    def allocate_neuron_coordinates(self, requested_coord=None):
        """
        Allocates unique (X, Y, Z) coordinates for a new neuron.
        Ensures no direct adjacency (simplified for now - just unique coordinates).
        The spec says "No Two Neurons Ever Touch" - this means neuromappers are in between.
        For allocation, we just need a unique spot for the neuron itself.
        
        Args:
            requested_coord (tuple, optional): A specific coordinate to try to allocate.
        
        Returns:
            tuple: (X, Y, Z) coordinates or None if allocation fails.
        """
        if requested_coord:
            if requested_coord not in self.occupied_coordinates and \
               0 <= requested_coord[0] < self.cube_dimensions[0] and \
               0 <= requested_coord[1] < self.cube_dimensions[1] and \
               0 <= requested_coord[2] < self.cube_dimensions[2]:
                self.occupied_coordinates.add(requested_coord)
                return requested_coord
            else:
                # print(f"Requested coordinate {requested_coord} is occupied or out of bounds.")
                return None # Or try to find a new one

        # Try to find a random unoccupied coordinate
        # For a large cube, this random approach is inefficient. A proper free-list or spatial index is needed.
        # For prototype, this is acceptable for small number of neurons.
        max_attempts = 1000 # Avoid infinite loop for a nearly full cube
        for _ in range(max_attempts):