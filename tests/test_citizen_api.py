"""
Tests for Citizen Portal: My land, unmasked RoR for owner, profile, and applications.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_citizen_token(phone="9876543210"):
    req = client.post("/api/v1/auth/citizen/login", json={"phone_or_email": phone})
    otp = req.json()["demo_hint_otp"]
    res = client.post("/api/v1/auth/citizen/otp", json={"phone_or_email": phone, "otp_code": otp})
    return res.json()["access_token"]


def test_citizen_profile():
    token = get_citizen_token()
    res = client.get("/api/v1/citizen/profile", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Ramesh Kumar"
    assert "XXXX" in data["aadhar_masked"]


def test_citizen_my_land():
    token = get_citizen_token()
    res = client.get("/api/v1/citizen/my-land", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["ulpin"] == "IN-TN-CHN-000001234567"
    assert data[0]["share_percentage"] == 100.0


def test_citizen_unmasked_ror_for_owner():
    token = get_citizen_token()
    ulpin = "IN-TN-CHN-000001234567"
    res = client.get(f"/api/v1/citizen/my-land/{ulpin}/ror", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    # The authenticated owner sees unmasked name
    assert data["owners"][0]["name"] == "Ramesh Kumar"
    assert data["status"] == "ACTIVE"
