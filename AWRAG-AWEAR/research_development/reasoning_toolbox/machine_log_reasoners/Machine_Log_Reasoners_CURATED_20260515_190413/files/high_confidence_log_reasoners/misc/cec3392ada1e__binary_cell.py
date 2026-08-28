#!/usr/bin/env python3
"""
Binary Cell Structure for AI Neural Memory

This module implements a binary storage format for word context data
based on the Binary Cell Structure Blueprint 2.0.

Features:
- Efficient binary storage of word frequency and context data
- B+Tree indexing for fast word lookup
- Overflow handling for words with many context relationships
- Data integrity with checksums and magic bytes
- Optional compression for space efficiency

Classes:
- BinaryCell: Core structure for word storage
- OverflowBlock: Handles words with many context relationships
- MasterIndex: B+Tree implementation for word lookup
- BinaryCellWriter: Converts text/JSON data to binary format
- BinaryCellReader: Reads binary data and provides query interface
"""

import os
import sys
import json
import struct
import zlib
import mmap
from collections import defaultdict, Counter
import bisect
from typing import Dict, List, Tuple, Set, Optional, Union, BinaryIO
import time
import hashlib

# Constants
MAGIC_BYTES = 0xB1C3
OVERFLOW_MAGIC = 0x4F564552  # "OVER" in ASCII
MAX_WORD_LENGTH = 128
DEFAULT_CONTEXT_ENTRIES = 100  # Number of context entries to store in main cell

