"""
Test fixtures for Wolf Engine acceptance tests.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid

import pytest

from wolf_engine.contracts import RawAnchor
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gnome.gnome_service import GnomeService
from wolf_engine.sql.sqlite_reader import SQLiteReader
from wolf_engine.sql.sqlite_writer import SQLiteWriter


def create_test_anchor(token: str, session_id: str = "", pulse_id: int = 1) -> RawAnchor:
    """Create a RawAnchor for testing."""
    return RawAnchor(
        event_id=str(uuid.uuid4()),
        session_id=session_id or str(uuid.uuid4()),
        pulse_id=pulse_id,
        token=token,
        context_before=["before1", "before2"],
        context_after=["after1", "after2"],
        position=0,
    )


@pytest.fixture
def genome_path(tmp_path):
    """Create a minimal Symbol Genome dictionary for testing."""
    genome_data = {
        "metadata": {
            "version": "v1.0",
            "total_symbols": 3,
            "categories": ["core", "specialized"],
        },
        "symbols": {
            "architecture": {
                "symbol_hex": "A1B2C3D4E5",
                "symbol_id_64": 1234567890,
                "category": "core",
                "priority": 1,
                "visual_grid": "########",
            },
            "data": {
                "symbol_hex": "F1F2F3F4F5",
                "symbol_id_64": 9876543210,
                "category": "core",
                "priority": 2,
                "visual_grid": "@@@@@@@@",
            },
            "test": {
                "symbol_hex": "010203040506",
                "symbol_id_64": 5555555555,
                "category": "specialized",
                "priority": 3,
                "visual_grid": "!!!!!!!!",
            },
        },
    }
    path = tmp_path / "symbol_genome_master_dictionary.json"
    path.write_text(json.dumps(genome_data), encoding="utf-8")
    return str(path)


@pytest.fixture
def db_path(tmp_path):
    """Return a temporary database path."""
    return str(tmp_path / "wolf_engine_test.db")


@pytest.fixture
def gnome(genome_path):
    """Create a GnomeService for testing."""
    return GnomeService(genome_path)


@pytest.fixture
def sql_writer(db_path):
    """Create a SQLiteWriter for testing."""
    writer = SQLiteWriter(db_path)
    yield writer
    writer.close()


@pytest.fixture
def sql_reader(db_path, sql_writer):
    """Create a SQLiteReader (depends on writer to ensure schema exists)."""
    reader = SQLiteReader(db_path)
    yield reader
    reader.close()


@pytest.fixture
def forge():
    """Create a ForgeMemory for testing."""
    return ForgeMemory(window_size=10000)


@pytest.fixture
def session_id(sql_writer):
    """Create a test session and return its ID."""
    sid = str(uuid.uuid4())
    sql_writer.create_session(sid, "v1.0", "test_config_hash")
    return sid
