#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"TrueCore"))
from truecore.training.symbolic_foundations_preflight import build_preflight
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--representation-root",type=Path,required=True);p.add_argument("--model-source",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();print(json.dumps(build_preflight(a.representation_root,a.model_source,a.output),indent=2,sort_keys=True))
