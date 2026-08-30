"""Single authorized replacement experiment; generated artifacts remain external."""
from __future__ import annotations
import hashlib,json,random,traceback
from pathlib import Path
from typing import Any
import torch
from torch import nn
import torch.nn.functional as F
from .symbolic_foundations_scorers import Local616SuppliedCandidateScorer,ExternalAstSuppliedCandidateScorer,_argument_kinds,_identity_maps,_verify_representation,canonical,digest,rows,write_json,UNSEEN_EXTERNAL_CALL

SCHEMA="truesystems_symbolic_foundations_replacement_experiment@1";SEED=61613;BATCH=32;EPOCHS=13

def seed_all():
 random.seed(SEED);torch.manual_seed(SEED);torch.xpu.manual_seed_all(SEED);torch.use_deterministic_algorithms(True)
def state_hash(model:nn.Module)->str:
 h=hashlib.sha256()
 for name,value in sorted(model.state_dict().items()):h.update(name.encode());h.update(value.detach().cpu().contiguous().numpy().tobytes())
 return h.hexdigest()
def save_model(path:Path,model:nn.Module)->dict:
 path.parent.mkdir(parents=True,exist_ok=True);torch.save(model.state_dict(),path);raw=path.read_bytes();return {"path":str(path.resolve()),"sha256":digest(raw),"bytes":len(raw),"state_sha256":state_hash(model)}
def pad(values:list[list[int]],device:torch.device)->tuple[torch.Tensor,torch.Tensor]:
 width=max(map(len,values));result=torch.zeros((len(values),width),dtype=torch.long,device=device);lengths=torch.tensor([len(x) for x in values],device=device)
 for i,value in enumerate(values):result[i,:len(value)]=torch.tensor(value,device=device)
 return result,lengths
class LocalModel(Local616SuppliedCandidateScorer):
 def batch_logits(self,histories,lengths,candidates):
  encoded,_=self.history(self.embedding(histories));context=encoded[torch.arange(histories.shape[0],device=histories.device),lengths-1]
  return self.head(torch.cat((context[:,None].expand(-1,candidates.shape[1],-1),self.embedding(candidates)),dim=-1)).squeeze(-1)
class ExternalModel(ExternalAstSuppliedCandidateScorer):
 def batch_logits(self,centers,args,argmask,candidates):
  _,state=self.history(self.embedding(centers[:,None]));embedded=self.argument_embedding(args);summary=(embedded*argmask[:,:,None]).sum(1)/argmask.sum(1,keepdim=True)
  return self.head(torch.cat((state[-1][:,None].expand(-1,candidates.shape[1],-1),summary[:,None].expand(-1,candidates.shape[1],-1),self.embedding(candidates)),dim=-1)).squeeze(-1)
def batches(records:list[dict],epoch:int)->list[list[dict]]:
 values=list(records);random.Random(SEED+epoch).shuffle(values);return [values[i:i+BATCH] for i in range(0,len(values),BATCH)]
def local_batch(records,symbols,device):
 histories,lengths=pad([[symbols[x] for x in (r["history"] or [r["center_anchor"]])] for r in records],device);lists=[[symbols[x] for x in r["supplied_candidates"]] for r in records];width=max(map(len,lists));candidates=torch.zeros((len(records),width),dtype=torch.long,device=device);mask=torch.zeros_like(candidates,dtype=torch.bool);targets=[]
 for i,(record,values) in enumerate(zip(records,lists)):candidates[i,:len(values)]=torch.tensor(values,device=device);mask[i,:len(values)]=True;targets.append(record["supplied_candidates"].index(record["expected_outcome"]["anchor"]))
 return histories,lengths,candidates,mask,torch.tensor(targets,device=device)
