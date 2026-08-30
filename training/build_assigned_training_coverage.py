#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"TrueCore"))
from truecore.training.coverage_assignment import build_assigned_coverage  # noqa: E402
if __name__ == "__main__":
 p=argparse.ArgumentParser(); p.add_argument("--release-root",type=Path,required=True); p.add_argument("--assignments",type=Path,required=True); p.add_argument("--steering-root",type=Path); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
 print(json.dumps(build_assigned_coverage(a.release_root,a.assignments,a.output,a.steering_root),indent=2,sort_keys=True))
