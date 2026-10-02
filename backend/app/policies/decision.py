from dataclasses import asdict
from app.ai.provider import Understanding

CATEGORIES = {"Network", "Hardware", "Software", "Database", "Authentication", "Access Management", "Email", "Cloud", "Security", "Application", "Other"}
GROUPS = {"Security":"Security Operations", "Network":"Network Support", "Hardware":"Endpoint Support", "Software":"Application Support", "Database":"Database Operations", "Authentication":"Identity Support", "Access Management":"Identity Support", "Email":"Messaging Support", "Cloud":"Platform SRE", "Application":"Application Support", "Other":"Service Desk"}
PRIORITY_MATRIX = {(1,1):"P1",(1,2):"P1",(1,3):"P2",(2,1):"P1",(2,2):"P2",(2,3):"P3",(3,1):"P2",(3,2):"P3",(3,3):"P4"}
SECURITY_TERMS = ("phishing", "malware", "breach", "compromised", "ransomware", "exfiltration")

def assess_priority(text: str, users: int, business_criticality: int) -> tuple[int, int, str, str]:
    t = text.lower()
    if any(word in t for word in SECURITY_TERMS):
        impact, urgency = 1, 1
        reason = "Security-sensitive language requires immediate high-priority human response."
    else:
        impact = 1 if users >= 100 or business_criticality == 3 else (2 if users >= 5 or business_criticality == 2 else 3)
        urgency = 1 if any(w in t for w in ("outage", "unavailable", "all users", "production down", "critical")) else (2 if any(w in t for w in ("cannot", "unable", "blocked", "timeout", "not working")) else 3)
        reason = f"Deterministic matrix used {users} affected user(s), business criticality {business_criticality}, and urgency signals from the description."
    return impact, urgency, PRIORITY_MATRIX[(impact, urgency)], reason

def decide(understanding: Understanding, title: str, description: str, users: int, criticality: int, auto_threshold: float, investigate_threshold: float, knowledge: list[dict], provider_error: bool = False) -> dict:
    impact, urgency, priority, priority_reason = assess_priority(f"{title} {description}", users, criticality)
    confidence = understanding.confidence
    escalate = provider_error or confidence < investigate_threshold or understanding.ambiguous or understanding.category not in CATEGORIES or understanding.category == "Security" or priority == "P1"
    if escalate:
        mode = "escalate"
        reason = "Provider unavailable." if provider_error else ("Security-sensitive or critical incident requires human handling." if understanding.category == "Security" or priority == "P1" else "Insufficient confidence or conflicting signals; safe escalation required.")
    elif confidence < auto_threshold:
        mode, reason = "investigate", "Confidence is below the autonomous-action threshold; gather evidence only."
    else:
        mode, reason = "resolve", "Confidence meets the configured threshold; only validated, allowlisted low-risk actions may run."
    return {"understanding":asdict(understanding),"priority":{"impact":impact,"urgency":urgency,"priority":priority,"reason":priority_reason},"confidence":confidence,"can_resolve":mode=="resolve","mode":mode,"recommended_action":understanding.recommended_action,"escalation_required":mode=="escalate","escalation_reason":reason,"decision_explanation":f"{understanding.category}/{understanding.subcategory} inferred from: {', '.join(understanding.signals) or 'no reliable signals'}. {priority_reason} Retrieved {len(knowledge)} source(s).","knowledge_sources":[x["id"] for x in knowledge]}
