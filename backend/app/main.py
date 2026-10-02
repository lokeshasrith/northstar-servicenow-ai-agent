import asyncio
import hmac
import time
from pathlib import Path
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api.health import router as health_router
from app.api.incidents import router as incident_router
from app.api.misc import router as misc_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import Base, SessionLocal, engine
from app.models.records import IncidentRecord
from app.agents.orchestrator import process_incident
import uuid

settings=get_settings(); configure_logging()
SAMPLES=[
 ("VPN authentication failing after password reset","User reported a VPN failure after a password change but confirms the VPN now connects again; verify current connectivity.",1,2),
 ("Unable to access shared finance drive","Finance team reports access denied on the Q drive. Two users are affected and access worked yesterday.",2,2),
 ("Outlook desktop app crashes on launch","Outlook closes immediately after its splash screen appears on Windows 11. Restart did not help.",1,2),
 ("Intermittent latency on customer portal","Customer portal response times exceed 15 seconds across several regions. Customer-facing production service is degraded.",250,3),
 ("Unknown error message","User says multiple possible causes exist and there is not enough information to identify what failed.",1,1),
 ("Laptop overheating during video calls","Device temperature spikes during video conferences and the fan runs continuously.",1,1),
 ("DNS resolution failure","Internal app hostname fails DNS lookup for several users in one office.",8,2),
 ("Account locked after repeated sign-in attempts","Employee is unable to sign in; account appears locked after repeated login failures.",1,2),
]

def initialize():
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try:
        if db.query(IncidentRecord).count()==0:
            for title,description,users,criticality in SAMPLES:
                row=IncidentRecord(id=str(uuid.uuid4()),number=f"INC{uuid.uuid4().hex[:7].upper()}",title=title,description=description,decision={"affected_users":users,"business_criticality":criticality},timeline=[])
                db.add(row); db.commit(); db.refresh(row)
                # Never trigger paid/provider calls during app startup. Live-provider
                # deployments start samples in New state and require explicit processing.
                if settings.llm_provider.lower()=="mock":
                    process_incident(db,row)
    finally: db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield

app=FastAPI(title=settings.app_name,version="0.2.0",description="Human-supervised IT incident triage and simulation.",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.allowed_origins,allow_credentials=True,allow_methods=["GET","POST","PUT","PATCH","DELETE"],allow_headers=["Authorization","Content-Type","X-API-Key"])
app.include_router(health_router,prefix=settings.api_prefix)
app.include_router(incident_router,prefix=settings.api_prefix)
app.include_router(misc_router,prefix=settings.api_prefix)
requests=defaultdict(deque); lock=asyncio.Lock()

@app.middleware("http")
async def security_controls(request:Request,call_next):
    if request.url.path.startswith(settings.api_prefix) and request.url.path != f"{settings.api_prefix}/health":
        configured={"admin":settings.dashboard_admin_key or settings.dashboard_api_key,"viewer":settings.dashboard_viewer_key}
        configured={role:key for role,key in configured.items() if key}
        if configured:
            supplied=request.headers.get("x-api-key","")
            role=next((role for role,key in configured.items() if hmac.compare_digest(supplied,key)),None)
            if not role: return JSONResponse({"detail":"Valid X-API-Key required"},status_code=401)
            if request.method not in {"GET","HEAD","OPTIONS"} and role!="admin":
                return JSONResponse({"detail":"Administrator role required"},status_code=403)
        ip=request.client.host if request.client else "unknown"; now=time.monotonic()
        async with lock:
            q=requests[ip]
            while q and q[0] < now-60: q.popleft()
            if len(q)>=120: return JSONResponse({"detail":"Rate limit exceeded"},status_code=429)
            q.append(now)
    return await call_next(request)

@app.get("/")
def root(): return {"name":settings.app_name,"docs":"/docs","phase":"complete demo","mode":settings.llm_provider}

static_dir = Path(__file__).resolve().parents[2] / "static"
if static_dir.is_dir():
    app.router.routes.remove(next(route for route in app.router.routes if getattr(route, "path", None) == "/"))
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
