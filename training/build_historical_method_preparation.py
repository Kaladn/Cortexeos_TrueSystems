#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
from truecore.training.historical_method_equivalence import build_historical_preparation
p=ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--curation",type=Path,required=True);p.add_argument("--source-root",type=Path,required=True);p.add_argument("--clean-method",type=Path,required=True);p.add_argument("--historical-run",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();print(build_historical_preparation(a.repo,a.curation,a.source_root,a.clean_method,a.historical_run,a.output)["release_id"])
