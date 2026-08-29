"""DPAPI-backed transparent encryption for Clearbox AI data files.

Windows Data Protection API (DPAPI):
- Encrypts data using the current Windows user's login credentials
- Another Windows user on the same machine CANNOT decrypt
- Files copied to another machine are unreadable
- No passwords or keys to manage — Windows handles everything
- Works on all Windows editions (Home, Pro, Enterprise)

Implementation uses ctypes (stdlib) — no pywin32 dependency.

File formats:
  V1 (whole-file): b'CLEARBOX_DPAPI_V1\n' + single DPAPI blob
  V2 (per-line):   b'CLEARBOX_DPAPI_V2\n' + base64(DPAPI(line))\n per line
  Plaintext:       no header (pre-migration files)

V2 is used for append-oriented files (JSONL). Appending is O(1).
V1 is used for write-once files (JSON config, .txt summaries).
Reads are backward-compatible across all three formats.
"""

import base64
import ctypes
import ctypes.wintypes
import json
import os
from pathlib import Path
from typing import Any

# ── Windows DPAPI via ctypes ───────────────────────────────────
_crypt32 = ctypes.windll.crypt32
_kernel32 = ctypes.windll.kernel32

MAGIC = b"CLEARBOX_DPAPI_V1\n"
MAGIC_V2 = b"CLEARBOX_DPAPI_V2\n"


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _dpapi_encrypt(data: bytes) -> bytes:
    """Encrypt bytes with DPAPI (current user scope)."""
    blob_in = _DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    blob_out = _DATA_BLOB()
    if not _crypt32.CryptProtectData(
        ctypes.byref(blob_in),  # pDataIn
        None,                   # szDataDescr
        None,                   # pOptionalEntropy
        None,                   # pvReserved
        None,                   # pPromptStruct
        0,                      # dwFlags
        ctypes.byref(blob_out), # pDataOut
    ):
        raise OSError(f"DPAPI CryptProtectData failed (error {ctypes.GetLastError()})")
    encrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    _kernel32.LocalFree(blob_out.pbData)
    return encrypted


def _dpapi_decrypt(data: bytes) -> bytes:
    """Decrypt bytes with DPAPI (current user scope)."""
    blob_in = _DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    blob_out = _DATA_BLOB()
    if not _crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),  # pDataIn
        None,                   # ppszDataDescr
        None,                   # pOptionalEntropy
        None,                   # pvReserved
        None,                   # pPromptStruct
        0,                      # dwFlags
        ctypes.byref(blob_out), # pDataOut
    ):
        raise OSError(f"DPAPI CryptUnprotectData failed (error {ctypes.GetLastError()})")
    decrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    _kernel32.LocalFree(blob_out.pbData)
    return decrypted


def _detect_format(raw: bytes) -> str:
    """Detect file format from raw bytes. Returns 'v2', 'v1', or 'plain'."""
    if raw.startswith(MAGIC_V2):
        return "v2"
    if raw.startswith(MAGIC):
        return "v1"
    return "plain"


def _decrypt_v2_lines(raw: bytes, encoding: str = "utf-8") -> list[str]:
    """Decrypt per-line V2 format into plaintext lines."""
    lines = []
    for b64_line in raw[len(MAGIC_V2):].split(b"\n"):
        if not b64_line:
            continue
        try:
            decrypted = _dpapi_decrypt(base64.b64decode(b64_line))
            lines.append(decrypted.decode(encoding))
        except Exception:
            lines.append('{"_corrupt": true, "_source": "secure_storage_v2"}')
    return lines


# ── Public API ────────────────────────────────────────────────


def is_encrypted(path: Path) -> bool:
    """Check if a file has a DPAPI encryption header (V1 or V2)."""
    if not path.exists():
        return False
    with open(path, "rb") as f:
        header = f.read(len(MAGIC_V2))
        return header.startswith(MAGIC) or header == MAGIC_V2


def secure_read_text(path: Path, encoding: str = "utf-8") -> str:
    """Read a text file, decrypting if DPAPI-encrypted.

    Handles V1 (whole-file), V2 (per-line), and plaintext formats.
    """
    raw = path.read_bytes()
    fmt = _detect_format(raw)
    if fmt == "v2":
        return "\n".join(_decrypt_v2_lines(raw, encoding))
    if fmt == "v1":
        return _dpapi_decrypt(raw[len(MAGIC):]).decode(encoding)
    return raw.decode(encoding)


