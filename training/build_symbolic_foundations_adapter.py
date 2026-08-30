#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"TrueCore"))
from truecore.training.symbolic_foundations_adapter import build_symbolic_adapter
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--curation-root",type=Path,required=True);p.add_argument("--source-root",type=Path,required=True);p.add_argument("--repo",type=Path,default=ROOT);p.add_argument("--output",type=Path,required=True);p.add_argument("--workers",type=int,default=24);p.add_argument("--local-to-external",type=int,default=13);a=p.parse_args();print(json.dumps(build_symbolic_adapter(a.curation_root,a.source_root,a.repo,a.output,a.workers,a.local_to_external),indent=2,sort_keys=True))
