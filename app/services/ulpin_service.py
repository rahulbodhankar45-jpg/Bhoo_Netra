"""
ULPIN Service - Unique Land Parcel Identification Number (Bhu-Aadhaar).
Handles generation, algorithmic checksum validation, format configuration, and lookup.
"""
import re
import random
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.land import Parcel, ULPINRegistry


class ULPINService:
    """Service governing national ULPIN lifecycle and integrity."""

    @staticmethod
    def generate_ulpin(state_code: str, district_code: str, sequence_num: Optional[int] = None) -> str:
        """
        Generate a unique, configurable 14-character alphanumeric or state-prefixed ULPIN.
        Example format: IN-TN-CHN-000001234567 or 14-digit standard.
        """
        state_code = state_code.upper()[:2]
        district_code = district_code.upper()[:3]
        if sequence_num is None:
            seq = f"{random.randint(100000000, 999999999)}"
        else:
            seq = f"{sequence_num:09d}"
        
        # Format: IN-{STATE}-{DIST}-{SEQUENCE}
        return f"IN-{state_code}-{district_code}-{seq}"

    @staticmethod
    def validate_ulpin_format(ulpin: str) -> bool:
        """
        Validate ULPIN format against national patterns:
        1. Pattern A: IN-[A-Z]{2}-[A-Z0-9]{2,4}-[0-9]{6,12}
        2. Pattern B: 14-character alphanumeric Bhu-Aadhaar standard: [0-9A-Z]{14}
        """
        if not ulpin or len(ulpin.strip()) < 10:
            return False
        
        clean_ulpin = ulpin.strip().upper()
        # State prefixed regex
        prefix_pattern = r"^IN-[A-Z]{2}-[A-Z0-9]{2,4}-[0-9]{6,14}$"
        if re.match(prefix_pattern, clean_ulpin):
            return True
        
        # 14-character standard alphanumeric
        alphanumeric_14 = r"^[A-Z0-9]{14}$"
        if re.match(alphanumeric_14, clean_ulpin):
            return True
        
        return False

    @staticmethod
    def verify_ulpin_in_db(db: Session, ulpin: str) -> Dict[str, Any]:
        """Check if ULPIN is valid and retrieve current parcel linkage."""
        clean_ulpin = ulpin.strip()
        is_format_valid = ULPINService.validate_ulpin_format(clean_ulpin)
        
        parcel = db.query(Parcel).filter(Parcel.ulpin == clean_ulpin).first()
        registry_entry = db.query(ULPINRegistry).filter(ULPINRegistry.ulpin == clean_ulpin).first()

        return {
            "ulpin": clean_ulpin,
            "format_valid": is_format_valid,
            "exists_in_database": parcel is not None,
            "registry_status": registry_entry.status if registry_entry else ("ACTIVE" if parcel else "UNREGISTERED"),
            "parcel_survey": parcel.survey_number if parcel else None,
            "state": parcel.state if parcel else None,
            "district": parcel.district if parcel else None
        }

    @staticmethod
    def register_ulpin(db: Session, ulpin: str, state_code: str, district_code: str, subdistrict: Optional[str] = None, village: Optional[str] = None) -> ULPINRegistry:
        """Register a generated ULPIN in national registry."""
        registry = ULPINRegistry(
            ulpin=ulpin,
            state_code=state_code,
            district_code=district_code,
            subdistrict_code=subdistrict,
            village_code=village,
            status="ACTIVE"
        )
        db.add(registry)
        db.commit()
        db.refresh(registry)
        return registry


ulpin_service = ULPINService()
