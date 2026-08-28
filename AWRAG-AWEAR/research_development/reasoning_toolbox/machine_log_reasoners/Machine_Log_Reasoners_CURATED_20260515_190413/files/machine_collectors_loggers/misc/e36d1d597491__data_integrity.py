#!/usr/bin/env python3
"""
Data Integrity Module for Binary Cell Structure

This module provides additional data integrity features for the Binary Cell Structure:
- Journal checkpointing for crash recovery
- Periodic validation of binary data
- Repair mechanisms for corrupted data
"""

import os
import sys
import struct
import zlib
import json
import time
import hashlib
from typing import Dict, List, Tuple, Set, Optional

# Import from binary_cell module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from binary_cell import BinaryCell, OverflowBlock, MasterIndex, BinaryCellReader, BinaryCellWriter

class JournalCheckpoint:
    """
    Implements journal checkpointing for crash recovery.
    
    Maintains a journal of write operations to allow recovery in case of crashes.
    """
    
    def __init__(self, journal_file: str):
        """
        Initialize a new journal checkpoint.
        
        Args:
            journal_file: Path to journal file
        """
        self.journal_file = journal_file
        self.journal_f = None
        self.entries = []
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def open(self):
        """Open the journal file."""
        if self.journal_f:
            return  # Already open
        
        # Open journal file in append mode
        self.journal_f = open(self.journal_file, 'a+')
        
        # Read existing entries
        self.journal_f.seek(0)
        for line in self.journal_f:
            try:
                entry = json.loads(line.strip())
                self.entries.append(entry)
            except json.JSONDecodeError:
                # Skip invalid entries
                pass
    
    def close(self):
        """Close the journal file."""
        if self.journal_f:
            self.journal_f.close()
            self.journal_f = None
    
    def add_entry(self, operation: str, word: str, token_id: int, offset: int):
        """
        Add a journal entry.
        
        Args:
            operation: Operation type (e.g., "write", "update")
            word: Word being operated on
            token_id: Token ID of the word
            offset: File offset where the word's data is stored
        """
        if not self.journal_f:
            raise ValueError("Journal not open")
        
        # Create entry
        entry = {
            "timestamp": time.time(),
            "operation": operation,
            "word": word,
            "token_id": token_id,
            "offset": offset
        }
        
        # Add to in-memory list
        self.entries.append(entry)
        
        # Write to file
        self.journal_f.write(json.dumps(entry) + "\n")
        self.journal_f.flush()
    
    def get_entries(self, since_timestamp: float = 0) -> List[Dict]:
        """
        Get journal entries since a timestamp.
        
        Args:
            since_timestamp: Timestamp to filter entries
            
        Returns:
            List of journal entries
        """
        return [entry for entry in self.entries if entry["timestamp"] > since_timestamp]
    
    def clear(self):
        """Clear the journal."""
        if self.journal_f:
            self.journal_f.close()
        
        # Truncate file
        self.journal_f = open(self.journal_file, 'w')
        self.journal_f.close()
        
        # Reopen in append mode
        self.journal_f = open(self.journal_file, 'a+')
        self.entries = []


