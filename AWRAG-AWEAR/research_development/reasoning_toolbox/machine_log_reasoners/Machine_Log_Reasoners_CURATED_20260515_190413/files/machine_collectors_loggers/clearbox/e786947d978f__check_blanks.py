"""Quick scan: find any blank/empty word entries across all lexicons."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BASE = REPO / "Lexical Data"
DIRS = [
    ("Canonical", BASE / "Canonical"),
    ("Medical", BASE / "Medical"),
    ("Pool", BASE / "Spare_Slots"),
]

if "--legacy-paths" not in sys.argv[1:]:
    raise SystemExit(
        "Refusing to run hardcoded legacy paths. Re-run with: "
        "python tools/audit/check_blanks.py --legacy-paths"
    )

for name, d in DIRS:
    if not d.exists():
        continue
    blanks = 0
    total = 0
    examples = []
    for f in sorted(d.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for entry in data:
            if isinstance(entry, dict):
                total += 1
                w = entry.get("word", "")
                if not w.strip():
                    blanks += 1
                    if len(examples) < 5:
                        examples.append((f.name, entry.get("hex", "?")))
    status = "CLEAN" if blanks == 0 else f"{blanks:,} BLANKS"
    print(f"  [{name}]  {total:,} entries  →  {status}")
    for fn, h in examples:
        print(f"    {fn}: hex={h}")
