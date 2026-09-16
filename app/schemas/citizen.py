"""
Pydantic schemas for the Citizen Portal.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MyLandItem(BaseModel):
    ulpin: str
    survey_number: str
    state: str
    district: str
    taluk: str
    village: str
    area: float
    area_unit: str
    land_type: str
    share_percentage: float
    acquisition_mode: str
    status: str


class CitizenRoRResponse(BaseModel):
    ulpin: str
    ror_number: str
    status: str
    owners: List[Dict[str, Any]]
    rights: List[str]
    tenure: str
    restrictions: str
    last_updated: datetime


class ApplicationCreateRequest(BaseModel):
    ulpin: str
    application_type: str = "OWNERSHIP_TRANSFER"
    target_citizen_email: str
    remarks: Optional[str] = None
    document_ids: List[str] = []


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


class CitizenActionRequest(BaseModel):
    remarks: Optional[str] = None


class CitizenInformationRequest(BaseModel):
    ulpin: str
    request_type: str = "RECORD_EXTRACT"
    message: str
