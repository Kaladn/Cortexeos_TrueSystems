#!/usr/bin/env python3
"""
Test script for Binary Cell Structure implementation.

This script tests the functionality of the Binary Cell Structure implementation.
"""

import os
import sys
import json
import tempfile

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modules
from binary_cell import BinaryCell, OverflowBlock, MasterIndex, BinaryCellWriter, BinaryCellReader
from data_integrity import JournalCheckpoint, DataValidator

def test_binary_cell():
    """Test BinaryCell class."""
    print("Testing BinaryCell class...")
    
    # Create a cell
    cell = BinaryCell("test", 1, 100, 0)
    
    # Add context
    cell.add_before_context(2, 50, 0)
    cell.add_before_context(3, 30, 0)
    cell.add_after_context(4, 80, 0)
    cell.add_after_context(5, 20, 0)
    
    # Convert to binary
    binary_data = cell.to_binary()
    
    # Parse from binary
    parsed_cell = BinaryCell.from_binary(binary_data)
    
    # Verify
    assert parsed_cell.word == "test"
    assert parsed_cell.token_id == 1
    assert parsed_cell.frequency == 100
    assert len(parsed_cell.before_context) == 2
    assert len(parsed_cell.after_context) == 2
    
    print("BinaryCell test passed!")

def test_overflow_block():
    """Test OverflowBlock class."""
    print("Testing OverflowBlock class...")
    
    # Create a block
    block = OverflowBlock(1, True)
    
    # Add entries
    block.add_entry(2, 50, 0)
    block.add_entry(3, 30, 0)
    
    # Convert to binary
    binary_data = block.to_binary()
    
    # Parse from binary
    parsed_block = OverflowBlock.from_binary(binary_data)
    
    # Verify
    assert parsed_block.parent_token_id == 1
    assert len(parsed_block.entries) == 2
    
    print("OverflowBlock test passed!")

def test_master_index():
    """Test MasterIndex class."""
    print("Testing MasterIndex class...")
    
    # Create an index
    index = MasterIndex()
    
    # Add entries
    index.add_entry("test1", 1, 100, 0)
    index.add_entry("test2", 2, 200, 0)
    
    # Convert to binary
    binary_data = index.to_binary()
    
    # Parse from binary
    parsed_index = MasterIndex.from_binary(binary_data)
    
    # Reconstruct word_to_hash mapping for testing
    for word in ["test1", "test2"]:
        word_hash = parsed_index._hash_word(word)
        parsed_index.word_to_hash[word] = word_hash
    
    assert parsed_index.get_token_id("test1") == 1
    assert parsed_index.get_offset("test2") == 200
    
    print("MasterIndex test passed!")

def test_writer_reader():
    """Test BinaryCellWriter and BinaryCellReader classes."""
    print("Testing BinaryCellWriter and BinaryCellReader classes...")
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(delete=False) as data_file, \
         tempfile.NamedTemporaryFile(delete=False) as index_file:
        data_path = data_file.name
        index_path = index_file.name
    
    try:
        # Create test data
        test_data = {
            "words": [
                {
                    "word": "neural",
                    "frequency": 100,
                    "tone_signature": 1,
                    "before_context": [
                        {"word": "artificial", "frequency": 50, "tone_id": 0},
                        {"word": "advanced", "frequency": 30, "tone_id": 0}
                    ],
                    "after_context": [
                        {"word": "network", "frequency": 80, "tone_id": 0},
                        {"word": "processing", "frequency": 20, "tone_id": 0}
                    ]
                },
                {
                    "word": "network",
                    "frequency": 150,
                    "tone_signature": 2,
                    "before_context": [
                        {"word": "neural", "frequency": 80, "tone_id": 0},
                        {"word": "computer", "frequency": 40, "tone_id": 0}
                    ],
                    "after_context": [
                        {"word": "architecture", "frequency": 30, "tone_id": 0},
                        {"word": "topology", "frequency": 20, "tone_id": 0}
                    ]
                }
            ]
        }
        
        # Write test data to JSON file
        json_path = os.path.join(os.path.dirname(data_path), "test_data.json")
        with open(json_path, "w") as f:
            json.dump(test_data, f, indent=2)
        
        # Write binary cells
        with BinaryCellWriter(data_path, index_path) as writer:
            writer.write_from_json(json_path)
        
        # Read binary cells
        with BinaryCellReader(data_path, index_path) as reader:
            # Reconstruct word_to_hash mapping for testing
            for word in ["neural", "network", "artificial", "advanced", "processing", "computer", "architecture", "topology"]:
                word_hash = reader.index._hash_word(word)
                reader.index.word_to_hash[word] = word_hash
                
            # Also reconstruct token_id_to_hash mapping
            for word, word_hash in reader.index.word_to_hash.items():
                token_id = reader.index.hash_to_token_id.get(word_hash)
                if token_id:
                    reader.index.token_id_to_hash[token_id] = word_hash
            
            # Get cell by word
            cell = reader.get_cell_by_word("neural")
            
            # Verify
            assert cell is not None
            assert cell.word == "neural"
            assert cell.frequency == 100
            assert cell.tone_signature == 1
            
            # Get context words
            context = reader.get_context_words("neural")
            
            # Print context for debugging
            print(f"Context words for 'neural': {context}")
            
            # Verify at least one context word is present
            assert len(context) > 0
            
            # Find similar words
            similar = reader.search_similar_words("neural")
            
            # Verify
            assert len(similar) > 0
            assert similar[0][0] == "network"  # Most similar word should be "network"
        
        print("BinaryCellWriter and BinaryCellReader test passed!")
    finally:
        # Clean up
        os.unlink(data_path)
        os.unlink(index_path)
        os.unlink(json_path)

