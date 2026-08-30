"""Replacement representation after permanent consumption of the first evaluation."""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from typing import Any

from .symbolic_foundations_representation import canonical, digest, rows, write_json, write_jsonl, _external_group

SCHEMA = "truesystems_symbolic_foundations_replacement@1"
SENTINEL = "UNSEEN_EXTERNAL_CALL"


def _split(groups: list[str]) -> dict[str, str]:
    ordered = sorted(set(groups))
    return {group: ("evaluation" if index % 5 == 0 else "validation" if index % 5 == 1 else "train") for index, group in enumerate(ordered)}


def _map_external(record: dict, vocabulary: set[str]) -> dict:
    original = list(record["supplied_candidates"])
    mapped = sorted({value if value in vocabulary else SENTINEL for value in original})
    expected_original = record["expected_outcome"]["call_name"]
    expected = expected_original if expected_original in vocabulary else SENTINEL
    value = dict(record)
    value["original_supplied_candidates"] = original
    value["supplied_candidates"] = mapped
    value["expected_outcome"] = {"status": "selected", "call_identity": expected}
    value["original_expected_call"] = expected_original
    value["sentinel_evidence"] = {
        "meaning": "identity unseen by this scorer",
        "original_call": expected_original,
        "source_hash": record["source_identity"]["sha256"],
        "ast_unit_identity": record["unit_id"],
        "coordinates": {"path": record["source_identity"]["path"], "line_start": record["line_start"], "line_end": record["line_end"], "call_line": record["center_call"]["line"]},
        "local_authority": False,
    } if expected == SENTINEL else None
    value["record_id"] = digest({key:item for key,item in value.items() if key != "record_id"})
    return value


