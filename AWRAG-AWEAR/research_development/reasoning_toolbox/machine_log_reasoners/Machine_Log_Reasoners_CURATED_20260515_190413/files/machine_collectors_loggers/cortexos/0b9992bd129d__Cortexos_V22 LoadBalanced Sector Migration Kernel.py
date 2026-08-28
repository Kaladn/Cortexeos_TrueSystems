# CortexOS Neurogrid V22: Load-Balanced Sector Migration Kernel
import numpy as np
import uuid
import json
import time
import random

class NeurogridV22:
    def __init__(self, cube_size=99):
        self.size = cube_size
        self.grid = np.zeros((cube_size, cube_size, cube_size), dtype=bool)
        self.mapping = {}
        self.snapshots = 0
        self.start_time = time.time()
        self.pressure_threshold = 0.35  # when local sector exceeds 35% capacity, migration triggers
        self.migration_log = []

        print(f"[INIT] Neurogrid V22 booted: {cube_size}³ sectors")

    def allocate_neuron(self):
        neuron_id = str(uuid.uuid4())
        coord = self.find_optimal_location()

        if coord is None:
            print("[FAIL] No available space!")
            return None

        x, y, z = coord
        self.grid[x, y, z] = True
        self.mapping[neuron_id] = (x, y, z)
        self.snapshots += 1
        self.save_snapshot()

        print(f"[ALLOC] Neuron {neuron_id} -> ({x},{y},{z})")

        # Run local sector pressure check after allocation
        self.migration_engine(coord)

        return neuron_id

    def find_optimal_location(self):
        center = self.size // 2
        search_order = [(dx, dy, dz)
                        for dx in range(-center, center)
                        for dy in range(-center, center)
                        for dz in range(-center, center)]
        random.shuffle(search_order)

        for dx, dy, dz in search_order:
            x, y, z = center + dx, center + dy, center + dz
            if (0 <= x < self.size) and (0 <= y < self.size) and (0 <= z < self.size):
                if not self.grid[x, y, z]:
                    return (x, y, z)
        return None

    def migration_engine(self, coord):
        sector_radius = 3  # 3x3x3 block sector scan
        x0, y0, z0 = coord

        xs = slice(max(0, x0 - sector_radius), min(self.size, x0 + sector_radius + 1))
        ys = slice(max(0, y0 - sector_radius), min(self.size, y0 + sector_radius + 1))
        zs = slice(max(0, z0 - sector_radius), min(self.size, z0 + sector_radius + 1))

        sector = self.grid[xs, ys, zs]
        occupancy = np.sum(sector)
        total_blocks = sector.size
        pressure = occupancy / total_blocks

        if pressure >= self.pressure_threshold:
            self.execute_migration(xs, ys, zs)

    def execute_migration(self, xs, ys, zs):
        sector_coords = [
            (x, y, z)
            for x in range(xs.start, xs.stop)
            for y in range(ys.start, ys.stop)
            for z in range(zs.start, zs.stop)
            if self.grid[x, y, z]
        ]

        moves = 0
        for x, y, z in sector_coords:
            target = self.find_sparse_adjacent(x, y, z)
            if target:
                self.grid[x, y, z] = False
                self.grid[target] = True
                neuron_id = self.get_neuron_by_coord((x, y, z))
                self.mapping[neuron_id] = target
                self.migration_log.append((neuron_id, (x, y, z), target))
                moves += 1

        if moves > 0:
            print(f"[MIGRATION] Sector rebalanced with {moves} neuron shifts.")
            self.save_snapshot()

    def find_sparse_adjacent(self, x, y, z):
        offsets = [(i, j, k) for i in [-1, 0, 1]
                              for j in [-1, 0, 1]
                              for k in [-1, 0, 1]
                              if not (i == j == k == 0)]
        random.shuffle(offsets)

        for dx, dy, dz in offsets:
            nx, ny, nz = x + dx, y + dy, z + dz
            if (0 <= nx < self.size) and (0 <= ny < self.size) and (0 <= nz < self.size):
                if not self.grid[nx, ny, nz]:
                    return (nx, ny, nz)
        return None

    def get_neuron_by_coord(self, coord):
        for nid, loc in self.mapping.items():
            if loc == coord:
                return nid
        return None

    def save_snapshot(self):
        self.snapshots += 1
        data = {
            "mapping": self.mapping,
            "migration_log": self.migration_log
        }
        filename = f"snapshot_v22_{self.snapshots}.json"
        with open(filename, "w") as f:
            json.dump(data, f)
        print(f"[SNAPSHOT] {filename} saved.")

    def health_check(self):
        uptime = time.time() - self.start_time
        print(f"[HEALTH] Uptime: {uptime:.2f}s | Total Neurons: {len(self.mapping)}")
        print(f"[HEALTH] Migration events: {len(self.migration_log)}")

# === EXECUTION ===
if __name__ == "__main__":
    cortex = NeurogridV22()

    for _ in range(50):
        cortex.allocate_neuron()

    cortex.health_check()
