from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from app.knowledge.service import kb
from app.actions.registry import REGISTRY
from app.integrations.servicenow.service import get_adapter
from app.evaluation import evaluate as run_evaluation
from app.models.records import IncidentRecord
from app.database.session import SessionLocal
from app.agents.orchestrator import process_incident
import uuid
from app.core.config import get_settings

router=APIRouter(tags=["knowledge","evaluation","actions"])

@router.get("/config")
def public_config():
    settings=get_settings()
    return {"confidence_auto_threshold":settings.confidence_auto_threshold,"confidence_investigate_threshold":settings.confidence_investigate_threshold,"llm_provider":settings.llm_provider,"servicenow_mode":settings.servicenow_mode,"authentication_enabled":bool(settings.dashboard_admin_key or settings.dashboard_viewer_key or settings.dashboard_api_key),"knowledge_sources":len(kb.documents)}

class ServiceNowUpdate(BaseModel):
    fields: dict
class Assignment(BaseModel):
    group: str|None=None
    assignee: str|None=None
class Note(BaseModel):
    text: str=Field(min_length=1,max_length=8000)

def sn_call(fn,*args,**kwargs):
    try: return fn(*args,**kwargs)
    except Exception as exc: raise HTTPException(502,"ServiceNow is unavailable or rejected the request") from exc

@router.get("/servicenow/incidents")
def servicenow_incidents(): return sn_call(get_adapter().list_incidents)

@router.post("/servicenow/sync")
def servicenow_sync():
    adapter=get_adapter(); remote_rows=sn_call(adapter.list_incidents); db=SessionLocal(); imported=updated=failed=0
    try:
        for remote in remote_rows:
            sys_id=str(remote.get("sys_id", ""))
            number=str(remote.get("number", ""))[:24]
            if not number: continue
            row=db.query(IncidentRecord).filter((IncidentRecord.servicenow_sys_id==sys_id)|(IncidentRecord.number==number)).first()
            title=str(remote.get("short_description") or "ServiceNow incident")[:200]
            description=str(remote.get("description") or title)[:8000]
            sn_state=str(remote.get("state", "1"))
            local_status="Resolved" if sn_state=="6" else "Closed" if sn_state=="7" else "New"
            if row:
                row.title=title;row.description=description;row.servicenow_sys_id=sys_id or row.servicenow_sys_id
                updated+=1
            else:
                row=IncidentRecord(id=str(uuid.uuid4()),number=number,servicenow_sys_id=sys_id,servicenow_sync_status="synced",title=title,description=description,status=local_status,timeline=[],decision={"affected_users":1,"business_criticality":2})
                db.add(row);db.commit();db.refresh(row)
                try:
                    if local_status=="New": process_incident(db,row)
                    state="6" if row.status=="Resolved" else "2"
                    adapter.update_incident(row.servicenow_sys_id,{"assignment_group":row.assigned_group,"priority":row.priority[-1],"impact":str(row.impact),"urgency":str(row.urgency),"state":state,"work_notes":row.work_notes or row.decision.get("decision_explanation","")})
                except Exception:
                    row.servicenow_sync_status="pending_retry";db.commit();failed+=1;continue
                imported+=1
        db.commit()
        return {"fetched":len(remote_rows),"imported":imported,"updated":updated,"failed":failed}
    finally: db.close()

@router.patch("/servicenow/incidents/{sys_id}")
def servicenow_update(sys_id:str,data:ServiceNowUpdate):
    allowed={"short_description","description","category","subcategory","priority","impact","urgency","state","assignment_group","assigned_to","work_notes","comments","correlation_id"}
    if not data.fields or set(data.fields)-allowed: raise HTTPException(422,"Unsupported or empty ServiceNow field update")
    for field in ("priority","impact","urgency","state"):
        if field in data.fields and str(data.fields[field]) not in {"1","2","3","4","5","6","7","8"}:
            raise HTTPException(422,f"Invalid ServiceNow {field} value")
    return sn_call(get_adapter().update_incident,sys_id,data.fields)

@router.post("/servicenow/incidents/{sys_id}/assign")
def servicenow_assign(sys_id:str,data:Assignment):
    return sn_call(get_adapter().assign_incident,sys_id,data.group,data.assignee) if hasattr(get_adapter(),"assign_incident") else sn_call(get_adapter().update_incident,sys_id,{"assignment_group":data.group,"assigned_to":data.assignee})

@router.post("/servicenow/incidents/{sys_id}/work-notes")
def servicenow_work_notes(sys_id:str,data:Note): return sn_call(get_adapter().add_work_notes,sys_id,data.text) if hasattr(get_adapter(),"add_work_notes") else sn_call(get_adapter().update_incident,sys_id,{"work_notes":data.text})

@router.post("/servicenow/incidents/{sys_id}/comments")
def servicenow_comments(sys_id:str,data:Note): return sn_call(get_adapter().add_comment,sys_id,data.text) if hasattr(get_adapter(),"add_comment") else sn_call(get_adapter().update_incident,sys_id,{"comments":data.text})

@router.get("/servicenow/knowledge")
def servicenow_knowledge(q:str=Query(min_length=2,max_length=200)):
    adapter=get_adapter()
    if not hasattr(adapter,"get_knowledge"): return {"result":[]}
    return sn_call(adapter.get_knowledge,q)

@router.post("/servicenow/retry-pending")
def servicenow_retry_pending():
    db=SessionLocal(); adapter=get_adapter(); succeeded=failed=0
    try:
        rows=db.query(IncidentRecord).filter(IncidentRecord.servicenow_sync_status=="pending_retry").limit(100).all()
        for row in rows:
            try:
                if row.servicenow_sys_id:
                    adapter.update_incident(row.servicenow_sys_id,{"assignment_group":row.assigned_group,"work_notes":row.work_notes,"correlation_id":row.number})
                else:
                    existing=adapter.find_by_correlation_id(row.number) if hasattr(adapter,"find_by_correlation_id") else None
                    remote=existing or adapter.create_incident({"short_description":row.title,"description":row.description,"correlation_id":row.number})
                    row.servicenow_sys_id=str(remote.get("sys_id",""))
                row.servicenow_sync_status="synced";succeeded+=1
            except Exception: failed+=1
        db.commit();return {"retried":len(rows),"succeeded":succeeded,"failed":failed}
    finally: db.close()

@router.get("/knowledge/search")
def search_knowledge(q:str=Query(min_length=2,max_length=500),limit:int=Query(default=5,ge=1,le=20)):
    return {"query":q,"results":kb.search(q,limit)}

@router.get("/actions")
def list_actions(): return REGISTRY

@router.get("/evaluation")
def evaluation(): return run_evaluation()
