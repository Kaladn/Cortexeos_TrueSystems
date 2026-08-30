"""Leakage-safe local 6-1-6 and external AST supplied-candidate representations."""
from __future__ import annotations
from collections import defaultdict
import hashlib,json
from pathlib import Path
from typing import Any

SCHEMA="truesystems_symbolic_foundations_representation@1"
def canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def digest(v:bytes|dict|list)->str:return hashlib.sha256(v if isinstance(v,bytes) else canonical(v)).hexdigest()
def rows(p:Path)->list[dict]:return [json.loads(x) for x in p.read_bytes().splitlines() if x]
def write_json(p:Path,v:Any)->dict:
 raw=canonical(v)+b"\n";p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return {"path":p.relative_to(p.parents[1]).as_posix(),"bytes":len(raw),"sha256":digest(raw),"records":1}
def write_jsonl(p:Path,v:list[dict])->dict:
 raw=b"".join(canonical(x)+b"\n" for x in v);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return {"path":p.relative_to(p.parents[1]).as_posix(),"bytes":len(raw),"sha256":digest(raw),"records":len(v)}

def _external_group(path:str)->str:
 value=path.replace("/tests/test_","/").replace("/tests/","/")
 aliases={"bfs":"breadth_first_search","dfs":"depth_first_search"};stem=Path(value).stem
 if stem in aliases:value=str(Path(value).with_name(aliases[stem]+".py"))
 return "networkx-group-"+digest({"module_family":value.removesuffix(".py")})[:24]
def _split(groups:list[str])->dict[str,str]:
 result={};ordered=sorted(set(groups))
 for i,g in enumerate(ordered):result[g]="evaluation" if i%5==0 else "validation" if i%5==1 else "train"
 return result
def _local_groups(blocks:list[dict])->dict[str,str]:
 # Connected components join every paragraph in one contract and contracts
 # sharing an exact paragraph, keeping duplicate families indivisible.
 parent={b["source_path"]:b["source_path"] for b in blocks}
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 def union(a,b):
  a,b=find(a),find(b)
  if a!=b:parent[max(a,b)]=min(a,b)
 by_hash=defaultdict(set)
 for b in blocks:by_hash[b["exact_text_sha256"]].add(b["source_path"])
 for paths in by_hash.values():
  values=sorted(paths)
  for value in values[1:]:union(values[0],value)
 return {path:"local-contract-group-"+digest({"connected_contract":find(path)})[:24] for path in parent}

