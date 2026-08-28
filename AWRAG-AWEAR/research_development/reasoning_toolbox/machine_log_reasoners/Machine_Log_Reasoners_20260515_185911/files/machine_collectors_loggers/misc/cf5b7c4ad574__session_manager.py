"""
Session Manager - Foundation of the Evidence Layer
Creates sequential session directories and manages COMPUCOG_SESSION_PATH env variable.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


def start_new_session(label: str = "gaming", mode: str = "capture") -> Path:
    """
    Create a new sequential session directory and export COMPUCOG_SESSION_PATH.
    
    Args:
        label: Session label (e.g., "gaming", "test")
        mode: Session mode (e.g., "capture", "replay")
    
    Returns:
        Path to the created session directory
    """
    # Create date-based root directory
    today = datetime.now().strftime("%Y-%m-%d")
    root_dir = Path(__file__).parent / today
    root_dir.mkdir(parents=True, exist_ok=True)
    
    # Find next sequential session number
    existing_sessions = [d for d in root_dir.iterdir() if d.is_dir() and d.name.startswith("session_")]
    if existing_sessions:
        max_num = max(int(d.name.split("_")[1]) for d in existing_sessions)
        session_num = max_num + 1
    else:
        session_num = 1
    
    # Create session directory
    session_dir = root_dir / f"session_{session_num:02d}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Export environment variable for workers to use
    os.environ["COMPUCOG_SESSION_PATH"] = str(session_dir.absolute())
    
    # Write session manifest
    manifest = {
        "session_id": f"session_{session_num:02d}",
        "label": label,
        "mode": mode,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "session_path": str(session_dir.absolute()),
        "date": today
    }
    
    manifest_path = session_dir / "session_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"[SESSION_MANAGER] Created session: {session_dir}")
    print(f"[SESSION_MANAGER] COMPUCOG_SESSION_PATH={os.environ['COMPUCOG_SESSION_PATH']}")
    
    return session_dir


def get_session_path_or_fallback(worker_label: str) -> Path:
    """
    Get the session path from environment variable, or create a fallback.
    
    Args:
        worker_label: Unique worker identifier (e.g., "gamepad", "video")
    
    Returns:
        Path to session directory
    """
    env_path = os.getenv("COMPUCOG_SESSION_PATH")
    
    if env_path:
        session_dir = Path(env_path)
        if session_dir.exists():
            return session_dir
        else:
            print(f"[{worker_label.upper()}] Warning: COMPUCOG_SESSION_PATH points to non-existent directory: {env_path}")
    
    # Fallback: create standalone session
    print(f"[{worker_label.upper()}] No COMPUCOG_SESSION_PATH found, creating fallback session")
    today = datetime.now().strftime("%Y-%m-%d")
    fallback_dir = Path(__file__).parent / today / f"session_{worker_label}_standalone"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    
    return fallback_dir


def finalize_session(session_dir: Path):
    """
    Finalize a session by updating the manifest with end time.
    
    Args:
        session_dir: Path to session directory
    """
    manifest_path = session_dir / "session_manifest.json"
    
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        manifest["end_time"] = datetime.now(timezone.utc).isoformat()
        
        # List all files created during session
        all_files = [str(f.relative_to(session_dir)) for f in session_dir.iterdir() if f.is_file()]
        manifest["files"] = sorted(all_files)
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"[SESSION_MANAGER] Finalized session: {session_dir}")
    else:
        print(f"[SESSION_MANAGER] Warning: No manifest found at {manifest_path}")


if __name__ == "__main__":
    # Test session creation
    session = start_new_session(label="test", mode="capture")
    print(f"Created test session: {session}")
    
    # Test worker path retrieval
    worker_path = get_session_path_or_fallback("test_worker")
    print(f"Worker would write to: {worker_path}")
    
    # Finalize
    finalize_session(session)
