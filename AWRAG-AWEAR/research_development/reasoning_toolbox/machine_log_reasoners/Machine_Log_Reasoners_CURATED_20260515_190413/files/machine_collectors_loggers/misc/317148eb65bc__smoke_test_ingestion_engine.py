#!/usr/bin/env python3
"""
SMOKE TEST: Ingestion Engine
Tests that all modules were implemented correctly by Copilot.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("TEST 1: Module Imports")
    print("=" * 60)
    
    try:
        from ingestion_engine.contracts import RawInput, RawAnchor, SymbolEvent
        print("✓ contracts.py imports successfully")
    except Exception as e:
        print(f"✗ contracts.py FAILED: {e}")
        return False
    
    try:
        from ingestion_engine.adapters.file_watcher_adapter import FileWatcherAdapter
        print("✓ file_watcher_adapter.py imports successfully")
    except Exception as e:
        print(f"✗ file_watcher_adapter.py FAILED: {e}")
        return False
    
    try:
        from ingestion_engine.normalizer import Normalizer
        print("✓ normalizer.py imports successfully")
    except Exception as e:
        print(f"✗ normalizer.py FAILED: {e}")
        return False
    
    try:
        from ingestion_engine.gnome.symbol_genome_loader import SymbolGenomeLoader
        print("✓ symbol_genome_loader.py imports successfully")
    except Exception as e:
        print(f"✗ symbol_genome_loader.py FAILED: {e}")
        return False
    
    try:
        from ingestion_engine.gnome.symbolizer import Symbolizer
        print("✓ symbolizer.py imports successfully")
    except Exception as e:
        print(f"✗ symbolizer.py FAILED: {e}")
        return False
    
    try:
        from ingestion_engine.persistence.sqlite_writer import SQLiteWriter
        print("✓ sqlite_writer.py imports successfully")
    except Exception as e:
        print(f"✗ sqlite_writer.py FAILED: {e}")
        return False
    
    try:
        from ingestion_engine.persistence.sqlite_reader import SQLiteReader
        print("✓ sqlite_reader.py imports successfully")
    except Exception as e:
        print(f"✗ sqlite_reader.py FAILED: {e}")
        return False
    
    try:
        from ingestion_engine.session_manager import SessionManager
        print("✓ session_manager.py imports successfully")
    except Exception as e:
        print(f"✗ session_manager.py FAILED: {e}")
        return False
    
    try:
        from ingestion_engine.orchestrator import IngestionOrchestrator
        print("✓ orchestrator.py imports successfully")
    except Exception as e:
        print(f"✗ orchestrator.py FAILED: {e}")
        return False
    
    print("\n✓ All imports successful\n")
    return True


def test_data_contracts():
    """Test that data contracts have the correct structure."""
    print("=" * 60)
    print("TEST 2: Data Contract Structure")
    print("=" * 60)
    
    from ingestion_engine.contracts import RawInput, RawAnchor, SymbolEvent
    from uuid import uuid4
    
    # Test RawInput
    try:
        raw_input = RawInput(
            source_id="test",
            channel="test_channel",
            payload="test payload",
            metadata={}
        )
        assert "source_id" in raw_input
        assert "channel" in raw_input
        assert "payload" in raw_input
        assert "metadata" in raw_input
        print("✓ RawInput structure correct")
    except Exception as e:
        print(f"✗ RawInput FAILED: {e}")
        return False
    
    # Test RawAnchor
    try:
        raw_anchor = RawAnchor(
            event_id=uuid4(),
            session_id=uuid4(),
            pulse_id=1,
            source_id="test",
            channel="test_channel",
            payload="test payload",
            payload_hash="abc123",
            metadata={},
            ingest_ts=123.456
        )
        assert "event_id" in raw_anchor
        assert "session_id" in raw_anchor
        assert "pulse_id" in raw_anchor
        assert "payload_hash" in raw_anchor
        print("✓ RawAnchor structure correct")
    except Exception as e:
        print(f"✗ RawAnchor FAILED: {e}")
        return False
    
    # Test SymbolEvent
    try:
        symbol_event = SymbolEvent(
            event_id=uuid4(),
            session_id=uuid4(),
            pulse_id=1,
            symbol_id=12345,
            context_symbols=[1, 2, 3],
            integrity_hash="abc123",
            genome_version="v1.0"
        )
        assert "symbol_id" in symbol_event
        assert "context_symbols" in symbol_event
        assert "integrity_hash" in symbol_event
        assert "genome_version" in symbol_event
        print("✓ SymbolEvent structure correct")
    except Exception as e:
        print(f"✗ SymbolEvent FAILED: {e}")
        return False
    
    print("\n✓ All data contracts valid\n")
    return True


def test_normalizer():
    """Test that the Normalizer works."""
    print("=" * 60)
    print("TEST 3: Normalizer Functionality")
    print("=" * 60)
    
    from ingestion_engine.normalizer import Normalizer
    from ingestion_engine.contracts import RawInput
    from uuid import uuid4
    
    normalizer = Normalizer()
    
    raw_input = RawInput(
        source_id="test_source",
        channel="test_channel",
        payload="test payload",
        metadata={"key": "value"}
    )
    
    try:
        raw_anchor = normalizer.normalize(raw_input, uuid4(), 1)
        
        assert raw_anchor["payload"] == "test payload"
        assert raw_anchor["pulse_id"] == 1
        assert "payload_hash" in raw_anchor
        assert "ingest_ts" in raw_anchor
        
        print("✓ Normalizer produces valid RawAnchor")
        print(f"  - event_id: {raw_anchor['event_id']}")
        print(f"  - payload_hash: {raw_anchor['payload_hash'][:16]}...")
        print(f"  - ingest_ts: {raw_anchor['ingest_ts']}")
    except Exception as e:
        print(f"✗ Normalizer FAILED: {e}")
        return False
    
    print("\n✓ Normalizer works\n")
    return True


def test_database_schema():
    """Test that the database schema is correct."""
    print("=" * 60)
    print("TEST 4: Database Schema")
    print("=" * 60)
    
    import sqlite3
    import tempfile
    from pathlib import Path
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Run the migration
        migration_sql = Path("migrations/001_init.sql").read_text()
        conn = sqlite3.connect(db_path)
        conn.executescript(migration_sql)
        conn.close()
        
        # Check that tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ["sessions", "raw_events", "symbol_events", "symbol_collisions"]
        for table in required_tables:
            if table in tables:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' MISSING")
                return False
        
        conn.close()
        
        # Clean up
        Path(db_path).unlink()
        
    except Exception as e:
        print(f"✗ Database schema FAILED: {e}")
        return False
    
    print("\n✓ Database schema valid\n")
    return True


def test_end_to_end():
    """Test a minimal end-to-end flow."""
    print("=" * 60)
    print("TEST 5: End-to-End Smoke Test")
    print("=" * 60)
    
    import tempfile
    import sqlite3
    from pathlib import Path
    from uuid import uuid4
    
    from ingestion_engine.normalizer import Normalizer
    from ingestion_engine.persistence.sqlite_writer import SQLiteWriter
    from ingestion_engine.session_manager import SessionManager
    from ingestion_engine.contracts import RawInput
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database
        migration_sql = Path("migrations/001_init.sql").read_text()
        conn = sqlite3.connect(db_path)
        conn.executescript(migration_sql)
        conn.close()
        
        # Create session
        session_manager = SessionManager(db_path)
        session_id = session_manager.open_session("v1.0", "test_hash", ["test_adapter"])
        print(f"✓ Session created: {session_id}")
        
        # Normalize input
        normalizer = Normalizer()
        raw_input = RawInput(
            source_id="test",
            channel="test",
            payload="hello world",
            metadata={}
        )
        raw_anchor = normalizer.normalize(raw_input, session_id, 1)
        print("✓ RawAnchor created")
        
        # Write to database
        writer = SQLiteWriter(db_path)
        writer.write_raw_anchor(raw_anchor)
        print("✓ RawAnchor written to database")
        
        # Verify it was written
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw_events;")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 1:
            print(f"✓ Verified: 1 event in database")
        else:
            print(f"✗ Expected 1 event, found {count}")
            return False
        
        # Clean up
        Path(db_path).unlink()
        
    except Exception as e:
        print(f"✗ End-to-end test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✓ End-to-end smoke test passed\n")
    return True


def main():
    """Run all smoke tests."""
    print("\n" + "=" * 60)
    print("INGESTION ENGINE - SMOKE TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        test_imports,
        test_data_contracts,
        test_normalizer,
        test_database_schema,
        test_end_to_end,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ Test crashed: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED - Copilot implementation is valid\n")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - Review Copilot implementation\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
