from datetime import datetime, timezone

REGISTRY = {
 "validate_connectivity":{"description":"Read-only reachability check","risk":"low","approval":False,"category":"Network"},
 "check_dns":{"description":"Read-only DNS lookup","risk":"low","approval":False,"category":"Network"},
 "check_account_status":{"description":"Read-only account state lookup","risk":"low","approval":False,"category":"Authentication"},
 "collect_logs":{"description":"Collect approved diagnostic metadata","risk":"low","approval":False,"category":"*"},
 "check_service_status":{"description":"Read-only service health check","risk":"low","approval":False,"category":"*"},
 "clear_cache":{"description":"Clear local application cache","risk":"medium","approval":True,"category":"Software"},
 "reset_session":{"description":"Reset the affected user session","risk":"medium","approval":True,"category":"Authentication"},
 "restart_service":{"description":"Restart a named service","risk":"high","approval":True,"category":"*"},
}
for action_name, spec in REGISTRY.items():
    spec.update({
        "name": action_name,
        "required_permissions": ["incident.read"] if spec["risk"] == "low" else ["incident.write", "human.approval"],
        "input_schema": {"type":"object","properties":{},"required":[],"additionalProperties":False},
        "output_schema": {"type":"object","required":["status","result"]},
        "validation": "Action name and category must match this registry; result is mock-only and audited.",
    })

def execute(action_name: str, category: str, approved_by: str | None = None) -> dict:
    spec = REGISTRY.get(action_name)
    if not spec:
        raise ValueError("Action is not registered")
    if spec["category"] not in ("*", category):
        raise ValueError("Action is not allowed for this incident category")
    if spec["approval"] and not approved_by:
        return {"name":action_name,"description":spec["description"],"risk":spec["risk"],"status":"approval_required","result":"Action held for human approval.","timestamp":datetime.now(timezone.utc).isoformat()}
    # Demo executor returns simulated results; production action connectors are intentionally not enabled.
    return {"name":action_name,"description":spec["description"],"risk":spec["risk"],"status":"simulated_success","result":"Mock check completed; no external system was modified.","approved_by":approved_by,"timestamp":datetime.now(timezone.utc).isoformat()}
