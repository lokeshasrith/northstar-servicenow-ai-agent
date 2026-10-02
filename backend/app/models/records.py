from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IncidentRecord(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    number: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    servicenow_sys_id: Mapped[str] = mapped_column(String(64), default="")
    servicenow_sync_status: Mapped[str] = mapped_column(String(32), default="local")
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), default="Other")
    subcategory: Mapped[str] = mapped_column(String(60), default="General")
    impact: Mapped[int] = mapped_column(Integer, default=3)
    urgency: Mapped[int] = mapped_column(Integer, default=3)
    priority: Mapped[str] = mapped_column(String(4), default="P4")
    confidence: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="New")
    assigned_group: Mapped[str] = mapped_column(String(100), default="Service Desk")
    assigned_to: Mapped[str] = mapped_column(String(100), default="Unassigned")
    decision: Mapped[dict] = mapped_column(JSON, default=dict)
    knowledge: Mapped[list] = mapped_column(JSON, default=list)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    work_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditRecord(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(40), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    agent_version: Mapped[str] = mapped_column(String(24), default="0.2.0")
    model: Mapped[str] = mapped_column(String(80), default="mock-rules-v1")
    event: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
