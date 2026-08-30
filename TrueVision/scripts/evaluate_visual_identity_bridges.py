#!/usr/bin/env python3
"""Evaluate read-only resolution over a frozen visual bridge release."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from truevision_runtime.visual_bridge_resolver import evaluate_visual_bridge_resolver  # noqa: E402
def main()->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--bridge-release",type=Path,required=True); p.add_argument("--cases",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--workers",type=int,default=24); a=p.parse_args()
    print(json.dumps(evaluate_visual_bridge_resolver(a.bridge_release,a.cases,a.output_root,a.workers),indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
