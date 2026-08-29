"""Plaintext storage for Clearbox AI data files.

DPAPI encryption removed. All files are now plaintext.
Same function signatures preserved — all 31 callers work unchanged.

File formats:
  JSONL: one JSON object per line
  JSON: standard json.dump/load
  Text: utf-8 encoded plaintext

Legacy DPAPI files (V1/V2 headers) are read transparently:
  V1: skip header, decrypt single blob
  V2: skip header, decrypt per-line base64 blobs
  Plaintext: read as-is

Migration: on first read of a DPAPI file, it works. On next write,
the file is overwritten as plaintext. Gradual, automatic, no tool needed.
"""

import json
import os
from pathlib import Path
from typing import Any

# Legacy DPAPI headers — recognized on read for backward compat
MAGIC = b"CLEARBOX_DPAPI_V1\n"
MAGIC_V2 = b"CLEARBOX_DPAPI_V2\n"


def _is_dpapi_v1(data: bytes) -> bool:
    return data.startswith(MAGIC)


def _is_dpapi_v2(data: bytes) -> bool:
    return data.startswith(MAGIC_V2)


def _try_dpapi_decrypt(data: bytes) -> bytes:
    """Attempt DPAPI decryption for legacy files. Falls back to raw."""
    try:
        import ctypes
        import ctypes.wintypes
        import base64

        class _DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char)),
            ]

        _crypt32 = ctypes.windll.crypt32
        _kernel32 = ctypes.windll.kernel32

        blob_in = _DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
        blob_out = _DATA_BLOB()
        if _crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out),
        ):
            result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            _kernel32.LocalFree(blob_out.pbData)
            return result
    except Exception:
        pass
    return data


def _read_raw(path: Path) -> bytes:
    """Read file, handle legacy DPAPI formats transparently."""
    raw = path.read_bytes()
    if _is_dpapi_v1(raw):
        return _try_dpapi_decrypt(raw[len(MAGIC):])
    return raw


def _read_lines_raw(path: Path, encoding: str = "utf-8") -> list[str]:
    """Read lines, handle legacy DPAPI V2 format transparently."""
    raw = path.read_bytes()
    if _is_dpapi_v2(raw):
        import base64
        lines = []
        for line in raw[len(MAGIC_V2):].split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                decrypted = _try_dpapi_decrypt(base64.b64decode(line))
                lines.append(decrypted.decode(encoding))
            except Exception:
                lines.append(line.decode(encoding, errors="replace"))
        return lines
    # Plaintext
    return raw.decode(encoding, errors="replace").splitlines()


# ── Public API (same signatures as DPAPI version) ────────────

def secure_read_text(path: Path, encoding: str = "utf-8") -> str:
    """Read entire file as text. Handles legacy DPAPI V1."""
    if not path.exists():
        return ""
    raw = _read_raw(path)
    return raw.decode(encoding, errors="replace")


def secure_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text to file. Plaintext."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)


def secure_read_bytes(path: Path) -> bytes:
    """Read raw bytes. Handles legacy DPAPI V1."""
    if not path.exists():
        return b""
    return _read_raw(path)


def secure_write_bytes(path: Path, data: bytes) -> None:
    """Write raw bytes. Plaintext."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def secure_json_load(path: Path) -> Any:
    """Load JSON file. Handles legacy DPAPI V1."""
    text = secure_read_text(path)
    if not text.strip():
        return {}
    return json.loads(text)


def secure_json_dump(path: Path, obj: Any, **kwargs) -> None:
    """Write JSON file. Plaintext."""
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("indent", 2)
    path.write_text(json.dumps(obj, **kwargs), encoding="utf-8")


# Alias for callers that use secure_json_save
secure_json_save = secure_json_dump


def secure_append_line(path: Path, line: str, encoding: str = "utf-8") -> None:
    """Append one line to file. Plaintext, O(1)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding=encoding) as f:
        f.write(line.rstrip("\n") + "\n")


def secure_read_lines(path: Path, encoding: str = "utf-8") -> list[str]:
    """Read all lines. Handles legacy DPAPI V2."""
    if not path.exists():
        return []
    return _read_lines_raw(path, encoding)


def secure_count_lines(path: Path, encoding: str = "utf-8") -> int:
    """Count lines without loading all content into memory."""
    if not path.exists():
        return 0
    raw = path.read_bytes()
    if _is_dpapi_v2(raw):
        return raw[len(MAGIC_V2):].count(b"\n")
    return raw.count(b"\n")
