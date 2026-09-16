"""
Tests for Integration Layer: State Revenue Adapters translating to Canonical Land Model.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_states():
    res = client.get("/api/v1/integration/states")
    assert res.status_code == 200
    states = res.json()["supported_states"]
    codes = [s["state_code"] for s in states]
    assert "TN" in codes
    assert "MH" in codes
    assert "KA" in codes


def test_tamil_nadu_adapter():
    payload = {
        "patta_number": "452",
        "survey_subdiv": "88/1A",
        "mavattam": "Chennai",
        "mavattam_code": "CHN",
        "vattam": "Guindy",
        "gramam": "Velachery",
        "visthiranam_sqm": 1500.0,
        "pattadhar_names": ["M. Senthil Nathan"]
    }
    res = client.post("/api/v1/integration/state/TN/transform", json=payload)
    assert res.status_code == 200
    canonical = res.json()
    assert canonical["state"] == "Tamil Nadu"
    assert canonical["survey_number"] == "88/1A"
    assert canonical["area_sqm"] == 1500.0
    assert canonical["source_system"] == "TN_NILAM_REGINSP_GATEWAY"
    assert canonical["ror"]["owners"][0]["name"] == "M. Senthil Nathan"


def test_maharashtra_adapter():
    payload = {
        "gat_kramank": "501",
        "zilha": "Pune",
        "zilha_code": "PUN",
        "taluka": "Haveli",
        "gaon": "Hinjawadi",
        "kshetra_hec_are_sqm": 2200.0,
        "khatedar_names": ["Dattatray Kulkarni"]
    }
    res = client.post("/api/v1/integration/state/MH/transform", json=payload)
    assert res.status_code == 200
    canonical = res.json()
    assert canonical["state"] == "Maharashtra"
    assert canonical["source_system"] == "MAHA_BHULEKH_ISARITA_GATEWAY"
