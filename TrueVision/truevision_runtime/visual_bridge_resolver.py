"""Read-only resolver for frozen language-to-visual-identity bridges."""
from __future__ import annotations
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import json, multiprocessing, os, re, resource, time
from pathlib import Path
from typing import Any, Iterable

from .language_visual_identity_bridge import SCHEMA as BRIDGE_SCHEMA, canonical, digest

SCHEMA="truevision_language_visual_bridge_resolver@1"
WORD=re.compile(r"[^\W_]+(?:[_'’\-‐‑‒–—―][^\W_]+)*",re.UNICODE)
FRAME=re.compile(r"\bframe\s+(-?\d+)\b",re.I)
ROW=re.compile(r"\brow\s+(-?\d+)\b",re.I)
COLUMN=re.compile(r"\bcolumn\s+(-?\d+)\b",re.I)
NEGATION={"not","never","without","exclude","don't","doesn't","isn't","cannot"}
SEMANTIC={"person","people","car","animal","dangerous","safe","meaning","caption","label","class","name","identify","recognize"}
RELATIONS={"contained_in":{"contained","within"},"adjacent_to":{"adjacent","beside","neighbor"},"before":{"before","earlier"},"after":{"after","later"},"persists_to":{"persists","persistent","remains","stable"},"changes_to":{"changes","changed","different","continuity"}}

def _write_json(path:Path,value:Any)->dict:
    raw=canonical(value)+b"\n"; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); return {"path":path.name,"sha256":digest(raw),"bytes":len(raw),"records":1}
def _write_jsonl(path:Path,rows:Iterable[dict])->dict:
    values=list(rows); raw=b"".join(canonical(x)+b"\n" for x in values); path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); return {"path":path.name,"sha256":digest(raw),"bytes":len(raw),"records":len(values)}
def anchors(text:str)->tuple[str,...]: return tuple(x.group(0).lower() for x in WORD.finditer(text))

class FrozenVisualBridgeAuthority:
    def __init__(self,root:Path):
        self.root=root.resolve(); self.manifest_bytes=(self.root/"manifest.json").read_bytes(); self.manifest=json.loads(self.manifest_bytes)
        if self.manifest.get("namespace")!="LANGUAGE_TO_VISUAL_IDENTITY_BRIDGES": raise ValueError("wrong visual bridge authority")
        raw=(self.root/"ledgers/accepted.jsonl").read_bytes(); declared=self.manifest.get("artifacts",{}).get("accepted",{})
        if declared.get("sha256")!=digest(raw) or declared.get("bytes")!=len(raw): raise ValueError("visual bridge ledger is not manifest-bound")
        self.rows=[json.loads(line) for line in raw.splitlines() if line]; self.release_id=digest(self.manifest_bytes)
        for row in self.rows:
            if row.get("schema")!=f"{BRIDGE_SCHEMA}:bridge" or row.get("namespace")!="LANGUAGE_TO_VISUAL_IDENTITY_BRIDGES": raise ValueError("non-bridge visual authority record")
            if digest({k:v for k,v in row.items() if k!="bridge_id"})!=row.get("bridge_id"): raise ValueError("visual bridge identity mismatch")
        self.by_id={row["bridge_id"]:row for row in self.rows}
        if len(self.by_id)!=len(self.rows): raise ValueError("duplicate visual bridge ID")
        self.frames={c["frame_number"] for row in self.rows for c in row["citations"]}; shapes={tuple(c["coordinates"]["grid_shape"]) for row in self.rows for c in row["citations"] if c.get("coordinates")}
        if len(shapes)!=1: raise ValueError("visual bridge geometry mismatch")
        self.grid_shape=next(iter(shapes))
    def frozen(self)->dict:
        return {"release_id":self.release_id,"manifest_sha256":digest(self.manifest_bytes),"rows":self.rows,"frames":self.frames,"grid_shape":self.grid_shape}

def _result(status:str,query:str,reason:str,case_id:str|None,**extra)->dict:
    value={"schema":f"{SCHEMA}:resolution","case_id":case_id,"query":query,"status":status,"reason":reason,
        "operation_executed":False,"visual_identity_inferred":False,"relationship_created":False,"authority_created":False,"model_training_performed":False}
    value.update(extra); return value

