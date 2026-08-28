class NeuroMagneticCore:
    """
    A class to simulate the behavior of a neuro-magnetic core, 
    which is a key component in understanding how memories are formed and retrieved.
    This class will be used to store and process information related to neuron activation patterns,
    resonance, and other aspects of memory formation.
    """

    def __init__(self, size_x=10, size_y=10, size_z=10, initial_value_generator=None):
        """
        Initialize the NeuroMagneticCore with specified dimensions and an optional initial value generator.

        Args:
            size_x (int): The size of the x-dimension of the core.
            size_y (int): The size of the y-dimension of the core.
            size_z (int): The size of the z-dimension of the core.
            initial_value_generator (function, optional): A function that takes (x, y, z) coordinates
                                                        and returns an initial value for that point in the core.
                                                        If None, all points are initialized to 0.
        """
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        # Initialize a 3D array (list of lists of lists) for the core memory
        # We are not using numpy here to keep the dependencies minimal for this example.
        # In a real scenario, for performance with large datasets, numpy would be preferred.
        if initial_value_generator:
            self.core = [[[initial_value_generator(x,y,z) for z in range(size_z)] for y in range(size_y)] for x in range(size_x)]
        else:
            self.core = [[[0 for _ in range(size_z)] for _ in range(size_y)] for _ in range(size_x)]

    def get_value(self, x, y, z):
        """
        Retrieve the value at a specific coordinate in the core.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            z (int): The z-coordinate.

        Returns:
            float: The value at the specified coordinate.
        """
        if 0 <= x < self.size_x and 0 <= y < self.size_y and 0 <= z < self.size_z:
            return self.core[x][y][z]
        else:
            raise ValueError("Coordinates are outside the bounds of the core.")

    def set_value(self, x, y, z, value):
        """
        Set the value at a specific coordinate in the core.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            z (int): The z-coordinate.
            value (float): The value to set.
        """
        if 0 <= x < self.size_x and 0 <= y < self.size_y and 0 <= z < self.size_z:
            self.core[x][y][z] = value
        else:
            raise ValueError("Coordinates are outside the bounds of the core.")

    def __str__(self):
        return f"NeuroMagneticCore(size_x={self.size_x}, size_y={self.size_y}, size_z={self.size_z})"

# Example usage (for testing purposes, if this file is run directly):
if __name__ == '__main__':
    # Create a 5x5x5 core
    nmc = NeuroMagneticCore(5,5,5)

    # Set a value at a specific coordinate
    nmc.set_value(2, 2, 2, 10.5)

    # Get the value at that coordinate
    value = nmc.get_value(2, 2, 2)
    print(f"Value at (2,2,2): {value}")

    # Example of iterating and printing values (optional)
    for i in range(nmc.size_x):
        for j in range(nmc.size_y):
            for k in range(nmc.size_z):
                # Check if the value is not zero before printing, to keep output clean for sparse data
                if nmc.core[i][j][k] != 0:
                    print(f"Value at ({i},{j},{k}): {nmc.core[i][j][k]}")

