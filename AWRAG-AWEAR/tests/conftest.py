from __future__ import annotations

import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

existing_pythonpath = os.environ.get("PYTHONPATH")
entries = [str(SRC)]
if existing_pythonpath:
    entries.extend(path for path in existing_pythonpath.split(os.pathsep) if path and path != str(SRC))
os.environ["PYTHONPATH"] = os.pathsep.join(entries)
