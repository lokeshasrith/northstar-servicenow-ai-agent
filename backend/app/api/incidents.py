import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.actions.registry import execute, REGISTRY
from app.agents.orchestrator import process_incident, _escalate, log_event
from app.database.session import SessionLocal
from app.knowledge.service import kb
from app.models.records import IncidentRecord, AuditRecord
from app.models.schemas import IncidentCreate, AnalyzeRequest, IncidentOut, EscalateRequest, ApproveActionRequest, RequestAction
from app.agents.orchestrator import provider
from app.policies.decision import decide
from app.core.config import get_settings
from app.integrations.servicenow.service import get_adapter

router=APIRouter(prefix="/incidents",tags=["incidents"])

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def get_incident(db, incident_id):
    row=db.get(IncidentRecord,incident_id)
    if not row: raise HTTPException(404,"Incident not found")
    return row

def payload(incident):
    return IncidentOut.model_validate(incident)

@router.get("",response_model=list[IncidentOut])
def list_incidents(status: str|None=None, priority: str|None=None, db:Session=Depends(get_db)):
    query=select(IncidentRecord).order_by(IncidentRecord.created_at.desc())
    if status: query=query.where(IncidentRecord.status==status)
    if priority: query=query.where(IncidentRecord.priority==priority)
    return [payload(x) for x in db.scalars(query.limit(200)).all()]

@router.post("",response_model=IncidentOut,status_code=201)
def create_incident(data:IncidentCreate,db:Session=Depends(get_db)):
    row=IncidentRecord(id=str(uuid.uuid4()),number=f"INC{uuid.uuid4().hex[:7].upper()}",title=data.title.strip(),description=data.description.strip(),decision={"affected_users":data.affected_users,"business_criticality":data.business_criticality,"service":data.service},timeline=[])
    db.add(row); db.commit(); db.refresh(row)
    try:
        impact=str(4-data.business_criticality)
        remote=get_adapter().create_incident({"short_description":row.title,"description":row.description,"correlation_id":row.number,"impact":impact,"urgency":"2"})
        row.servicenow_sys_id=str(remote.get("sys_id","")); row.servicenow_sync_status="synced"
    except Exception:
        row.servicenow_sync_status="pending_retry"
    db.commit();db.refresh(row);return payload(row)

@router.post("/analyze")
def analyze(data:AnalyzeRequest):
    settings=get_settings()
    try: understanding=provider().analyze(data.title,data.description); failed=False
    except Exception:
        from app.ai.provider import Understanding
        understanding=Understanding("Other","Unknown","Analysis unavailable; human review required.",0,"Manual review",[],True); failed=True
    try: knowledge=kb.search(f"{data.title} {data.description} {understanding.category}",3)
    except Exception:
        knowledge=[]; failed=True
    decision=decide(understanding,data.title,data.description,data.affected_users,data.business_criticality,settings.confidence_auto_threshold,settings.confidence_investigate_threshold,knowledge,failed)
    return decision

@router.get("/{incident_id}",response_model=IncidentOut)
def get_one(incident_id:str,db:Session=Depends(get_db)): return payload(get_incident(db,incident_id))

@router.post("/{incident_id}/process",response_model=IncidentOut)
def process(incident_id:str,db:Session=Depends(get_db)):
    row=process_incident(db,get_incident(db,incident_id))
    if row.servicenow_sys_id:
        try:
            state="6" if row.status=="Resolved" else "2"
            get_adapter().update_incident(row.servicenow_sys_id,{"assignment_group":row.assigned_group,"priority":row.priority[-1],"impact":str(row.impact),"urgency":str(row.urgency),"state":state,"work_notes":row.work_notes or row.decision.get("decision_explanation","")})
            row.servicenow_sync_status="synced"
        except Exception:
            row.servicenow_sync_status="pending_retry"
        db.commit();db.refresh(row)
    return payload(row)

@router.post("/{incident_id}/escalate",response_model=IncidentOut)
def escalate(incident_id:str,data:EscalateRequest,db:Session=Depends(get_db)):
    row=get_incident(db,incident_id); _escalate(db,row,data.reason,data.assignment_group); db.commit(); db.refresh(row); return payload(row)

@router.post("/{incident_id}/approve-action",response_model=IncidentOut)
def approve(incident_id:str,data:ApproveActionRequest,db:Session=Depends(get_db)):
    row=get_incident(db,incident_id)
    pending=next((a for a in row.actions if a.get("status")=="approval_required"),None)
    if not pending: raise HTTPException(409,"No action is awaiting approval")
    if pending.get("requested_by","").casefold()==data.approved_by.strip().casefold(): raise HTTPException(403,"Approval must come from a different operator than the requester")
    action=execute(pending["name"],row.category,data.approved_by.strip())
    row.actions=[action if a is pending else a for a in row.actions]
    log_event(db,row,"action_approved_and_executed",action); row.status="Human review"
    row.decision={**row.decision,"verification":{"verified":False,"message":"Approval is recorded. A human must verify the incident before closure."}}
    db.commit(); db.refresh(row); return payload(row)

@router.post("/{incident_id}/actions",response_model=IncidentOut)
def request_action(incident_id:str,data:RequestAction,db:Session=Depends(get_db)):
    row=get_incident(db,incident_id)
    if data.action not in REGISTRY: raise HTTPException(422,"Action is not in the allowlist")
    if row.status=="Resolved" or row.category=="Security": raise HTTPException(403,"Policy does not permit actions for this incident")
    spec=REGISTRY[data.action]
    if not spec["approval"] and (row.decision.get("mode")!="resolve" or row.confidence<get_settings().confidence_auto_threshold or row.status=="Escalated"):
        raise HTTPException(403,"Policy does not permit autonomous actions for this incident")
    try: result=execute(data.action,row.category)
    except ValueError as exc: raise HTTPException(403,str(exc)) from exc
    if result["status"]=="approval_required": result["requested_by"]=data.requested_by.strip()
    row.actions=(row.actions or [])+[result]
    log_event(db,row,"action_requested",result)
    db.commit();db.refresh(row);return payload(row)

@router.get("/{incident_id}/timeline")
def timeline(incident_id:str,db:Session=Depends(get_db)): return get_incident(db,incident_id).timeline

@router.get("/{incident_id}/audit")
def audit(incident_id:str,db:Session=Depends(get_db)):
    get_incident(db,incident_id)
    rows=db.scalars(select(AuditRecord).where(AuditRecord.incident_id==incident_id).order_by(AuditRecord.timestamp)).all()
    return [{"id":x.id,"incident_id":x.incident_id,"timestamp":x.timestamp,"agent_version":x.agent_version,"model":x.model,"event":x.event,"payload":x.payload} for x in rows]

@router.patch("/{incident_id}",response_model=IncidentOut)
def update(incident_id:str,fields:dict,db:Session=Depends(get_db)):
    allowed={"status","assigned_group","assigned_to","work_notes","title","description"}
    if set(fields)-allowed: raise HTTPException(422,"Unsupported incident fields")
    row=get_incident(db,incident_id)
    for key,value in fields.items(): setattr(row,key,str(value)[:8000])
    log_event(db,row,"incident_updated",{"fields":list(fields)})
    db.commit();db.refresh(row);return payload(row)
