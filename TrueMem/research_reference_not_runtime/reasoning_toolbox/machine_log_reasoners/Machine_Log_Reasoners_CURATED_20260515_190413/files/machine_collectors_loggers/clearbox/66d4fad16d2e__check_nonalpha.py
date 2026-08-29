"""Quick scan: find any words containing hyphens, apostrophes, or non-alpha chars."""
import json
import sys
from pathlib import Path
from collections import Counter

REPO = Path(__file__).resolve().parent.parent.parent
BASE = REPO / "Lexical Data"
DIRS = [
    ("Canonical", BASE / "Canonical"),
    ("Medical", BASE / "Medical"),
]

if "--legacy-paths" not in sys.argv[1:]:
    raise SystemExit(
        "Refusing to run hardcoded legacy paths. Re-run with: "
        "python tools/audit/check_nonalpha.py --legacy-paths"
    )

for name, d in DIRS:
    if not d.exists():
        continue
    bad = Counter()
    examples = []
    total = 0
    for f in sorted(d.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for entry in data:
            if isinstance(entry, dict):
                w = entry.get("word", "")
                if not w:
                    continue
                total += 1
                for ch in w:
                    if not ch.isalpha():
                        bad[ch] += 1
                        if len(examples) < 20:
                            examples.append((f.name, w, ch))
                        break  # one flag per word
    if bad:
        print(f"  [{name}]  {total:,} words  →  {sum(bad.values()):,} NON-ALPHA")
        for ch, count in bad.most_common():
            print(f"    char '{ch}' (ord {ord(ch)}): {count:,} words")
        print(f"    Examples:")
        for fn, w, ch in examples[:15]:
            print(f"      {fn}: '{w}'")
    else:
        print(f"  [{name}]  {total:,} words  →  ALL ALPHA (clean)")
