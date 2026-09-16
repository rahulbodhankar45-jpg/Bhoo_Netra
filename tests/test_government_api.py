"""
Tests for Government Portal: ULPIN deep verification, SRO status, police check, letters, audit trail, and analytics.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ULPIN_TN = "IN-TN-CHN-000001234567"
ULPIN_MH = "IN-MH-PUN-000003456789"


def get_token(email="admin@landstack.gov.in"):
    log = client.post("/api/v1/auth/government/login", json={"email": email, "password": "Password@123"})
    mfa = log.json()["demo_hint_mfa"]
    res = client.post("/api/v1/auth/government/mfa", json={"email": email, "mfa_code": mfa})
    return res.json()["access_token"]


def test_government_ulpin_verification():
    token = get_token("revenue.officer@landstack.gov.in")
    res = client.get(f"/api/v1/government/verify/ulpin/{ULPIN_TN}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["exists"] is True
    assert data["parcel"]["state"] == "Tamil Nadu"
    assert data["risk_level"] in ["LOW", "MODERATE"]


def test_government_sro_status():
    token = get_token("sro.guindy@landstack.gov.in")
    res = client.get(f"/api/v1/government/sro/status/{ULPIN_TN}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["deeds"]) >= 1


def test_government_police_check():
    token = get_token("police.officer@landstack.gov.in")
    res = client.get(f"/api/v1/government/police/check/{ULPIN_TN}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["clearance_status"] == "CLEARED"


def test_government_disputes():
    token = get_token("revenue.officer@landstack.gov.in")
    res = client.get(f"/api/v1/government/disputes/{ULPIN_MH}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["has_active_disputes"] is True
    assert len(data["disputes"]) >= 1


def test_government_letter_generation():
    token = get_token("revenue.officer@landstack.gov.in")
    res = client.post(
        "/api/v1/government/letters/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "ulpin": ULPIN_TN,
            "letter_type": "MUTATION_NOTICE",
            "content": "Notice is hereby issued to all interested parties regarding pending mutation application."
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "GOV-LTR-" in data["letter_id"]
    assert data["letter_type"] == "MUTATION_NOTICE"


def test_government_audit_trail_auditor_access():
    token = get_token("auditor@landstack.gov.in")
    res = client.get("/api/v1/government/audit-trail", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1


def test_government_analytics_dashboard():
    token = get_token("admin@landstack.gov.in")
    res = client.get("/api/v1/government/analytics/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_parcels"] >= 3
    assert data["total_area_hectares"] > 0
    assert "Tamil Nadu" in data["state_breakdown"]
