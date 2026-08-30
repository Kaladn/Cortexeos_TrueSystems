"""Prepare new admitted data for the unchanged Windows provisional-chat method."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
from typing import Any

AUTH_COMMIT="170ad86c44a87cbbaa273719ac6231b2872d6f68"
AUTH_SHA="823299a010d76ab6bbba02c1782e6d1f2241e5d42dfdb9ef82021aac8d8075ec"
LOCAL_FILES=("docs/OPERATOR_MODEL_TRAINING_CONTRACT.md","docs/TRUEMEM_RELATIONSHIP_TRAINING_SHAPE.md","TrueMem/system/contracts/RELATIONSHIP_GRAPH_616.md","TrueMem/system/contracts/COMPLETE_ANCHOR_INTAKE.md")

def canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()+b"\n"
def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def rows(p:Path)->list[dict]:return [json.loads(x) for x in p.read_bytes().splitlines() if x]
def write(p:Path,v:Any)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical(v))
def _load_authority(clean:Path):
 commit=subprocess.run(["git","-C",str(clean),"rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip();dirty=subprocess.run(["git","-C",str(clean),"status","--porcelain"],capture_output=True,text=True,check=True).stdout
 source=clean/"src/awrag_location_model/modeling/provisional_chat.py"
 if commit!=AUTH_COMMIT or dirty or sha(source.read_bytes())!=AUTH_SHA:raise ValueError("historical method authority mismatch")
 sys.path.insert(0,str(clean/"src"))
 try:from awrag_location_model.modeling import provisional_chat as method
 finally:sys.path.pop(0)
 return method,{"commit":commit,"source":str(source.resolve()),"source_sha256":AUTH_SHA,"clean_status_sha256":sha(dirty.encode())}
def _split(records:list[dict])->dict[str,list[dict]]:
 result={"train":[],"validation":[],"test":[]}
 by_domain={}
 for record in records:by_domain.setdefault(record["domain"],[]).append(record)
 for domain,values in sorted(by_domain.items()):
  for index,record in enumerate(sorted(values,key=lambda x:x["source_id"])):result["test" if index%10==0 else "validation" if index%10==1 else "train"].append(record)
 return result
def build_historical_preparation(repo:Path,curation:Path,source_root:Path,clean_method:Path,historical_run:Path,output:Path)->dict:
 if output.exists():raise FileExistsError(output)
 method,authority=_load_authority(clean_method);repo=repo.resolve();source_root=source_root.resolve();records=[]
 for path in LOCAL_FILES:
  raw=(repo/path).read_bytes();records.append({"domain":"LOCAL_TRUESYSTEMS","source_id":"local:"+path,"path":path,"sha256":sha(raw),"content":raw.decode("utf-8"),"authority":"LOCAL_SOURCE_BACKED"})
 for item in rows(curation/"accepted.jsonl"):
  identity=item["source_identity"];path=source_root/"networkx"/identity["path"];raw=path.read_bytes()
  if sha(raw)!=identity["sha256"]:raise ValueError(f"external source mismatch: {path}")
  records.append({"domain":"EXTERNAL_NETWORKX","source_id":"external:"+identity["path"],"path":identity["path"],"sha256":identity["sha256"],"commit":identity["commit"],"content":raw.decode("utf-8"),"authority":"EXTERNAL_NOT_LOCAL_TRUTH"})
 splits=_split(records);package=output/"source-package";prepared=output/"prepared";package.mkdir(parents=True)
 hashes={};split_manifest=[]
 for split,values in splits.items():
  payload=b""
  for record in values:
   session_id=sha(canonical({"source_id":record["source_id"],"sha256":record["sha256"]}));row={"session_id":session_id,"messages":[{"role":"user","content":record["content"]}]};payload+=canonical(row);split_manifest.append({key:value for key,value in record.items() if key!="content"}|{"split":split,"session_id":session_id})
  (package/f"{split}.jsonl").write_bytes(payload);hashes[f"{split}.jsonl"]=sha(payload)
 write(package/"sha256_manifest.json",hashes);write(package/"source-split-manifest.json",sorted(split_manifest,key=lambda x:x["source_id"]));method.CORPUS=package;freeze=method.prepare(prepared)
 audit_rows=[
  ("ChatDecoder architecture","EXACT_IMPORT"),("ChatLocationInput construction","EXACT_IMPORT"),("signed -6..-1/+1..+6 lanes","EXACT_IMPORT"),("240-wide location state","EXACT_IMPORT"),("anchor embedding + location field","EXACT_IMPORT"),("512-anchor causal windows","EXACT_IMPORT"),("full-vocabulary next-anchor cross-entropy","EXACT_IMPORT"),("tied output embeddings","EXACT_IMPORT"),("RoPE","EXACT_IMPORT"),("six-head causal attention","EXACT_IMPORT"),("seed 1729","EXACT_IMPORT"),("batch size 1","EXACT_IMPORT"),("gradient clipping 1.0","EXACT_IMPORT"),("100-update warmup","EXACT_IMPORT"),("cosine decay to 0.0001","EXACT_IMPORT"),("validation every 250 updates","EXACT_IMPORT"),("early stopping after eight validation checks without improvement","EXACT_IMPORT"),("5,000-update ceiling","EXACT_IMPORT")]
 current_gru=repo/"TrueCore/truecore/training/symbolic_foundations_replacement_experiment.py"
 prior_diff=[
  {"property":"model topology","windows":"one 8-layer 240-wide causal decoder","prior_linux":"two independent GRU64 candidate scorers","equivalent":False},
  {"property":"objective","windows":"full-vocabulary next-anchor cross-entropy","prior_linux":"cross-entropy over supplied candidate list","equivalent":False},
  {"property":"location input","windows":"12 signed M002 lanes concatenated to 240 and added to anchor embedding","prior_linux":"preceding-history GRU / center-call argument summary","equivalent":False},
  {"property":"context","windows":"512-anchor causal windows","prior_linux":"up to six local anchors / one external center","equivalent":False},
  {"property":"schedule","windows":"batch 1; 100-update warmup; cosine decay; clip 1.0; validate each 250; early-stop 8; ceiling 5000","prior_linux":"batch 32; constant learning rate; 13 epochs; validate per epoch","equivalent":False},
  {"property":"seed","windows":1729,"prior_linux":61613,"equivalent":False},
 ]
 audit={"schema":"truesystems_historical_method_equivalence@1","authority":authority,"authoritative_artifacts":{"modeling_provisional_chat_sha256":AUTH_SHA,"experiment_result_sha256":sha((historical_run/"result/experiment-result.json").read_bytes()),"curve_sha256":sha((historical_run/"result/curve.json").read_bytes()),"freeze_receipt_sha256":sha((historical_run/"prepared/pretraining-freeze-receipt.json").read_bytes())},"prior_linux_diff":prior_diff,"method_table":[{"property":name,"linux_status":status,"implementation":"authoritative module imported without source modification"} for name,status in audit_rows],"runtime_changes":[{"change":"CORPUS path injection","reason":"replace Windows absolute path with external Linux source package","method_effect":"NONE_DATA_LOCATION_ONLY"}],"recent_gru":{"path":str(current_gru),"status":"HISTORICAL_EVIDENCE_ONLY_FORBIDDEN_FROM_REUSE","source_sha256":sha(current_gru.read_bytes()),"checkpoints":"FORBIDDEN_FROM_REUSE"},"data_changes_only":True,"optimizer_updates":0,"method_equivalent":True}
 write(output/"method-equivalence.json",audit)
 result={"schema":"truesystems_historical_preparation@1","classification":"PREPARED_NOT_TRAINED","authority":authority,"source_counts":{k:len(v) for k,v in splits.items()},"domains":{domain:sum(x["domain"]==domain for x in records) for domain in sorted({x["domain"] for x in records})},"prepared":freeze,"method_audit_sha256":sha((output/"method-equivalence.json").read_bytes()),"optimizer_updates":0,"model_training_performed":False,"authority_created":False};result["release_id"]=sha(canonical(result));write(output/"manifest.json",result);return result
