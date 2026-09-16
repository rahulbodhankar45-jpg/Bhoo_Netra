"""
Unit & Integration tests for Authentication, JWT tokens, and RBAC role boundaries.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_and_health():
    """Verify API Gateway root info, frontend HTML, and health check endpoints."""
    # Web UI at /
    web_res = client.get("/")
    assert web_res.status_code == 200
    assert "BhooNetra" in web_res.text or "html" in web_res.headers.get("content-type", "")

    # JSON gateway info at /api-info
    res = client.get("/api-info")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert "public" in data["portals"]

    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["status"] == "healthy"


def test_citizen_otp_flow():
    """Verify citizen login OTP request and verification to obtain JWT."""
    # 1. Request OTP
    req = client.post("/api/v1/auth/citizen/login", json={"phone_or_email": "9876543210"})
    assert req.status_code == 200
    data = req.json()
    assert "demo_hint_otp" in data
    otp = data["demo_hint_otp"]

    # 2. Verify OTP
    verify_res = client.post("/api/v1/auth/citizen/otp", json={
        "phone_or_email": "9876543210",
        "otp_code": otp
    })
    assert verify_res.status_code == 200
    token_data = verify_res.json()
    assert "access_token" in token_data
    assert token_data["role"] == "CITIZEN"


def test_officer_mfa_flow():
    """Verify government officer login and MFA verification."""
    # 1. Officer login with correct password
    login_res = client.post("/api/v1/auth/government/login", json={
        "email": "revenue.officer@landstack.gov.in",
        "password": "Password@123"
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["mfa_required"] is True
    mfa_code = data["demo_hint_mfa"]

    # 2. Verify MFA
    mfa_res = client.post("/api/v1/auth/government/mfa", json={
        "email": "revenue.officer@landstack.gov.in",
        "mfa_code": mfa_code
    })
    assert mfa_res.status_code == 200
    token_data = mfa_res.json()
    assert "access_token" in token_data
    assert token_data["role"] == "REVENUE_OFFICER"


def test_rbac_boundary_citizen_cannot_access_audit_trail():
    """Verify Citizens are forbidden from accessing auditor and officer endpoints."""
    # Citizen login
    req = client.post("/api/v1/auth/citizen/login", json={"phone_or_email": "9876543210"})
    otp = req.json()["demo_hint_otp"]
    token = client.post("/api/v1/auth/citizen/otp", json={
        "phone_or_email": "9876543210",
        "otp_code": otp
    }).json()["access_token"]

    # Attempt to access Auditor endpoint
    res = client.get("/api/v1/government/audit-trail", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
