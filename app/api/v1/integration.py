"""
Integration Layer Router - Dynamic state adapters translating disparate state schemas to Canonical Model.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from app.services.integration import (
    list_supported_states,
    get_adapter,
    CanonicalLandParcel
)

router = APIRouter(prefix="/integration", tags=["Integration Layer & State Adapters"])


@router.get("/states", summary="List Integrated State Revenue Systems")
def get_integrated_states():
    """Lists state revenue systems supported by Land Stack India interoperability adapters."""
    return {
        "supported_states": list_supported_states(),
        "canonical_version": "1.0-NATIONAL",
        "description": "Translates legacy state formats (e.g. TN Nilam Patta/Chitta, MahaBhulekh 7/12, KA Bhoomi RTC) into Land Stack Canonical Standard."
    }


@router.post("/state/{stateCode}/transform", response_model=CanonicalLandParcel, summary="Transform State Schema to Canonical Land Model")
def transform_state_record(stateCode: str, raw_payload: Dict[str, Any]):
    """Ingests raw state land record and maps it to the National Canonical Land Model."""
    try:
        adapter = get_adapter(stateCode)
        canonical_record = adapter.transform_to_canonical(raw_payload)
        return canonical_record
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
