#!/usr/bin/env python3
"""Build deterministic steering representations and sealed reservations."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"TrueCore"))
from truecore.training.steering_prerequisites import build_steering_prerequisites  # noqa: E402

def main()->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--source-manifest",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--workers",type=int,default=24); a=p.parse_args()
    print(json.dumps(build_steering_prerequisites(a.source_manifest,a.output_root,a.workers),indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
