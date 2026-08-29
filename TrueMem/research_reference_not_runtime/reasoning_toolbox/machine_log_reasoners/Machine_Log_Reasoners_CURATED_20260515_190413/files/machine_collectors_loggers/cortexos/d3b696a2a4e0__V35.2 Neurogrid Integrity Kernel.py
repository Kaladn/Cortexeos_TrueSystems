import json
import win32file

# Config paths
ledger_path = r"C:\Users\Blame\Desktop\cortexos_organized\kernel\contracts\ledgers\V33_resonance_ledger.json"
device_path = r"\\.\PhysicalDrive2"
SECTOR_SIZE = 512

# Bind to device
handle = win32file.CreateFile(
    device_path,
    win32file.GENERIC_READ,
    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
    None,
    win32file.OPEN_EXISTING,
    0,
    None
)

# Load ledger
with open(ledger_path, 'r') as f:
    raw_ledger = json.load(f)

# Normalize ledger (handles legacy entries stored as strings)
ledger = []
for entry in raw_ledger:
    if isinstance(entry, str):
        ledger.append(json.loads(entry))
    else:
        ledger.append(entry)

# Start verification
print(f"[BOOT] Resonance Kernel V35.2 Validator Starting...")
print(f"[LEDGER] Loaded {len(ledger)} entries.")

for entry in ledger:
    sector = entry['sector']
    neuron_id = entry['neuron_id']

    # Seek to sector
    win32file.SetFilePointer(handle, sector * SECTOR_SIZE, win32file.FILE_BEGIN)
    result, raw = win32file.ReadFile(handle, SECTOR_SIZE)

    hex_snippet = raw[:16].hex()
    print(f"[VERIFY] Sector {sector} (Neuron {neuron_id[:8]}): {hex_snippet}")

# Close device
win32file.CloseHandle(handle)
print("[SHUTDOWN] V35.2 verification complete.")
