"""
GIS Router - PostGIS & GeoJSON Cadastral Spatial Services.
Provides multi-layer geographic queries, boundary polygons, and proximity searches.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.gis import (
    GeoJSONFeatureCollection,
    SpatialQueryRequest,
    GISLayerMetadata
)
from app.services.gis_service import gis_service

router = APIRouter(prefix="/gis", tags=["GIS Engine"])


@router.get("/layers", response_model=List[GISLayerMetadata], summary="List Available GIS Layers")
def list_gis_layers():
    """Retrieve catalog of available Base, Governance, Planning, Utility, and Environment spatial layers."""
    return [
        GISLayerMetadata(
            layer_id=l["layer_id"],
            layer_name=l["layer_name"],
            category=l["category"],
            description=l["description"],
            feature_count=100
        )
        for l in gis_service.get_layer_catalog()
    ]


@router.get("/layers/{layerId}", summary="Get Layer GeoJSON Features")
def get_layer_geojson(layerId: str, limit: int = Query(100, le=500), db: Session = Depends(get_db)):
    """Fetch GeoJSON features for a specified layer (e.g. 'gov_encumbrance', 'plan_zoning')."""
    return gis_service.get_layer_features(db=db, layer_id=layerId, limit=limit)


@router.get("/parcels/geojson", summary="Get Cadastral Parcels GeoJSON FeatureCollection")
def get_parcels_geojson(
    state: Optional[str] = Query(None, description="State filter"),
    district: Optional[str] = Query(None, description="District filter"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """Retrieve full cadastral parcel boundary geometries in standard GeoJSON format."""
    return gis_service.get_cadastral_geojson(db=db, state=state, district=district, limit=limit)


@router.post("/spatial-query", summary="Execute Point/Radius or Bounding Box Spatial Search")
def execute_spatial_query(req: SpatialQueryRequest, db: Session = Depends(get_db)):
    """Spatial query by bounding box (min_lng, min_lat, max_lng, max_lat) or point with radius (meters)."""
    if req.point_lng is not None and req.point_lat is not None:
        return gis_service.spatial_distance_query(
            db=db,
            center_lng=req.point_lng,
            center_lat=req.point_lat,
            radius_meters=req.radius_meters or 1000.0
        )
    elif None not in (req.min_lng, req.min_lat, req.max_lng, req.max_lat):
        parcels = gis_service.get_cadastral_geojson(db=db, limit=100)
        # Filter features inside bbox
        filtered_features = []
        for feat in parcels.get("features", []):
            cent = feat.get("properties", {}).get("centroid")
            if cent and (req.min_lng <= cent[0] <= req.max_lng) and (req.min_lat <= cent[1] <= req.max_lat):
                filtered_features.append(feat)
        return {
            "type": "FeatureCollection",
            "features": filtered_features,
            "query_bbox": [req.min_lng, req.min_lat, req.max_lng, req.max_lat]
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either (point_lng, point_lat, radius_meters) or (min_lng, min_lat, max_lng, max_lat)."
        )