class BinaryCell:
    """
    Core structure for storing word data in binary format.
    
    Implements the Binary Cell Structure as specified in the blueprint.
    """
    
    def __init__(self, word: str, token_id: int, frequency: int = 0, tone_signature: int = 0):
        """
        Initialize a new binary cell for a word.
        
        Args:
            word: The word to store
            token_id: Unique ID for the word
            frequency: Global occurrence frequency
            tone_signature: Encoded tonal fingerprint
        """
        self.word = word
        self.token_id = token_id
        self.frequency = frequency
        self.tone_signature = tone_signature
        self.before_context = []  # List of (token_id, frequency, tone_id) tuples
        self.after_context = []   # List of (token_id, frequency, tone_id) tuples
        self.overflow_before_offset = 0
        self.overflow_after_offset = 0
        
    def add_before_context(self, token_id: int, frequency: int = 1, tone_id: int = 0):
        """Add a word that appears before this word."""
        # Check if token already exists in context
        for i, (tid, freq, tone) in enumerate(self.before_context):
            if tid == token_id:
                # Update existing entry
                self.before_context[i] = (tid, freq + frequency, tone_id)
                return
        # Add new entry
        self.before_context.append((token_id, frequency, tone_id))
        
    def add_after_context(self, token_id: int, frequency: int = 1, tone_id: int = 0):
        """Add a word that appears after this word."""
        # Check if token already exists in context
        for i, (tid, freq, tone) in enumerate(self.after_context):
            if tid == token_id:
                # Update existing entry
                self.after_context[i] = (tid, freq + frequency, tone_id)
                return
        # Add new entry
        self.after_context.append((token_id, frequency, tone_id))
    
    def sort_contexts(self):
        """Sort context lists by frequency (descending)."""
        self.before_context.sort(key=lambda x: x[1], reverse=True)
        self.after_context.sort(key=lambda x: x[1], reverse=True)
    
    def to_binary(self, include_overflow: bool = True) -> bytes:
        """
        Convert the cell to binary format.
        
        Args:
            include_overflow: Whether to include overflow pointers
            
        Returns:
            Binary representation of the cell
        """
        # Limit context entries to DEFAULT_CONTEXT_ENTRIES
        before_entries = self.before_context[:DEFAULT_CONTEXT_ENTRIES]
        after_entries = self.after_context[:DEFAULT_CONTEXT_ENTRIES]
        
        # Calculate sizes
        word_bytes = self.word.encode('utf-8')
        word_length = len(word_bytes)
        
        # Header
        header = struct.pack(
            '>HBLLLL',  # Format: magic, word_length, token_id, frequency, tone_signature, reserved
            MAGIC_BYTES,
            word_length,
            self.token_id,
            self.frequency,
            self.tone_signature,
            0  # Reserved
        )
        
        # Before context table
        before_count = len(before_entries)
        before_header = struct.pack('>H', before_count)
        before_data = b''
        for token_id, freq, tone_id in before_entries:
            before_data += struct.pack('>LLH', token_id, freq, tone_id)
        
        # After context table
        after_count = len(after_entries)
        after_header = struct.pack('>H', after_count)
        after_data = b''
        for token_id, freq, tone_id in after_entries:
            after_data += struct.pack('>LLH', token_id, freq, tone_id)
        
        # Overflow pointers (optional)
        overflow_data = b''
        if include_overflow:
            overflow_data = struct.pack(
                '>QQ',
                self.overflow_before_offset,
                self.overflow_after_offset
            )
        
        # Combine all parts
        data = header + word_bytes + before_header + before_data + after_header + after_data + overflow_data
        
        # Add checksum
        checksum = zlib.crc32(data)
        data += struct.pack('>L', checksum)
        
        return data
    
    @classmethod
    def from_binary(cls, data: bytes) -> 'BinaryCell':
        """
        Create a BinaryCell from binary data.
        
        Args:
            data: Binary data to parse
            
        Returns:
            BinaryCell object
        
        Raises:
            ValueError: If data is invalid
        """
        # Check minimum length
        if len(data) < 20:  # Minimum header size
            raise ValueError("Data too short for a valid BinaryCell")
        
        # Parse header
        # Calculate the correct size for the header (H=2, B=1, L=4 bytes each)
        header_size = 2 + 1 + (4 * 4)  # 19 bytes total
        if len(data) < header_size:
            raise ValueError(f"Data too short for header: {len(data)} bytes, need {header_size}")
        magic, word_length, token_id, frequency, tone_signature, reserved = struct.unpack('>HBLLLL', data[:header_size])
        
        # Verify magic bytes
        if magic != MAGIC_BYTES:
            raise ValueError(f"Invalid magic bytes: {magic:04x}, expected: {MAGIC_BYTES:04x}")
        
        # Extract word
        word_end = header_size + word_length
        word_bytes = data[header_size:word_end]
        word = word_bytes.decode('utf-8')
        
        # Create cell
        cell = cls(word, token_id, frequency, tone_signature)
        
        # Parse before context
        pos = word_end
        if pos + 2 > len(data):
            raise ValueError("Data truncated before context count")
            
        before_count = struct.unpack('>H', data[pos:pos+2])[0]
        pos += 2
        
        for _ in range(before_count):
            if pos + 10 > len(data):  # 4 + 4 + 2 = 10 bytes per entry
                raise ValueError("Data truncated in before context")
                
            before_token, before_freq, before_tone = struct.unpack('>LLH', data[pos:pos+10])
            cell.before_context.append((before_token, before_freq, before_tone))
            pos += 10
        
        # Parse after context
        if pos + 2 > len(data):
            raise ValueError("Data truncated before after context")
            
        after_count = struct.unpack('>H', data[pos:pos+2])[0]
        pos += 2
        
        for _ in range(after_count):
            if pos + 10 > len(data):  # 4 + 4 + 2 = 10 bytes per entry
                raise ValueError("Data truncated in after context")
                
            after_token, after_freq, after_tone = struct.unpack('>LLH', data[pos:pos+10])
            cell.after_context.append((after_token, after_freq, after_tone))
            pos += 10
        
        # Parse overflow pointers if present
        if pos + 16 <= len(data) - 4:  # -4 for checksum
            cell.overflow_before_offset, cell.overflow_after_offset = struct.unpack(
                '>QQ', data[pos:pos+16]
            )
            pos += 16
        
        # Verify checksum if present
        if pos + 4 <= len(data):
            stored_checksum = struct.unpack('>L', data[pos:pos+4])[0]
            calculated_checksum = zlib.crc32(data[:-4])
            
            if stored_checksum != calculated_checksum:
                raise ValueError(f"Checksum mismatch: stored={stored_checksum}, calculated={calculated_checksum}")
        
        return cell

