Common utilities for all loggers.

Features:
1. Unified timestamp format
2. Auto-cleanup of data older than 1 day
3. Evidence sealing when issues detected
4. Session metadata creation
5. System health checks
6. Rate limiting for high-frequency writes
7. Session compression for archival

ALL loggers import from here to ensure format consistency.
"""

import os
import json
import time
import gzip
import shutil
import tarfile
import logging
import platform
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, Optional


# ===============================================================================
# UNIFIED TIMESTAMP FORMAT - All loggers use this
# ===============================================================================

def get_timestamp() -> Dict[str, Any]:
    """
    Get unified timestamp dict for all loggers.
    
    Returns consistent format:
        {
            "timestamp": "2026-01-03T10:30:45.123456",  # ISO 8601
            "epoch": 1767450645.123456,                 # Unix epoch
            "date": "20260103"                          # For file naming
        }
    """
    now = datetime.now()
    return {
        "timestamp": now.isoformat(),
        "epoch": time.time(),
        "date": now.strftime("%Y%m%d")
    }


# ===============================================================================
# UNIFIED WRITE - All loggers use this
# ===============================================================================

def write_safe(log_file: Path, data: Dict[str, Any], max_retries: int = 3) -> bool:
    """
    IMMORTAL write - retry up to max_retries times, never crash.
    
    Args:
        log_file: Path to JSONL file
        data: Dict to write as JSON line
        max_retries: Number of retry attempts
        
    Returns:
        True if written, False if failed (but NEVER crashes)
    """
    for attempt in range(max_retries):
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
                f.flush()
            return True
        except Exception:
            time.sleep(0.05 * (attempt + 1))  # Backoff
    return False


# ===============================================================================
# AUTO-CLEANUP - Delete data older than 1 day
# ===============================================================================

def cleanup_old_logs(logs_dir: Path, max_age_days: int = 1) -> int:
    """
    Delete log files older than max_age_days.
    
    Args:
        logs_dir: Directory containing log files
        max_age_days: Maximum age in days (default: 1)
        
    Returns:
        Number of files deleted
    """
    if not logs_dir.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(days=max_age_days)
    deleted = 0
    