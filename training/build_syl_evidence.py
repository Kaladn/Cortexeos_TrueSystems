#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"TrueCore"))
from truecore.training.syl_evidence import build_syl_evidence
def main():
 p=argparse.ArgumentParser(); p.add_argument('--source-manifest',type=Path,required=True); p.add_argument('--prerequisite-release',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--workers',type=int,default=24); a=p.parse_args(); print(json.dumps(build_syl_evidence(a.source_manifest,a.prerequisite_release,a.output,a.workers),sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
