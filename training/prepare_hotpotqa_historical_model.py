#!/usr/bin/env python3
"""Run the unchanged historical preparation method on a frozen RAG package."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

from truecore.training.historical_method_equivalence import AUTH_COMMIT, AUTH_SHA, _load_authority, canonical, sha

def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        while chunk:=stream.read(8*1024*1024):h.update(chunk)
    return h.hexdigest()

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-package",type=Path,required=True)
    parser.add_argument("--clean-method",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    method,authority=_load_authority(args.clean_method)
    if args.output.exists():raise FileExistsError(args.output)
    method.CORPUS=args.source_package.resolve()
    receipt=method.prepare(args.output)
    envelope={
        "schema":"truesystems_hotpotqa_historical_preparation@1",
        "classification":"HISTORICAL_METHOD_EXACT_PREPARED_NOT_TRAINED",
        "authority":authority,
        "authority_commit":AUTH_COMMIT,
        "authority_source_sha256":AUTH_SHA,
        "source_package":str(args.source_package.resolve()),
        "source_package_manifest_sha256":file_sha(args.source_package/"sha256_manifest.json"),
        "pretraining_freeze_receipt_sha256":file_sha(args.output/"pretraining-freeze-receipt.json"),
        "dataset_id":receipt["dataset_id"],
        "generation_id":receipt["generation_id"],
        "vocabulary_size":receipt["dense_vocabulary_size"],
        "parameter_count":receipt["parameter_count"],
        "split_statistics":receipt["split_statistics"],
        "optimizer_updates":0,
        "model_training_performed":False,
        "authority_created":False,
    }
    envelope["preparation_id"]=sha(canonical(envelope))
    (args.output/"truesystems-preparation-envelope.json").write_bytes(canonical(envelope))
    print(json.dumps(envelope,indent=2));return 0

if __name__=="__main__":raise SystemExit(main())
