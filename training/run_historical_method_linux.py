#!/usr/bin/env python3
"""Runtime-path-only Linux launcher for the unchanged historical method."""
from argparse import ArgumentParser
from pathlib import Path
import sys
p=ArgumentParser();p.add_argument("--clean-method",type=Path,required=True);p.add_argument("--preparation",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.clean_method/"src"))
from awrag_location_model.modeling import provisional_chat
provisional_chat.CORPUS=a.preparation/"source-package"
provisional_chat.run(a.preparation/"prepared",a.output)
