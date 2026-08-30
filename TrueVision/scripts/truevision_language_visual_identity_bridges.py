#!/usr/bin/env python3
"""Build explicit language bridges to a frozen TrueVision visual release."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from truevision_runtime.language_visual_identity_bridge import build_language_visual_identity_bridges  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()
    print(json.dumps(build_language_visual_identity_bridges(args.source_manifest, args.output_root, args.workers), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