def resolve_visual_query(request:dict[str,Any],frozen:dict[str,Any])->dict:
    query=request.get("query"); case_id=request.get("case_id")
    if not isinstance(query,str) or not query: return _result("unsupported",str(query or ""),"empty_or_non_string_query",case_id)
    words=anchors(query); wordset=set(words)
    if wordset&NEGATION: return _result("unsupported",query,"negated_visual_binding_request",case_id,evidence={"anchors":list(words)})
    if wordset&SEMANTIC: return _result("unsupported",query,"appearance_name_class_caption_or_meaning_forbidden",case_id,evidence={"forbidden_anchors":sorted(wordset&SEMANTIC)})
    expected=request.get("expected_release_id")
    if expected is not None and expected!=frozen["release_id"]: return _result("stale",query,"expected_release_is_not_frozen_authority",case_id,expected_release_id=expected,authority_release_id=frozen["release_id"])
    hint=request.get("bridge_record_id_hint")
    if hint is not None and not any(row["bridge_id"]==hint for row in frozen["rows"]): return _result("missing",query,"bridge_record_id_not_in_frozen_authority",case_id,bridge_record_id_hint=hint)
    frame_match=FRAME.search(query); row_match=ROW.search(query); column_match=COLUMN.search(query)
    frame=int(frame_match.group(1)) if frame_match else None; row=int(row_match.group(1)) if row_match else None; column=int(column_match.group(1)) if column_match else None
    location=frame is not None and row is not None and column is not None; coordinate=row is not None and column is not None
    if location:
        if frame not in frozen["frames"]: return _result("missing",query,"frame_not_in_frozen_bridge_evidence",case_id,frame_number=frame)
        if row<0 or row>=frozen["grid_shape"][0] or column<0 or column>=frozen["grid_shape"][1]: return _result("missing",query,"invalid_native_coordinate",case_id,coordinate=[row,column],grid_shape=list(frozen["grid_shape"]))
    elif coordinate:
        if row<0 or row>=frozen["grid_shape"][0] or column<0 or column>=frozen["grid_shape"][1]: return _result("missing",query,"invalid_native_coordinate",case_id,coordinate=[row,column],grid_shape=list(frozen["grid_shape"]))
    relation_requests={name for name,terms in RELATIONS.items() if wordset&terms}
    candidates=[]
    for bridge in frozen["rows"]:
        if hint is not None and bridge["bridge_id"]!=hint: continue
        target=bridge["target_record"]; relation=target.get("relationship")
        if relation_requests and relation not in relation_requests: continue
        if not relation_requests and relation is not None and query!=bridge["phrase"]: continue
        cites=bridge["citations"]
        if location and not any(c["frame_number"]==frame and c["coordinates"]["grid_row"]==row and c["coordinates"]["grid_column"]==column for c in cites if c.get("coordinates")): continue
        if coordinate and not location and not any(c["coordinates"]["grid_row"]==row and c["coordinates"]["grid_column"]==column for c in cites if c.get("coordinates")): continue
        phrase_words=set(anchors(bridge["phrase"])); overlap=len(wordset&phrase_words); exact=int(query==bridge["phrase"])
        qualifies=bool(hint or exact or relation_requests or location)
        if qualifies: candidates.append((exact,int(bool(location or coordinate)),overlap,bridge))
    if not candidates: return _result("unsupported",query,"insufficient_frozen_visual_bridge_evidence",case_id,authority_release_id=frozen["release_id"])
    vector=max(item[:3] for item in candidates); best=[item[3] for item in candidates if item[:3]==vector]
    if len(best)!=1: return _result("ambiguous",query,"multiple_frozen_visual_bridges_share_best_evidence",case_id,authority_release_id=frozen["release_id"],candidate_bridge_record_ids=sorted(x["bridge_id"] for x in best))
    bridge=best[0]
    return _result("resolved",query,"unique_frozen_visual_bridge_evidence",case_id,authority_release_id=frozen["release_id"],authority_manifest_sha256=frozen["manifest_sha256"],
        bridge_record_id=bridge["bridge_id"],target_hash=bridge["target_hash"],target_kind=bridge["target_kind"],identity_classification=bridge.get("identity_classification"),
        relationship_path=bridge["verified_relationship_path"],citations=bridge["citations"],target_record=bridge["target_record"],evidence={"exact_query_anchors":list(words),"bridge_phrase":bridge["phrase"]})

def _task(value): return resolve_visual_query(*value)

