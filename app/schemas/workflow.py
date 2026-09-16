"""
Workflow schemas for application state transitions and auditing.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    application_type: str
    ulpin: str
    applicant_citizen_id: int
    target_citizen_id: Optional[int] = None
    status: str
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WorkflowTransitionRequest(BaseModel):
    next_stage: str
    comments: Optional[str] = None
