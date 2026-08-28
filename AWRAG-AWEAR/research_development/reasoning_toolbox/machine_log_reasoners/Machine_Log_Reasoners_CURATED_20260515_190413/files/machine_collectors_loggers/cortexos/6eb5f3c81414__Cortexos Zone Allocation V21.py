import numpy as np
import uuid
import json
import os
import time

# Neurogrid specs
CUBE_SIZE = 99
PADDING = 1  # 1-layer padding per face

# Cortex Padding Zone Roles
PADDING_ZONE_ROLES = {
    "front": "broadcast",
    "back": "receive",
    "left": "chord_link",
    "right": "context_mod",
    "top": "system_trigger",
    "bottom": "decay_sink",
}

# Initialize neurogrid
class Neurogrid:
    def __init__(self, size):
        self.size = size
        self.grid = np.full((size, size, size), None)
        self.rbmt = {}
        self.snapshots = 0
        self.start_time = time.time()
        print(f"[INIT] Neurogrid Zone-Aware V21.5 booted: {size}³")

    def is_zone_available(self, x, y, z):
        # Check if center block is free
        if self.grid[x, y, z] is not None:
            return False
        # Check all 6 face zones
        face_offsets = {
            "front": (0, 0, 1),
            "back":  (0, 0, -1),
            "left":  (-1, 0, 0),
            "right": (1, 0, 0),
            "top":   (0, 1, 0),
            "bottom":(0, -1, 0),
        }
        for role, (dx, dy, dz) in face_offsets.items():
            nx, ny, nz = x+dx, y+dy, z+dz
            if not (0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size):
                return False  # don't allow boundary neurons without full padding
            if self.grid[nx, ny, nz] is not None:
                return False
        return True

    def allocate_neuron(self):
        center = self.size // 2
        search_radius = 0
        while search_radius < (self.size // 2):
            for dx in range(-search_radius, search_radius+1):
                for dy in range(-search_radius, search_radius+1):
                    for dz in range(-search_radius, search_radius+1):
                        x, y, z = center+dx, center+dy, center+dz
                        if not (0 <= x < self.size and 0 <= y < self.size and 0 <= z < self.size):
                            continue
                        if self.is_zone_available(x, y, z):
                            neuron_id = str(uuid.uuid4())
                            self.grid[x, y, z] = neuron_id
                            self.reserve_padding_zones(x, y, z, neuron_id)
                            self.rbmt[neuron_id] = (x, y, z)
                            self.save_snapshot()
                            print(f"[ALLOC] Neuron {neuron_id} -> ({x},{y},{z})")
                            return
            search_radius += 1
        print("[ERROR] No valid allocation position found.")

    def reserve_padding_zones(self, x, y, z, neuron_id):
        face_offsets = {
            "front": (0, 0, 1),
            "back":  (0, 0, -1),
            "left":  (-1, 0, 0),
            "right": (1, 0, 0),
            "top":   (0, 1, 0),
            "bottom":(0, -1, 0),
        }
        for role, (dx, dy, dz) in face_offsets.items():
            nx, ny, nz = x+dx, y+dy, z+dz
            if 0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.size:
                self.grid[nx, ny, nz] = f"{neuron_id}:{role}"

    def save_snapshot(self):
        self.snapshots += 1
        filename = f"snapshot_v21_5_{self.snapshots}.json"
        with open(filename, "w") as f:
            json.dump(self.rbmt, f)
        print(f"[SNAPSHOT] {filename} saved.")

    def export_heatmap(self):
        occupied = sum(v is not None for v in self.grid.flatten())
        print(f"[EXPORT] Heatmap: {occupied} blocks occupied.")

    def health_check(self):
        uptime = time.time() - self.start_time
        print(f"[HEALTH] Uptime: {uptime:.2f}s | Total Neurons: {len(self.rbmt)}")


# === LIVE TEST ===
if __name__ == '__main__':
    cortex = Neurogrid(CUBE_SIZE)

    for _ in range(30):
        cortex.allocate_neuron()

    cortex.health_check()
    cortex.export_heatmap()
