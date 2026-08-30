#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
from truecore.training.historical_method_preflight import build_historical_preflight
p=ArgumentParser();p.add_argument("--preparation",type=Path,required=True);p.add_argument("--clean-method",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();print(build_historical_preflight(a.preparation,a.clean_method,a.output)["preflight_id"])
