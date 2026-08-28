# CortexOS Neurogrid V26 - Physical Drive Binder (Prototype Scaffold)
import os
import json
import uuid
import ctypes
import platform
from ctypes import wintypes

# -------------------------------
# Device Identifier (Samsung 990 Pro)
# -------------------------------
NVME_DEVICE_SIGNATURE = "Samsung_SSD_990"

# -------------------------------
# Windows NVMe Disk Identification (Prototype)
# -------------------------------
class PhysicalDriveBinder:
    def __init__(self):
        self.device_path = self.locate_nvme_device()

    def locate_nvme_device(self):
        drives = self.get_physical_drives()
        for drive in drives:
            if NVME_DEVICE_SIGNATURE in drive:
                print(f"[NVME FOUND] {drive}")
                return drive
        print("[NVME NOT FOUND] Using simulated path.")
        return "SIMULATION_MODE"

    def get_physical_drives(self):
        devices = []
        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_string_buffer(10000)
        size = wintypes.DWORD()

        query = kernel32.QueryDosDeviceA(None, buffer, len(buffer))
        if query != 0:
            result = buffer.raw[:query].split(b'\x00')
            for item in result:
                if item:
                    devices.append(item.decode())
        return devices

# -------------------------------
# Neurogrid Allocation (Safe Test Mode)
# -------------------------------
class NeurogridV26:
    def __init__(self, binder):
        self.binder = binder
        self.grid_size = 99
        self.ledger_file = "v26_ledger.json"
        self.ledger = self.load_or_init_ledger()
        print(f"[INIT] Neurogrid V26 initialized.")

    def load_or_init_ledger(self):
        if os.path.exists(self.ledger_file):
            with open(self.ledger_file, 'r') as f:
                return json.load(f)
        return {"neurons": []}

    def allocate_neuron(self):
        neuron_id = str(uuid.uuid4())
        coord = self.get_next_available_coord()
        self.ledger["neurons"].append({"id": neuron_id, "coord": coord})
        self.save_ledger()
        print(f"[ALLOC] Neuron {neuron_id} -> {coord}")

    def save_ledger(self):
        with open(self.ledger_file, 'w') as f:
            json.dump(self.ledger, f, indent=4)

    def get_next_available_coord(self):
        used = {tuple(n["coord"]) for n in self.ledger["neurons"]}
        for x in range(47, 52):
            for y in range(47, 52):
                for z in range(47, 52):
                    if (x, y, z) not in used:
                        return [x, y, z]
        raise RuntimeError("Neurogrid full (prototype range)")

    def health_check(self):
        print(f"[HEALTH] Neurons allocated: {len(self.ledger['neurons'])}")

# -------------------------------
# LAUNCH V26
# -------------------------------
if __name__ == '__main__':
    if platform.system() != 'Windows':
        print("[ERROR] V26 prototype only runs on Windows for binder access.")
    else:
        binder = PhysicalDriveBinder()
        cortex = NeurogridV26(binder)
        cortex.allocate_neuron()
        cortex.health_check()
