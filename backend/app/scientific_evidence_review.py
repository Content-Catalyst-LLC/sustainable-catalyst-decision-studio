"""Stage source-linked scientific readiness in existing governed Decision Rooms.

Machine checks are not human review, scientific approval or legal eligibility.
"""
import hashlib,json,os,re
import httpx
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import Response
from pydantic import BaseModel,ConfigDict,Field
from .services import decision_service as svc
from .decision_rooms import RoomSnapshotCreateRequest
router=APIRouter(tags=['scientific-evidence-readiness'])
class ScientificReadinessRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 workspaceProjectId:str=Field(min_length=1,max_length=160)
 figureArtifactId:str=Field(pattern=r'^artifact:sha256:[a-f0-9]{64}$')

def readiness_from_figure(figure,workspace_project_id,core_project_id,artifact_id):
 try:
  spec=figure['spec']
  if spec['project_id']!=workspace_project_id or spec['family']!='evidence-gates':raise ValueError()
  gates=[{'id':n['id'],'label':n['label'],'source_refs':n['source_ids'],'blockers':n['blockers'],
          'source_declared_disposition':n['disposition'],'independent_review_status':'UNREVIEWED'} for n in spec['nodes']]
  if not gates:raise ValueError()
  return {'schema':'scds-scientific-evidence-readiness/1.0','workspaceProjectId':workspace_project_id,'coreProjectId':core_project_id,
   'figureArtifactId':artifact_id,'spec_sha256':figure['spec_sha256'],'gates':gates,'source_refs':spec['sources'],
   'review_disposition':'UNREVIEWED','net_removal_status':'NOT_QUANTIFIED','certification_eligibility':'NOT_ASSESSED',
   'automatic_scientific_approval':False,'human_decision_recorded':False,'limitations':spec['limitations']}
 except (ValueError,KeyError,TypeError) as exc:raise HTTPException(422,'A project-bound native evidence-gate figure is required.') from exc

def fetch_json(url,headers,limit=1_500_000):
 try:
  with httpx.Client(timeout=20,follow_redirects=False,trust_env=False) as client:
   with client.stream('GET',url,headers=headers) as response:
    if response.status_code!=200:raise HTTPException(502,'Scientific authority retrieval failed.')
    chunks=[];size=0
    for chunk in response.iter_bytes():
     size+=len(chunk)
     if size>limit:raise HTTPException(413,'Scientific source exceeds the limit.')
     chunks.append(chunk)
    raw=b''.join(chunks)
    return raw,json.loads(raw)
 except httpx.HTTPError as exc:raise HTTPException(502,'Scientific authority is unavailable.') from exc
 except ValueError as exc:raise HTTPException(422,'Invalid scientific authority response.') from exc

@router.post('/decision-rooms/{room_id}/scientific-readiness')
def stage_scientific_readiness(room_id:str,body:ScientificReadinessRequest,request:Request):
 denied=svc._decision_room_scope_error(request,'rooms:write')
 if denied:return denied
 owned=svc.decision_rooms_get_endpoint(room_id,request)
 if isinstance(owned,Response):return owned
 try:bindings=json.loads(os.getenv('SCDS_SCIENTIFIC_PROJECT_BINDINGS','{}'))
 except ValueError:raise HTTPException(503,'Scientific project bindings are not configured.')
 core_project=bindings.get(body.workspaceProjectId)
 room=owned['decision_room']
 if not core_project or room.get('metadata',{}).get('workspaceProjectId')!=body.workspaceProjectId:
  raise HTTPException(403,'Decision Room is not authorized for this scientific project.')
 core=os.getenv('SCDS_SCIENTIFIC_CORE_URL','').rstrip('/');ck=os.getenv('SCDS_SCIENTIFIC_CORE_KEY','')
 library=os.getenv('SCDS_SCIENTIFIC_LIBRARY_URL','').rstrip('/');lk=os.getenv('SCDS_SCIENTIFIC_LIBRARY_KEY','')
 if not all((core,ck,library,lk)):raise HTTPException(503,'Scientific authorities are not configured.')
 from urllib.parse import quote
 _,bundle=fetch_json(core+'/v1/research/projects/'+quote(core_project,safe='')+'/bundle',{'X-SC-API-Key':ck},2_000_000)
 if not any(c.get('canonical_ref')==body.figureArtifactId and c.get('component_kind')=='visualization' for c in bundle.get('components',[])):
  raise HTTPException(404,'Figure is not registered to this research project.')
 raw,figure=fetch_json(library+'/v1/admin/artifacts/'+quote(body.figureArtifactId,safe='')+'/content',{'Authorization':'Bearer '+lk})
 if hashlib.sha256(raw).hexdigest()!=body.figureArtifactId.rsplit(':',1)[1]:raise HTTPException(409,'Scientific artifact SHA256 mismatch.')
 payload=readiness_from_figure(figure,body.workspaceProjectId,core_project,body.figureArtifactId)
 principal=svc._request_principal(request)
 return svc.decision_rooms_create_snapshot_endpoint(room_id,RoomSnapshotCreateRequest(payload=payload,
  provenance_ref=body.figureArtifactId,label='Scientific evidence readiness — independent review pending',actor_ref=principal.principal_id,actor_role='editor'),request)