class OverflowBlock:
    """
    Overflow block for storing additional context entries.
    
    Used when a word has more context relationships than can fit in the main cell.
    """
    
    def __init__(self, parent_token_id: int, is_before: bool = True):
        """
        Initialize a new overflow block.
        
        Args:
            parent_token_id: Token ID of the parent word
            is_before: True if this block stores "before" context, False for "after"
        """
        self.parent_token_id = parent_token_id
        self.is_before = is_before
        self.entries = []  # List of (token_id, frequency, tone_id) tuples
        self.next_overflow_ptr = 0
    
    def add_entry(self, token_id: int, frequency: int, tone_id: int = 0):
        """Add a context entry to this overflow block."""
        self.entries.append((token_id, frequency, tone_id))
    
    def to_binary(self, compress: bool = False) -> bytes:
        """
        Convert the overflow block to binary format.
        
        Args:
            compress: Whether to compress the entries using zstd
            
        Returns:
            Binary representation of the overflow block
        """
        # Header
        header = struct.pack(
            '>BL L H',  # Format: compression_type, magic, parent_token_id, entry_count
            1 if compress else 0,  # compression_type: 0=none, 1=zstd
            OVERFLOW_MAGIC,
            self.parent_token_id,
            len(self.entries)
        )
        
        # Entries
        entries_data = b''
        for token_id, freq, tone_id in self.entries:
            entries_data += struct.pack('>LLH', token_id, freq, tone_id)
        
        # Next overflow pointer
        next_ptr = struct.pack('>Q', self.next_overflow_ptr)
        
        # Combine parts
        data = header + entries_data + next_ptr
        
        # Compress if requested
        if compress:
            try:
                import zstandard as zstd
                compressor = zstd.ZstdCompressor(level=3)
                compressed_data = compressor.compress(entries_data + next_ptr)
                data = header + compressed_data
            except ImportError:
                # Fall back to zlib if zstandard is not available
                compressed_data = zlib.compress(entries_data + next_ptr)
                data = header + compressed_data
        
        return data
    
    @classmethod
    def from_binary(cls, data: bytes) -> 'OverflowBlock':
        """
        Create an OverflowBlock from binary data.
        
        Args:
            data: Binary data to parse
            
        Returns:
            OverflowBlock object
        
        Raises:
            ValueError: If data is invalid
        """
        # Check minimum length
        if len(data) < 11:  # Minimum header size
            raise ValueError("Data too short for a valid OverflowBlock")
        
        # Parse header
        compression_type = struct.unpack('>B', data[0:1])[0]
        magic, parent_token_id, entry_count = struct.unpack('>L L H', data[1:11])
        
        # Verify magic bytes
        if magic != OVERFLOW_MAGIC:
            raise ValueError(f"Invalid overflow magic: {magic:08x}, expected: {OVERFLOW_MAGIC:08x}")
        
        # Create block
        block = cls(parent_token_id, True)  # is_before will be set by caller
        
        # Parse entries
        if compression_type == 0:  # Uncompressed
            pos = 11
            for _ in range(entry_count):
                if pos + 10 > len(data) - 8:  # -8 for next_ptr
                    raise ValueError("Data truncated in overflow entries")
                    
                token_id, freq, tone_id = struct.unpack('>LLH', data[pos:pos+10])
                block.entries.append((token_id, freq, tone_id))
                pos += 10
            
            # Parse next overflow pointer
            if pos + 8 <= len(data):
                block.next_overflow_ptr = struct.unpack('>Q', data[pos:pos+8])[0]
        else:  # Compressed
            try:
                # Try to use zstandard
                import zstandard as zstd
                decompressor = zstd.ZstdDecompressor()
                decompressed = decompressor.decompress(data[11:])
            except ImportError:
                # Fall back to zlib
                decompressed = zlib.decompress(data[11:])
            
            # Parse decompressed data
            pos = 0
            for _ in range(entry_count):
                if pos + 10 > len(decompressed) - 8:  # -8 for next_ptr
                    raise ValueError("Data truncated in decompressed overflow entries")
                
                token_id, freq, tone_id = struct.unpack('>LLH', decompressed[pos:pos+10])
                block.entries.append((token_id, freq, tone_id))
                pos += 10
            
            # Parse next overflow pointer
            if pos + 8 <= len(decompressed):
                block.next_overflow_ptr = struct.unpack('>Q', decompressed[pos:pos+8])[0]
        
        return block

