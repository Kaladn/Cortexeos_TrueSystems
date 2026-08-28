# CortexOS V14.1 Recovery Kernel Patch — Full Data Chunks Logging
import os
import uuid
import time

BLOCK_SIZE = 4096

# Safe Mock NVMe BlockStore with full data logging
class NVMeBlockStore:
    def __init__(self, total_blocks=1000000):
        self.total_blocks = total_blocks
        self.blocks = [None] * total_blocks
        self.alloc_map = {}
        self.recovery_log = []
        print(f"[NVME INIT] Mock NVMe with {total_blocks} blocks.")

    def allocate_neuron(self, neuron_id, data_bytes):
        required_blocks = (len(data_bytes) + BLOCK_SIZE - 1) // BLOCK_SIZE
        allocated = []
        chunks = []

        for i in range(self.total_blocks):
            if len(allocated) == required_blocks:
                break
            if self.blocks[i] is None:
                chunk = data_bytes[len(allocated)*BLOCK_SIZE:(len(allocated)+1)*BLOCK_SIZE]
                self.blocks[i] = chunk
                allocated.append(i)
                chunks.append(chunk)

        if len(allocated) != required_blocks:
            raise Exception("Insufficient NVMe space.")

        self.alloc_map[neuron_id] = allocated
        self.recovery_log.append({
            "neuron_id": neuron_id,
            "blocks": allocated,
            "data_chunks": [chunk.hex() for chunk in chunks]  # fully capture data for recovery
        })
        print(f"[ALLOC] Neuron {neuron_id} -> {allocated}")

    def read_neuron(self, neuron_id):
        blocks = self.alloc_map.get(neuron_id, [])
        data = b''.join(self.blocks[blk] for blk in blocks)
        return data

    def audit(self):
        print("[RBMT AUDIT]")
        for nid, blks in self.alloc_map.items():
            print(f" - {nid}: {blks}")

    def save_recovery_log(self, path):
        import json
        with open(path, "w") as f:
            json.dump(self.recovery_log, f)
        print(f"[LOG SAVED] {path}")

    def load_recovery_log(self, path):
        import json
        with open(path, "r") as f:
            self.recovery_log = json.load(f)
        print(f"[LOG LOADED] {path}")

    def recover_from_log(self):
        for entry in self.recovery_log:
            neuron_id = entry['neuron_id']
            blocks = entry['blocks']
            data_chunks = [bytes.fromhex(c) for c in entry['data_chunks']]
            self.alloc_map[neuron_id] = blocks
            for blk, chunk in zip(blocks, data_chunks):
                self.blocks[blk] = chunk
            print(f"[RECOVERED] Neuron {neuron_id} -> {blocks}")

# Cortex Kernel
class CortexKernelRecovery:
    def __init__(self, log_path=None):
        self.nvme = NVMeBlockStore()
        self.start_time = time.time()
        if log_path and os.path.exists(log_path):
            self.nvme.load_recovery_log(log_path)
            self.nvme.recover_from_log()

    def create_neuron(self, data_bytes):
        neuron_id = str(uuid.uuid4())
        self.nvme.allocate_neuron(neuron_id, data_bytes)
        return neuron_id

    def read_neuron(self, neuron_id):
        return self.nvme.read_neuron(neuron_id)

    def health_check(self):
        uptime = time.time() - self.start_time
        print(f"[HEALTH] Uptime: {uptime:.2f}s | Neurons: {len(self.nvme.alloc_map)}")
        self.nvme.audit()

# Boot test
if __name__ == "__main__":
    LOG_PATH = "nvme_recovery_v14.json"

    cortex = CortexKernelRecovery(log_path=LOG_PATH)

    if not cortex.nvme.alloc_map:
        sample_data = b"Active Cortex Kernel Memory Block - V14.1" * 100
        nid = cortex.create_neuron(sample_data)
        cortex.nvme.save_recovery_log(LOG_PATH)
        recovered = cortex.read_neuron(nid)
        print(f"[VERIFY] {sample_data == recovered}")
    else:
        cortex.health_check()

    print("[SAFE SHUTDOWN]")
