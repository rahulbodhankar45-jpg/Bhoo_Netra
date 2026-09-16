"""
Pydantic schemas for AI/ML Engine: Change Detection, Risk Scoring, and Valuation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ChangeDetectionRequest(BaseModel):
    ulpin: str
    baseline_year: int = 2024
    comparison_year: int = 2026
    detect_construction: bool = True
    detect_encroachment: bool = True


class ChangeDetectionResponse(BaseModel):
    ulpin: str
    change_detected: bool
    change_category: Optional[str] = None  # UNAUTHORIZED_CONSTRUCTION, BOUNDARY_ENCROACHMENT, VEGETATION_CLEARING, NONE
    confidence_score: float                # 0.0 - 1.0
    detected_area_sqm: float
    satellite_baseline_timestamp: str
    satellite_latest_timestamp: str
    planning_violation_alert: bool
    details: str


class RiskScoreResponse(BaseModel):
    ulpin: str
    composite_risk_score: float            # 0 to 100
    risk_tier: str                         # "LOW", "MODERATE", "HIGH", "CRITICAL"
    factors: Dict[str, float]              # e.g., {"encumbrance_risk": 20, "dispute_risk": 40, ...}
    flags: List[str]
    recommendation: str


class ValuationPredictionResponse(BaseModel):
    ulpin: str
    estimated_market_value_inr: float
    confidence_range_inr: Dict[str, float]  # {"min": ..., "max": ...}
    unit_rate_per_sqm: float
    guideline_value_inr: float
    zone_multiplier: float
    factors_considered: List[str]
