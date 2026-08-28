import uuid
from ray import Ray # Assuming ray.py is in the same directory or accessible in PYTHONPATH
import math

class FunctionModule:
    def __init__(self, func_id=None, label="", color_band_center=(0, 0, 0),                  color_band_range=0.0, spectrum_type="hue", min_amplitude=0.0,                  phase_preference=0.0, phase_tolerance=0.0, vector_bias_compatibility=None):
        self.func_id = func_id if func_id else str(uuid.uuid4())
        self.label = label
        self.color_band_center = color_band_center # Expected HSV: (H_degrees, S_0_1, V_0_1)
        self.color_band_range = color_band_range  # Degrees of hue match (total width of the band)
        self.spectrum_type = spectrum_type # "hue", "saturation", "brightness" - v1 focuses on "hue"
        self.min_amplitude = min_amplitude
        self.phase_preference = phase_preference
        self.phase_tolerance = phase_tolerance
        self.vector_bias_compatibility = vector_bias_compatibility if vector_bias_compatibility is not None else []

    def resonates(self, ray: Ray) -> bool:
        # 1. Chromatic Match (Focus on Hue for v1.0 as per spec)
        if self.spectrum_type == "hue":
            ray_hue = ray.color[0]
            center_hue = self.color_band_center[0]
            
            # Calculate the shortest angle between hues (0-360 degrees)
            abs_diff = abs(ray_hue - center_hue)
            hue_difference = min(abs_diff, 360 - abs_diff)
            
            # color_band_range is total width, so check if within +/- range/2
            if hue_difference > self.color_band_range / 2:
                return False
        # Future: Add checks for saturation/brightness if spectrum_type indicates

        # 2. Amplitude Threshold Check
        if ray.amplitude < self.min_amplitude:
            return False

        # 3. Phase Compatibility Check
        if abs(ray.phase - self.phase_preference) > self.phase_tolerance:
            return False

        # 4. Vector Bias Alignment Check
        if ray.vector_bias not in self.vector_bias_compatibility:
            return False

        return True

    def __repr__(self):
        return f"FunctionModule(id={self.func_id}, label=\'{self.label}\', color_band_center={self.color_band_center}, range={self.color_band_range})"

if __name__ == '__main__':
    # Example Usage
    # Define a sample Ray (ensure ray.py is accessible)
    # Assuming Ray class is defined in ray.py and takes color as (H,S,V)
    test_ray = Ray(color=(45, 0.8, 0.9), amplitude=0.75, phase=0.5, vector_bias="logical")
    print(f"Test Ray: {test_ray}")

    # Define a sample FunctionModule
    module1 = FunctionModule(
        label="Logic Processor A",
        color_band_center=(50, 0.7, 0.8), # HSV
        color_band_range=20, # Hue range of +/- 10 degrees from center
        min_amplitude=0.5,
        phase_preference=0.4,
        phase_tolerance=0.15,
        vector_bias_compatibility=["logical", "contextual"]
    )
    print(f"Module 1: {module1}")
    print(f"Module 1 resonates with Test Ray: {module1.resonates(test_ray)}") # Expected: True

    module2 = FunctionModule(
        label="Creative Engine X",
        color_band_center=(180, 0.9, 0.95), # HSV - different hue
        color_band_range=30,
        min_amplitude=0.6,
        phase_preference=0.0,
        phase_tolerance=0.1,
        vector_bias_compatibility=["emotional", "creative"]
    )
    print(f"Module 2: {module2}")
    print(f"Module 2 resonates with Test Ray: {module2.resonates(test_ray)}") # Expected: False (hue and bias mismatch)

    # Test hue circularity
    # Ray hue 350, module center 10, range 30 (+/- 15). Should match.
    # Shortest diff between 350 and 10 is 20 (via 360). 20 > 30/2 = 15. So False.
    # Wait, if range is 30, it means it covers 10-15 = 355 to 10+15 = 25. So 350 is outside.
    # Let's test ray_hue = 5, module_center = 355, range = 20 (+/- 10)
    # Shortest diff between 5 and 355 is 10. 10 <= 20/2 = 10. So True.
    ray_circ_test = Ray(color=(5, 0.8, 0.9), amplitude=0.75, phase=0.5, vector_bias="logical") 
    module_circ = FunctionModule(
        label="Circular Hue Test Module",
        color_band_center=(355, 0.7, 0.8),
        color_band_range=20, # Hue range of +/- 10 degrees
        min_amplitude=0.5,
        phase_preference=0.4,
        phase_tolerance=0.15,
        vector_bias_compatibility=["logical"]
    )
    print(f"Circular Test Ray: {ray_circ_test}")
    print(f"Circular Module: {module_circ}")
    print(f"Circular Module resonates: {module_circ.resonates(ray_circ_test)}") # Expected: True

    ray_circ_test_fail = Ray(color=(30, 0.8, 0.9), amplitude=0.75, phase=0.5, vector_bias="logical")
    print(f"Circular Test Ray Fail: {ray_circ_test_fail}")
    print(f"Circular Module resonates (fail case): {module_circ.resonates(ray_circ_test_fail)}") # Expected: False

