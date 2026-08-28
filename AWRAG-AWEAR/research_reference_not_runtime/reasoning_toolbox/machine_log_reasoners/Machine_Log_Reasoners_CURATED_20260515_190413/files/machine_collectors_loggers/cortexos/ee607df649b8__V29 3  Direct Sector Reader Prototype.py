import ctypes
import os

# Device to target (this remains your bound drive)
TARGET_DRIVE = r'\\.\PhysicalDrive2'

# Windows constants
GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_WRITE_THROUGH = 0x80000000

SECTOR_SIZE = 512  # standard sector size

# Bind kernel32 functions
CreateFile = ctypes.windll.kernel32.CreateFileW
CloseHandle = ctypes.windll.kernel32.CloseHandle
SetFilePointerEx = ctypes.windll.kernel32.SetFilePointerEx
ReadFile = ctypes.windll.kernel32.ReadFile

class NVMeSectorReader:
    def __init__(self, path):
        self.path = path
        self.handle = None

    def open(self):
        print(f"[READER] Opening: {self.path}")
        self.handle = CreateFile(
            self.path,
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH,
            None
        )

        if self.handle == -1 or self.handle == 0:
            error_code = ctypes.GetLastError()
            raise OSError(f"[ERROR] Failed to open device: WinError {error_code}")

    def read_sector(self, sector_number):
        offset = sector_number * SECTOR_SIZE
        distance = ctypes.c_longlong(offset)
        if not SetFilePointerEx(self.handle, distance, None, 0):
            raise OSError("Failed to seek sector.")

        buffer = ctypes.create_string_buffer(SECTOR_SIZE)
        bytes_read = ctypes.c_ulong(0)
        success = ReadFile(self.handle, buffer, SECTOR_SIZE, ctypes.byref(bytes_read), None)

        if not success:
            raise OSError("Failed to read sector.")

        print(f"[READ] Sector {sector_number}: {buffer.raw.hex()[:64]}...")  # Print partial hex

    def close(self):
        if self.handle:
            CloseHandle(self.handle)
            print("[READER] Device closed.")

if __name__ == "__main__":
    reader = NVMeSectorReader(TARGET_DRIVE)
    try:
        reader.open()
        reader.read_sector(0)  # Boot sector read (safe)
    except Exception as e:
        print(e)
    finally:
        reader.close()
