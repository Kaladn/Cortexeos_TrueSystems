FORGE MEMORY SYSTEM - BINARY LOG
Append-only record log per FORGE_PSEUDOCODE_PHASE1_CRITICAL.txt
"""

from __future__ import annotations

import os
import struct
import threading
from typing import List, Iterable

from forge_memory.core.mmap_file import MMapFile
from forge_memory.core.record import ForgeRecord
from forge_memory.core.string_dict import StringDictionary
from forge_memory.utils.constants import MAGIC_RECORD


class BinaryLog:
    """
    Append-only binary log for ForgeRecord entries (records.bin).
    
    Responsibilities:
    - Owns records.bin via MMapFile
    - Provides atomic appends (single-process, multi-thread)
    - Supports batch appends
    - Supports random-access reads by byte offset
    - Maintains in-memory record_offsets for fast iteration
    
    Per FORGE_PSEUDOCODE_PHASE1_CRITICAL.txt:
    - Scans existing records at startup (_scan_existing_records)
    - Tracks all record offsets in memory
    - Uses threading.Lock for append atomicity
    - Auto-resizes via MMapFile when needed
    """
    
    DEFAULT_INITIAL_SIZE = 1 * 1024 * 1024 * 1024  # 1 GiB
    
    def __init__(
        self,
        data_dir: str,
        string_dict: StringDictionary,
        initial_size: int = None,
        filename: str = "records.bin",
    ) -> None:
        """
        Initialize BinaryLog.
        
        Algorithm (per spec):
        1. Ensure data_dir exists
        2. Determine log_path = data_dir/records.bin
        3. If file new → create with initial_size, current_offset = 0
        4. If file exists → open and scan existing records to find current_offset
        
        Args:
            data_dir: Directory for records.bin
            string_dict: StringDictionary for string compression
            initial_size: Initial file size (default 1 GiB)
            filename: Log filename (default "records.bin")
        """
        self.data_dir = data_dir
        self.log_path = os.path.join(data_dir, filename)
        self.string_dict = string_dict
        
        if initial_size is None:
            initial_size = self.DEFAULT_INITIAL_SIZE
        
        os.makedirs(self.data_dir, exist_ok=True)
        
        # MMapFile will create/resize as needed per spec
        self.mmap_file = MMapFile(self.log_path, initial_size, mode="r+")
        self.lock = threading.Lock()
        self.record_offsets: List[int] = []
        self.current_offset: int = 0
        
        # If file is effectively empty (no MAGIC_RECORD at 0), treat as new
        if self._is_file_empty():
            self.current_offset = 0
            self.record_offsets = []
        else:
            self._scan_existing_records()
    
    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    
    def _is_file_empty(self) -> bool:
        """
        Check if file is empty (no valid record at offset 0).
        
        Algorithm (per spec):
        1. Read first 4 bytes
        2. If less than 4 bytes or MAGIC != MAGIC_RECORD → treat as empty
        
        Returns:
            True if file is empty/invalid
        """
        if self.mmap_file.size < 4:
            return True
        