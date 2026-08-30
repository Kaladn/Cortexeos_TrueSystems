"""Prepare NetworkX AST fixtures and local TrueSystems 6-1-6 instruction maps.

External sources remain exact flat files and NOT_LOCAL_TRUTH.  Only selected
local contracts are mapped into signed 6-1-6 windows.  No model is trained.
"""
from __future__ import annotations

import ast
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib, json, multiprocessing, struct
from pathlib import Path
from typing import Any

SCHEMA="truesystems_symbolic_foundations_adapter@1"; OFFSETS=tuple(range(-6,0))+tuple(range(1,7))
ANCHOR_RECORD=struct.Struct(">6sQ"); RELATION_RECORD=struct.Struct(">6s6shI"); POSTING_RECORD=struct.Struct(">6sIH")

def canonical(v:Any)->bytes:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def digest(v:bytes|dict|list)->str:return hashlib.sha256(v if isinstance(v,bytes) else canonical(v)).hexdigest()
def rows(p:Path)->list[dict]:return [json.loads(x) for x in p.read_bytes().splitlines() if x]
def write_json(p:Path,v:Any)->dict:
 raw=canonical(v)+b"\n";p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return {"path":p.name,"bytes":len(raw),"sha256":digest(raw),"records":1}
def write_jsonl(p:Path,v:list[dict])->dict:
 raw=b"".join(canonical(x)+b"\n" for x in v);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return {"path":p.name,"bytes":len(raw),"sha256":digest(raw),"records":len(v)}

def _name(node:ast.AST)->str:
 if isinstance(node,ast.Name):return node.id
 if isinstance(node,ast.Attribute):return _name(node.value)+"."+node.attr
 return ast.dump(node,include_attributes=False)
def _safe_literal(value:Any)->Any:
 if isinstance(value,set):return {"set_members":[_safe_literal(x) for x in sorted(value,key=repr)]}
 if isinstance(value,tuple):return {"tuple_members":[_safe_literal(x) for x in value]}
 if isinstance(value,list):return [_safe_literal(x) for x in value]
 if isinstance(value,dict):return {str(k):_safe_literal(v) for k,v in value.items()}
 return value
def _argument(node:ast.AST,text:str)->dict[str,Any]:
 if isinstance(node,ast.Name):return {"kind":"name","value":node.id}
 if isinstance(node,ast.Attribute):return {"kind":"attribute","value":_name(node)}
 try:
  return {"kind":"literal","value":_safe_literal(ast.literal_eval(node))}
 except Exception:
  source=ast.get_source_segment(text,node)
  return {"kind":"expression","source":source,"ast":ast.dump(node,include_attributes=False)} if source is not None else {"kind":"unavailable","ast":ast.dump(node,include_attributes=False)}
def _scope_nodes(root:ast.AST):
 """Walk one definition without absorbing observations from nested definitions."""
 stack=list(reversed(list(ast.iter_child_nodes(root))))
 while stack:
  node=stack.pop()
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda)):
   continue
  yield node;stack.extend(reversed(list(ast.iter_child_nodes(node))))
def _networkx_task(task:tuple[dict,str])->dict:
 record,root_text=task; identity=record["source_identity"]; path=Path(root_text)/"networkx"/identity["path"];raw=path.read_bytes()
 if digest(raw)!=identity["sha256"]:raise ValueError(f"source mismatch: {path}")
 text=raw.decode("utf-8");tree=ast.parse(text,filename=identity["path"],type_comments=True); units=[]
 for node in ast.walk(tree):
  if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
  calls=[];assertions=[];fixtures=[]
  for child in _scope_nodes(node):
   if isinstance(child,ast.Call):
    name=_name(child.func); entry={"name":name,"line":child.lineno,"arguments":[_argument(x,text) for x in child.args],"keywords":[{"name":x.arg,"argument":_argument(x.value,text)} for x in child.keywords]};calls.append(entry)
    if name.endswith(("Graph","DiGraph","MultiGraph","MultiDiGraph","add_edge","add_edges_from","add_node","add_nodes_from")):fixtures.append(entry)
   elif isinstance(child,ast.Assert):assertions.append({"line":child.lineno,"expression":ast.get_source_segment(text,child.test)})
  if calls:
   source=ast.get_source_segment(text,node) or ""; unit={"symbol":node.name,"line_start":node.lineno,"line_end":node.end_lineno,"source_sha256":digest(source.encode()),"calls":sorted(calls,key=lambda x:(x["line"],x["name"])),"fixture_constructions":sorted(fixtures,key=lambda x:(x["line"],x["name"])),"assertions":sorted(assertions,key=lambda x:x["line"])};unit["unit_id"]=digest(unit);units.append(unit)
 result={"schema":f"{SCHEMA}:networkx_ast_source","truth_status":"EXTERNAL_NOT_LOCAL_TRUTH","source_record_id":record["source_record_id"],"source_identity":identity,"exact_flat_file":{"path":str(path),"sha256":identity["sha256"],"bytes":len(raw)},"ast_units":sorted(units,key=lambda x:(x["line_start"],x["symbol"])),"adapter_claim":"PYTHON_AST_OBSERVATIONS_ONLY_NO_GRAPH_MEANING_INFERRED","training_eligible":False}
 result["record_id"]=digest(result);return result

