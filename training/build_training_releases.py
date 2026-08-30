#!/usr/bin/env python3
"""Build deterministic role-selected releases from a TrueCore intake corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TrueCore"))
from truecore.training.selection import build_releases  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reservation-manifest", type=Path)
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()
    result = build_releases(args.corpus_root, args.output_root, args.reservation_manifest, workers=args.workers)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
