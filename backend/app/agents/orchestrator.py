import logging
import re
from datetime import datetime, timezone
from app.ai.provider import MockLLMProvider, OpenAIProvider
from app.actions.registry import execute
from app.core.config import get_settings
from app.knowledge.service import kb
from app.models.records import AuditRecord
from app.policies.decision import decide, GROUPS

logger = logging.getLogger("incident_agent")

def log_event(db, incident, event: str, payload: dict):
    settings=get_settings()
    model=settings.openai_model if settings.llm_provider=="openai" else "mock-rules-v1"
    db.add(AuditRecord(incident_id=incident.id, model=model, event=event, payload=payload))
    incident.timeline = (incident.timeline or []) + [{"timestamp":datetime.now(timezone.utc).isoformat(),"event":event,"details":payload}]
    logger.info("incident_event", extra={"incident_id":incident.number,"event":event,"details":payload})

def provider():
    settings=get_settings()
    if settings.llm_provider == "openai":
        if not settings.openai_api_key: raise RuntimeError("LLM provider is unavailable: API key is not configured")
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    return MockLLMProvider()

def process_incident(db, incident):
    settings=get_settings()
    log_event(db,incident,"incident_received",{"number":incident.number})
    try:
        understanding=provider().analyze(incident.title,incident.description)
        provider_error=False
    except Exception as exc:
        from app.ai.provider import Understanding
        understanding=Understanding("Other","Unknown","AI analysis unavailable; human assessment is required.",0.0,"Review the incident manually.",[],True)
        provider_error=True
        logger.warning("provider_unavailable",extra={"incident_id":incident.number,"error_type":type(exc).__name__})
    try:
        knowledge=kb.search(f"{incident.title} {incident.description} {understanding.category}",limit=3)
    except Exception as exc:
        knowledge=[]; provider_error=True
        logger.warning("knowledge_unavailable",extra={"incident_id":incident.number,"error_type":type(exc).__name__})
    users=int(incident.decision.get("affected_users",1))
    criticality=int(incident.decision.get("business_criticality",2))
    result=decide(understanding,incident.title,incident.description,users,criticality,settings.confidence_auto_threshold,settings.confidence_investigate_threshold,knowledge,provider_error)
    incident.category=understanding.category; incident.subcategory=understanding.subcategory
    incident.assigned_group=GROUPS.get(incident.category,"Service Desk")
    incident.confidence=result["confidence"]; incident.impact=result["priority"]["impact"]; incident.urgency=result["priority"]["urgency"]; incident.priority=result["priority"]["priority"]
    incident.decision={**result,"affected_users":users,"business_criticality":criticality}
    incident.knowledge=knowledge
    log_event(db,incident,"analysis_complete",{"category":incident.category,"confidence":incident.confidence,"priority":incident.priority,"mode":result["mode"],"sources":[x["id"] for x in knowledge]})
    if result["mode"] == "escalate":
        _escalate(db,incident,result["escalation_reason"])
    elif result["mode"] == "investigate":
        incident.status="Human review"; incident.assigned_group=GROUPS.get(incident.category,"Service Desk")
        log_event(db,incident,"human_review_required",{"reason":result["escalation_reason"],"assignment_group":incident.assigned_group})
    else:
        action_name="check_dns" if incident.category=="Network" and incident.subcategory=="DNS" else "validate_connectivity" if incident.category=="Network" else "check_account_status" if incident.category=="Authentication" else "check_service_status"
        action=execute(action_name,incident.category)
        incident.actions=(incident.actions or [])+[action]
        log_event(db,incident,"action_executed",action)
        verification=verify_simulated_recovery(incident.description,action)
        if settings.servicenow_mode.lower()=="real":
            verification={"verified":False,"mode":"unavailable","message":"Production action and verification connectors are not configured. The agent will not close a real ServiceNow incident."}
        incident.decision={**incident.decision,"verification":verification}
        if verification["verified"]:
            incident.status="Resolved"
            log_event(db,incident,"resolution_verified",verification)
        else:
            log_event(db,incident,"resolution_not_verified",verification)
            _escalate(db,incident,"The issue could not be independently verified as resolved.")
    db.commit(); db.refresh(incident)
    return incident

def verify_simulated_recovery(description: str, action: dict) -> dict:
    text=description.lower()
    recovery_evidence=any(term in text for term in ("now connects","working again","now working","recovered","restored","service is healthy","confirmed resolved"))
    negated=bool(re.search(r"\b(?:not|never|isn.t|has not|hasn.t|no longer)\b.{0,40}\b(?:connects|working|recovered|restored|healthy|resolved)\b",text))
    recovery_evidence=recovery_evidence and not negated
    verified=action.get("status")=="simulated_success" and recovery_evidence
    return {"verified":verified,"mode":"simulation","message":"Mock verification found explicit recovery evidence in the incident report; no production system was changed." if verified else "The read-only mock check did not prove that the reported issue is resolved. Ticket remains escalated for human verification."}

def _escalate(db,incident,reason,assignment_group=None):
    group=assignment_group or GROUPS.get(incident.category,"Service Desk")
    incident.status="Escalated"; incident.assigned_group=group
    note=(f"AI Escalation Summary\nIssue: {incident.title}\nCategory: {incident.category} / {incident.subcategory}\nConfidence: {incident.confidence:.0%}\nReason: {reason}\nActions attempted: {', '.join(a['name'] for a in incident.actions) or 'None'}\nKnowledge sources: {', '.join(x['id'] for x in incident.knowledge) or 'None'}\nRecommended next step: {incident.decision.get('recommended_action', 'Human assessment required')}\nAI made no production changes.")
    incident.work_notes=(incident.work_notes+"\n\n"+note).strip()
    incident.decision={**incident.decision,"escalation_reason":reason}
    log_event(db,incident,"escalated",{"assignment_group":group,"reason":reason,"confidence":incident.confidence,"notes":note})
    if incident.servicenow_sys_id:
        try:
            from app.integrations.servicenow.service import get_adapter
            get_adapter().update_incident(incident.servicenow_sys_id,{"assignment_group":group,"work_notes":note,"state":"2"})
            incident.servicenow_sync_status="synced"
        except Exception as exc:
            incident.servicenow_sync_status="pending_retry"
            logger.warning("servicenow_sync_failed",extra={"incident_id":incident.number,"error_type":type(exc).__name__})
