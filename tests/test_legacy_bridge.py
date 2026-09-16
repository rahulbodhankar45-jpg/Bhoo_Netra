"""
Tests for Frontend Compatibility Bridge (/api/...) and HTML serving.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_serve_frontend_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "BhooNetra" in res.text
    assert "<!DOCTYPE html>" in res.text


def test_frontend_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "OK"


def test_frontend_auth_login():
    res = client.post("/api/auth/login", json={
        "email": "citizen.ramesh@gmail.com",
        "password": "Password@123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["name"] == "Ramesh Kumar"
    assert data["user"]["role"] == "citizen"


def test_frontend_dashboard_summary():
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["totalParcels"] >= 3
    assert "verifiedParcels" in data
    assert "activeDisputes" in data
    assert "totalVillages" in data


def test_frontend_gis_geojson():
    res = client.get("/api/gis/geojson")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1
    props = data["features"][0]["properties"]
    assert "ulpin" in props
    assert "owner" in props
    assert "village" in props


def test_frontend_parcels_search():
    res = client.get("/api/parcels?search=Velachery")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["village"] == "Velachery"


def test_frontend_checklist():
    res = client.get("/api/checklist/IN-TN-CHN-000001234567")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 4
