"""
Retrospection Report Writer
Immutable snapshot system for workspace analysis.

Core Principle: A retrospection report is an EVENT, not a catalog.
Reports are immutable once created. No updates, only new reports.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class RetrospectionWriter:
    """Writer for immutable retrospection reports."""
    
    def __init__(self, db_path: str):
        """Initialize writer with database path."""
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        
    def __enter__(self):
        """Context manager entry."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._conn:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
            self._conn.close()
            self._conn = None
    
    def initialize_database(self):
        """Create all tables. Only call once on new database."""
        cursor = self._conn.cursor()
        
        # 1. Retrospection reports (the anchor)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retrospection_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_name TEXT NOT NULL,
                workspace_root TEXT NOT NULL,
                canonical_root TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Modules (scoped to a report)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                module_name TEXT NOT NULL,
                intended_role TEXT,
                what_it_does TEXT,
                what_it_does_not_do TEXT,
                FOREIGN KEY (report_id) REFERENCES retrospection_reports(id) ON DELETE CASCADE,
                UNIQUE(report_id, module_name)
            )
        """)
        
        # 3. Data ownership
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_ownership (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                ownership_type TEXT NOT NULL
                    CHECK(ownership_type IN ('creates', 'consumes', 'persists', 'does_not_persist')),
                data_type TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        """)
        
        # 4. Public interfaces
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_interfaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                interface_type TEXT NOT NULL
                    CHECK(interface_type IN ('class', 'function', 'method')),
                name TEXT NOT NULL,
                input_types TEXT,
                output_types TEXT,
                side_effects TEXT,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        """)
        
        # 5. Dependencies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                dependency_type TEXT NOT NULL
                    CHECK(dependency_type IN ('internal', 'external', 'runtime')),
                dependency_name TEXT NOT NULL,
                import_path TEXT,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        """)
        
        # 6. State & memory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                state_description TEXT,
                is_bounded BOOLEAN,
                eviction_policy TEXT,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        """)
        
        # 7. Integration points
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integration_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                point_type TEXT NOT NULL
                    CHECK(point_type IN ('upstream_input', 'downstream_output', 'external_condition')),
                description TEXT NOT NULL,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        """)
        
        # 8. Open questions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS open_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                question_type TEXT NOT NULL
                    CHECK(question_type IN (
                        'unused_code',
                        'unraised_exception',
                        'missing_component',
                        'implicit_assumption'
                    )),
                question_text TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_modules_report ON modules(report_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_ownership_module ON data_ownership(module_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_public_interfaces_module ON public_interfaces(module_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dependencies_module ON dependencies(module_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_state_memory_module ON state_memory(module_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_integration_points_module ON integration_points(module_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_open_questions_module ON open_questions(module_id)")
        
        self._conn.commit()
    
    def create_report(self, report_name: str, workspace_root: str, 
                     canonical_root: Optional[str] = None, 
                     description: Optional[str] = None) -> int:
        """
        Create a new retrospection report.
        Returns report_id.
        """
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO retrospection_reports (report_name, workspace_root, canonical_root, description)
            VALUES (?, ?, ?, ?)
        """, (report_name, workspace_root, canonical_root, description))
        return cursor.lastrowid
    
    def add_module(self, report_id: int, module_name: str,
                   intended_role: Optional[str] = None,
                   what_it_does: Optional[str] = None,
                   what_it_does_not_do: Optional[str] = None) -> int:
        """
        Add a module to a report.
        Returns module_id.
        """
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO modules (report_id, module_name, intended_role, what_it_does, what_it_does_not_do)
            VALUES (?, ?, ?, ?, ?)
        """, (report_id, module_name, intended_role, what_it_does, what_it_does_not_do))
        return cursor.lastrowid
    
    def add_data_ownership(self, module_id: int, ownership_type: str, 
                          data_type: str, description: Optional[str] = None):
        """Add data ownership entry."""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO data_ownership (module_id, ownership_type, data_type, description)
            VALUES (?, ?, ?, ?)
        """, (module_id, ownership_type, data_type, description))
    
    def add_public_interface(self, module_id: int, interface_type: str, name: str,
                            input_types: Optional[str] = None,
                            output_types: Optional[str] = None,
                            side_effects: Optional[str] = None):
        """Add public interface entry."""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO public_interfaces (module_id, interface_type, name, input_types, output_types, side_effects)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (module_id, interface_type, name, input_types, output_types, side_effects))
    
    def add_dependency(self, module_id: int, dependency_type: str, 
                      dependency_name: str, import_path: Optional[str] = None):
        """Add dependency entry."""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO dependencies (module_id, dependency_type, dependency_name, import_path)
            VALUES (?, ?, ?, ?)
        """, (module_id, dependency_type, dependency_name, import_path))
    
    def add_state_memory(self, module_id: int, state_description: str,
                        is_bounded: Optional[bool] = None,
                        eviction_policy: Optional[str] = None):
        """Add state & memory entry."""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO state_memory (module_id, state_description, is_bounded, eviction_policy)
            VALUES (?, ?, ?, ?)
        """, (module_id, state_description, is_bounded, eviction_policy))
    
    def add_integration_point(self, module_id: int, point_type: str, description: str):
        """Add integration point entry."""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO integration_points (module_id, point_type, description)
            VALUES (?, ?, ?)
        """, (module_id, point_type, description))
    
    def add_open_question(self, module_id: int, question_type: str, 
                         question_text: str, resolved: bool = False):
        """Add open question entry."""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO open_questions (module_id, question_type, question_text, resolved)
            VALUES (?, ?, ?, ?)
        """, (module_id, question_type, question_text, resolved))


# Example usage
if __name__ == "__main__":
    # Create a new retrospection database
    with RetrospectionWriter("retrospection.db") as writer:
        # Initialize database (only needed once)
        writer.initialize_database()
        
        # Create a report
        report_id = writer.create_report(
            report_name="Initial Analysis",
            workspace_root="F:\\From removable drive\\AI_Storage",
            canonical_root=None,
            description="First retrospection of AI_Storage workspace"
        )
        
        # Add a module
        module_id = writer.add_module(
            report_id=report_id,
            module_name="jsonsymbol.py",
            intended_role="JSON symbol processing",
            what_it_does="Processes and transforms JSON symbol data",
            what_it_does_not_do="Does not persist to external database"
        )
        
        # Add module details
        writer.add_data_ownership(module_id, "consumes", "dict[str, Any]", "JSON symbol dictionaries")
        writer.add_public_interface(module_id, "function", "process_symbols", 
                                   input_types="dict", output_types="dict", 
                                   side_effects="none")
        writer.add_dependency(module_id, "external", "json", "import json")
        
    print(f"Report {report_id} created successfully")
