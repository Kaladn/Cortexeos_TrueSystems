#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from truecore.training.hotpotqa_evidence_speech import build_evidence_speech_sessions

p=argparse.ArgumentParser();p.add_argument("--authority",type=Path,required=True);p.add_argument("--consumed-results",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
print(json.dumps(build_evidence_speech_sessions(a.authority,a.consumed_results,a.output),indent=2))
