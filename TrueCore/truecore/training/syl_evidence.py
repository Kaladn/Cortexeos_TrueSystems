"""Deterministic five-channel SYL evidence construction.

The bridge phrase is the admitted source object.  Frozen bridge provenance is
retained as its explicit target binding; it is not converted into semantics.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib, json, multiprocessing, os, resource, time
from pathlib import Path
from typing import Any, Iterable

SCHEMA="truesystems_syl_evidence@1"
OFFSETS=(-6,-5,-4,-3,-2,-1,1,2,3,4,5,6)

def canonical(value:Any)->bytes: return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode("utf-8")
def digest(value:bytes|dict|list)->str: return hashlib.sha256(value if isinstance(value,bytes) else canonical(value)).hexdigest()
def rows(path:Path)->list[dict]: return [json.loads(line) for line in path.read_bytes().splitlines() if line]
def artifact(path:Path)->dict: raw=path.read_bytes(); return {"path":str(path.resolve()),"bytes":len(raw),"sha256":digest(raw)}
def write_json(path:Path,value:Any)->dict:
 raw=canonical(value)+b"\n"; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); return {"path":path.relative_to(path.parents[1]).as_posix(),"bytes":len(raw),"sha256":digest(raw),"records":1}
def write_jsonl(path:Path,values:Iterable[dict])->dict:
 data=list(values); raw=b"".join(canonical(x)+b"\n" for x in data); path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); return {"path":path.relative_to(path.parents[1]).as_posix(),"bytes":len(raw),"sha256":digest(raw),"records":len(data)}

def _relations(streams:list[dict])->Counter:
 result=Counter()
 for source in streams:
  values=source["anchors"]
  for i,center in enumerate(values):
   for offset in OFFSETS:
    j=i+offset
    if 0<=j<len(values): result[(center,values[j],offset)]+=1
 return result

def _fragment_rows(streams:list[dict])->list[dict]:
 occurrences=defaultdict(list)
 for source in streams:
  values=source["anchors"]
  for width in (2,3):
   for start in range(max(0,len(values)-width+1)):
    members=values[start:start+width]; identity=digest({"schema":f"{SCHEMA}:fragment_identity","members":members})
    occurrences[(identity,tuple(members))].append({"source_object_id":source["source_object_id"],"start_position":start,"end_position":start+width-1})
 return [{"schema":f"{SCHEMA}:symbol_fragment","fragment_id":identity,"members":list(members),"width":len(members),"support":len(found),"occurrences":found} for (identity,members),found in sorted(occurrences.items())]

def _source_task(task:tuple[dict,dict[str,int]])->dict:
 assignment,mapping=task
 from truemem.engine.anchors import anchorize,anchor_kind
 from truemem.engine.dataset_local_v2 import symbol_hex
 from truevision_intake.docufilm_truemem import build_docufilm_truemem_hierarchy
 phrase=assignment["phrase"]; read_hash=digest(phrase.encode("utf-8"))
 read={"record_type":"document_state_read","read_hash":read_hash,"glyph_records":[],"derived_text":phrase}
 hierarchy=build_docufilm_truemem_hierarchy(read,dataset_id="syl-bridge-phrases-v1",dataset_symbol_for=lambda anchor:symbol_hex(mapping[anchor]))
 anchors=[hierarchy["parent"]["anchor"],*[x["anchor"] for x in hierarchy["contained"]]]
 return {"schema":f"{SCHEMA}:admitted_source_object","source_object_id":assignment["bridge_record_id"],"domain":assignment["domain"],"exact_phrase":phrase,"exact_phrase_sha256":digest(phrase.encode()),"docufilm_read_hash":read_hash,"docufilm_parent":hierarchy["parent"],"docufilm_edges":hierarchy["edges"],"anchors":anchors,"anchor_items":[hierarchy["parent"],*hierarchy["contained"]],"target_identity":assignment["target_identity"],"relation_path_hash":assignment["relation_path_hash"],"source_group_id":assignment["source_group_id"],"paraphrase_family_id":assignment["paraphrase_family_id"],"target_provenance":assignment["assignment_evidence"],"whitespace_symbols":0,"normalization":"none"}

def _channel_record(task:tuple[dict,dict,dict,dict,dict])->dict:
 candidate,source,counts,relation_counts,fragments=task
 frag=[x for x in fragments if any(o["source_object_id"]==source["source_object_id"] for o in x["occurrences"])]
 patterns=[x for x in frag if x["support"]>=2]
 lanes=[]
 for position,center in enumerate(source["anchors"]):
  for offset in OFFSETS:
   j=position+offset
   if 0<=j<len(source["anchors"]):
    neighbor=source["anchors"][j]; lanes.append({"center":center,"center_position":position,"signed_offset":offset,"neighbor":neighbor,"observed_count":relation_counts[(center,neighbor,offset)]})
 record={"schema":f"{SCHEMA}:candidate_channels","candidate_bridge_id":candidate["bridge_record_id"],"domain":candidate["domain"],"source_object":{"status":"observed","source_object_id":source["source_object_id"],"exact_phrase_sha256":source["exact_phrase_sha256"],"docufilm_read_hash":source["docufilm_read_hash"],"target_identity":source["target_identity"],"target_provenance":source["target_provenance"]},"stable_anchor":{"status":"observed","anchors":[{**item,"observed_support":counts[item["anchor"]]} for item in source["anchor_items"]]},"anchor_sequence":{"status":"observed","ordered_anchors":source["anchors"],"signed_lanes":lanes},"derived_symbol_fragment":{"status":"observed","fragments":frag,"derivation":"contiguous admitted-anchor subsequences of widths 2 and 3"},"grouped_symbol_pattern":{"status":"observed","patterns":patterns,"grouping":"identical fragment members with support >= 2"},"authority":{"may_create_meaning":False,"may_create_operation":False,"may_create_relationship":False,"model_training_performed":False}}
 record["record_id"]=digest(record); return record

def _vector(query:list[str],source:dict,channel:dict,name:str)->tuple:
 qset=set(query); anchors=source["anchors"]; aset=set(anchors); overlap=qset&aset
 if name=="source_object": return (int(query==source["anchors"][1:]),len(overlap))
 if name=="stable_anchor":
  support={x["anchor"]:x["observed_support"] for x in channel["stable_anchor"]["anchors"]}; return (len(overlap),sum(support[x] for x in overlap))
 qpair=set(zip(query,query[1:])); spair=set(zip(anchors,anchors[1:]))
 if name=="anchor_sequence": return (len(qpair&spair),len(overlap))
 qfrags={tuple(query[i:i+w]) for w in (2,3) for i in range(max(0,len(query)-w+1))}
 key="fragments" if name=="derived_symbol_fragment" else "patterns"
 members={tuple(x["members"]) for x in channel[name][key]}; return (len(qfrags&members),len(overlap))

def evaluate_channels(records:list[dict],channels:dict[str,dict],sources:dict[str,dict])->dict:
 from truemem.engine.anchors import anchorize
 channel_names=("source_object","stable_anchor","anchor_sequence","derived_symbol_fragment","grouped_symbol_pattern")
 combinations=[(name,) for name in channel_names]+[("source_object","stable_anchor","anchor_sequence"),("stable_anchor","anchor_sequence","derived_symbol_fragment"),channel_names]
 results={}
 for combo in combinations:
  correct=resolved=0; domain=defaultdict(lambda:{"correct":0,"total":0,"resolved":0})
  for record in records:
   query=anchorize(record["phrase"]); scored=[]
   for candidate in record["candidates"]:
    cid=candidate["bridge_record_id"]; vector=tuple(value for name in combo for value in _vector(query,sources[cid],channels[cid],name)); scored.append((vector,cid))
   best=max(x[0] for x in scored); winners=[cid for vector,cid in scored if vector==best]; selected=winners[0] if len(winners)==1 and any(best) else None
   expected=record["expected_outcome"]["bridge_record_id"]; hit=selected==expected; correct+=hit; resolved+=selected is not None
   d=domain[record["domain"]]; d["correct"]+=hit; d["total"]+=1; d["resolved"]+=selected is not None
  results["+".join(combo)]={"correct":correct,"total":len(records),"resolved":resolved,"by_domain":dict(sorted(domain.items()))}
 return {"schema":f"{SCHEMA}:channel_ablation","resolver_baseline":{"correct":6,"total":14},"selection_policy":"lexicographic channel vectors; unique nonzero winner only; no scalar weights","results":results,"model_training_performed":False}

class SylEvidenceBuilder:
 def __init__(self,source_manifest:Path,prerequisite_release:Path,output:Path,workers:int=24): self.source_manifest=source_manifest.resolve(); self.release=prerequisite_release.resolve(); self.output=output.resolve(); self.workers=workers
 def run(self)->dict:
  if self.output.exists(): raise FileExistsError(self.output)
  start=time.perf_counter(); s0=resource.getrusage(resource.RUSAGE_SELF); c0=resource.getrusage(resource.RUSAGE_CHILDREN)
  sysroot=Path(__file__).resolve().parents[3]; import sys; sys.path[:0]=[str(sysroot/"TrueMem/src"),str(sysroot/"TrueVisionIntake")]
  from truemem.engine.anchors import anchorize
  from truemem.engine.dataset_local_v2 import allocate_dataset_local_symbols
  from .steering_prerequisites import SteeringPrerequisiteBuilder,_assign_splits,_candidate_record
  from .steering_experiment import _open_evaluation_records
  helper=SteeringPrerequisiteBuilder(self.source_manifest,self.output/".never",1); assignments,authorities=helper._load(); split_by_group=_assign_splits(assignments)
  counts=Counter(); prelim=[]
  for row in assignments:
   values=[f"object:docufilm:{digest(row['phrase'].encode())}",*anchorize(row["phrase"])]; counts.update(values); prelim.append(values)
  allocation=allocate_dataset_local_symbols(counts); mapping=allocation["mapping"]
  tasks=[(row,mapping) for row in assignments]
  if self.workers==1: sources=list(map(_source_task,tasks))
  else:
   with ProcessPoolExecutor(max_workers=self.workers,mp_context=multiprocessing.get_context("fork")) as ex: sources=list(ex.map(_source_task,tasks,chunksize=max(1,len(tasks)//self.workers)))
  sources.sort(key=lambda x:x["source_object_id"]); relations=_relations(sources); fragments=_fragment_rows(sources)
  source_by={x["source_object_id"]:x for x in sources}; pools={(d,s):[x for x in assignments if x["domain"]==d and split_by_group[x["source_group_id"]]==s] for d in {x["domain"] for x in assignments} for s in ("train","validation","evaluation")}
  candidate_records=[]
  for row in assignments:
   split=split_by_group[row["source_group_id"]]
   if split!="evaluation": candidate_records.append(_candidate_record((row,pools[(row["domain"],split)],split)))
  evaluation,_=_open_evaluation_records(self.source_manifest,self.release); candidate_records.extend(evaluation); candidate_records.sort(key=lambda x:x["record_id"])
  unique_candidates={c["bridge_record_id"]:c for record in candidate_records for c in record["candidates"]}
  channel_tasks=[(candidate,source_by[cid],dict(counts),dict(relations),fragments) for cid,candidate in sorted(unique_candidates.items())]
  if self.workers==1: channel_rows=list(map(_channel_record,channel_tasks))
  else:
   with ProcessPoolExecutor(max_workers=self.workers,mp_context=multiprocessing.get_context("fork")) as ex: channel_rows=list(ex.map(_channel_record,channel_tasks,chunksize=max(1,len(channel_tasks)//self.workers)))
  channel_rows.sort(key=lambda x:x["candidate_bridge_id"]); channel_by={x["candidate_bridge_id"]:x for x in channel_rows}
  self.output.mkdir(parents=True); artifacts={}
  lexicon={**allocation["lexicon"],"dataset_id":"syl-bridge-phrases-v1","normalization":"none","docufilm_only_entrypoint":True}
  artifacts["lexicon"]=write_json(self.output/"dataset/dataset_lexicon.json",lexicon); artifacts["sources"]=write_jsonl(self.output/"dataset/source_objects.jsonl",sources); artifacts["fragments"]=write_jsonl(self.output/"dataset/fragments.jsonl",fragments); artifacts["channels"]=write_jsonl(self.output/"channels/candidate_channels.jsonl",channel_rows)
  enriched=[]
  for record in candidate_records:
   value={**record,"syl_channel_record_ids":{c["bridge_record_id"]:channel_by[c["bridge_record_id"]]["record_id"] for c in record["candidates"]}}; enriched.append(value)
  artifacts["candidate_records"]=write_jsonl(self.output/"records/supplied_candidates.jsonl",enriched)
  ablation=evaluate_channels([x for x in enriched if x["split"]=="evaluation"],channel_by,source_by); artifacts["ablation"]=write_json(self.output/"evaluation/channel-ablation.json",ablation)
  manifest={"schema":SCHEMA,"classification":"DETERMINISTIC_EVIDENCE_NOT_TRAINED","source_manifest":artifact(self.source_manifest),"prerequisite_manifest":artifact(self.release/"manifest.json"),"authorities":authorities,"source_objects":len(sources),"candidate_channel_records":len(channel_rows),"fragments":len(fragments),"grouped_patterns":sum(x["support"]>=2 for x in fragments),"normalization":"none","whitespace_symbols":0,"channels":["source_object","stable_anchor","anchor_sequence","derived_symbol_fragment","grouped_symbol_pattern"],"model_training_performed":False,"optimizer_updates":0,"baseline_checkpoint_modified":False,"artifacts":artifacts}
  write_json(self.output/"manifest.json",manifest)
  s1=resource.getrusage(resource.RUSAGE_SELF); c1=resource.getrusage(resource.RUSAGE_CHILDREN); wall=time.perf_counter()-start
  write_json(self.output/"performance-receipt.json",{"schema":f"{SCHEMA}:performance","workers":self.workers,"logical_cpus":os.cpu_count(),"elapsed_wall_seconds":wall,"aggregate_cpu_seconds":s1.ru_utime+s1.ru_stime-s0.ru_utime-s0.ru_stime+c1.ru_utime+c1.ru_stime-c0.ru_utime-c0.ru_stime})
  return manifest

def build_syl_evidence(source_manifest:Path,prerequisite_release:Path,output:Path,workers:int=24)->dict: return SylEvidenceBuilder(source_manifest,prerequisite_release,output,workers).run()
