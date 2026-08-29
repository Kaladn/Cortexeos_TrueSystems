# test_noninvasive_monitoring.py

import numpy as np
import os
import hashlib

# Assuming these modules are in the same directory or accessible in PYTHONPATH
from cortex_cube_nvme import CortexCubeNVMe
from resonance_field import ResonanceFieldMonitor

# Define a consistent way to get a hash of the cube's data
def get_cube_data_hash(cube_instance):
    """Returns an MD5 hash of the cube's data array."""
    # Ensure data is flushed from memory map to be certain of the state if it were disk-backed
    # For an in-memory numpy array, direct hashing is fine.
    # If cube.data is a memmap, it's already in memory.
    return hashlib.md5(np.ascontiguousarray(cube_instance.cube).tobytes()).hexdigest()

def main():
    print("--- Test: Validating Non-Invasive Monitoring of ResonanceFieldMonitor ---")
    
    # Setup parameters
    cube_filename = "test_noninvasive_cube.dat"
    cube_shape = (16, 16, 16) # Smaller cube for faster testing
    CORTEX_APP_DIR = os.path.dirname(os.path.abspath(__file__))
    cube_filepath = os.path.join(CORTEX_APP_DIR, cube_filename)

    # Ensure a clean slate for the cube file if it exists
    if os.path.exists(cube_filepath):
        os.remove(cube_filepath)
        print(f"Removed existing test cube file: {cube_filepath}")

    # 1. Initialize CortexCubeNVMe instance
    print(f"Initializing CortexCubeNVMe at {cube_filepath} with shape {cube_shape}...")
    cortex_cube = CortexCubeNVMe(cube_filepath, shape=cube_shape)
    
    # Optionally activate a voxel to have some initial state other than all zeros
    cortex_cube.activate_voxel(1, 1, 1, intensity=0.5)
    cortex_cube.flush() # Ensure this initial state is "set"
    print("Activated a test voxel (1,1,1) in the cube.")

    # 2. Get initial state hash of the cube's data
    initial_cube_data_hash = get_cube_data_hash(cortex_cube)
    print(f"Initial Cortex Cube data hash: {initial_cube_data_hash}")

    # 3. Initialize ResonanceFieldMonitor with this cube
    print("Initializing ResonanceFieldMonitor...")
    monitor = ResonanceFieldMonitor(cortex_cube)

    # 4. Call all public methods of ResonanceFieldMonitor
    print("Calling ResonanceFieldMonitor methods...")
    monitor.register_neuron("test_neuron_1", 2, 2, 2)
    print("Called register_neuron.")
    
    monitor.scan_for_phase_clusters()
    print("Called scan_for_phase_clusters.")
    
    monitor.broadcast_resonance("test_neuron_1", {"type": "test_event", "value": 123})
    print("Called broadcast_resonance.")
    
    monitor.query_nearby_resonance(3, 3, 3, radius=2)
    print("Called query_nearby_resonance.")
    
    monitor.visualize_field(z_slice=cube_shape[2] // 2)
    print("Called visualize_field.")

    # 5. Get final state hash of the cube's data
    # Important: Ensure no other operations modified the cube between hash calculations
    final_cube_data_hash = get_cube_data_hash(cortex_cube)
    print(f"Final Cortex Cube data hash: {final_cube_data_hash}")

    # 6. Compare initial and final states
    if initial_cube_data_hash == final_cube_data_hash:
        print("\nSUCCESS: Cortex Cube data remained unchanged after ResonanceFieldMonitor operations.")
        print("Validation of non-invasive monitoring PASSED.")
    else:
        print("\nFAILURE: Cortex Cube data was modified by ResonanceFieldMonitor operations.")
        print("Validation of non-invasive monitoring FAILED.")
        print(f"Initial hash: {initial_cube_data_hash}")
        print(f"Final hash:   {final_cube_data_hash}")

    # Cleanup the test cube file
    if os.path.exists(cube_filepath):
        # cortex_cube.close() # If CortexCubeNVMe had a close method for the memmap
        del cortex_cube # Release the object to allow file deletion on some OS
        try:
            os.remove(cube_filepath)
            print(f"Cleaned up test cube file: {cube_filepath}")
        except Exception as e:
            print(f"Warning: Could not remove test cube file {cube_filepath}: {e}")

if __name__ == "__main__":
    main()

