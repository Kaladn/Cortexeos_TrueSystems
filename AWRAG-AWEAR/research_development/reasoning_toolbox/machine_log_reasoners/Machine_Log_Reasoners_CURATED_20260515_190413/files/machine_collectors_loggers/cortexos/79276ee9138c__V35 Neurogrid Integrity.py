import json
import win32file

# --- Config ---
LEDGER_PATH = r"C:\Users\Blame\Desktop\cortexos_organized\kernel\contracts\ledgers\V33_resonance_ledger_normalized.json"
DEVICE_PATH = r"\\.\PhysicalDrive2"
SECTOR_SIZE = 512

class NVMeBinder:
    def __init__(self, device_path):
        self.device_path = device_path
        self.handle = None

    def open(self):
        self.handle = win32file.CreateFile(
            self.device_path,
            win32file.GENERIC_READ,
            win32file.FILE_SHARE_READ,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        print(f"[BINDER] Bound to {self.device_path}")

    def read_sector(self, sector):
        win32file.SetFilePointer(self.handle, sector * SECTOR_SIZE, win32file.FILE_BEGIN)
        data = win32file.ReadFile(self.handle, SECTOR_SIZE)[1]
        return data

    def close(self):
        if self.handle:
            win32file.CloseHandle(self.handle)
            print("[BINDER] Device closed.")

class IntegrityValidator:
    def __init__(self, ledger_path, binder):
        self.ledger_path = ledger_path
        self.binder = binder

    def load_ledger(self):
        with open(self.ledger_path, "r") as f:
            self.ledger = json.load(f)
        print(f"[LEDGER] Loaded {len(self.ledger)} entries.")

    def verify(self):
        import json

# right before you enter your loop
normalized_ledger = [json.loads(e) if isinstance(e, str) else e for e in ledger]

for entry in normalized_ledger:
    sector = entry['sector']
    neuron_id = entry['neuron_id']
    # ... do your verification here ...

for entry in self.ledger:
            sector = entry['sector']
            neuron_id = entry['neuron_id']
            data = self.binder.read_sector(sector)
            checksum = data[:8].hex()
            print(f"[CHECK] Sector {sector} | Neuron {neuron_id} | First 8 bytes: {checksum}")

if __name__ == "__main__":
    binder = NVMeBinder(DEVICE_PATH)
    binder.open()

    validator = IntegrityValidator(LEDGER_PATH, binder)
    validator.load_ledger()
    validator.verify()

    binder.close()
