"""Audit all canonical slot files — count total, assigned, available per letter."""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
LEXICON_DIR = REPO / "Lexical Data" / "Canonical"

if "--legacy-paths" not in sys.argv[1:]:
    raise SystemExit(
        "Refusing to run hardcoded legacy paths. Re-run with: "
        "python tools/audit/audit_slots.py --legacy-paths"
    )

print(f"{'Letter':>6} {'Total':>10} {'Assigned':>10} {'Available':>10}")
print("-" * 48)

grand_total = 0
grand_assigned = 0
grand_available = 0

for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    path = LEXICON_DIR / f"canonical_{letter}.json"
    if not path.exists():
        print(f"  [{letter}]  MISSING")
        continue
    with open(path, "r", encoding="utf-8") as f:
        slots = json.load(f)
    total = len(slots)
    assigned = sum(1 for s in slots if s.get("status") == "ASSIGNED")
    available = sum(1 for s in slots if s.get("status") == "AVAILABLE")
    print(f"     {letter}  {total:>10,}  {assigned:>10,}  {available:>10,}")
    grand_total += total
    grand_assigned += assigned
    grand_available += available

print("-" * 48)
print(f" TOTAL  {grand_total:>10,}  {grand_assigned:>10,}  {grand_available:>10,}")
print(f"\n Unbound U words: {202968 - 139589} (if fix_u_overflow not run yet)")
