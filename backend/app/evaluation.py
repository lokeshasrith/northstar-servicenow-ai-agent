import json
from pathlib import Path
from app.ai.provider import MockLLMProvider
from app.knowledge.service import kb
from app.policies.decision import decide
from app.core.config import get_settings
from app.agents.orchestrator import verify_simulated_recovery

DATA=Path(__file__).resolve().parents[2]/"knowledge"/"sample_incidents"/"evaluation.json"

def evaluate():
    cases=json.loads(DATA.read_text(encoding="utf-8"));provider=MockLLMProvider();settings=get_settings()
    class_ok=priority_ok=escalation_ok=false_autonomous=resolved=0;confidence_brier=0.0;confidences=[];human_handled=0
    for case in cases:
        understanding=provider.analyze(case["title"],case["description"])
        knowledge=kb.search(f"{case['title']} {case['description']} {understanding.category}",3)
        prediction=decide(understanding,case["title"],case["description"],case.get("affected_users",1),case.get("business_criticality",2),settings.confidence_auto_threshold,settings.confidence_investigate_threshold,knowledge)
        c=understanding.category==case["expected_category"];p=prediction["priority"]["priority"]==case["expected_priority"]
        e=prediction["escalation_required"]==case.get("expected_escalation",False)
        class_ok+=int(c);priority_ok+=int(p);escalation_ok+=int(e)
        verification=verify_simulated_recovery(case["description"],{"status":"simulated_success"})
        verified_resolution=prediction["mode"]=="resolve" and verification["verified"]
        resolved+=int(verified_resolution)
        human_handled+=int(not verified_resolution)
        false_autonomous+=int(prediction["mode"]=="resolve" and (not c or case.get("expected_escalation",False)))
        confidence_brier+=(understanding.confidence-float(c))**2;confidences.append(understanding.confidence)
    n=len(cases)
    return {"sample_size":n,"classification_accuracy":round(class_ok/n,3),"priority_accuracy":round(priority_ok/n,3),"escalation_accuracy":round(escalation_ok/n,3),"confidence_brier_score":round(confidence_brier/n,3),"mean_confidence":round(sum(confidences)/n,3),"false_autonomous_resolutions":false_autonomous,"false_autonomous_resolution_rate":round(false_autonomous/n,3),"simulated_verified_resolutions":resolved,"human_escalation_or_review_rate":round(human_handled/n,3),"average_resolution_time_seconds":None,"notes":"Deterministic mock evaluation on the included labeled dataset. A mock resolution is counted only when the case contains explicit recovery evidence. It is not production incident recovery. Time-to-resolution requires measured timestamps."}