LOCAL_FILES=("docs/OPERATOR_MODEL_TRAINING_CONTRACT.md","docs/TRUEMEM_RELATIONSHIP_TRAINING_SHAPE.md","TrueMem/system/contracts/RELATIONSHIP_GRAPH_616.md","TrueMem/system/contracts/COMPLETE_ANCHOR_INTAKE.md")
def _paragraphs(text:str):
 for match in re.finditer(r"(?:\A|(?<=\n\n))(.+?)(?=\n\n|\Z)",text,re.DOTALL):
  value=match.group(1)
  if not value.strip():continue
  start,end=match.start(1),match.end(1);yield value,start,end,text.count("\n",0,start)+1,text.count("\n",0,end)+1
def _local_maps(repo:Path)->tuple[list[dict],Counter,Counter,list[tuple]]:
 import sys;sys.path.insert(0,str(repo/"TrueMem/src"));from truemem.engine.anchors import anchorize
 blocks=[];counts=Counter();relations=Counter();postings=[]
 for source_path in LOCAL_FILES:
  raw=(repo/source_path).read_bytes();text=raw.decode("utf-8")
  for paragraph,char_start,char_end,line_start,line_end in _paragraphs(text):
   byte_start=len(text[:char_start].encode());byte_end=len(text[:char_end].encode())
   read_hash=digest(paragraph.encode());anchors=[f"object:docufilm:{read_hash}",*anchorize(paragraph)];ordinal=len(blocks);counts.update(anchors)
   for position,center in enumerate(anchors):
    postings.append((center,ordinal,position))
    for offset in OFFSETS:
     j=position+offset
     if 0<=j<len(anchors):relations[(center,anchors[j],offset)]+=1
   blocks.append({"block_ordinal":ordinal,"source_path":source_path,"source_sha256":digest(raw),"byte_start":byte_start,"byte_end_exclusive":byte_end,"line_start":line_start,"line_end":line_end,"exact_text":paragraph,"exact_text_sha256":read_hash,"docufilm_read_hash":read_hash,"anchors":anchors})
 return blocks,counts,relations,postings

