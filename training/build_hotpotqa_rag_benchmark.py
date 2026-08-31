#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from truecore.training.hotpotqa_rag_benchmark import build_benchmark_source

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--corpus-size",type=int,default=100_000)
    parser.add_argument("--shard-size",type=int,default=250)
    args=parser.parse_args()
    result=build_benchmark_source(args.frozen_root,args.output,corpus_size=args.corpus_size,shard_size=args.shard_size)
    print(json.dumps(result,indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
