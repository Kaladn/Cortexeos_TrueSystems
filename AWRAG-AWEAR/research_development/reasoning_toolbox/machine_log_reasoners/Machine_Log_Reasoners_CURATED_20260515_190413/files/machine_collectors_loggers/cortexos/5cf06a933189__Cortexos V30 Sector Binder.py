import ctypes
import os
import uuid
import struct
import time

SECTOR_SIZE = 512
RESERVED_MB = 100
RESERVED_SECTORS = (RESERVED_MB * 1024 * 1024) // SECTOR_SIZE
TOTAL_SECTORS = 1953525168  # Samsung 990 Pro 1TB
BIND_SECTORS = TOTAL_SECTORS - RESERVED_SECTORS

class NeuroGridV30:
    def __init__(self, drive_path):
        self.drive_path = drive_path
        self.handle = None
        self.ledger_file = "neurogrid_v30_ledger.json"
        self.allocated_sectors = {}
        self.next_sector = RESERVED_SECTORS
        self.load_ledger()

    def open_drive(self):
        GENERIC_READ_WRITE = 0xC0000000
        FILE_SHARE_READ_WRITE = 0x3
        OPEN_EXISTING = 0x3
        self.handle = ctypes.windll.kernel32.CreateFileW(
            self.drive_path,
            GENERIC_READ_WRITE,
            FILE_SHARE_READ_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None
        )
        if self.handle == -1:
            raise OSError("Failed to open device.")

    def close_drive(self):
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(self.handle)

    def load_ledger(self):
        if os.path.exists(self.ledger_file):
            import json
            with open(self.ledger_file, "r") as f:
                self.allocated_sectors = json.load(f)
                self.next_sector = max(map(int, self.allocated_sectors.values())) + 1
            print("[LEDGER] Existing ledger loaded.")
        else:
            print("[LEDGER] Starting fresh.")

    def save_ledger(self):
        import json
        with open(self.ledger_file, "w") as f:
            json.dump(self.allocated_sectors, f)

    def allocate_neuron(self):
        neuron_id = str(uuid.uuid4())
        sector = self.next_sector
        if sector >= TOTAL_SECTORS:
            raise Exception("Out of sectors!")
        data = neuron_id.encode("utf-8")
        padded = data.ljust(SECTOR_SIZE, b'\x00')
        self.write_sector(sector, padded)
        self.allocated_sectors[neuron_id] = sector
        self.next_sector += 1
        self.save_ledger()
        print(f"[ALLOC] Neuron {neuron_id} -> Sector {sector}")

    def write_sector(self, sector_num, data):
        overlapped = ctypes.c_ulonglong(sector_num * SECTOR_SIZE)
        ctypes.windll.kernel32.SetFilePointerEx(self.handle, overlapped, None, 0)
        written = ctypes.c_ulong(0)
        ctypes.windll.kernel32.WriteFile(self.handle, data, SECTOR_SIZE, ctypes.byref(written), None)

if __name__ == "__main__":
    binder = NeuroGridV30("\\\\.\\PhysicalDrive2")
    try:
        binder.open_drive()
        for _ in range(10):
            binder.allocate_neuron()
        binder.close_drive()
    except Exception as e:
        print("[ERROR]", e)
        binder.close_drive()
