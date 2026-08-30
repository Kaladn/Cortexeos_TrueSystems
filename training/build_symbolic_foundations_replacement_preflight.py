#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
from truecore.training.symbolic_foundations_replacement_preflight import build_replacement_preflight
parser=ArgumentParser();parser.add_argument("--representation",type=Path,required=True);parser.add_argument("--readiness",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();print(build_replacement_preflight(args.representation,args.readiness,args.output)["preflight_id"])
