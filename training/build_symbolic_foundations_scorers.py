#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
from truecore.training.symbolic_foundations_scorers import build_scorer_readiness

parser = ArgumentParser()
parser.add_argument("--representation", type=Path, required=True)
parser.add_argument("--adapter", type=Path, required=True)
parser.add_argument("--clean-model-source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = build_scorer_readiness(args.representation, args.adapter, args.clean_model_source, args.output)
print(result["readiness_id"])