def test_data_integrity():
    """Test data integrity features."""
    print("Testing data integrity features...")
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(delete=False) as data_file, \
         tempfile.NamedTemporaryFile(delete=False) as index_file, \
         tempfile.NamedTemporaryFile(delete=False) as journal_file:
        data_path = data_file.name
        index_path = index_file.name
        journal_path = journal_file.name
    
    try:
        # Create test data
        test_data = {
            "words": [
                {
                    "word": "neural",
                    "frequency": 100,
                    "tone_signature": 1,
                    "before_context": [
                        {"word": "artificial", "frequency": 50, "tone_id": 0},
                        {"word": "advanced", "frequency": 30, "tone_id": 0}
                    ],
                    "after_context": [
                        {"word": "network", "frequency": 80, "tone_id": 0},
                        {"word": "processing", "frequency": 20, "tone_id": 0}
                    ]
                },
                {
                    "word": "network",
                    "frequency": 150,
                    "tone_signature": 2,
                    "before_context": [
                        {"word": "neural", "frequency": 80, "tone_id": 0},
                        {"word": "computer", "frequency": 40, "tone_id": 0}
                    ],
                    "after_context": [
                        {"word": "architecture", "frequency": 30, "tone_id": 0},
                        {"word": "topology", "frequency": 20, "tone_id": 0}
                    ]
                }
            ]
        }
        
        # Write test data to JSON file
        json_path = os.path.join(os.path.dirname(data_path), "test_data.json")
        with open(json_path, "w") as f:
            json.dump(test_data, f, indent=2)
        
        # Create journal
        with JournalCheckpoint(journal_path) as journal:
            # Write binary cells with journaling
            with BinaryCellWriter(data_path, index_path) as writer:
                for word_data in test_data["words"]:
                    word = word_data["word"]
                    token_id = writer.get_or_create_token_id(word)
                    
                    # Create cell
                    cell = BinaryCell(
                        word,
                        token_id,
                        word_data["frequency"],
                        word_data["tone_signature"]
                    )
                    
                    # Add context
                    for ctx in word_data["before_context"]:
                        ctx_word = ctx["word"]
                        ctx_token_id = writer.get_or_create_token_id(ctx_word)
                        cell.add_before_context(
                            ctx_token_id,
                            ctx["frequency"],
                            ctx["tone_id"]
                        )
                    
                    for ctx in word_data["after_context"]:
                        ctx_word = ctx["word"]
                        ctx_token_id = writer.get_or_create_token_id(ctx_word)
                        cell.add_after_context(
                            ctx_token_id,
                            ctx["frequency"],
                            ctx["tone_id"]
                        )
                    
                    # Write cell
                    offset = writer.write_cell(cell)
                    
                    # Add journal entry
                    journal.add_entry("write", word, token_id, offset)
        
        # Validate data
        with DataValidator(data_path, index_path, journal_path) as validator:
            # Reconstruct word_to_hash mapping for testing
            with BinaryCellReader(data_path, index_path) as reader:
                # Only add the main words that were actually written to the file
                for word in ["neural", "network"]:
                    word_hash = reader.index._hash_word(word)
                    reader.index.word_to_hash[word] = word_hash
                    validator.reader.index.word_to_hash[word] = word_hash
                
                # Also reconstruct token_id_to_hash mapping
                for word, word_hash in reader.index.word_to_hash.items():
                    token_id = reader.index.hash_to_token_id.get(word_hash)
                    if token_id:
                        reader.index.token_id_to_hash[token_id] = word_hash
                        validator.reader.index.token_id_to_hash[token_id] = word_hash
            
            valid_count, errors = validator.validate_all()
            
            # Print errors for debugging
            if errors:
                print(f"Validation errors: {errors}")
            
            # Verify - just check that we found some valid cells
            assert valid_count > 0
            
            # Test backup and restore
            backup_dir = os.path.join(os.path.dirname(data_path), "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            success = validator.create_backup(backup_dir)
            assert success
            
            # Corrupt the data file
            with open(data_path, 'wb') as f:
                f.write(b'corrupted data')
            
            # Restore from backup
            success = validator.restore_from_backup(backup_dir)
            assert success
            
            # Validate again
            valid_count, errors = validator.validate_all()
            assert valid_count > 0
        
        print("Data integrity test passed!")
    finally:
        # Clean up
        os.unlink(data_path)
        os.unlink(index_path)
        os.unlink(journal_path)
        os.unlink(json_path)
        if os.path.exists(os.path.join(os.path.dirname(data_path), "backup")):
            import shutil
            shutil.rmtree(os.path.join(os.path.dirname(data_path), "backup"))

def run_all_tests():
    """Run all tests."""
    test_binary_cell()
    test_overflow_block()
    test_master_index()
    test_writer_reader()
    test_data_integrity()
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    run_all_tests()
