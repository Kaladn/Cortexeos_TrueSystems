import json
import win32file

SECTOR_SIZE = 512

class ResonanceValidator:
    def __init__(self, device_path):
        self.device_path = device_path
        self.handle = None
        self.ledger = {}

    def open_device(self):
        self.handle = win32file.CreateFile(
            self.device_path,
            win32file.GENERIC_READ,
            win32file.FILE_SHARE_READ,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )

    def close_device(self):
        if self.handle:
            win32file.CloseHandle(self.handle)
            self.handle = None

    def load_ledger(self, ledger_path):
        with open(ledger_path, 'r') as f:
            self.ledger = json.load(f)

    def read_sector(self, sector):
        win32file.SetFilePointer(self.handle, sector * SECTOR_SIZE, win32file.FILE_BEGIN)
        _, data = win32file.ReadFile(self.handle, SECTOR_SIZE)
        return data

    def verify_all(self):
        print("[VERIFY] Starting full ledger verification...")
        for neuron_id, sector_entry in self.ledger.items():
            # 💡 Patch Here: Compatibility for int or dict
            if isinstance(sector_entry, dict):
                sector = sector_entry.get("sector", 0)
            else:
                sector = sector_entry

            raw = self.read_sector(sector)
            print(f"[CHECK] Neuron {neuron_id} @ Sector {sector}: {raw[:16].hex()}...")

        print("[VERIFY] Ledger validation complete.")

# --- RUN SECTION ---
if __name__ == "__main__":
    print("[BOOT] Resonance Kernel V33.1 Validator Starting...")

    device_path = r"\\.\PhysicalDrive2"
    ledger_path = r"C:\Users\Blame\Desktop\cortexos_organized\kernel\contracts\ledgers\V33_resonance_ledger.json"

    validator = ResonanceValidator(device_path)
    validator.open_device()
    validator.load_ledger(ledger_path)
    validator.verify_all()
    validator.close_device()

    print("[SHUTDOWN] Resonance Kernel V33.1 complete.")
