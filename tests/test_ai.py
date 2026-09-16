"""
Tests for AI / ML Engine: Satellite change detection, risk scoring, and valuation prediction.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ULPIN_TN = "IN-TN-CHN-000001234567"
ULPIN_MH = "IN-MH-PUN-000003456789"


def test_satellite_change_detection():
    res = client.post("/api/v1/ai/change-detection", json={
        "ulpin": ULPIN_TN,
        "baseline_year": 2024,
        "comparison_year": 2026
    })
    assert res.status_code == 200
    data = res.json()
    assert "change_detected" in data
    assert "confidence_score" in data
    assert data["confidence_score"] > 0.8


def test_risk_analysis():
    # Disputed Maharashtra parcel
    res = client.get(f"/api/v1/ai/risk-analysis/{ULPIN_MH}")
    assert res.status_code == 200
    data = res.json()
    assert data["composite_risk_score"] > 30.0
    assert data["risk_tier"] in ["MODERATE", "HIGH"]
    assert len(data["flags"]) >= 1


def test_predict_valuation():
    res = client.get(f"/api/v1/ai/predict-valuation/{ULPIN_TN}")
    assert res.status_code == 200
    data = res.json()
    assert data["estimated_market_value_inr"] > 0
    assert data["unit_rate_per_sqm"] > 0
    assert "min" in data["confidence_range_inr"]
