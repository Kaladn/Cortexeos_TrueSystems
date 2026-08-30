#!/usr/bin/env python3
"""Curate a frozen symbolic-foundations source pilot without training."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TrueCore"))

from truecore.training.symbolic_foundations_curation import build_curation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()
    print(json.dumps(build_curation(args.source_root, args.output, args.workers), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
