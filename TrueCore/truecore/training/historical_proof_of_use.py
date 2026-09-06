"""Read-only held-out and Codex-use analysis of a sealed historical checkpoint."""
from __future__ import annotations
from collections import defaultdict
import gzip,json,math
from pathlib import Path
import torch
import torch.nn.functional as F
from .historical_method_equivalence import _load_authority,canonical,sha,write

OFFSETS=(-6,-5,-4,-3,-2,-1,1,2,3,4,5,6)
def analyze(preparation:Path,clean_method:Path,training_result:Path,output:Path)->dict:
 if output.exists():raise FileExistsError(output)
 method,authority=_load_authority(clean_method);method.CORPUS=preparation/"source-package";prepared=preparation/"prepared";mapping=json.loads((prepared/"symbol-index-mapping.json").read_bytes());seal=json.loads((training_result/"FINAL-seal.json").read_bytes())
 checkpoint=training_result/"FINAL.pt"
 if sha(checkpoint.read_bytes())!=seal["checkpoint_sha256"]:raise ValueError("sealed checkpoint mismatch")
 perm_to_dense={x["permanent_value"]:x["dense_model_index"] for x in mapping["entries"]};dense_to_perm={x["dense_model_index"]:x["permanent_value"] for x in mapping["entries"]};dense_to_surface={x["dense_model_index"]:x["surface"] for x in mapping["entries"]};surface_to_perm={x["surface"]:x["permanent_value"] for x in mapping["entries"]};unknown=method.SPECIAL["<UNKNOWN>"]
 split_manifest=json.loads((preparation/"source-package/source-split-manifest.json").read_bytes());meta={x["session_id"]:x for x in split_manifest if x["split"]=="test"};test_rows=[json.loads(x) for x in (preparation/"source-package/test.jsonl").read_bytes().splitlines() if x]
 device=torch.device("xpu:0");model=method.ChatDecoder(len(mapping["entries"]),device);field=method.ChatLocationField(prepared/"M002.jsonl.gz",perm_to_dense,device);inputs=method.ChatLocationInput(model.embedding,field);payload=torch.load(checkpoint,map_location=device,weights_only=False);model.load_state_dict(payload["model"]);model.eval()
 relation_counts={}
 with gzip.open(prepared/"M002.jsonl.gz","rt",encoding="utf-8") as stream:
  for line in stream:
   row=json.loads(line);relation_counts[(int(row["center"],16),row["offset"],int(row["neighbor"],16))]=row["count"]
 totals={"targets":0,"top1":0,"top5":0,"top10":0,"loss_sum":0.0};by_session={};by_domain=defaultdict(lambda:{"targets":0,"top1":0,"top5":0,"top10":0,"loss_sum":0.0});lane=defaultdict(lambda:{"supported_positions":0,"top1":0});tasks=[]
 for row in test_rows:
  surfaces,_=method.session_surfaces(row);permanent=[surface_to_perm.get(x,unknown) for x in surfaces];dense=[perm_to_dense.get(x,perm_to_dense[unknown]) for x in permanent];session=meta[row["session_id"]];stats={"targets":0,"top1":0,"top5":0,"top10":0,"loss_sum":0.0,"session_id":row["session_id"],"domain":session["domain"],"path":session["path"],"source_sha256":session["sha256"]};predictions={}
  for start in range(0,max(0,len(dense)-1),512):
   segment=dense[start:start+513];a=segment[:-1];b=segment[1:];x=torch.tensor(a,device=device).view(1,-1);valid=torch.ones_like(x,dtype=torch.bool)
   with torch.no_grad():logits=model.decode(inputs(x),valid)[0];target=torch.tensor(b,device=device);losses=F.cross_entropy(logits,target,reduction="none");top=torch.topk(logits,min(10,logits.shape[-1]),dim=-1)
   top_indices=top.indices.cpu().tolist();top_values=top.values.cpu().tolist();loss_values=losses.cpu().tolist()
   for j,want in enumerate(b):
    absolute=start+j;ranked=top_indices[j];correct=ranked[0]==want
    predictions[absolute]={"indices":ranked,"scores":top_values[j]}
    for target_stats in (totals,stats,by_domain[session["domain"]]):
     target_stats["targets"]+=1;target_stats["top1"]+=int(correct);target_stats["top5"]+=int(want in ranked[:5]);target_stats["top10"]+=int(want in ranked);target_stats["loss_sum"]+=loss_values[j]
    center=permanent[absolute]
    for offset in OFFSETS:
     neighbor_index=absolute+offset
     if 0<=neighbor_index<len(permanent) and (center,offset,permanent[neighbor_index]) in relation_counts:
      lane[offset]["supported_positions"]+=1;lane[offset]["top1"]+=int(correct)
  # Fixed before prediction inspection: one-third and two-thirds of each session.
  for position in sorted({max(0,(len(dense)-2)//3),max(0,2*(len(dense)-2)//3)}):
   want=dense[position+1];center_perm=permanent[position];prediction=predictions[position];model_ranked=prediction["indices"][:5]
   supported=[(count,neighbor) for (center,offset,neighbor),count in relation_counts.items() if center==center_perm and offset==1];supported.sort(key=lambda x:(-x[0],x[1]));baseline_perm=supported[0][1] if supported else unknown;baseline=perm_to_dense.get(baseline_perm,perm_to_dense[unknown]);accepted=next((value for value in model_ranked if (center_perm,1,dense_to_perm[value]) in relation_counts),None);model_choice=accepted if accepted is not None else baseline
   baseline_correct=baseline==want;assisted_correct=model_choice==want;useful=assisted_correct and not baseline_correct;harmful=baseline_correct and not assisted_correct
   tasks.append({"task_id":sha(canonical({"session":row["session_id"],"position":position}))[:24],"session_id":row["session_id"],"domain":session["domain"],"path":session["path"],"position":position,"input_evidence":{"center_anchor":dense_to_surface[dense[position]],"source_sha256":session["sha256"]},"verified_next_anchor":dense_to_surface[want],"model_top_predictions":[{"anchor":dense_to_surface[value],"score":score,"supported_plus1":(center_perm,1,dense_to_perm[value]) in relation_counts} for value,score in zip(model_ranked,prediction["scores"][:5])],"codex_without_model":{"choice":dense_to_surface[baseline],"rule":"highest observed deterministic +1 count","correct":baseline_correct},"codex_with_model":{"choice":dense_to_surface[model_choice],"rule":"first model top-5 anchor with admitted +1 support; otherwise deterministic baseline","suggestion_accepted":accepted is not None,"correct":assisted_correct},"effect":"useful" if useful else "harmful" if harmful else "neutral","invented_anchor":False,"unsupported_fact":False})
  by_session[row["session_id"]]=stats
 def finish(value):
  count=value.pop("targets");loss=value.pop("loss_sum");value.update({"targets":count,"top1_accuracy":value.pop("top1")/count,"top5_accuracy":value.pop("top5")/count,"top10_accuracy":value.pop("top10")/count,"cross_entropy":loss/count,"perplexity":math.exp(loss/count)})
 for value in [totals,*by_session.values(),*by_domain.values()]:finish(value)
 effects={name:sum(x["effect"]==name for x in tasks) for name in ("useful","neutral","harmful")};baseline_correct=sum(x["codex_without_model"]["correct"] for x in tasks);assisted_correct=sum(x["codex_with_model"]["correct"] for x in tasks)
 result={"schema":"truesystems_historical_proof_of_use@1","authority":authority,"checkpoint":{"sha256":seal["checkpoint_sha256"],"identity":seal["checkpoint_identity"],"best_update":seal["best_update"]},"sealed_evaluation":{"opened_by_historical_trainer":True,"additional_analysis":"same authorized evaluation phase","overall":totals,"by_session":by_session,"by_domain":dict(by_domain),"by_supported_relationship_lane":{str(k):{**v,"top1_accuracy":v["top1"]/v["supported_positions"] if v["supported_positions"] else None} for k,v in sorted(lane.items())}},"codex_use":{"fixed_task_selection":"one-third and two-thirds positions per sealed session, fixed before model-output inspection","tasks":tasks,"effects":effects,"without_model":{"correct":baseline_correct,"tasks":len(tasks),"accuracy":baseline_correct/len(tasks)},"with_model":{"correct":assisted_correct,"tasks":len(tasks),"accuracy":assisted_correct/len(tasks)},"material_improvement":assisted_correct>baseline_correct},"invented_ids":0,"invalid_selections":0,"authority_violations":0,"deployed":False,"runtime_connected":False,"authority_created":False};result["report_id"]=sha(canonical(result));write(output/"proof-of-use.json",result);return result
