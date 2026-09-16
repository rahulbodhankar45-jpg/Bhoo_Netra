"""
Pydantic schemas for the Government Portal & RBAC Officer operations.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ULPINVerificationResponse(BaseModel):
    ulpin: str
    is_valid: bool
    exists: bool
    parcel: Optional[Dict[str, Any]] = None
    ror: Optional[Dict[str, Any]] = None
    sro_status: Optional[str] = None
    encumbrances_count: int = 0
    disputes_count: int = 0
    police_status: Optional[str] = None
    risk_level: str = "LOW"


class DocumentVerificationRequest(BaseModel):
    decision: str  # "VERIFIED" | "REJECTED"
    remarks: Optional[str] = None


class SROStatusResponse(BaseModel):
    ulpin: str
    registration_records: List[Dict[str, Any]]
    deeds: List[Dict[str, Any]]
    encumbrances: List[Dict[str, Any]]
    mortgages: List[Dict[str, Any]]


class OfficerReviewRequest(BaseModel):
    decision: str  # "APPROVE" | "REJECT"
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None


class MutationExecuteRequest(BaseModel):
    remarks: Optional[str] = None
    custom_mutation_no: Optional[str] = None


class PoliceCheckResponse(BaseModel):
    ulpin: str
    incident_reported: bool
    incident_details: Optional[str] = None
    clearance_status: str
    verified_by: Optional[str] = None
    verification_date: Optional[datetime] = None


class DisputeResponse(BaseModel):
    ulpin: str
    has_active_disputes: bool
    disputes: List[Dict[str, Any]]


class LetterGenerateRequest(BaseModel):
    ulpin: str
    application_id: Optional[str] = None
    letter_type: str  # NOTICE, MUTATION_ORDER, NOC, REJECTION_NOTICE
    content: str


class AuditLogResponse(BaseModel):
    log_id: int
    user_id: str
    user_role: str
    action: str
    ulpin: Optional[str] = None
    timestamp: datetime
    ip_address: Optional[str] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None


class AnalyticsDashboardResponse(BaseModel):
    total_parcels: int
    total_area_hectares: float
    total_active_applications: int
    completed_mutations: int
    active_disputes: int
    total_registered_deeds: int
    state_breakdown: Dict[str, int]
    land_type_breakdown: Dict[str, int]
