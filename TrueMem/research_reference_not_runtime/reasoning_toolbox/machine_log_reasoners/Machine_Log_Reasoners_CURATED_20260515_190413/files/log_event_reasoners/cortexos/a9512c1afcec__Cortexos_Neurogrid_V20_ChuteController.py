import os
import json
import random
import uuid
import time
from collections import defaultdict

class NVMeNeurogridV20:
    def __init__(self, size=99, core_reserve=5):
        self.size = size
        self.center = size // 2
        self.cube = [[[None for _ in range(size)] for _ in range(size)] for _ in range(size)]
        self.rbmt = {}
        self.snapshot_count = 0
        self.start_time = time.time()
        self.core_reserve = core_reserve
        self.chute_zones = self._init_chute_zones()
        print(f"[INIT] Neurogrid V20 booted with cube size {size}³.")

    def _init_chute_zones(self):
        return {
            'UP':    (0, 0, 1),
            'DOWN':  (0, 0, -1),
            'LEFT':  (-1, 0, 0),
            'RIGHT': (1, 0, 0),
            'FRONT': (0, 1, 0),
            'BACK':  (0, -1, 0)
        }

    def is_available(self, x, y, z):
        return 0 <= x < self.size and 0 <= y < self.size and 0 <= z < self.size and self.cube[x][y][z] is None

    def allocate_neuron(self, neuron_id):
        coords = self.predictive_chute_placement()
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

    def predictive_chute_placement(self):
        priorities = self._chute_priority()

        for chute, offset in priorities:
            for radius in range(self.core_reserve, self.size // 2):
                dx, dy, dz = offset
                x = self.center + dx * radius
                y = self.center + dy * radius
                z = self.center + dz * radius

                if self.is_available(x, y, z):
                    return (x, y, z)

                # Predictive tunneling sweep in localized zone
                for sx in range(-1, 2):
                    for sy in range(-1, 2):
                        for sz in range(-1, 2):
                            nx, ny, nz = x+sx, y+sy, z+sz
                            if self.is_available(nx, ny, nz):
                                return (nx, ny, nz)
        return None

    def _chute_priority(self):
        # Smart rotation of chutes to balance sectors dynamically
        chute_loads = defaultdict(int)
        for neuron in self.rbmt.values():
            dx = neuron[0] - self.center
            dy = neuron[1] - self.center
            dz = neuron[2] - self.center
            if abs(dx) > abs(dy) and abs(dx) > abs(dz):
                chute_loads['LEFT' if dx < 0 else 'RIGHT'] += 1
            elif abs(dy) > abs(dz):
                chute_loads['FRONT' if dy > 0 else 'BACK'] += 1
            else:
                chute_loads['UP' if dz > 0 else 'DOWN'] += 1

        chute_order = sorted(self.chute_zones.items(), key=lambda x: chute_loads[x[0]])
        return chute_order

    def snapshot(self):
        self.snapshot_count += 1
        snapshot_file = f"snapshot_v20_{self.snapshot_count}.json"
        with open(snapshot_file, "w") as f:
            json.dump(self.rbmt, f)
        print(f"[SNAPSHOT] {snapshot_file} saved.")

    def export_heatmap(self):
        heatmap = [[[1 if self.cube[x][y][z] else 0 for z in range(self.size)] 
                    for y in range(self.size)] for x in range(self.size)]
        with open("heatmap_v20.json", "w") as f:
            json.dump(heatmap, f)
        print("[EXPORT] Heatmap exported.")

    def health_report(self):
        uptime = time.time() - self.start_time
        print(f"[HEALTH] Uptime: {uptime:.2f}s | Total Neurons: {len(self.rbmt)}")

### --- V20 TEST EXECUTION ---
if __name__ == "__main__":
    cortex = NVMeNeurogridV20()

    for _ in range(50):
        neuron_id = str(uuid.uuid4())
        cortex.allocate_neuron(neuron_id)

    cortex.health_report()
    cortex.export_heatmap()