def build_symbolic_adapter(curation_root:Path,source_root:Path,repo:Path,output:Path,workers:int=24,local_to_external:int=13)->dict:
 if output.exists():raise FileExistsError(output)
 curation_root=curation_root.resolve();source_root=source_root.resolve();repo=repo.resolve(); manifest_raw=(curation_root/"manifest.json").read_bytes();manifest=json.loads(manifest_raw)
 if manifest.get("curation_release_id")!="cce813f42b56f639fe0b0eb9e8a6418641dea8121f9066d2d3d710d0d3d123ba":raise ValueError("unexpected curation release")
 accepted=rows(curation_root/"accepted.jsonl");tasks=[(x,str(source_root)) for x in accepted]
 if workers==1:external=list(map(_networkx_task,tasks))
 else:
  with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context("fork")) as ex:external=list(ex.map(_networkx_task,tasks,chunksize=max(1,len(tasks)//workers)))
 external.sort(key=lambda x:x["source_record_id"]);blocks,counts,relations,postings=_local_maps(repo)
 symbols={anchor:index for index,anchor in enumerate(sorted(counts))};symbol_hex={a:"0x"+i.to_bytes(6,"big").hex().upper() for a,i in symbols.items()}
 import sys;sys.path.insert(0,str(repo/"TrueVisionIntake"));sys.path.insert(0,str(repo/"TrueMem/src"));from truevision_intake.docufilm_truemem import build_docufilm_truemem_hierarchy
 for block in blocks:
  read={"record_type":"document_state_read","read_hash":block["docufilm_read_hash"],"glyph_records":[],"derived_text":block["exact_text"]}
  hierarchy=build_docufilm_truemem_hierarchy(read,dataset_id="truesystems-system-laws-v1",dataset_symbol_for=lambda a:symbol_hex[a])
  if [hierarchy["parent"]["anchor"],*[x["anchor"] for x in hierarchy["contained"]]]!=block["anchors"]:raise ValueError("DocuFilm anchor stream mismatch")
  block["docufilm_hierarchy"]=hierarchy
 output.mkdir(parents=True);(output/"local-map").mkdir();
 with (output/"local-map/anchor_counts.awbin").open("wb") as h:
  for a,n in sorted(counts.items()):h.write(ANCHOR_RECORD.pack(symbols[a].to_bytes(6,"big"),n))
 with (output/"local-map/relation_counts.awbin").open("wb") as h:
  for (a,b,o),n in sorted(relations.items()):h.write(RELATION_RECORD.pack(symbols[a].to_bytes(6,"big"),symbols[b].to_bytes(6,"big"),o,n))
 with (output/"local-map/block_anchor_postings.awbin").open("wb") as h:
  for a,b,p in sorted(postings,key=lambda x:(symbols[x[0]],x[1],x[2])):h.write(POSTING_RECORD.pack(symbols[a].to_bytes(6,"big"),b,p))
 receipts=[{"schema":f"{SCHEMA}:docufilm_source_receipt","record_type":"document_state_read","read_hash":b["docufilm_read_hash"],"source_path":b["source_path"],"source_sha256":b["source_sha256"],"byte_start":b["byte_start"],"byte_end_exclusive":b["byte_end_exclusive"],"line_start":b["line_start"],"line_end":b["line_end"],"hierarchy_sha256":digest(b["docufilm_hierarchy"]),"intake_authority":"TrueVision.DocuFilm"} for b in blocks]
 artifacts={"external_ast":write_jsonl(output/"external-networkx-ast.jsonl",external),"local_blocks":write_jsonl(output/"local-map/blocks.jsonl",blocks),"docufilm_receipts":write_jsonl(output/"local-map/docufilm-receipts.jsonl",receipts),"lexicon":write_json(output/"local-map/dataset_lexicon.json",{"schema":f"{SCHEMA}:isolated_six_byte_lexicon","symbol_bytes":6,"allocation":"sorted_frozen_isolated_curriculum_namespace","anchors":[{"anchor":a,"symbol":symbol_hex[a],"observed_count":counts[a]} for a in sorted(counts)]})}
 for key in ("local_blocks","docufilm_receipts","lexicon"):artifacts[key]["path"]="local-map/"+artifacts[key]["path"]
 for key,name in (("anchor_binary","anchor_counts.awbin"),("relation_binary","relation_counts.awbin"),("posting_binary","block_anchor_postings.awbin")):
  raw=(output/"local-map"/name).read_bytes();artifacts[key]={"path":"local-map/"+name,"bytes":len(raw),"sha256":digest(raw)}
 local_windows=[]
 for block in blocks:
  a=block["anchors"]
  for i,center in enumerate(a):local_windows.append({"block_ordinal":block["block_ordinal"],"center_position":i,"center":center,"before":a[max(0,i-6):i],"after":a[i+1:i+7],"source_path":block["source_path"],"source_sha256":block["source_sha256"]})
 local_windows.sort(key=lambda x:(x["source_path"],x["block_ordinal"],x["center_position"]));external_units=[{"source_record_id":x["source_record_id"],"unit_id":u["unit_id"]} for x in external for u in x["ast_units"]]
 schedule=[];total=max(len(local_windows),len(external_units))
 for i in range(total):
  if external_units:schedule.append({"role":"EXTERNAL_FLAT_AST","identity":external_units[i%len(external_units)]})
  if local_windows:
   for j in range(local_to_external):schedule.append({"role":"LOCAL_SYSTEM_616","identity":{"source_path":local_windows[(i*local_to_external+j)%len(local_windows)]["source_path"],"block_ordinal":local_windows[(i*local_to_external+j)%len(local_windows)]["block_ordinal"],"center_position":local_windows[(i*local_to_external+j)%len(local_windows)]["center_position"]}})
 artifacts["windows"]=write_jsonl(output/"local-map/windows-616.jsonl",local_windows);artifacts["windows"]["path"]="local-map/"+artifacts["windows"]["path"];artifacts["schedule"]=write_jsonl(output/"curriculum-schedule.jsonl",schedule)
 result={"schema":SCHEMA,"classification":"PREPARED_CURRICULUM_NOT_TRAINED","curation_manifest_sha256":digest(manifest_raw),"external_sources":len(external),"external_ast_units":len(external_units),"local_contract_files":len(LOCAL_FILES),"local_blocks":len(blocks),"local_windows_616":len(local_windows),"curriculum_presentation_ratio":{"local_system_616":local_to_external,"external_flat_ast":1},"observed_counts_modified_by_schedule":False,"mathlib_status":"SEALED_QUARANTINED","despite_status":"SEALED_QUARANTINED","model_training_performed":False,"optimizer_updates":0,"authority_created":False,"artifacts":artifacts};result["release_id"]=digest(result);write_json(output/"manifest.json",result);return result
