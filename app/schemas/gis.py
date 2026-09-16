"""
Pydantic schemas for GIS Engine, Layers, and Spatial Features.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class GeoJSONGeometry(BaseModel):
    type: str = "Polygon"
    coordinates: List[Any]


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]


class SpatialQueryRequest(BaseModel):
    min_lng: Optional[float] = None
    min_lat: Optional[float] = None
    max_lng: Optional[float] = None
    max_lat: Optional[float] = None
    point_lng: Optional[float] = None
    point_lat: Optional[float] = None
    radius_meters: Optional[float] = 1000.0


class GISLayerMetadata(BaseModel):
    layer_id: str
    layer_name: str
    category: str  # BASE, GOVERNANCE, PLANNING, UTILITY, ENVIRONMENT
    description: str
    feature_count: int
    geometry_type: str = "Polygon"