class MasterIndex:
    """
    Master index for fast word lookup.
    
    Implements a B+Tree-like structure with embedded bloom filter for efficient word lookup.
    """
    
    def __init__(self, order: int = 100, bloom_size: int = 10000):
        """
        Initialize a new master index.
        
        Args:
            order: B+Tree order (max children per node)
            bloom_size: Size of bloom filter in bytes
        """
        self.order = order
        self.word_to_hash = {}  # Word to hash mapping
        self.hash_to_offset = {}  # Hash to file offset mapping
        self.hash_to_token_id = {}  # Hash to token ID mapping
        self.hash_to_tone_id = {}  # Hash to tone ID mapping
        self.token_id_to_hash = {}  # Token ID to hash mapping (reverse lookup)
        self.bloom_filter = bytearray(bloom_size)  # Bloom filter for quick hit/miss
    
    def _hash_word(self, word: str) -> int:
        """Calculate hash for a word."""
        # Use SHA-256 truncated to 32 bits
        hash_obj = hashlib.sha256(word.encode('utf-8'))
        # Return as 32-bit unsigned integer
        return int.from_bytes(hash_obj.digest()[:4], byteorder='big')
    
    def _add_to_bloom(self, word_hash: int):
        """Add a hash to the bloom filter."""
        # Use 3 hash functions for bloom filter
        for i in range(3):
            # Create different hashes by adding a salt
            h = (word_hash + i * 0xdeadbeef) % (len(self.bloom_filter) * 8)
            # Set the bit
            byte_pos = h // 8
            bit_pos = h % 8
            self.bloom_filter[byte_pos] |= (1 << bit_pos)
    
    def _check_bloom(self, word_hash: int) -> bool:
        """Check if a hash might be in the bloom filter."""
        # Use 3 hash functions for bloom filter
        for i in range(3):
            # Create different hashes by adding a salt
            h = (word_hash + i * 0xdeadbeef) % (len(self.bloom_filter) * 8)
            # Check the bit
            byte_pos = h // 8
            bit_pos = h % 8
            if not (self.bloom_filter[byte_pos] & (1 << bit_pos)):
                return False  # Definitely not in the set
        return True  # Might be in the set
    
    def add_entry(self, word: str, token_id: int, offset: int, tone_id: int = 0):
        """
        Add an entry to the index.
        
        Args:
            word: The word to index
            token_id: Token ID for the word
            offset: File offset where the word's data is stored
            tone_id: Tone ID for the word
        """
        # Calculate hash
        word_hash = self._hash_word(word)
        
        # Add to bloom filter
        self._add_to_bloom(word_hash)
        
        # Store mappings
        self.word_to_hash[word] = word_hash
        self.hash_to_offset[word_hash] = offset
        self.hash_to_token_id[word_hash] = token_id
        self.hash_to_tone_id[word_hash] = tone_id
        self.token_id_to_hash[token_id] = word_hash
    
    def get_offset(self, word: str) -> Optional[int]:
        """Get file offset for a word."""
        word_hash = self._hash_word(word)
        
        # Quick check with bloom filter
        if not self._check_bloom(word_hash):
            return None
            
        return self.hash_to_offset.get(word_hash)
    
    def get_token_id(self, word: str) -> Optional[int]:
        """Get token ID for a word."""
        word_hash = self._hash_word(word)
        
        # Quick check with bloom filter
        if not self._check_bloom(word_hash):
            return None
            
        return self.hash_to_token_id.get(word_hash)
    
    def get_tone_id(self, word: str) -> Optional[int]:
        """Get tone ID for a word."""
        word_hash = self._hash_word(word)
        
        # Quick check with bloom filter
        if not self._check_bloom(word_hash):
            return None
            
        return self.hash_to_tone_id.get(word_hash)
    
    def get_word_by_token_id(self, token_id: int) -> Optional[str]:
        """Get word for a token ID (reverse lookup)."""
        word_hash = self.token_id_to_hash.get(token_id)
        if word_hash is None:
            return None
        
        # Find word by hash
        for word, hash_val in self.word_to_hash.items():
            if hash_val == word_hash:
                return word
        
        return None
    
    def to_binary(self) -> bytes:
        """Convert the index to binary format."""
        # Format: count, bloom_filter_size, bloom_filter, [hash, offset, token_id, tone_id] * count
        count = len(self.hash_to_offset)
        bloom_size = len(self.bloom_filter)
        
        header = struct.pack('>L L', count, bloom_size)
        entries = b''
        
        for word_hash, offset in self.hash_to_offset.items():
            token_id = self.hash_to_token_id.get(word_hash, 0)
            tone_id = self.hash_to_tone_id.get(word_hash, 0)
            entries += struct.pack('>L Q L L', word_hash & 0xFFFFFFFF, offset, token_id, tone_id)
        
        return header + self.bloom_filter + entries
    
    @classmethod
    def from_binary(cls, data: bytes) -> 'MasterIndex':
        """Create a MasterIndex from binary data."""
        # Check minimum length
        if len(data) < 8:
            raise ValueError("Data too short for a valid MasterIndex")
        
        # Parse header
        count, bloom_size = struct.unpack('>L L', data[:8])
        
        # Create index
        index = cls()
        
        # Extract bloom filter
        bloom_end = 8 + bloom_size
        if bloom_end > len(data):
            raise ValueError("Data truncated in bloom filter")
            
        index.bloom_filter = bytearray(data[8:bloom_end])
        
        # Parse entries
        pos = bloom_end
        for _ in range(count):
            if pos + 20 > len(data):  # L=4, Q=8, L=4, L=4 bytes
                raise ValueError("Data truncated in index entries")
                
            word_hash, offset, token_id, tone_id = struct.unpack('>L Q L L', data[pos:pos+20])
            
            # Store mappings
            index.hash_to_offset[word_hash] = offset
            index.hash_to_token_id[word_hash] = token_id
            index.hash_to_tone_id[word_hash] = tone_id
            index.token_id_to_hash[token_id] = word_hash
            
            pos += 20
        
        return index
    
    def save_to_file(self, filename: str):
        """Save the index to a file."""
        with open(filename, 'wb') as f:
            f.write(self.to_binary())
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'MasterIndex':
        """Load the index from a file."""
        with open(filename, 'rb') as f:
            data = f.read()
        return cls.from_binary(data)

