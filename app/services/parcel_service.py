"""
Parcel Service - Manages core land parcel entities, spatial lookups, and multi-service aggregation.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.land import Parcel
from app.models.ror import RoRRecord
from app.models.registration import RegistrationRecord, Encumbrance
from app.models.planning import LandUse, BuildingPermission
from app.models.municipal import PropertyTax, UtilityConnection, DisputeRecord
from app.models.ownership import ParcelOwner, Owner
from app.core.security import mask_name
from app.core.cache import cache


class ParcelService:
    """Core service for parcel discovery, spatial search, and cross-system aggregation."""

    @staticmethod
    def get_by_ulpin(db: Session, ulpin: str) -> Optional[Parcel]:
        """Fetch parcel by unique ULPIN, checking cache first."""
        cached = cache.get(f"parcel:{ulpin}")
        if cached:
            # We can reconstruct or query if needed, but DB query with cache wrapper is fast
            pass
        parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin.strip()).first()
        if parcel:
            cache.set(f"parcel:{ulpin}", parcel, ttl_seconds=300)
        return parcel

    @staticmethod
    def search_parcels(
        db: Session,
        ulpin: Optional[str] = None,
        survey_number: Optional[str] = None,
        state: Optional[str] = None,
        district: Optional[str] = None,
        taluk: Optional[str] = None,
        village: Optional[str] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Parcel]:
        """Multi-criteria search supporting administrative hierarchy and survey numbers."""
        query = db.query(Parcel)

        if ulpin:
            query = query.filter(Parcel.ulpin.ilike(f"%{ulpin.strip()}%"))
        if survey_number:
            query = query.filter(Parcel.survey_number.ilike(f"%{survey_number.strip()}%"))
        if state:
            query = query.filter(Parcel.state.ilike(f"%{state.strip()}%"))
        if district:
            query = query.filter(Parcel.district.ilike(f"%{district.strip()}%"))
        if taluk:
            query = query.filter(Parcel.taluk.ilike(f"%{taluk.strip()}%"))
        if village:
            query = query.filter(Parcel.village.ilike(f"%{village.strip()}%"))
        if min_area is not None:
            query = query.filter(Parcel.area >= min_area)
        if max_area is not None:
            query = query.filter(Parcel.area <= max_area)

        return query.offset(offset).limit(limit).all()

    @staticmethod
    def search_by_bounding_box(
        db: Session,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        limit: int = 100
    ) -> List[Parcel]:
        """Spatial bounding box query using parcel centroid coordinates."""
        query = db.query(Parcel).filter(
            Parcel.centroid_lng >= min_lng,
            Parcel.centroid_lng <= max_lng,
            Parcel.centroid_lat >= min_lat,
            Parcel.centroid_lat <= max_lat
        )
        return query.limit(limit).all()

    @staticmethod
    def get_public_parcel_detail(db: Session, ulpin: str) -> Optional[Dict[str, Any]]:
        """Privacy-compliant parcel detail for public view without exposing personal PII."""
        parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin.strip()).first()
        if not parcel:
            return None

        return {
            "ulpin": parcel.ulpin,
            "survey_number": parcel.survey_number,
            "location": {
                "village": parcel.village,
                "taluk": parcel.taluk,
                "district": parcel.district,
                "state": parcel.state
            },
            "area": parcel.area,
            "area_unit": parcel.area_unit,
            "land_type": parcel.land_type,
            "geometry_available": parcel.coordinates is not None,
            "centroid": [parcel.centroid_lng, parcel.centroid_lat] if parcel.centroid_lng else None
        }

    @staticmethod
    def get_public_ownership_summary(db: Session, ulpin: str) -> Optional[Dict[str, Any]]:
        """Masked ownership summary for public viewing protecting privacy under DPDP act."""
        parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin.strip()).first()
        if not parcel:
            return None

        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin).first()
        parcel_owners = db.query(ParcelOwner).filter(ParcelOwner.ulpin == ulpin).all()
        
        masked_owners = []
        for po in parcel_owners:
            owner = db.query(Owner).filter(Owner.owner_id == po.owner_id).first()
            if owner:
                masked_owners.append({
                    "owner_id": f"OWN-***{owner.owner_id[-2:] if len(owner.owner_id) >= 2 else ''}",
                    "name_masked": mask_name(owner.name),
                    "share_percentage": po.share_percentage,
                    "status": po.status
                })

        return {
            "ulpin": parcel.ulpin,
            "total_owners": len(masked_owners),
            "owners_summary": masked_owners,
            "tenure": ror.tenure if ror else "Unknown",
            "status": ror.status if ror else "ACTIVE",
            "legal_disclaimer": "PII masked under Digital Personal Data Protection Act & Land Stack Public Standards."
        }

    @staticmethod
    def get_aggregated_360_view(db: Session, ulpin: str) -> Optional[Dict[str, Any]]:
        """
        Comprehensive 360-degree aggregated response as detailed in Section 27:
        ULPIN + Parcel + GIS + RoR + Registration + Land Use + Building Permission + Tax + Utilities + Disputes.
        """
        parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin.strip()).first()
        if not parcel:
            return None

        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin).first()
        reg = db.query(RegistrationRecord).filter(RegistrationRecord.ulpin == ulpin).order_by(RegistrationRecord.registration_date.desc()).first()
        encumbrance = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin, Encumbrance.legal_status == "ACTIVE").first()
        land_use = db.query(LandUse).filter(LandUse.ulpin == ulpin).first()
        building = db.query(BuildingPermission).filter(BuildingPermission.ulpin == ulpin).first()
        tax = db.query(PropertyTax).filter(PropertyTax.ulpin == ulpin).first()
        utilities = db.query(UtilityConnection).filter(UtilityConnection.ulpin == ulpin).all()
        disputes = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin, DisputeRecord.status == "ACTIVE").all()

        return {
            "ulpin": parcel.ulpin,
            "parcel": {
                "surveyNumber": parcel.survey_number,
                "area": parcel.area,
                "areaUnit": parcel.area_unit,
                "landType": parcel.land_type,
                "state": parcel.state,
                "district": parcel.district,
                "taluk": parcel.taluk,
                "village": parcel.village
            },
            "gis": {
                "geometryAvailable": parcel.coordinates is not None,
                "centroid": [parcel.centroid_lng, parcel.centroid_lat] if parcel.centroid_lng else None,
                "geometryType": parcel.geometry_type
            },
            "ror": {
                "rorNumber": ror.ror_number if ror else None,
                "status": ror.status if ror else "NONE",
                "tenure": ror.tenure if ror else "Unknown",
                "restrictions": ror.restrictions if ror else "NONE"
            },
            "registration": {
                "registrationNumber": reg.registration_number if reg else None,
                "status": reg.status if reg else "NOT_REGISTERED",
                "deedType": reg.deed_type if reg else None,
                "encumbrance": "ACTIVE" if encumbrance else "NONE"
            },
            "landUse": {
                "zone": land_use.zone if land_use else "Unclassified",
                "permittedUse": land_use.permitted_use if land_use else "Standard",
                "fsiAllowed": land_use.fsi_allowed if land_use else 1.0,
                "developmentRestrictions": land_use.development_restrictions if land_use else "NONE"
            },
            "buildingPermission": {
                "permissionId": building.permission_id if building else None,
                "status": building.status if building else "NO_PERMISSION_ON_FILE",
                "approvedFloors": building.approved_floors if building else None
            },
            "municipal": {
                "taxAssessmentNo": tax.assessment_no if tax else None,
                "taxStatus": tax.paid_status if tax else "UNKNOWN",
                "activeDisputesCount": len(disputes),
                "utilityConnections": [u.utility_type for u in utilities]
            }
        }


parcel_service = ParcelService()