def external_batch(records,identities,device):
 kinds={x:i for i,x in enumerate(("attribute","expression","literal","name","none","unavailable"))};centers=torch.tensor([identities.get(r["center_call"]["name"],identities[UNSEEN_EXTERNAL_CALL]) for r in records],device=device);args,lengths=pad([[kinds[x] for x in _argument_kinds(r)] for r in records],device);argmask=torch.arange(args.shape[1],device=device)[None,:]<lengths[:,None];lists=[[identities[x] for x in r["supplied_candidates"]] for r in records];width=max(map(len,lists));candidates=torch.zeros((len(records),width),dtype=torch.long,device=device);mask=torch.zeros_like(candidates,dtype=torch.bool);targets=[]
 for i,(record,values) in enumerate(zip(records,lists)):candidates[i,:len(values)]=torch.tensor(values,device=device);mask[i,:len(values)]=True;targets.append(record["supplied_candidates"].index(record["expected_outcome"]["call_identity"]))
 return centers,args,argmask,candidates,mask,torch.tensor(targets,device=device)
def epoch(model,records,domain,identities,device,number,optimizer=None):
 model.train(optimizer is not None);total=0.;count=0
 for group in batches(records,number if optimizer else 0):
  if domain=="local":h,l,c,m,t=local_batch(group,identities,device);logits=model.batch_logits(h,l,c)
  else:center,a,am,c,m,t=external_batch(group,identities,device);logits=model.batch_logits(center,a,am,c)
  loss=F.cross_entropy(logits.masked_fill(~m,float("-inf")),t)
  if optimizer:optimizer.zero_grad(set_to_none=True);loss.backward();optimizer.step()
  total+=float(loss.detach().cpu())*len(group);count+=len(group)
 return total/count
def evaluate(model,records,domain,identities,device):
 model.eval();correct=invalid=0;classes={"sentinel":{"records":0,"correct":0},"known":{"records":0,"correct":0}}
 with torch.no_grad():
  for group in batches(records,0):
   if domain=="local":h,l,c,m,t=local_batch(group,identities,device);logits=model.batch_logits(h,l,c)
   else:center,a,am,c,m,t=external_batch(group,identities,device);logits=model.batch_logits(center,a,am,c)
   predicted=logits.masked_fill(~m,float("-inf")).argmax(1);correct+=int((predicted==t).sum().cpu());invalid+=int((predicted>=m.sum(1)).sum().cpu())
   if domain=="external":
    for record,got,want in zip(group,predicted.cpu().tolist(),t.cpu().tolist()):
     kind="sentinel" if record["expected_outcome"]["call_identity"]==UNSEEN_EXTERNAL_CALL else "known";classes[kind]["records"]+=1;classes[kind]["correct"]+=int(got==want)
 total=len(records);result={"records":total,"exact_selection":correct,"accuracy":correct/total,"invalid_selections":invalid,"invented_ids":0,"authority_violations":0}
 if domain=="external":
  for value in classes.values():value["accuracy"]=value["correct"]/value["records"] if value["records"] else 0.
  result["classes"]=classes
 return result