def secure_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text to a file, encrypted with DPAPI (V1 whole-file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _dpapi_encrypt(text.encode(encoding))
    path.write_bytes(MAGIC + encrypted)


def secure_read_bytes(path: Path) -> bytes:
    """Read raw bytes, decrypting if DPAPI-encrypted."""
    raw = path.read_bytes()
    fmt = _detect_format(raw)
    if fmt == "v2":
        return "\n".join(_decrypt_v2_lines(raw)).encode("utf-8")
    if fmt == "v1":
        return _dpapi_decrypt(raw[len(MAGIC):])
    return raw


def secure_write_bytes(path: Path, data: bytes) -> None:
    """Write raw bytes, encrypted with DPAPI."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _dpapi_encrypt(data)
    path.write_bytes(MAGIC + encrypted)


def secure_json_load(path: Path) -> Any:
    """Read and parse a JSON file, decrypting if DPAPI-encrypted."""
    text = secure_read_text(path)
    return json.loads(text)


def secure_json_dump(path: Path, obj: Any, **kwargs) -> None:
    """Serialize to JSON and write encrypted with DPAPI.

    Accepts same kwargs as json.dumps (indent, ensure_ascii, etc.).
    """
    kwargs.setdefault("indent", 2)
    kwargs.setdefault("ensure_ascii", False)
    text = json.dumps(obj, **kwargs)
    secure_write_text(path, text)


def secure_append_line(path: Path, line: str, encoding: str = "utf-8") -> None:
    """Append a line to a per-line encrypted file (O(1) amortized).

    New files are created in V2 format (per-line encryption).
    Legacy V1/plaintext files are migrated to V2 on first append.
    After migration, all subsequent appends are O(1).
    """
    line = line.rstrip("\n")
    encrypted_line = base64.b64encode(_dpapi_encrypt(line.encode(encoding)))

    if not path.exists():
        # New file: V2 header + first encrypted line
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(MAGIC_V2)
            f.write(encrypted_line + b"\n")
        return

    # Detect existing format
    with open(path, "rb") as f:
        header = f.read(len(MAGIC_V2))

    if header == MAGIC_V2:
        # Already V2: append only (O(1))
        with open(path, "ab") as f:
            f.write(encrypted_line + b"\n")
    else:
        # V1 or plaintext: migrate to V2, then append
        existing_lines = secure_read_lines(path, encoding)
        with open(path, "wb") as f:
            f.write(MAGIC_V2)
            for existing in existing_lines:
                enc = base64.b64encode(_dpapi_encrypt(existing.encode(encoding)))
                f.write(enc + b"\n")
            f.write(encrypted_line + b"\n")


def secure_read_lines(path: Path, encoding: str = "utf-8") -> list[str]:
    """Read all lines from a DPAPI-encrypted file.

    Handles V2 (per-line), V1 (whole-file), and plaintext formats.
    Returns empty list if file doesn't exist.
    """
    if not path.exists():
        return []
    raw = path.read_bytes()
    fmt = _detect_format(raw)
    if fmt == "v2":
        return _decrypt_v2_lines(raw, encoding)
    if fmt == "v1":
        return _dpapi_decrypt(raw[len(MAGIC):]).decode(encoding).splitlines()
    return raw.decode(encoding).splitlines()


def secure_count_lines(path: Path, encoding: str = "utf-8") -> int:
    """Count lines in a DPAPI-encrypted file.

    For V2 files, counts base64 lines without decrypting (fast).
    For V1/plaintext, must decrypt to count.
    """
    if not path.exists():
        return 0
    raw = path.read_bytes()
    fmt = _detect_format(raw)
    if fmt == "v2":
        # Count non-empty base64 lines after header (no decrypt needed)
        return sum(1 for line in raw[len(MAGIC_V2):].split(b"\n") if line)
    if fmt == "v1":
        text = _dpapi_decrypt(raw[len(MAGIC):]).decode(encoding)
    else:
        text = raw.decode(encoding)
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)
