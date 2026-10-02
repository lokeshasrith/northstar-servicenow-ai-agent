from app.ai.provider import MockLLMProvider
from app.policies.decision import decide, assess_priority
from app.actions.registry import execute
from app.knowledge.service import kb
from app.agents.orchestrator import verify_simulated_recovery

def test_unknown_incident_escalates():
    result=MockLLMProvider().analyze("Unknown error","Not enough information to identify the issue")
    policy=decide(result,"Unknown error","Not enough information",1,1,.85,.60,[])
    assert policy["mode"]=="escalate"
    assert policy["escalation_required"]

def test_ambiguous_incident_never_autoresolves():
    result=MockLLMProvider().analyze("VPN issue","VPN authentication failed; multiple possible causes exist")
    policy=decide(result,"VPN issue","VPN authentication failed; multiple possible causes exist",1,2,.85,.60,[])
    assert policy["mode"]=="escalate"

def test_priority_is_deterministic_and_critical_security_is_p1():
    assert assess_priority("possible malware compromise",1,1)[2]=="P1"
    assert assess_priority("cannot connect to service",1,2)==assess_priority("cannot connect to service",1,2)

def test_knowledge_returns_real_source_ids():
    results=kb.search("VPN authentication password MFA",3)
    assert results and results[0]["id"]=="KB-VPN-001"
    assert results[0]["source"].startswith("IT Runbook")

def test_allowlisted_actions_require_approval_for_risky_change():
    held=execute("restart_service","Network")
    assert held["status"]=="approval_required"
    done=execute("restart_service","Network","authorized.operator")
    assert done["status"]=="simulated_success"

def test_unknown_actions_and_category_mismatch_fail_closed():
    try: execute("run_shell_command","Network")
    except ValueError: pass
    else: raise AssertionError("Unknown action was accepted")
    try: execute("check_dns","Hardware")
    except ValueError: pass
    else: raise AssertionError("Action category mismatch was accepted")

def test_verifier_requires_positive_recovery_evidence():
    result={"status":"simulated_success"}
    assert verify_simulated_recovery("VPN is working again",result)["verified"]
    assert not verify_simulated_recovery("VPN is not recovered",result)["verified"]
    assert not verify_simulated_recovery("VPN still fails",result)["verified"]
