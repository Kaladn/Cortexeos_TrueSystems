#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
from truecore.training.symbolic_foundations_replacement_experiment import run
parser=ArgumentParser();parser.add_argument("--preflight",type=Path,required=True);parser.add_argument("--representation",type=Path,required=True);parser.add_argument("--adapter",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();print(run(args.preflight,args.representation,args.adapter,args.output)["experiment_id"])