class DataValidator:
    """
    Validates binary cell data for integrity.
    
    Provides methods to check and repair corrupted data.
    """
    
    def __init__(self, data_file: str, index_file: str, journal_file: str = None):
        """
        Initialize a new data validator.
        
        Args:
            data_file: Path to binary data file
            index_file: Path to index file
            journal_file: Path to journal file (optional)
        """
        self.data_file = data_file
        self.index_file = index_file
        self.journal_file = journal_file
        self.reader = None
        self.journal = None
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def open(self):
        """Open the data files."""
        if self.reader:
            return  # Already open
        
        # Open reader
        self.reader = BinaryCellReader(self.data_file, self.index_file)
        self.reader.open()
        
        # Open journal if provided
        if self.journal_file:
            self.journal = JournalCheckpoint(self.journal_file)
            self.journal.open()
    
    def close(self):
        """Close the data files."""
        if self.reader:
            self.reader.close()
            self.reader = None
        
        if self.journal:
            self.journal.close()
            self.journal = None
    
    def validate_all(self) -> Tuple[int, List[Dict]]:
        """
        Validate all cells in the data file.
        
        Returns:
            Tuple of (valid_count, errors)
        """
        if not self.reader or not self.reader.data_f:
            # Open reader if not already open
            if not self.reader:
                self.open()
            else:
                self.reader.open()
        
        valid_count = 0
        errors = []
        
        # Iterate through all words in the index
        for word, word_hash in self.reader.index.word_to_hash.items():
            offset = self.reader.index.hash_to_offset.get(word_hash)
            if offset is None:
                errors.append({
                    "word": word,
                    "error": "Missing offset in index"
                })
                continue
            
            # Try to read cell
            try:
                cell = self.reader.read_cell(offset)
                
                # Verify word matches
                if cell.word != word:
                    errors.append({
                        "word": word,
                        "error": f"Word mismatch: expected '{word}', got '{cell.word}'"
                    })
                    continue
                
                # Verify token ID matches
                expected_token_id = self.reader.index.hash_to_token_id.get(word_hash)
                if cell.token_id != expected_token_id:
                    errors.append({
                        "word": word,
                        "error": f"Token ID mismatch: expected {expected_token_id}, got {cell.token_id}"
                    })
                    continue
                
                valid_count += 1
            except Exception as e:
                errors.append({
                    "word": word,
                    "error": str(e)
                })
        
        return valid_count, errors
    
    def repair_from_journal(self) -> Tuple[int, List[Dict]]:
        """
        Repair corrupted data using the journal.
        
        Returns:
            Tuple of (repaired_count, errors)
        """
        if not self.reader or not self.journal:
            raise ValueError("Validator or journal not open")
        
        repaired_count = 0
        errors = []
        
        # Get all journal entries
        entries = self.journal.get_entries()
        
        # Group by word (keep only the latest entry for each word)
        word_to_entry = {}
        for entry in entries:
            word = entry["word"]
            word_to_entry[word] = entry
        
        # Create a temporary file for repaired data
        temp_data_file = f"{self.data_file}.repair"
        temp_index_file = f"{self.index_file}.repair"
        
        # Create writer for repaired data
        with BinaryCellWriter(temp_data_file, temp_index_file) as writer:
            # Read all valid cells and write them to the new file
            for word, entry in word_to_entry.items():
                try:
                    # Try to read the cell from the original file
                    cell = self.reader.get_cell_by_word(word)
                    
                    if cell:
                        # Write the cell to the new file
                        writer.write_cell(cell)
                        repaired_count += 1
                except Exception as e:
                    errors.append({
                        "word": word,
                        "error": str(e)
                    })
        
        # Replace original files with repaired files
        if repaired_count > 0:
            os.rename(temp_data_file, self.data_file)
            os.rename(temp_index_file, self.index_file)
        else:
            # Remove temporary files if no repairs were made
            os.remove(temp_data_file)
            os.remove(temp_index_file)
        
        return repaired_count, errors
    
    def create_backup(self, backup_dir: str) -> bool:
        """
        Create a backup of the data and index files.
        
        Args:
            backup_dir: Directory to store backups
            
        Returns:
            True if backup was successful, False otherwise
        """
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        data_backup = os.path.join(backup_dir, f"{os.path.basename(self.data_file)}.{timestamp}")
        index_backup = os.path.join(backup_dir, f"{os.path.basename(self.index_file)}.{timestamp}")
        
        try:
            # Copy files
            with open(self.data_file, 'rb') as src, open(data_backup, 'wb') as dst:
                dst.write(src.read())
            
            with open(self.index_file, 'rb') as src, open(index_backup, 'wb') as dst:
                dst.write(src.read())
            
            return True
        except Exception:
            return False
    
    def restore_from_backup(self, backup_dir: str, timestamp: str = None) -> bool:
        """
        Restore data and index files from backup.
        
        Args:
            backup_dir: Directory containing backups
            timestamp: Specific backup timestamp to restore (latest if None)
            
        Returns:
            True if restore was successful, False otherwise
        """
        try:
            # Find backup files
            if timestamp:
                data_backup = os.path.join(backup_dir, f"{os.path.basename(self.data_file)}.{timestamp}")
                index_backup = os.path.join(backup_dir, f"{os.path.basename(self.index_file)}.{timestamp}")
            else:
                # Find latest backup
                data_backups = [f for f in os.listdir(backup_dir) if f.startswith(os.path.basename(self.data_file))]
                index_backups = [f for f in os.listdir(backup_dir) if f.startswith(os.path.basename(self.index_file))]
                
                if not data_backups or not index_backups:
                    return False
                
                data_backups.sort(reverse=True)
                index_backups.sort(reverse=True)
                
                data_backup = os.path.join(backup_dir, data_backups[0])
                index_backup = os.path.join(backup_dir, index_backups[0])
            
            # Check if backup files exist
            if not os.path.exists(data_backup) or not os.path.exists(index_backup):
                return False
            
            # Close reader if open
            if self.reader:
                self.reader.close()
                self.reader = None
            
            # Restore files
            with open(data_backup, 'rb') as src, open(self.data_file, 'wb') as dst:
                dst.write(src.read())
            
            with open(index_backup, 'rb') as src, open(self.index_file, 'wb') as dst:
                dst.write(src.read())
            
            return True
        except Exception:
            return False
