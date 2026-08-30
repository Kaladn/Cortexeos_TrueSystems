"""Independent no-training preflight for the replacement sentinel experiment."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .symbolic_foundations_scorers import canonical,digest,write_json

SCHEMA="truesystems_symbolic_foundations_replacement_preflight@1"

def _artifact(path:Path)->dict:
 raw=path.read_bytes();return {"path":str(path.resolve()),"bytes":len(raw),"sha256":digest(raw)}

def build_replacement_preflight(representation_root:Path,readiness_path:Path,output:Path)->dict:
 if output.exists():raise FileExistsError(output)
 representation_root=representation_root.resolve();readiness_path=readiness_path.resolve()
 manifest=json.loads((representation_root/"manifest.json").read_bytes());readiness=json.loads(readiness_path.read_bytes())
 if manifest.get("schema")!="truesystems_symbolic_foundations_replacement@1":raise ValueError("not replacement representation")
 if readiness.get("representation_release_id")!=manifest["release_id"]:raise ValueError("readiness release mismatch")
 if readiness.get("blockers") or readiness.get("training_execution_allowed") is not False:raise ValueError("readiness boundary failed")
 if readiness["retained_model"].get("commit")!="170ad86c44a87cbbaa273719ac6231b2872d6f68":raise ValueError("retained identity changed")
 custody=json.loads((representation_root/"consumed-custody.json").read_bytes())
 if custody["old_evaluation"]!="PERMANENTLY_OPENED_NEVER_REUSE" or not manifest["consumed_evaluation_groups_excluded"]:raise ValueError("consumed evaluation not excluded")
 result={"schema":SCHEMA,"classification":"FROZEN_REPLACEMENT_PREFLIGHT_NO_TRAINING","representation":_artifact(representation_root/"manifest.json"),"representation_release_id":manifest["release_id"],"readiness":_artifact(readiness_path),"readiness_id":readiness["readiness_id"],"retained_model_commit":"170ad86c44a87cbbaa273719ac6231b2872d6f68","sentinel":readiness["sentinel_contract"],"models":{"local":"TrueSystemsLocal616SuppliedCandidateScorer@1","external":"TrueSystemsExternalAstSuppliedCandidateScorer@1","initialization":"ORIGINAL_RETAINED_IDENTITY_NO_FAILED_CHECKPOINTS"},"execution":{"seed":61613,"device":"xpu:Intel(R) Arc(TM) Pro B70 Graphics","batch_size":32,"epochs":13,"presentation_ratio":{"local":13,"external":1},"optimizer":readiness["optimizer_policy"],"checkpoint":readiness["checkpoint_policy"],"score_fusion":"NONE_SEPARATE_EVIDENCE_PACKETS"},"evaluation":{"reserved_records":manifest["evaluation_records_reserved"],"payloads_opened":False,"unseen_expected":manifest["sentinel_expected_counts"]["evaluation"],"known_expected":manifest["counts"]["external"]["evaluation"]-manifest["sentinel_expected_counts"]["evaluation"],"open_rule":"ONCE_AFTER_TRAINING_AND_CHECKPOINT_SELECTION"},"consumed":{"old_evaluation":"NEVER_REUSE","failed_checkpoints":"NEVER_DEPLOY_CONTINUE_OR_SELECT"},"training_execution_allowed":False,"authorization_present":False,"optimizer_updates":0,"checkpoints_created":0,"model_training_performed":False,"authority_created":False};result["preflight_id"]=digest(result);write_json(output/"preflight.json",result);return result
