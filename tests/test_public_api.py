"""
Tests for Public Portal: Privacy masking, parcel search, and status.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ULPIN = "IN-TN-CHN-000001234567"


def test_public_parcel_detail():
    res = client.get(f"/api/v1/public/parcels/{ULPIN}")
    assert res.status_code == 200
    data = res.json()
    assert data["ulpin"] == ULPIN
    assert data["survey_number"] == "123/4A"
    assert data["location"]["state"] == "Tamil Nadu"


def test_public_search():
    res = client.get("/api/v1/public/search?state=Tamil Nadu&district=Chennai")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert any(p["ulpin"] == ULPIN for p in data)


def test_privacy_preserving_ownership_summary():
    """Verify owner names are masked for public protection."""
    res = client.get(f"/api/v1/public/parcels/{ULPIN}/ownership-summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_owners"] >= 1
    # Check that owner name is masked (e.g. 'R*** K***' not 'Ramesh Kumar')
    owner = data["owners_summary"][0]
    assert "R***" in owner["name_masked"]
    assert "Ramesh Kumar" not in owner["name_masked"]


def test_public_land_use_and_map():
    map_res = client.get(f"/api/v1/public/parcels/{ULPIN}/map")
    assert map_res.status_code == 200
    assert map_res.json()["type"] == "Feature"

    lu_res = client.get(f"/api/v1/public/parcels/{ULPIN}/land-use")
    assert lu_res.status_code == 200
    assert lu_res.json()["zone"] == "Residential"
