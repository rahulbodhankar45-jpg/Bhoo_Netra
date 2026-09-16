"""
Tests for GIS Engine: GeoJSON endpoints, spatial layers, and proximity queries.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_gis_layers():
    res = client.get("/api/v1/gis/layers")
    assert res.status_code == 200
    layers = res.json()
    assert len(layers) >= 5
    categories = {l["category"] for l in layers}
    assert "BASE" in categories
    assert "GOVERNANCE" in categories
    assert "PLANNING" in categories


def test_cadastral_geojson():
    res = client.get("/api/v1/gis/parcels/geojson")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1
    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert "geometry" in feat
    assert "properties" in feat


def test_spatial_query():
    # Chennai Velachery coords
    res = client.post("/api/v1/gis/spatial-query", json={
        "point_lng": 80.2215,
        "point_lat": 12.9815,
        "radius_meters": 5000.0
    })
    assert res.status_code == 200
    results = res.json()
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "distance_meters" in results[0]
