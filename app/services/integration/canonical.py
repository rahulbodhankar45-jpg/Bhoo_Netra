"""
Canonical Land Model - Standardized National Representation for Interoperable Land Records.
Acts as the central target model for heterogeneous State/SRO/Municipal systems.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class CanonicalOwner(BaseModel):
    owner_id: str
    name: str
    share_percentage: float
    identity_hash: Optional[str] = None


class CanonicalRoR(BaseModel):
    ror_number: str
    status: str
    tenure: str
    rights: List[str]
    restrictions: str
    owners: List[CanonicalOwner]


class CanonicalRegistration(BaseModel):
    registration_number: Optional[str] = None
    sro_code: Optional[str] = None
    deed_type: Optional[str] = None
    market_value: Optional[float] = None
    consideration_amount: Optional[float] = None
    encumbrance_status: str = "NONE"


class CanonicalLandUse(BaseModel):
    zone: str
    permitted_use: str
    fsi_allowed: float = 1.5
    restrictions: str = "NONE"


class CanonicalLandParcel(BaseModel):
    ulpin: str
    survey_number: str
    state: str
    district: str
    taluk: str
    village: str
    area_sqm: float
    land_type: str
    geometry: Dict[str, Any]
    ror: Optional[CanonicalRoR] = None
    registration: Optional[CanonicalRegistration] = None
    land_use: Optional[CanonicalLandUse] = None
    source_system: str