class VisualBridgeResolverEvaluation:
    def __init__(self,release:Path,cases:Path,output:Path,workers:int=24):
        if workers<1: raise ValueError("workers must be at least 1")
        self.authority=FrozenVisualBridgeAuthority(release); self.case_path=cases.resolve(); self.case_bytes=self.case_path.read_bytes(); self.cases=[json.loads(x) for x in self.case_bytes.splitlines() if x]
        self.output=output.resolve(); self.workers=workers
        if self.output.exists(): raise FileExistsError(f"output root already exists: {self.output}")
        ids=[x.get("case_id") for x in self.cases]
        if not all(isinstance(x,str) and x for x in ids) or len(ids)!=len(set(ids)): raise ValueError("cases require unique IDs")
        if any(x.get("reservation_role")!="PREREQUISITE_ACCEPTANCE_NOT_MODEL_EVALUATION" for x in self.cases): raise ValueError("sealed model evaluation cases may not be opened here")
    def run(self)->dict:
        self.output.mkdir(parents=True); start=time.perf_counter(); s0=resource.getrusage(resource.RUSAGE_SELF); c0=resource.getrusage(resource.RUSAGE_CHILDREN); frozen=self.authority.frozen(); tasks=[(x,frozen) for x in self.cases]
        if self.workers==1: results=list(map(_task,tasks))
        else:
            with ProcessPoolExecutor(max_workers=self.workers,mp_context=multiprocessing.get_context("fork")) as executor: results=list(executor.map(_task,tasks,chunksize=max(1,len(tasks)//(self.workers*4))))
        by={x["case_id"]:x for x in self.cases}; outcomes=[]; categories=defaultdict(lambda:Counter(cases=0,passed=0))
        for result in sorted(results,key=lambda x:x["case_id"]):
            case=by[result["case_id"]]; passed=result["status"]==case["expected_status"] and (case.get("expected_bridge_record_id") is None or result.get("bridge_record_id")==case["expected_bridge_record_id"])
            categories[case["category"]]["cases"]+=1; categories[case["category"]]["passed"]+=int(passed); outcomes.append({"case_id":case["case_id"],"category":case["category"],"passed":passed,"resolution":result})
        artifacts={"results":_write_jsonl(self.output/"results.jsonl",outcomes)}
        report={"schema":f"{SCHEMA}:evaluation_report","authority_release_id":self.authority.release_id,"cases":len(outcomes),"passed":sum(x["passed"] for x in outcomes),"failed":sum(not x["passed"] for x in outcomes),
            "category_counts":{k:dict(v) for k,v in sorted(categories.items())},"model_evaluation_reservations_opened":False,"operations_executed":0,"new_relationships_created":0,"visual_meanings_inferred":0,"model_training_performed":False}
        artifacts["report"]=_write_json(self.output/"evaluation-report.json",report)
        manifest={"schema":SCHEMA,"classification":"READ_ONLY_FROZEN_VISUAL_BRIDGE_ACCEPTANCE_NOT_MODEL_EVALUATION","authority":{"release_id":self.authority.release_id,"manifest_sha256":digest(self.authority.manifest_bytes)},"cases_sha256":digest(self.case_bytes),"model_evaluation_reservations_opened":False,"artifacts":artifacts,"operation_executed":False,"authority_created":False,"model_training_performed":False}
        _write_json(self.output/"manifest.json",manifest); wall=time.perf_counter()-start; s1=resource.getrusage(resource.RUSAGE_SELF); c1=resource.getrusage(resource.RUSAGE_CHILDREN)
        _write_json(self.output/"performance-receipt.json",{"schema":f"{SCHEMA}:performance_receipt","workers":self.workers,"logical_cpus":os.cpu_count(),"elapsed_wall_seconds":wall,"aggregate_cpu_seconds":s1.ru_utime+s1.ru_stime-s0.ru_utime-s0.ru_stime+c1.ru_utime+c1.ru_stime-c0.ru_utime-c0.ru_stime,"cases_per_second":len(self.cases)/wall if wall else 0,"maximum_resident_kib":max(s1.ru_maxrss,c1.ru_maxrss)})
        return manifest

def evaluate_visual_bridge_resolver(release:Path,cases:Path,output:Path,workers:int=24)->dict: return VisualBridgeResolverEvaluation(release,cases,output,workers).run()
