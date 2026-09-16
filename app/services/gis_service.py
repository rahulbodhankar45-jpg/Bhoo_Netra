"""
GIS Engine - Spatial Queries, PostGIS GeoJSON generation, and Cadastral Map Layer Services.
Supports Base, Governance, Planning, Utility, and Environment spatial layers.
"""
from typing import List, Dict, Any, Optional
import math
from sqlalchemy.orm import Session
from app.models.land import Parcel
from app.models.planning import LandUse, BuildingPermission
from app.models.registration import Encumbrance
from app.models.municipal import DisputeRecord, UtilityConnection


class GISService:
    """Provides spatial analysis, GeoJSON FeatureCollections, and multi-tier GIS layers."""

    LAYER_CATALOG = [
        # BASE LAYERS
        {"layer_id": "base_cadastral", "layer_name": "Cadastral Parcels", "category": "BASE", "description": "High-precision boundary cadastral parcel geometries and survey marks."},
        {"layer_id": "base_ulpin", "layer_name": "ULPIN Grid", "category": "BASE", "description": "National Bhu-Aadhaar ULPIN geocoded parcel centroids."},
        {"layer_id": "base_administrative", "layer_name": "Administrative Boundaries", "category": "BASE", "description": "State, District, Taluk, and Village administrative boundaries."},
        
        # GOVERNANCE LAYERS
        {"layer_id": "gov_ror", "layer_name": "RoR & Title Status", "category": "GOVERNANCE", "description": "Active, pending, and clear Record of Rights titles."},
        {"layer_id": "gov_encumbrance", "layer_name": "Encumbered Land", "category": "GOVERNANCE", "description": "Parcels under active bank mortgage or statutory charges."},
        {"layer_id": "gov_disputes", "layer_name": "Litigation & Disputes", "category": "GOVERNANCE", "description": "Parcels subject to active court litigation or stay orders."},

        # PLANNING LAYERS
        {"layer_id": "plan_zoning", "layer_name": "Zoning & Master Plan", "category": "PLANNING", "description": "Urban and rural zoning designations (Residential, Commercial, Eco-zone)."},
        {"layer_id": "plan_building_permissions", "layer_name": "Sanctioned Building Permissions", "category": "PLANNING", "description": "Approved building layouts and authorized heights."},

        # UTILITY LAYERS
        {"layer_id": "util_networks", "layer_name": "Utility Infrastructure", "category": "UTILITY", "description": "Water, electricity, sewerage, and telecom transmission corridors."},

        # ENVIRONMENT LAYERS
        {"layer_id": "env_eco_zones", "layer_name": "Environmental & Hazard Zones", "category": "ENVIRONMENT", "description": "Flood plains, coastal regulation zones (CRZ), and protected forests."}
    ]

    @staticmethod
    def get_layer_catalog() -> List[Dict[str, Any]]:
        return GISService.LAYER_CATALOG

    @staticmethod
    def get_cadastral_geojson(
        db: Session,
        state: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Generate GeoJSON FeatureCollection of cadastral parcels with land attributes."""
        query = db.query(Parcel)
        if state:
            query = query.filter(Parcel.state.ilike(f"%{state.strip()}%"))
        if district:
            query = query.filter(Parcel.district.ilike(f"%{district.strip()}%"))

        parcels = query.limit(limit).all()
        features = []

        for p in parcels:
            coords = p.coordinates
            # Ensure coordinates are in GeoJSON Polygon format [[[lng, lat], ...]]
            if coords and isinstance(coords, list):
                # If single ring was passed, wrap in polygon coordinate array
                if coords and isinstance(coords[0], list) and not isinstance(coords[0][0], list):
                    coords = [coords]

            feature = {
                "type": "Feature",
                "id": p.ulpin,
                "geometry": {
                    "type": p.geometry_type or "Polygon",
                    "coordinates": coords or []
                },
                "properties": {
                    "ulpin": p.ulpin,
                    "surveyNumber": p.survey_number,
                    "state": p.state,
                    "district": p.district,
                    "taluk": p.taluk,
                    "village": p.village,
                    "area": p.area,
                    "areaUnit": p.area_unit,
                    "landType": p.land_type,
                    "centroid": [p.centroid_lng, p.centroid_lat] if p.centroid_lng else None
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": features
        }

    @staticmethod
    def get_layer_features(db: Session, layer_id: str, limit: int = 100) -> Dict[str, Any]:
        """Fetch spatial features specifically filtered and styled by layer type."""
        parcels = db.query(Parcel).limit(limit).all()
        features = []

        for p in parcels:
            coords = p.coordinates
            if coords and isinstance(coords, list):
                if coords and isinstance(coords[0], list) and not isinstance(coords[0][0], list):
                    coords = [coords]

            props: Dict[str, Any] = {
                "ulpin": p.ulpin,
                "surveyNumber": p.survey_number,
                "layer": layer_id
            }

            if layer_id == "gov_encumbrance":
                enc = db.query(Encumbrance).filter(Encumbrance.ulpin == p.ulpin, Encumbrance.legal_status == "ACTIVE").first()
                if not enc:
                    continue  # Only include encumbered parcels in this layer
                props.update({"encumbranceType": enc.encumbrance_type, "beneficiary": enc.beneficiary, "amount": enc.amount})

            elif layer_id == "gov_disputes":
                disp = db.query(DisputeRecord).filter(DisputeRecord.ulpin == p.ulpin, DisputeRecord.status == "ACTIVE").first()
                if not disp:
                    continue
                props.update({"court": disp.court_name, "caseNo": disp.case_number, "disputeType": disp.dispute_type})

            elif layer_id == "plan_zoning":
                lu = db.query(LandUse).filter(LandUse.ulpin == p.ulpin).first()
                props.update({
                    "zone": lu.zone if lu else p.land_type,
                    "fsiAllowed": lu.fsi_allowed if lu else 1.5,
                    "permittedUse": lu.permitted_use if lu else "Standard"
                })

            elif layer_id == "plan_building_permissions":
                bp = db.query(BuildingPermission).filter(BuildingPermission.ulpin == p.ulpin).first()
                props.update({
                    "permissionStatus": bp.status if bp else "NONE",
                    "approvedFloors": bp.approved_floors if bp else 0
                })

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coords or []
                },
                "properties": props
            })

        return {
            "type": "FeatureCollection",
            "layer_id": layer_id,
            "features": features
        }

    @staticmethod
    def spatial_distance_query(
        db: Session,
        center_lng: float,
        center_lat: float,
        radius_meters: float = 1000.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Calculates Haversine distance from center point to parcel centroids.
        Works across SQLite or PostgreSQL seamlessly.
        """
        parcels = db.query(Parcel).filter(Parcel.centroid_lat.isnot(None), Parcel.centroid_lng.isnot(None)).all()
        results = []

        # 1 deg lat approx 111,000 meters
        r_earth = 6371000.0

        for p in parcels:
            d_lat = math.radians(p.centroid_lat - center_lat)
            d_lng = math.radians(p.centroid_lng - center_lng)
            a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(center_lat)) * math.cos(math.radians(p.centroid_lat)) * math.sin(d_lng / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist = r_earth * c

            if dist <= radius_meters:
                results.append({
                    "ulpin": p.ulpin,
                    "survey_number": p.survey_number,
                    "distance_meters": round(dist, 2),
                    "area": p.area,
                    "land_type": p.land_type,
                    "centroid": [p.centroid_lng, p.centroid_lat]
                })

        results.sort(key=lambda x: x["distance_meters"])
        return results[:limit]


gis_service = GISService()
