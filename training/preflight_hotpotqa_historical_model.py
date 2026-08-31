#!/usr/bin/env python3
"""No-optimizer XPU feasibility check for the HotpotQA historical package."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
import torch.nn.functional as F
from truecore.training.historical_method_equivalence import _load_authority, canonical, sha

def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument("--prepared",type=Path,required=True);parser.add_argument("--clean-method",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    envelope=json.loads((args.prepared/"truesystems-preparation-envelope.json").read_bytes());freeze=json.loads((args.prepared/"pretraining-freeze-receipt.json").read_bytes())
    if envelope["optimizer_updates"] or envelope["model_training_performed"]:raise ValueError("preparation is not update-free")
    method,authority=_load_authority(args.clean_method);mapping=json.loads((args.prepared/"symbol-index-mapping.json").read_bytes());perm={x["permanent_value"]:x["dense_model_index"] for x in mapping["entries"]}
    if not torch.xpu.is_available():raise RuntimeError("XPU unavailable")
    device=torch.device("xpu:0");torch.xpu.reset_peak_memory_stats();model=method.ChatDecoder(len(mapping["entries"]),device);field=method.ChatLocationField(args.prepared/"M002.jsonl.gz",perm,device);inputs=method.ChatLocationInput(model.embedding,field)
    train=method.windows(method.read_paths(args.prepared/"train-paths.bin"),perm);x,y,valid=method.batch(train,[0],device);loss=F.cross_entropy(model.decode(inputs(x),valid).view(-1,len(mapping["entries"])),y.view(-1),ignore_index=-100);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);torch.xpu.synchronize()
    result={"schema":"truesystems_hotpotqa_historical_preflight@1","classification":"XPU_FORWARD_BACKWARD_NO_OPTIMIZER_UPDATES","preparation_id":envelope["preparation_id"],"authority":authority,"device":torch.xpu.get_device_name(0),"vocabulary_size":len(mapping["entries"]),"parameter_count":sum(p.numel() for p in model.parameters()),"training_windows":freeze["split_statistics"]["train"]["windows"],"validation_windows":freeze["split_statistics"]["validation"]["windows"],"probe_loss":float(loss.detach().cpu()),"peak_allocated_bytes":int(torch.xpu.max_memory_allocated()),"peak_reserved_bytes":int(torch.xpu.max_memory_reserved()),"optimizer_updates":0,"checkpoints_created":0,"training_execution_allowed":False,"sealed_test_opened":False,"authority_created":False}
    result["preflight_id"]=sha(canonical(result));args.output.mkdir(parents=True);(args.output/"preflight.json").write_bytes(canonical(result));print(json.dumps(result,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
