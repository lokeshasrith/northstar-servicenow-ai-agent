from app.main import initialize
from app.database.session import SessionLocal
from app.models.records import IncidentRecord
from app.agents.orchestrator import process_incident
import uuid

CASES=[
 ("Case 1 · confident and safe","VPN connectivity verification","VPN connection was restored after a transient issue; user confirms it is working again and requests a connectivity verification.",1,2),
 ("Case 2 · understands but requests review","Cloud portal latency","Customer portal service is slow for several users.",8,2),
 ("Case 3 · does not understand","Unknown issue","Unknown error; no details available and user does not understand the issue.",1,1),
 ("Case 4 · insufficient evidence","VPN or identity issue","VPN authentication fails and multiple possible causes exist; not enough information.",1,2),
 ("Case 5 · critical incident","Customer portal outage","Production customer portal unavailable to all users in all regions.",500,3),
]

def main():
    initialize(); db=SessionLocal()
    try:
        for label,title,description,users,criticality in CASES:
            row=IncidentRecord(id=str(uuid.uuid4()),number=f"SIM{uuid.uuid4().hex[:7].upper()}",title=title,description=description,decision={"affected_users":users,"business_criticality":criticality},timeline=[])
            db.add(row);db.commit();db.refresh(row);process_incident(db,row)
            print(f"{label}: {row.status} · {row.category} · {row.priority} · confidence {row.confidence:.0%} · group {row.assigned_group}")
    finally: db.close()

if __name__=="__main__": main()
