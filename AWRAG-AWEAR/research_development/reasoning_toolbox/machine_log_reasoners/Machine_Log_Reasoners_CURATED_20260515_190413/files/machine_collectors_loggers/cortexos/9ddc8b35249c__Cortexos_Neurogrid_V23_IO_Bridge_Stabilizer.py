import numpy as np
import uuid
import json
import os
import time

# Parameters
CUBE_SIZE = 99
BLOCK_SIZE = 4096  # 4K per neuron
NVME_FILE = "nvme_bridge_v23.dat"

class NVMeIOBridge:
    def __init__(self, filename, total_blocks):
        self.filename = filename
        self.total_blocks = total_blocks
        self._init_file()

    def _init_file(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "wb") as f:
                f.truncate(self.total_blocks * BLOCK_SIZE)
            print(f"[NVME BRIDGE] Created new simulated NVMe file: {self.filename}")
        else:
            print(f"[NVME BRIDGE] Using existing NVMe file: {self.filename}")

    def write_block(self, block_index, data_bytes):
        with open(self.filename, "r+b") as f:
            f.seek(block_index * BLOCK_SIZE)
            padded = data_bytes.ljust(BLOCK_SIZE, b'\x00')
            f.write(padded)

    def read_block(self, block_index):
        with open(self.filename, "rb") as f:
            f.seek(block_index * BLOCK_SIZE)
            return f.read(BLOCK_SIZE)

class NeurogridV23:
    def __init__(self):
        self.cube = np.zeros((CUBE_SIZE, CUBE_SIZE, CUBE_SIZE), dtype=bool)
        self.rbmt = {}
        self.block_counter = 0
        self.io_bridge = NVMeIOBridge(NVME_FILE, total_blocks=CUBE_SIZE**3)
        self.start_time = time.time()
        print(f"[INIT] Neurogrid V23 booted with cube size {CUBE_SIZE}³.")

    def save_snapshot(self):
        snap = {
            "rbmt": self.rbmt,
            "block_counter": self.block_counter
        }
        snap_file = f"snapshot_v23_{len(self.rbmt)}.json"
        with open(snap_file, "w") as f:
            json.dump(snap, f)
        print(f"[SNAPSHOT] {snap_file} saved.")

    def allocate_neuron(self, data_bytes):
        coords = self._find_next_slot()
        if coords is None:
            print("[ERROR] Cube full!")
            return

        neuron_id = str(uuid.uuid4())
        self.cube[coords] = True
        self.rbmt[neuron_id] = {"coords": coords, "block": self.block_counter}

        self.io_bridge.write_block(self.block_counter, data_bytes)
        print(f"[ALLOC] Neuron {neuron_id} -> {coords} (block {self.block_counter})")
        self.block_counter += 1
        self.save_snapshot()

    def _find_next_slot(self):
        for offset in range(CUBE_SIZE//2):
            candidates = [
                (CUBE_SIZE//2 + dx, CUBE_SIZE//2 + dy, CUBE_SIZE//2 + dz)
                for dx in (-offset, offset)
                for dy in (-offset, offset)
                for dz in (-offset, offset)
                if 0 <= CUBE_SIZE//2 + dx < CUBE_SIZE and
                   0 <= CUBE_SIZE//2 + dy < CUBE_SIZE and
                   0 <= CUBE_SIZE//2 + dz < CUBE_SIZE
            ]
            for coord in candidates:
                if not self.cube[coord]:
                    return coord
        return None

    def health_check(self):
        uptime = time.time() - self.start_time
        print(f"[HEALTH] Uptime: {uptime:.2f}s | Neurons: {len(self.rbmt)}")
        print(f"[RBMT] Total occupied blocks: {self.block_counter}")

if __name__ == "__main__":
    grid = NeurogridV23()
    for _ in range(30):  # simulate 30 allocations
        data = b"NeuronPacketV23" * 100
        grid.allocate_neuron(data)
    grid.health_check()
