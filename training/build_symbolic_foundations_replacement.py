#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
from truecore.training.symbolic_foundations_replacement import build_replacement
parser=ArgumentParser();parser.add_argument("--adapter",type=Path,required=True);parser.add_argument("--consumed-representation",type=Path,required=True);parser.add_argument("--failed-experiment",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();print(build_replacement(args.adapter,args.consumed_representation,args.failed_experiment,args.output)["release_id"])
