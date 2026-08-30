"""Frozen read-only preflight for two conjoined supplied-candidate scorers."""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
from typing import Any

SCHEMA="truesystems_symbolic_foundations_preflight@1"
def canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def digest(v:bytes|dict|list)->str:return hashlib.sha256(v if isinstance(v,bytes) else canonical(v)).hexdigest()
def artifact(p:Path)->dict:
 raw=p.read_bytes();return {"path":str(p.resolve()),"bytes":len(raw),"sha256":digest(raw)}
def write_json(p:Path,v:Any)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical(v)+b"\n")

def build_preflight(representation_root:Path,model_source:Path,output:Path)->dict:
 if output.exists():raise FileExistsError(output)
 representation_root=representation_root.resolve();model_source=model_source.resolve();manifest_path=representation_root/"manifest.json";manifest=json.loads(manifest_path.read_bytes())
 if manifest.get("schema")!="truesystems_symbolic_foundations_representation@1" or manifest.get("evaluation_records_reserved",0)<=0:raise ValueError("unfrozen representation")
 for key,item in manifest["artifacts"].items():
  path=representation_root/item["path"]
  if not path.exists() or digest(path.read_bytes())!=item["sha256"]:raise ValueError(f"representation artifact mismatch: {key}")
 commit=subprocess.run(["git","-C",str(model_source),"rev-parse","HEAD"],capture_output=True,text=True,check=False).stdout.strip()
 dirty=subprocess.run(["git","-C",str(model_source),"status","--porcelain"],capture_output=True,text=True,check=False).stdout
 retained={"path":str(model_source),"commit":commit or None,"dirty_status_sha256":digest(dirty.encode()),"modified":bool(dirty),"expected_commit":"170ad86c44a87cbbaa273719ac6231b2872d6f68"}
 scorer_laws={
  "local":{"model_identity":"TrueSystemsLocal616SuppliedCandidateScorer@1","objective":"cross-entropy over only supplied next-anchor candidates from local signed 6-1-6 history","identity_input":"exact isolated six-byte anchor identity plus dataset identity","architecture":{"candidate_embedding":32,"history_encoder":"GRU64","candidate_head":"shared MLP 96-64-1","generated_vocabulary":False},"may_generate_identity":False,"input_authority":"LOCAL_SOURCE_BACKED_616","implementation_status":"MISSING_EXACT_BINARY_IDENTITY_SCORER"},
  "external":{"model_identity":"TrueSystemsExternalAstSuppliedCandidateScorer@1","objective":"cross-entropy over only supplied next-call candidates from exact external AST observations","identity_input":"dataset-local full call-name identity; unseen identity remains explicit","architecture":{"candidate_embedding":32,"ordered_call_encoder":"GRU64","tagged_argument_summary":32,"candidate_head":"shared MLP 128-64-1","generated_vocabulary":False},"may_generate_identity":False,"input_authority":"EXTERNAL_NOT_LOCAL_TRUTH","implementation_status":"MISSING_TAGGED_AST_CANDIDATE_SCORER"}}
 weave={"combination":"NO_SCORE_FUSION","law":"Each scorer returns its own supplied-candidate result and evidence packet; deterministic orchestration preserves both domains and never creates cross-dataset edges.","training_ratio":{"local":13,"external":1},"validation_evaluation_ratio":"NATURAL_SEPARATE"}
 frozen_execution={"seed":61613,"device_policy":"XPU_ONLY: Intel(R) Arc(TM) Pro B70 Graphics; block unless two identical no-optimizer forward passes and two bounded training rehearsals reproduce","optimizer":{"name":"AdamW","learning_rate":0.001,"betas":[0.9,0.95],"epsilon":1e-8,"weight_decay":0.01},"batch_size_records":32,"maximum_epochs":13,"validation_interval":"end_of_each_epoch","stopping_rule":"run exactly 13 epochs; validation cannot alter hyperparameters","checkpoint_selection":{"local":"lowest local validation cross-entropy; earliest epoch wins exact ties","external":"lowest external validation cross-entropy; earliest epoch wins exact ties","combined":"no combined checkpoint score; weave references both independently frozen checkpoint hashes"},"evaluation_must_remain_sealed":True,"runtime_deployment":False}
 blockers=[]
 if retained["commit"]!=retained["expected_commit"]:blockers.append("RETAINED_MODEL_COMMIT_MISMATCH")
 if retained["modified"]:blockers.append("RETAINED_MODEL_SOURCE_DIRTY")
 blockers.extend(["LOCAL_SCORER_NOT_IMPLEMENTED","EXTERNAL_SCORER_NOT_IMPLEMENTED","DETERMINISTIC_XPU_EQUIVALENCE_NOT_PROVEN"])
 result={"schema":SCHEMA,"classification":"PREFLIGHT_ONLY_NO_TRAINING","representation":artifact(manifest_path),"representation_release_id":manifest["release_id"],"accounting":manifest["representation_accounting"],"evaluation":{"reserved_records":manifest["evaluation_records_reserved"],"payloads_opened":False},"retained_model":retained,"scorers":scorer_laws,"weave":weave,"frozen_execution":frozen_execution,"blockers":blockers,"training_execution_allowed":False,"optimizer_updates":0,"checkpoints_created":0,"model_training_performed":False,"authority_created":False};result["preflight_id"]=digest(result);output.mkdir(parents=True);write_json(output/"preflight.json",result);return result
