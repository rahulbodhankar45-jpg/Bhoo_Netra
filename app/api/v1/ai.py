"""
AI / ML Router - Remote Sensing Change Detection, Risk Scoring, and Automated Valuation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.ai import (
    ChangeDetectionRequest,
    ChangeDetectionResponse,
    RiskScoreResponse,
    ValuationPredictionResponse
)
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI / ML Engine"])


@router.post("/change-detection", response_model=ChangeDetectionResponse, summary="Satellite Imagery Change Detection")
def detect_change(req: ChangeDetectionRequest, db: Session = Depends(get_db)):
    """Compares temporal satellite captures against sanctioned building permits to detect unauthorized construction."""
    try:
        result = ai_service.detect_satellite_changes(
            db=db,
            ulpin=req.ulpin,
            baseline_year=req.baseline_year,
            comparison_year=req.comparison_year
        )
        return ChangeDetectionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/risk-analysis/{ulpin}", response_model=RiskScoreResponse, summary="Multi-Factor Land Title Risk Scoring")
def get_risk_analysis(ulpin: str, db: Session = Depends(get_db)):
    """Computes title risk score (0-100) evaluating active mortgages, litigation, and planning alerts."""
    try:
        result = ai_service.calculate_risk_score(db=db, ulpin=ulpin)
        return RiskScoreResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/predict-valuation/{ulpin}", response_model=ValuationPredictionResponse, summary="Predictive Land Valuation")
def predict_valuation(ulpin: str, db: Session = Depends(get_db)):
    """Algorithmic land valuation based on circle rates, zoning multipliers, and parcel dimensions."""
    try:
        result = ai_service.predict_valuation(db=db, ulpin=ulpin)
        return ValuationPredictionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
