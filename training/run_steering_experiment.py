#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"TrueCore"))
from truecore.training.steering_experiment import evaluate_frozen_checkpoint, train_and_validate

def main():
 p=argparse.ArgumentParser(); p.add_argument("phase",choices=("train","evaluate")); p.add_argument("--model-source",type=Path,required=True); p.add_argument("--release",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--frozen",type=Path)
 a=p.parse_args()
 if a.phase=="train":
  if not a.frozen: raise SystemExit("--frozen required")
  value=train_and_validate(a.model_source,a.release/"splits/train.jsonl",a.release/"splits/validation.jsonl",a.output,json.loads(a.frozen.read_text("utf-8")))
 else: value=evaluate_frozen_checkpoint(a.model_source,a.output/"FINAL.pt",a.release/"reservations/evaluation.jsonl",a.release/"reservations/refusal-evaluation.jsonl",a.output)
 print(json.dumps(value,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
