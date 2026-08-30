#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"TrueCore"))
from truecore.training.symbolic_foundations_representation import build_representations
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--adapter-root",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--local-to-external",type=int,default=13);a=p.parse_args();print(json.dumps(build_representations(a.adapter_root,a.output,a.local_to_external),indent=2,sort_keys=True))
