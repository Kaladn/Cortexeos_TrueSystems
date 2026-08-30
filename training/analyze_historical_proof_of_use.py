#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
from truecore.training.historical_proof_of_use import analyze
p=ArgumentParser();p.add_argument("--preparation",type=Path,required=True);p.add_argument("--clean-method",type=Path,required=True);p.add_argument("--training-result",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();print(analyze(a.preparation,a.clean_method,a.training_result,a.output)["report_id"])