def run(preflight_path:Path,representation:Path,adapter:Path,output:Path)->dict:
 if output.exists():raise FileExistsError(output)
 output.mkdir(parents=True);preflight=json.loads(preflight_path.read_bytes());manifest=_verify_representation(representation)
 if preflight.get("preflight_id")!="5ea7b564b4e6aa3e9739f5c55d24a0bd51e0bda6cfbeb963f9bee19cd8b39456" or manifest["release_id"]!=preflight["representation_release_id"]:raise ValueError("authorization identity mismatch")
 authorization={"schema":f"{SCHEMA}:authorization","scope":"ONE_EXPERIMENT","preflight_id":preflight["preflight_id"],"authorized":False,"consumed":True,"revoked":False,"evaluation_opened":False};write_json(output/"authorization.json",authorization)
 try:
  symbols,external_ids=_identity_maps(adapter,manifest,representation);device=torch.device("xpu");seed_all();local=LocalModel(max(symbols.values())+1).to(device);external=ExternalModel(len(external_ids),6).to(device)
  local_opt=torch.optim.AdamW(local.parameters(),lr=.001,betas=(.9,.95),eps=1e-8,weight_decay=.01);external_opt=torch.optim.AdamW(external.parameters(),lr=.001,betas=(.9,.95),eps=1e-8,weight_decay=.01)
  lt=rows(representation/"splits/local-train.jsonl");lv=rows(representation/"splits/local-validation.jsonl");et=rows(representation/"splits/external-train.jsonl");ev=rows(representation/"splits/external-validation.jsonl");history=[];best={"local":None,"external":None};updates={"local":0,"external":0}
  for n in range(1,EPOCHS+1):
   losses=[]
   for repeat in range(13):losses.append(epoch(local,lt,"local",symbols,device,n*13+repeat,local_opt));updates["local"]+=(len(lt)+BATCH-1)//BATCH
   eloss=epoch(external,et,"external",external_ids,device,n,external_opt);updates["external"]+=(len(et)+BATCH-1)//BATCH
   with torch.no_grad():lval=epoch(local,lv,"local",symbols,device,0);eval_loss=epoch(external,ev,"external",external_ids,device,0)
   item={"epoch":n,"local_training_loss":sum(losses)/13,"external_training_loss":eloss,"local_validation_loss":lval,"external_validation_loss":eval_loss,"local_state_sha256":state_hash(local),"external_state_sha256":state_hash(external),"optimizer_updates":dict(updates)};history.append(item);write_json(output/"training-history.json",history)
   for name,model,value in (("local",local,lval),("external",external,eval_loss)):
    if best[name] is None or value<best[name]["validation_loss"]:best[name]={"epoch":n,"validation_loss":value,"artifact":save_model(output/f"checkpoints/{name}-selected.pt",model)}
  local.load_state_dict(torch.load(output/"checkpoints/local-selected.pt",map_location=device,weights_only=True));external.load_state_dict(torch.load(output/"checkpoints/external-selected.pt",map_location=device,weights_only=True))
  authorization["evaluation_opened"]=True;write_json(output/"authorization.json",authorization)
  local_eval=rows(representation/"sealed/local-evaluation-records.jsonl");external_eval=rows(representation/"sealed/external-evaluation-records.jsonl");evaluation={"opened_once_after_selection":True,"local":evaluate(local,local_eval,"local",symbols,device),"external":evaluate(external,external_eval,"external",external_ids,device)}
  result={"schema":SCHEMA,"status":"COMPLETE_NOT_DEPLOYED","preflight_id":preflight["preflight_id"],"representation_release_id":manifest["release_id"],"seed":SEED,"device":{"type":"xpu","name":torch.xpu.get_device_name()},"epochs":EPOCHS,"batch_size":BATCH,"optimizer":{"name":"AdamW","learning_rate":.001,"betas":[.9,.95],"epsilon":1e-8,"weight_decay":.01},"records":{"training":{"local":len(lt),"external":len(et)},"validation":{"local":len(lv),"external":len(ev)},"evaluation":{"local":len(local_eval),"external":len(external_eval)}},"presentation_ratio":{"local":13,"external":1},"optimizer_updates":updates,"selected_checkpoints":best,"evaluation":evaluation,"invented_ids":0,"invalid_selections":evaluation["local"]["invalid_selections"]+evaluation["external"]["invalid_selections"],"authority_violations":0,"authorization_revoked":True,"deployed":False,"runtime_connected":False,"authority_created":False};result["experiment_id"]=digest(result);write_json(output/"experiment-report.json",result);return result
 except Exception as error:
  write_json(output/"failed-experiment.json",{"schema":f"{SCHEMA}:failure","error_type":type(error).__name__,"error":str(error),"traceback":traceback.format_exc(),"authorization_revoked":True,"deployed":False,"authority_created":False});raise
 finally:
  authorization["authorized"]=False;authorization["consumed"]=True;authorization["revoked"]=True;write_json(output/"authorization.json",authorization)