def build_representations(adapter_root:Path,output:Path,local_to_external:int=13)->dict:
 if output.exists():raise FileExistsError(output)
 adapter_root=adapter_root.resolve();raw=(adapter_root/"manifest.json").read_bytes();manifest=json.loads(raw)
 if manifest.get("schema")!="truesystems_symbolic_foundations_adapter@1" or manifest.get("model_training_performed") is not False:raise ValueError("unsupported adapter release")
 blocks=rows(adapter_root/manifest["artifacts"]["local_blocks"]["path"]);external=rows(adapter_root/manifest["artifacts"]["external_ast"]["path"])
 local_group_by_path=_local_groups(blocks);external_groups=[_external_group(x["source_identity"]["path"]) for x in external];split_by_group=_split(list(local_group_by_path.values())+external_groups)
 local=[]
 for block in blocks:
  anchors=block["anchors"]
  for position in range(len(anchors)-1):
   candidates=sorted(set(anchors[position+1:position+7]));expected=anchors[position+1]
   record={"schema":f"{SCHEMA}:local_616_candidate","domain":"local_system_616","split":split_by_group[local_group_by_path[block["source_path"]]],"source_group_id":local_group_by_path[block["source_path"]],"duplicate_family_id":"paragraph-"+block["exact_text_sha256"],"source_path":block["source_path"],"source_sha256":block["source_sha256"],"byte_start":block["byte_start"],"byte_end_exclusive":block["byte_end_exclusive"],"line_start":block["line_start"],"line_end":block["line_end"],"block_ordinal":block["block_ordinal"],"center_position":position,"center_anchor":anchors[position],"history":anchors[max(0,position-6):position],"supplied_candidates":candidates,"expected_outcome":{"status":"selected","anchor":expected},"authority":"LOCAL_SOURCE_BACKED_616"};record["record_id"]=digest(record);local.append(record)
 external_records=[]
 for source in external:
  group=_external_group(source["source_identity"]["path"]);split=split_by_group[group]
  for unit in source["ast_units"]:
   calls=unit["calls"]
   for position in range(len(calls)-1):
    choices=sorted({x["name"] for x in calls[position+1:position+7]});expected=calls[position+1]["name"]
    record={"schema":f"{SCHEMA}:external_ast_candidate","domain":"external_networkx_ast","split":split,"source_group_id":group,"source_record_id":source["source_record_id"],"source_identity":source["source_identity"],"unit_id":unit["unit_id"],"symbol":unit["symbol"],"line_start":unit["line_start"],"line_end":unit["line_end"],"center_call":calls[position],"supplied_candidates":choices,"expected_outcome":{"status":"selected","call_name":expected},"authority":"EXTERNAL_NOT_LOCAL_TRUTH"};record["record_id"]=digest(record);external_records.append(record)
 local.sort(key=lambda x:x["record_id"]);external_records.sort(key=lambda x:x["record_id"])
 artifacts={};counts={}
 for domain,data in (("local",local),("external",external_records)):
  counts[domain]={}
  for split in ("train","validation","evaluation"):
   selected=[x for x in data if x["split"]==split];counts[domain][split]=len(selected)
   if split=="evaluation":
    reservations=[{"record_id":x["record_id"],"sealed_record_sha256":digest(x),"source_group_id":x["source_group_id"],"domain":x["domain"],"eligibility":"EVALUATION_RESERVED"} for x in selected]
    artifacts[f"{domain}_evaluation_reservations"]=write_jsonl(output/f"reservations/{domain}-evaluation.jsonl",reservations)
    artifacts[f"{domain}_evaluation_sealed"]=write_jsonl(output/f"sealed/{domain}-evaluation-records.jsonl",selected)
   else:artifacts[f"{domain}_{split}"]=write_jsonl(output/f"splits/{domain}-{split}.jsonl",selected)
 train_local=[x for x in local if x["split"]=="train"];train_external=[x for x in external_records if x["split"]=="train"];schedule=[];total=max(len(train_local),len(train_external))
 for i in range(total):
  if train_external:schedule.append({"domain":"external","record_id":train_external[i%len(train_external)]["record_id"]})
  if train_local:
   for j in range(local_to_external):schedule.append({"domain":"local","record_id":train_local[(i*local_to_external+j)%len(train_local)]["record_id"]})
 artifacts["training_schedule"]=write_jsonl(output/"training/presentation-schedule.jsonl",schedule)
 split_manifest={"schema":f"{SCHEMA}:split_manifest","assignment":"deterministic_source_group_modulo_5","local_grouping":"connected contracts joined by exact paragraph duplicate families","external_grouping":"implementation module and associated test module","counts":counts,"evaluation_opened":False,"schedule_applies_to":"train_only","validation_evaluation_natural_ratio":True};artifacts["split_manifest"]=write_json(output/"split-manifest.json",split_manifest);artifacts["split_manifest"]["path"]="split-manifest.json"
 local_windows=int(manifest["local_windows_616"]);local_candidates=len(local);external_units=int(manifest["external_ast_units"]);external_candidates=len(external_records)
 accounting={"local":{"input_windows":local_windows,"candidate_records":local_candidates,"excluded":local_windows-local_candidates,"law":"Each DocuFilm block contributes one terminal parent/anchor window without a next anchor; exactly one terminal window per block is excluded from next-anchor candidate construction.","expected_excluded":int(manifest["local_blocks"])},"external":{"input_ast_units":external_units,"candidate_records":external_candidates,"law":"Each AST unit with N observed calls expands to max(0,N-1) ordered next-call candidate records; units are containers, not training records."}}
 if accounting["local"]["excluded"]!=accounting["local"]["expected_excluded"]:raise ValueError("local representation accounting mismatch")
 result={"schema":SCHEMA,"classification":"REPRESENTED_RESERVED_NOT_TRAINED","adapter_manifest_sha256":digest(raw),"counts":counts,"representation_accounting":accounting,"curriculum_presentation_ratio":{"local":local_to_external,"external":1},"evaluation_records_reserved":counts["local"]["evaluation"]+counts["external"]["evaluation"],"model_training_performed":False,"optimizer_updates":0,"authority_created":False,"artifacts":artifacts};result["release_id"]=digest(result);write_json(output/"manifest.json",result);return result
