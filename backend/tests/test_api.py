from fastapi.testclient import TestClient
from app.main import app

def test_create_process_unknown_and_read_audit():
    with TestClient(app) as client:
        created=client.post("/api/incidents",json={"title":"Unknown device fault","description":"Unknown error and not enough information to identify the failed device."})
        assert created.status_code==201
        row=created.json()
        assert row["servicenow_sync_status"]=="synced"
        processed=client.post(f"/api/incidents/{row['id']}/process")
        assert processed.status_code==200
        assert processed.json()["status"]=="Escalated"
        events=client.get(f"/api/incidents/{row['id']}/audit").json()
        assert any(event["event"]=="escalated" for event in events)

def test_evaluation_endpoint_reports_measured_fields():
    with TestClient(app) as client:
        report=client.get("/api/evaluation").json()
        assert report["sample_size"]==11
        assert report["false_autonomous_resolutions"]==0
        assert report["average_resolution_time_seconds"] is None

def test_medium_risk_action_waits_for_human_approval():
    with TestClient(app) as client:
        row=client.post("/api/incidents",json={"title":"Outlook application startup crash","description":"Outlook crashes immediately on launch. User needs access to email."}).json()
        assert client.post(f"/api/incidents/{row['id']}/process").status_code==200
        held=client.post(f"/api/incidents/{row['id']}/actions",json={"action":"clear_cache","requested_by":"request.operator"})
        assert held.status_code==200
        assert held.json()["actions"][-1]["status"]=="approval_required"
        same_operator=client.post(f"/api/incidents/{row['id']}/approve-action",json={"approved_by":"request.operator"})
        assert same_operator.status_code==403
        approved=client.post(f"/api/incidents/{row['id']}/approve-action",json={"approved_by":"different.operator"})
        assert approved.status_code==200
        assert approved.json()["actions"][-1]["status"]=="simulated_success"
