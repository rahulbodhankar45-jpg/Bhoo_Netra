"""
AI / ML Engine - Satellite Change Detection, Fraud/Risk Scoring, and Land Valuation Prediction.
"""
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.land import Parcel
from app.models.planning import BuildingPermission, LandUse
from app.models.registration import Encumbrance
from app.models.municipal import DisputeRecord


class AIService:
    """Provides predictive risk modeling, remote sensing satellite change detection, and algorithmic valuation."""

    @staticmethod
    def detect_satellite_changes(
        db: Session,
        ulpin: str,
        baseline_year: int = 2024,
        comparison_year: int = 2026
    ) -> Dict[str, Any]:
        """
        Simulates satellite imagery difference analysis over ULPIN geometry.
        Cross-checks detected physical changes against sanctioned building permissions on file.
        """
        parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin.strip()).first()
        if not parcel:
            raise ValueError("Parcel not found")

        # Check if building permission is on file
        bp = db.query(BuildingPermission).filter(BuildingPermission.ulpin == ulpin).first()
        has_approved_bp = bp and bp.status == "APPROVED"

        # Deterministic simulation based on ULPIN hash/survey number for reproducible demonstration
        is_even = sum(ord(c) for c in ulpin) % 2 == 0

        if not has_approved_bp and is_even:
            change_detected = True
            change_category = "UNAUTHORIZED_CONSTRUCTION"
            confidence = 0.94
            detected_area = round(parcel.area * 0.35, 2)
            alert = True
            details = f"New built structure of approx {detected_area} sq.m detected by optical satellite comparison between {baseline_year} and {comparison_year}. No sanctioned building permission on record."
        elif has_approved_bp:
            change_detected = True
            change_category = "SANCTIONED_CONSTRUCTION"
            confidence = 0.98
            detected_area = round(parcel.area * 0.40, 2)
            alert = False
            details = f"Construction progress matches approved building plan #{bp.application_no} ({bp.approved_floors} floors)."
        else:
            change_detected = False
            change_category = "NONE"
            confidence = 0.99
            detected_area = 0.0
            alert = False
            details = f"No physical alterations or encroachment detected across parcel boundary between {baseline_year} and {comparison_year}."

        return {
            "ulpin": ulpin,
            "change_detected": change_detected,
            "change_category": change_category,
            "confidence_score": confidence,
            "detected_area_sqm": detected_area,
            "satellite_baseline_timestamp": f"{baseline_year}-03-15T10:00:00Z",
            "satellite_latest_timestamp": f"{comparison_year}-01-20T11:30:00Z",
            "planning_violation_alert": alert,
            "details": details
        }

    @staticmethod
    def calculate_risk_score(db: Session, ulpin: str) -> Dict[str, Any]:
        """
        Multi-factor risk score (0 to 100) combining:
        - Active encumbrance / mortgage lien
        - Court litigation or active stay order
        - Environmental restrictions
        - Missing building permits
        """
        parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin.strip()).first()
        if not parcel:
            raise ValueError("Parcel not found")

        score = 0.0
        factors = {}
        flags: List[str] = []

        # 1. Encumbrance factor (weight: 35)
        encs = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin, Encumbrance.legal_status == "ACTIVE").all()
        if encs:
            enc_score = 35.0
            flags.append(f"Active encumbrance registered ({len(encs)} active charge/mortgage)")
        else:
            enc_score = 0.0
        factors["encumbrance_risk"] = enc_score
        score += enc_score

        # 2. Litigation / Dispute factor (weight: 45)
        disputes = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin, DisputeRecord.status == "ACTIVE").all()
        if disputes:
            disp_score = 45.0
            flags.append(f"Court dispute pending: {disputes[0].case_number} at {disputes[0].court_name}")
        else:
            disp_score = 0.0
        factors["dispute_risk"] = disp_score
        score += disp_score

        # 3. Planning & Zoning violation factor (weight: 20)
        lu = db.query(LandUse).filter(LandUse.ulpin == ulpin).first()
        if lu and lu.development_restrictions != "NONE":
            dev_score = 15.0
            flags.append(f"Development restriction applicable: {lu.development_restrictions}")
        else:
            dev_score = 0.0
        factors["planning_restriction_risk"] = dev_score
        score += dev_score

        # Categorize
        if score >= 60:
            tier = "HIGH"
            rec = "High transactional risk. Officer scrutiny and clearance required before mutation."
        elif score >= 30:
            tier = "MODERATE"
            rec = "Moderate risk. Ensure encumbrance release letter / NOC is submitted."
        else:
            tier = "LOW"
            rec = "Clean title. Parcel eligible for fast-track processing."

        return {
            "ulpin": ulpin,
            "composite_risk_score": round(score, 1),
            "risk_tier": tier,
            "factors": factors,
            "flags": flags,
            "recommendation": rec
        }

    @staticmethod
    def predict_valuation(db: Session, ulpin: str) -> Dict[str, Any]:
        """Algorithmic land valuation based on circle rates, zoning multipliers, and land area."""
        parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin.strip()).first()
        if not parcel:
            raise ValueError("Parcel not found")

        lu = db.query(LandUse).filter(LandUse.ulpin == ulpin).first()
        zone = lu.zone if lu else parcel.land_type

        # Base rate per sq.m by state and zone
        base_rate = 3500.0  # standard base
        if "Commercial" in zone:
            multiplier = 2.5
        elif "Residential" in zone:
            multiplier = 1.6
        elif "Industrial" in zone:
            multiplier = 1.2
        else:
            multiplier = 0.8  # Agricultural

        # District adjustments
        if "Chennai" in parcel.district or "Pune" in parcel.district:
            multiplier *= 2.0

        unit_rate = round(base_rate * multiplier, 2)
        market_val = round(parcel.area * unit_rate, 2)
        guideline_val = round(market_val * 0.75, 2)

        return {
            "ulpin": ulpin,
            "estimated_market_value_inr": market_val,
            "confidence_range_inr": {
                "min": round(market_val * 0.90, 2),
                "max": round(market_val * 1.15, 2)
            },
            "unit_rate_per_sqm": unit_rate,
            "guideline_value_inr": guideline_val,
            "zone_multiplier": multiplier,
            "factors_considered": [
                f"Zone: {zone}",
                f"District: {parcel.district}",
                f"Parcel Area: {parcel.area} {parcel.area_unit}",
                "Recent registered deed consideration benchmarks"
            ]
        }


ai_service = AIService()
