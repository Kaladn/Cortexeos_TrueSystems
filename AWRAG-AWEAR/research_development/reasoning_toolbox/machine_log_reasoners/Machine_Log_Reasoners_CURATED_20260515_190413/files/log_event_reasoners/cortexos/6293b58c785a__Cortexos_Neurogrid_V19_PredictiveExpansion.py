import os
import json
import random
import uuid
import time

class NVMeCubeStore:
    def __init__(self, size=99):
        self.size = size
        self.center = size // 2
        self.cube = [[[None for _ in range(size)] for _ in range(size)] for _ in range(size)]
        self.rbmt = {}
        self.snapshot_count = 0
        self.start_time = time.time()
        print(f"[INIT] Neurogrid initialized with cube size {size}³.")

    def is_available(self, x, y, z):
        return self.cube[x][y][z] is None

    def allocate_neuron(self, neuron_id):
        coords = self.predictive_placement()
        if coords:
            x, y, z = coords
            self.cube[x][y][z] = neuron_id
            self.rbmt[neuron_id] = (x, y, z)
            self.snapshot()
            print(f"[ALLOC] Neuron {neuron_id} -> ({x}, {y}, {z})")
            return True
        else:
            print("[FAIL] No available slots.")
            return False

    def predictive_placement(self):
        max_offset = self.size // 2
        search_radius = 0

        while search_radius <= max_offset:
            candidates = []
            for dx in range(-search_radius, search_radius + 1):
                for dy in range(-search_radius, search_radius + 1):
                    for dz in range(-search_radius, search_radius + 1):
                        x = self.center + dx
                        y = self.center + dy
                        z = self.center + dz
                        if 0 <= x < self.size and 0 <= y < self.size and 0 <= z < self.size:
                            if self.is_available(x, y, z):
                                candidates.append((x, y, z))
            if candidates:
                return random.choice(candidates)
            search_radius += 1
        return None

    def snapshot(self):
        self.snapshot_count += 1
        snapshot_file = f"snapshot_v19_{self.snapshot_count}.json"
        data = {nid: coords for nid, coords in self.rbmt.items()}
        with open(snapshot_file, "w") as f:
            json.dump(data, f)
        print(f"[SNAPSHOT] Saved {snapshot_file}")

    def export_heatmap(self):
        heatmap = [[[1 if self.cube[x][y][z] else 0 for z in range(self.size)] 
                    for y in range(self.size)] for x in range(self.size)]
        with open("heatmap_v19.json", "w") as f:
            json.dump(heatmap, f)
        print("[EXPORT] Heatmap exported.")

    def health_report(self):
        uptime = time.time() - self.start_time
        print(f"[HEALTH] Uptime: {uptime:.2f}s | Total Neurons: {len(self.rbmt)}")

### --- RUN ENGINE TEST SEQUENCE ---
if __name__ == "__main__":
    cortex = NVMeCubeStore()

    for _ in range(30):  # Add 30 neurons to visualize spread
        neuron_id = str(uuid.uuid4())
        cortex.allocate_neuron(neuron_id)

    cortex.health_report()
    cortex.export_heatmap()
