from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class IncidentCreate(BaseModel):
    title: str = Field(min_length=4, max_length=200)
    description: str = Field(min_length=8, max_length=8000)
    affected_users: int = Field(default=1, ge=1, le=100000)
    service: str | None = Field(default=None, max_length=100)
    business_criticality: int = Field(default=2, ge=1, le=3)


class AnalyzeRequest(BaseModel):
    title: str = Field(min_length=4, max_length=200)
    description: str = Field(min_length=8, max_length=8000)
    affected_users: int = Field(default=1, ge=1, le=100000)
    service: str | None = Field(default=None, max_length=100)
    business_criticality: int = Field(default=2, ge=1, le=3)


class EscalateRequest(BaseModel):
    reason: str = Field(min_length=4, max_length=1000)
    assignment_group: str | None = Field(default=None, max_length=100)


class ApproveActionRequest(BaseModel):
    approved_by: str = Field(min_length=2, max_length=100)

class RequestAction(BaseModel):
    action: str = Field(min_length=3, max_length=60)
    requested_by: str = Field(min_length=2, max_length=100)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    number: str
    servicenow_sys_id: str
    servicenow_sync_status: str
    title: str
    description: str
    category: str
    subcategory: str
    impact: int
    urgency: int
    priority: str
    confidence: float
    status: str
    assigned_group: str
    assigned_to: str
    decision: dict
    knowledge: list
    actions: list
    timeline: list
    work_notes: str
    created_at: datetime
    updated_at: datetime
