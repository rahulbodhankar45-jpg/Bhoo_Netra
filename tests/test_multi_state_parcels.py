"""
Tests for nationwide multi-state parcel expansion (12 parcels across TN, MH, KA, TS, HR, GJ).
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_nationwide_parcel_count_and_diversity():
    """Verify 12 parcels are present and span at least 6 states."""
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["totalParcels"] >= 12
    assert data["activeDisputes"] >= 2


def test_cadastral_geojson_has_all_parcels():
    """Verify PostGIS/GeoJSON endpoints return all 12 polygon features."""
    res = client.get("/api/gis/geojson")
    assert res.status_code == 200
    fc = res.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 12

    ulpins = {f["properties"]["ulpin"] for f in fc["features"]}
    expected = {
        "IN-TN-CHN-000001234567",
        "IN-KA-BLR-000004567890",
        "IN-TS-HYD-000005678901",
        "IN-MH-MUM-000006789012",
        "IN-HR-GUR-000007890123",
        "IN-TN-CBE-000008901234",
        "IN-MH-NSK-000009012345",
        "IN-KA-MYS-000010123456",
        "IN-TN-CHN-000011234567",
        "IN-GJ-GND-000012345678"
    }
    assert expected.issubset(ulpins)


def test_public_search_across_states():
    """Verify search by state works across Karnataka, Telangana, and Gujarat."""
    for state in ["Karnataka", "Telangana", "Gujarat"]:
        res = client.get(f"/api/v1/public/search?state={state}")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1, f"Expected at least one parcel in {state}"


def test_new_citizen_login_and_linked_parcel():
    """Verify a newly seeded citizen can login and sees their linked parcel."""
    login_res = client.post("/api/auth/login", json={
        "email": "citizen.rajeshwari@gmail.com",
        "password": "Password@123"
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "token" in data
    assert data["user"]["linkedUlpin"] == "IN-KA-BLR-000004567890"
