"""
Pydantic schemas for the Public Portal (Privacy-Preserving Land Discovery).
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class PublicParcelSummary(BaseModel):
    ulpin: str
    survey_number: str
    state: str
    district: str
    taluk: str
    village: str
    area: float
    area_unit: str
    land_type: str


class PublicParcelDetail(BaseModel):
    ulpin: str
    survey_number: str
    location: Dict[str, str]
    area: float
    area_unit: str
    land_type: str
    geometry_available: bool
    centroid: Optional[List[float]] = None


class PublicLandUse(BaseModel):
    ulpin: str
    zone: str
    permitted_use: str
    fsi_allowed: Optional[float] = None
    development_restrictions: str


class PublicOwnershipSummary(BaseModel):
    ulpin: str
    total_owners: int
    owners_summary: List[Dict[str, Any]]  # Masked names and shares only
    tenure: str
    status: str
    legal_disclaimer: str = "PII masked under Digital Personal Data Protection Act & Land Stack Public Access Standards."


class PublicParcelStatus(BaseModel):
    ulpin: str
    ror_status: str
    registration_status: str
    encumbrance_status: str  # "NONE" | "ENCUMBERED"
    dispute_status: str      # "CLEAR" | "LITIGATION_PENDING"


class InformationRequestCreate(BaseModel):
    ulpin: str
    requester_name: str
    requester_contact: str
    query_details: str


class InformationRequestResponse(BaseModel):
    request_id: str
    ulpin: str
    status: str
    acknowledgment: str


class PurchaseRequestCreate(BaseModel):
    ulpin: str
    requester_name: str
    requester_contact: str
    message: str
    offer: Optional[str] = None


class PurchaseRequestResponse(BaseModel):
    request_id: str
    ulpin: str
    status: str
    message: str