class BinaryCellWriter:
    """
    Converts text/JSON word context data to binary format.
    
    Handles the conversion of word frequency and context data to the
    Binary Cell Structure format.
    """
    
    def __init__(self, output_file: str, index_file: str):
        """
        Initialize a new binary cell writer.
        
        Args:
            output_file: Path to output binary file
            index_file: Path to output index file
        """
        self.output_file = output_file
        self.index_file = index_file
        self.output_f = None
        self.index = MasterIndex()
        self.next_token_id = 1  # Start from 1, 0 reserved
        self.word_to_token_id = {}
        self.current_offset = 0
    
    def __enter__(self):
        """Context manager entry."""
        self.output_f = open(self.output_file, 'wb')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.output_f:
            self.output_f.close()
            self.output_f = None
        
        # Save index
        self.index.save_to_file(self.index_file)
    
    def get_or_create_token_id(self, word: str) -> int:
        """Get token ID for a word, creating a new one if needed."""
        if word in self.word_to_token_id:
            return self.word_to_token_id[word]
        
        token_id = self.next_token_id
        self.next_token_id += 1
        self.word_to_token_id[word] = token_id
        
        return token_id
    
    def write_cell(self, cell: BinaryCell) -> int:
        """
        Write a binary cell to the output file.
        
        Args:
            cell: BinaryCell to write
            
        Returns:
            File offset where the cell was written
        """
        if not self.output_f:
            raise ValueError("Writer not open")
        
        # Sort contexts by frequency
        cell.sort_contexts()
        
        # Check if we need overflow blocks
        overflow_before = cell.before_context[DEFAULT_CONTEXT_ENTRIES:] if len(cell.before_context) > DEFAULT_CONTEXT_ENTRIES else []
        overflow_after = cell.after_context[DEFAULT_CONTEXT_ENTRIES:] if len(cell.after_context) > DEFAULT_CONTEXT_ENTRIES else []
        
        # Write overflow blocks if needed
        if overflow_before:
            cell.overflow_before_offset = self._write_overflow_block(cell.token_id, overflow_before, True)
        
        if overflow_after:
            cell.overflow_after_offset = self._write_overflow_block(cell.token_id, overflow_after, False)
        
        # Convert cell to binary
        binary_data = cell.to_binary()
        
        # Get current offset
        offset = self.current_offset
        
        # Write to file
        self.output_f.write(binary_data)
        self.output_f.flush()
        
        # Update current offset
        self.current_offset += len(binary_data)
        
        # Update index
        self.index.add_entry(cell.word, cell.token_id, offset, 0)  # tone_id=0 for now
        
        return offset
    
    def _write_overflow_block(self, parent_token_id: int, entries: List[Tuple[int, int, int]], is_before: bool) -> int:
        """
        Write an overflow block to the output file.
        
        Args:
            parent_token_id: Token ID of the parent word
            entries: List of (token_id, frequency, tone_id) tuples
            is_before: True if this block stores "before" context, False for "after"
            
        Returns:
            File offset where the block was written
        """
        if not self.output_f:
            raise ValueError("Writer not open")
        
        # Create overflow block
        block = OverflowBlock(parent_token_id, is_before)
        
        # Add entries
        for token_id, freq, tone_id in entries:
            block.add_entry(token_id, freq, tone_id)
        
        # Determine if we need to chain blocks (if too many entries)
        max_entries_per_block = 1000
        if len(entries) > max_entries_per_block:
            # Create additional blocks for remaining entries
            remaining_entries = entries[max_entries_per_block:]
            block.entries = entries[:max_entries_per_block]
            
            # Write the next block first to get its offset
            next_offset = self._write_overflow_block(parent_token_id, remaining_entries, is_before)
            
            # Set the next pointer
            block.next_overflow_ptr = next_offset
        
        # Convert block to binary
        binary_data = block.to_binary(compress=len(block.entries) > 100)
        
        # Get current offset
        offset = self.current_offset
        
        # Write to file
        self.output_f.write(binary_data)
        self.output_f.flush()
        
        # Update current offset
        self.current_offset += len(binary_data)
        
        return offset
    
    def write_from_json(self, json_file: str):
        """
        Write cells from a JSON file.
        
        JSON format:
        {
            "words": [
                {
                    "word": "example",
                    "frequency": 100,
                    "tone_signature": 0,
                    "before_context": [{"word": "an", "frequency": 50, "tone_id": 0}, ...],
                    "after_context": [{"word": "of", "frequency": 30, "tone_id": 0}, ...]
                },
                ...
            ]
        }
        """
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # First pass: assign token IDs to all words
        for word_data in data.get("words", []):
            word = word_data.get("word", "")
            if word:
                self.get_or_create_token_id(word)
                
                # Also assign token IDs to context words
                for ctx in word_data.get("before_context", []):
                    ctx_word = ctx.get("word", "")
                    if ctx_word:
                        self.get_or_create_token_id(ctx_word)
                
                for ctx in word_data.get("after_context", []):
                    ctx_word = ctx.get("word", "")
                    if ctx_word:
                        self.get_or_create_token_id(ctx_word)
        
        # Second pass: create and write cells
        for word_data in data.get("words", []):
            word = word_data.get("word", "")
            if not word:
                continue
                
            frequency = word_data.get("frequency", 0)
            tone_signature = word_data.get("tone_signature", 0)
            token_id = self.word_to_token_id.get(word, 0)
            
            if token_id == 0:
                continue  # Skip if no token ID
            
            # Create cell
            cell = BinaryCell(word, token_id, frequency, tone_signature)
            
            # Add before context
            for ctx in word_data.get("before_context", []):
                ctx_word = ctx.get("word", "")
                ctx_freq = ctx.get("frequency", 1)
                ctx_tone = ctx.get("tone_id", 0)
                
                ctx_token_id = self.word_to_token_id.get(ctx_word, 0)
                if ctx_token_id > 0:
                    cell.add_before_context(ctx_token_id, ctx_freq, ctx_tone)
            
            # Add after context
            for ctx in word_data.get("after_context", []):
                ctx_word = ctx.get("word", "")
                ctx_freq = ctx.get("frequency", 1)
                ctx_tone = ctx.get("tone_id", 0)
                
                ctx_token_id = self.word_to_token_id.get(ctx_word, 0)
                if ctx_token_id > 0:
                    cell.add_after_context(ctx_token_id, ctx_freq, ctx_tone)
            
            # Write cell
            self.write_cell(cell)