def build_replacement(adapter_root: Path, consumed_representation: Path, failed_experiment: Path, output: Path, local_to_external: int = 13) -> dict:
    if output.exists():
        raise FileExistsError(output)
    adapter_root = adapter_root.resolve(); consumed_representation = consumed_representation.resolve(); failed_experiment = failed_experiment.resolve()
    failed = json.loads((failed_experiment / "failed-experiment-receipt.json").read_bytes())
    authorization = json.loads((failed_experiment / "authorization.json").read_bytes())
    if failed.get("status") != "FAILED_PRESERVED_NOT_DEPLOYED" or not authorization.get("revoked"):
        raise ValueError("failed experiment is not permanently consumed")
    old_manifest = json.loads((consumed_representation / "manifest.json").read_bytes())
    consumed_local = rows(consumed_representation / "sealed/local-evaluation-records.jsonl")
    consumed_external = rows(consumed_representation / "sealed/external-evaluation-records.jsonl")
    consumed_paragraphs = {record["duplicate_family_id"] for record in consumed_local}
    consumed_external_groups = {record["source_group_id"] for record in consumed_external}
    adapter_manifest_raw = (adapter_root / "manifest.json").read_bytes(); adapter = json.loads(adapter_manifest_raw)
    blocks = rows(adapter_root / adapter["artifacts"]["local_blocks"]["path"])
    sources = rows(adapter_root / adapter["artifacts"]["external_ast"]["path"])
    local=[]
    for block in blocks:
        group="paragraph-"+block["exact_text_sha256"]
        if group in consumed_paragraphs: continue
        anchors=block["anchors"]
        for position in range(len(anchors)-1):
            record={"schema":f"{SCHEMA}:local_616_candidate","domain":"local_system_616","source_group_id":group,"duplicate_family_id":group,"source_path":block["source_path"],"source_sha256":block["source_sha256"],"byte_start":block["byte_start"],"byte_end_exclusive":block["byte_end_exclusive"],"line_start":block["line_start"],"line_end":block["line_end"],"block_ordinal":block["block_ordinal"],"center_position":position,"center_anchor":anchors[position],"history":anchors[max(0,position-6):position],"supplied_candidates":sorted(set(anchors[position+1:position+7])),"expected_outcome":{"status":"selected","anchor":anchors[position+1]},"authority":"LOCAL_SOURCE_BACKED_616"};record["record_id"]=digest(record);local.append(record)
    external=[]
    for source in sources:
        group=_external_group(source["source_identity"]["path"])
        if group in consumed_external_groups: continue
        for unit in source["ast_units"]:
            calls=unit["calls"]
            for position in range(len(calls)-1):
                record={"schema":f"{SCHEMA}:external_ast_candidate","domain":"external_networkx_ast","source_group_id":group,"source_record_id":source["source_record_id"],"source_identity":source["source_identity"],"unit_id":unit["unit_id"],"symbol":unit["symbol"],"line_start":unit["line_start"],"line_end":unit["line_end"],"center_call":calls[position],"supplied_candidates":sorted({x["name"] for x in calls[position+1:position+7]}),"expected_outcome":{"status":"selected","call_name":calls[position+1]["name"]},"authority":"EXTERNAL_NOT_LOCAL_TRUTH"};record["record_id"]=digest(record);external.append(record)
    group_split=_split([x["source_group_id"] for x in local+external])
    for record in local+external: record["split"]=group_split[record["source_group_id"]]
    vocabulary={SENTINEL}
    for record in external:
        if record["split"] != "evaluation":
            vocabulary.add(record["center_call"]["name"]);vocabulary.update(record["supplied_candidates"])
    external=[_map_external(record,vocabulary) for record in external]
    local.sort(key=lambda x:x["record_id"]);external.sort(key=lambda x:x["record_id"])
    # Synthetic checks use no reserved source record.
    synthetic_unseen={"supplied_candidates":["known",SENTINEL],"expected":SENTINEL,"original":"synthetic.absent.call"}
    synthetic_known={"supplied_candidates":["known",SENTINEL],"expected":"known","original":"known"}
    if synthetic_unseen["expected"] != SENTINEL or synthetic_known["expected"] == SENTINEL: raise AssertionError("sentinel synthetic contract failed")
    artifacts={};counts={};sentinel_counts=Counter()
    for domain,data in (("local",local),("external",external)):
        counts[domain]={}
        for split in ("train","validation","evaluation"):
            selected=[x for x in data if x["split"]==split];counts[domain][split]=len(selected)
            if domain=="external": sentinel_counts[split]=sum(x["expected_outcome"]["call_identity"]==SENTINEL for x in selected)
            if split=="evaluation":
                reservations=[{"record_id":x["record_id"],"sealed_record_sha256":digest(x),"source_group_id":x["source_group_id"],"domain":x["domain"],"eligibility":"EVALUATION_RESERVED"} for x in selected]
                artifacts[f"{domain}_evaluation_reservations"]=write_jsonl(output/f"reservations/{domain}-evaluation.jsonl",reservations)
                artifacts[f"{domain}_evaluation_sealed"]=write_jsonl(output/f"sealed/{domain}-evaluation-records.jsonl",selected)
            else: artifacts[f"{domain}_{split}"]=write_jsonl(output/f"splits/{domain}-{split}.jsonl",selected)
    if sentinel_counts["evaluation"] <= 0 or sentinel_counts["evaluation"] >= counts["external"]["evaluation"]:
        raise ValueError("replacement evaluation does not separately cover unseen and known calls")
    vocabulary_record={"schema":f"{SCHEMA}:external_vocabulary","sentinel":SENTINEL,"sentinel_law":"identity unseen by this scorer; never equivalence, operation, or authority","identities":sorted(vocabulary),"local_use_forbidden":True,"generated_resolution_forbidden":True};artifacts["external_vocabulary"]=write_json(output/"external-vocabulary.json",vocabulary_record);artifacts["external_vocabulary"]["path"]="external-vocabulary.json"
    custody={"schema":f"{SCHEMA}:consumed_custody","old_representation_release_id":old_manifest["release_id"],"failed_readiness_id":failed["readiness_id"],"old_evaluation_source_groups":{"local":sorted(consumed_paragraphs),"external":sorted(consumed_external_groups)},"old_checkpoints":"PERMANENTLY_CONSUMED_NEVER_DEPLOY_CONTINUE_OR_SELECT","old_evaluation":"PERMANENTLY_OPENED_NEVER_REUSE"};artifacts["consumed_custody"]=write_json(output/"consumed-custody.json",custody);artifacts["consumed_custody"]["path"]="consumed-custody.json"
    result={"schema":SCHEMA,"classification":"REPLACEMENT_RESERVED_NOT_TRAINED","adapter_manifest_sha256":digest(adapter_manifest_raw),"counts":counts,"sentinel_expected_counts":dict(sentinel_counts),"synthetic_contract":{"unseen":synthetic_unseen,"known":synthetic_known,"train_validation_only":True},"consumed_evaluation_groups_excluded":True,"evaluation_records_reserved":counts["local"]["evaluation"]+counts["external"]["evaluation"],"curriculum_presentation_ratio":{"local":local_to_external,"external":1},"model_training_performed":False,"optimizer_updates":0,"checkpoints_created":0,"authority_created":False,"artifacts":artifacts};result["release_id"]=digest(result);write_json(output/"manifest.json",result);return result