class BinaryCellReader:
    """
    Reads binary cell data and provides query interface.
    
    Handles the reading and querying of Binary Cell Structure data.
    """
    
    def __init__(self, data_file: str, index_file: str):
        """
        Initialize a new binary cell reader.
        
        Args:
            data_file: Path to binary data file
            index_file: Path to index file
        """
        self.data_file = data_file
        self.index_file = index_file
        self.data_f = None
        self.index = None
        self.mmap = None
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def open(self):
        """Open the data and index files."""
        if self.data_f:
            return  # Already open
        
        # Open data file
        self.data_f = open(self.data_file, 'rb')
        
        # Memory-map the data file for faster access
        self.mmap = mmap.mmap(self.data_f.fileno(), 0, access=mmap.ACCESS_READ)
        
        # Load index
        self.index = MasterIndex.load_from_file(self.index_file)
    
    def close(self):
        """Close the data and index files."""
        if self.mmap:
            self.mmap.close()
            self.mmap = None
        
        if self.data_f:
            self.data_f.close()
            self.data_f = None
        
        self.index = None
    
    def read_cell(self, offset: int) -> BinaryCell:
        """
        Read a binary cell from the data file.
        
        Args:
            offset: File offset where the cell is stored
            
        Returns:
            BinaryCell object
        """
        if not self.mmap:
            raise ValueError("Reader not open")
        
        # Seek to offset
        self.mmap.seek(offset)
        
        # Read header to determine size
        header_data = self.mmap.read(19)  # Fixed header size
        magic, word_length = struct.unpack('>HB', header_data[:3])
        
        # Verify magic bytes
        if magic != MAGIC_BYTES:
            raise ValueError(f"Invalid magic bytes at offset {offset}: {magic:04x}")
        
        # Calculate total size (approximate)
        # Header + word + before count + after count + overflow pointers + checksum
        approx_size = 19 + word_length + 2 + 2 + 16 + 4
        
        # Read before context count
        self.mmap.seek(offset + 19 + word_length)
        before_count = struct.unpack('>H', self.mmap.read(2))[0]
        
        # Add before context size
        approx_size += before_count * 10
        
        # Read after context count
        self.mmap.seek(offset + 19 + word_length + 2 + before_count * 10)
        after_count = struct.unpack('>H', self.mmap.read(2))[0]
        
        # Add after context size
        approx_size += after_count * 10
        
        # Read the entire cell data
        self.mmap.seek(offset)
        cell_data = self.mmap.read(approx_size)
        
        # Parse cell
        cell = BinaryCell.from_binary(cell_data)
        
        # Load overflow blocks if needed
        if cell.overflow_before_offset > 0:
            before_entries = self._read_overflow_entries(cell.overflow_before_offset)
            cell.before_context.extend(before_entries)
        
        if cell.overflow_after_offset > 0:
            after_entries = self._read_overflow_entries(cell.overflow_after_offset)
            cell.after_context.extend(after_entries)
        
        return cell
    
    def _read_overflow_entries(self, offset: int) -> List[Tuple[int, int, int]]:
        """
        Read entries from overflow blocks.
        
        Args:
            offset: File offset where the overflow block is stored
            
        Returns:
            List of (token_id, frequency, tone_id) tuples
        """
        if not self.mmap:
            raise ValueError("Reader not open")
        
        entries = []
        current_offset = offset
        
        while current_offset > 0:
            # Seek to offset
            self.mmap.seek(current_offset)
            
            # Read compression header
            compression_type = struct.unpack('>B', self.mmap.read(1))[0]
            
            # Read overflow block header
            header = self.mmap.read(10)
            magic, parent_token_id, entry_count = struct.unpack('>L L H', header)
            
            # Verify magic bytes
            if magic != OVERFLOW_MAGIC:
                raise ValueError(f"Invalid overflow magic at offset {current_offset}: {magic:08x}")
            
            # Read entries
            if compression_type == 0:  # Uncompressed
                for _ in range(entry_count):
                    entry_data = self.mmap.read(10)
                    token_id, freq, tone_id = struct.unpack('>LLH', entry_data)
                    entries.append((token_id, freq, tone_id))
                
                # Read next overflow pointer
                next_ptr = struct.unpack('>Q', self.mmap.read(8))[0]
            else:  # Compressed
                # Read the rest of the block
                compressed_data = bytearray()
                while True:
                    chunk = self.mmap.read(1024)
                    if not chunk:
                        break
                    compressed_data.extend(chunk)
                    # Try to decompress
                    try:
                        if b'zstd' in chunk[:4]:  # Check for zstd magic
                            import zstandard as zstd
                            decompressor = zstd.ZstdDecompressor()
                            decompressed = decompressor.decompress(compressed_data)
                        else:
                            decompressed = zlib.decompress(compressed_data)
                        break
                    except (zlib.error, ImportError):
                        # Need more data or zstd not available
                        pass
                
                # Parse decompressed data
                pos = 0
                for _ in range(entry_count):
                    token_id, freq, tone_id = struct.unpack('>LLH', decompressed[pos:pos+10])
                    entries.append((token_id, freq, tone_id))
                    pos += 10
                
                # Read next overflow pointer
                next_ptr = struct.unpack('>Q', decompressed[pos:pos+8])[0]
            
            # Update current offset for next iteration
            current_offset = next_ptr
        
        return entries
    
    def get_cell_by_word(self, word: str) -> Optional[BinaryCell]:
        """
        Get a cell by word.
        
        Args:
            word: Word to look up
            
        Returns:
            BinaryCell object or None if not found
        """
        if not self.index:
            raise ValueError("Reader not open")
        
        # Look up offset in index
        offset = self.index.get_offset(word)
        if offset is None:
            return None
        
        # Read cell
        return self.read_cell(offset)
    
    def get_cell_by_token_id(self, token_id: int) -> Optional[BinaryCell]:
        """
        Get a cell by token ID.
        
        Args:
            token_id: Token ID to look up
            
        Returns:
            BinaryCell object or None if not found
        """
        if not self.index:
            raise ValueError("Reader not open")
        
        # Look up word by token ID
        word = self.index.get_word_by_token_id(token_id)
        if word is None:
            return None
        
        # Get cell by word
        return self.get_cell_by_word(word)
    
    def get_context_words(self, word: str, before: bool = True, after: bool = True, 
                         limit: int = 10) -> Dict[str, int]:
        """
        Get context words for a word.
        
        Args:
            word: Word to get context for
            before: Whether to include words that appear before
            after: Whether to include words that appear after
            limit: Maximum number of context words to return
            
        Returns:
            Dictionary mapping context words to frequencies
        """
        # Get cell
        cell = self.get_cell_by_word(word)
        if cell is None:
            return {}
        
        # Collect context entries
        context_entries = []
        if before:
            context_entries.extend(cell.before_context)
        if after:
            context_entries.extend(cell.after_context)
        
        # Sort by frequency
        context_entries.sort(key=lambda x: x[1], reverse=True)
        
        # Limit number of entries
        context_entries = context_entries[:limit]
        
        # Convert token IDs to words
        result = {}
        for token_id, freq, _ in context_entries:
            context_word = self.index.get_word_by_token_id(token_id)
            if context_word:
                result[context_word] = freq
        
        return result
    
    def search_similar_words(self, word: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Search for words with similar context.
        
        Args:
            word: Word to find similar words for
            limit: Maximum number of similar words to return
            
        Returns:
            List of (word, similarity_score) tuples
        """
        # Get context for the input word
        cell = self.get_cell_by_word(word)
        if cell is None:
            return []
        
        # Create context vector (token_id -> frequency)
        context_vector = {}
        for token_id, freq, _ in cell.before_context:
            context_vector[token_id] = freq
        for token_id, freq, _ in cell.after_context:
            context_vector[token_id] = context_vector.get(token_id, 0) + freq
        
        # Calculate similarity with all other words
        similarities = []
        
        # This is inefficient but works for demonstration
        # In a real implementation, we would use an inverted index
        for other_word, other_hash in self.index.word_to_hash.items():
            if other_word == word:
                continue
                
            other_offset = self.index.hash_to_offset.get(other_hash)
            if other_offset is None:
                continue
                
            other_cell = self.read_cell(other_offset)
            
            # Create context vector for other word
            other_context = {}
            for token_id, freq, _ in other_cell.before_context:
                other_context[token_id] = freq
            for token_id, freq, _ in other_cell.after_context:
                other_context[token_id] = other_context.get(token_id, 0) + freq
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(context_vector, other_context)
            similarities.append((other_word, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Limit number of results
        return similarities[:limit]
    
    def _cosine_similarity(self, vec1: Dict[int, int], vec2: Dict[int, int]) -> float:
        """Calculate cosine similarity between two vectors."""
        # Find common keys
        common_keys = set(vec1.keys()) & set(vec2.keys())
        
        # Calculate dot product
        dot_product = sum(vec1[k] * vec2[k] for k in common_keys)
        
        # Calculate magnitudes
        mag1 = sum(v * v for v in vec1.values()) ** 0.5
        mag2 = sum(v * v for v in vec2.values()) ** 0.5
        
        # Calculate similarity
        if mag1 == 0 or mag2 == 0:
            return 0
        return dot_product / (mag1 * mag2)
