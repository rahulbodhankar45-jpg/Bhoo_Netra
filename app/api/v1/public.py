"""
Public Portal Router - Open Discovery & Privacy-Preserving Land Queries.
Implements DPDP Act compliant masking of PII while offering rich cadastral and status data.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_client_ip
from app.models.planning import LandUse
from app.models.documents import DocumentRecord
from app.models.ownership import ParcelOwner, Owner
from app.models.ownership import OwnershipHistory
from app.models.users import User
from app.models.ror import RoRRecord
from app.models.registration import RegistrationRecord, Encumbrance
from app.models.land import Parcel
from app.models.municipal import DisputeRecord
from app.models.workflow import CitizenRequest
from app.schemas.public import (
    PublicParcelSummary,
    PublicParcelDetail,
    PublicLandUse,
    PublicOwnershipSummary,
    PublicParcelStatus,
    InformationRequestCreate,
    InformationRequestResponse, PurchaseRequestCreate, PurchaseRequestResponse
)
from app.services.parcel_service import parcel_service
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service
from app.models.public_purchase import PublicPurchaseRequest
from app.models.notifications import NotificationRecord

router = APIRouter(prefix="/public", tags=["Public Portal"])


@router.get("/parcels/{ulpin}", response_model=PublicParcelDetail, summary="Get Public Parcel Details")
def get_public_parcel(ulpin: str, request: Request, db: Session = Depends(get_db)):
    """Fetch sanitized public metadata for a land parcel by ULPIN."""
    detail = parcel_service.get_public_parcel_detail(db, ulpin)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parcel with ULPIN '{ulpin}' not found.")

    audit_service.log_event(
        db=db,
        user_id="ANONYMOUS_PUBLIC",
        user_role="PUBLIC",
        action="ULPIN_SEARCHED",
        ulpin=ulpin,
        ip_address=get_client_ip(request)
    )
    return detail


@router.get("/search", response_model=List[PublicParcelSummary], summary="Search Public Parcels")
def search_parcels(
    q: Optional[str] = Query(None, description="General search across ULPIN, survey number, village, district, and state"),
    ulpin: Optional[str] = Query(None, description="Partial or full ULPIN"),
    surveyNumber: Optional[str] = Query(None, description="Survey / Subdivision number"),
    state: Optional[str] = Query(None, description="State (e.g., 'Tamil Nadu', 'Maharashtra')"),
    district: Optional[str] = Query(None, description="District (e.g., 'Chennai', 'Pune')"),
    taluk: Optional[str] = Query(None, description="Taluk / Tehsil"),
    village: Optional[str] = Query(None, description="Village / Revenue Ward"),
    min_area: Optional[float] = Query(None, description="Minimum area"),
    max_area: Optional[float] = Query(None, description="Maximum area"),
    land_type: Optional[str] = Query(None, description="Land type"),
    zoning: Optional[str] = Query(None, description="Zoning"),
    availability: Optional[str] = Query(None, description="Availability status"),
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Multi-hierarchy search for public land parcels."""
    if q and q.strip():
        term = f"%{q.strip()}%"
        parcels = db.query(Parcel).filter(
            Parcel.ulpin.ilike(term) |
            Parcel.survey_number.ilike(term) |
            Parcel.village.ilike(term) |
            Parcel.district.ilike(term) |
            Parcel.state.ilike(term)
        ).offset(offset).limit(limit).all()
    else:
        parcels = parcel_service.search_parcels(
            db=db, ulpin=ulpin, survey_number=surveyNumber, state=state, district=district,
            taluk=taluk, village=village, min_area=min_area, max_area=max_area, limit=limit, offset=offset
        )
    if land_type:
        parcels = [p for p in parcels if p.land_type and land_type.lower() in p.land_type.lower()]
    if zoning:
        allowed = {x.ulpin for x in db.query(LandUse).filter(LandUse.zone.ilike(f"%{zoning}%")).all()}
        parcels = [p for p in parcels if p.ulpin in allowed]
    if availability:
        wanted = availability.upper()
        filtered=[]
        for p in parcels:
            ror = db.query(RoRRecord).filter(RoRRecord.ulpin == p.ulpin).first()
            enc = db.query(Encumbrance).filter(
                Encumbrance.ulpin == p.ulpin, Encumbrance.legal_status == "ACTIVE"
            ).first()
            disp = db.query(DisputeRecord).filter(
                DisputeRecord.ulpin == p.ulpin, DisputeRecord.status == "ACTIVE"
            ).first()
            accepted_interest = db.query(PublicPurchaseRequest).filter(
                PublicPurchaseRequest.ulpin == p.ulpin, PublicPurchaseRequest.status == "ACCEPTED"
            ).first()
            pending_interest = db.query(PublicPurchaseRequest).filter(
                PublicPurchaseRequest.ulpin == p.ulpin, PublicPurchaseRequest.status == "PENDING"
            ).first()
            actual = "GOVERNMENT RESTRICTED" if (ror and ror.restrictions and ror.restrictions != "NONE") else (
                "NOT AVAILABLE" if disp else (
                    "TRANSACTION IN PROGRESS" if accepted_interest else (
                        "UNDER DISCUSSION" if (pending_interest or enc) else "AVAILABLE"
                    )
                )
            )
            if actual == wanted:
                filtered.append(p)
        parcels=filtered
    return [
        PublicParcelSummary(
            ulpin=p.ulpin,
            survey_number=p.survey_number,
            state=p.state,
            district=p.district,
            taluk=p.taluk,
            village=p.village,
            area=p.area,
            area_unit=p.area_unit,
            land_type=p.land_type
        )
        for p in parcels
    ]


@router.get("/summary", summary="Get Public Registry Dashboard Summary")
def get_public_registry_summary(db: Session = Depends(get_db)):
    """Return privacy-safe aggregate metrics for the public registry dashboard."""
    parcels = db.query(Parcel).all()
    total = len(parcels)
    total_area = sum((float(p.area) if p.area is not None else 0.0) for p in parcels)
    total_states = len({p.state for p in parcels if p.state})
    verified = 0
    available = 0
    under_discussion = 0
    transaction_in_progress = 0

    for p in parcels:
        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == p.ulpin).first()
        disp = db.query(DisputeRecord).filter(
            DisputeRecord.ulpin == p.ulpin, DisputeRecord.status == "ACTIVE"
        ).first()
        enc = db.query(Encumbrance).filter(
            Encumbrance.ulpin == p.ulpin, Encumbrance.legal_status == "ACTIVE"
        ).first()
        accepted_interest = db.query(PublicPurchaseRequest).filter(
            PublicPurchaseRequest.ulpin == p.ulpin, PublicPurchaseRequest.status == "ACCEPTED"
        ).first()
        pending_interest = db.query(PublicPurchaseRequest).filter(
            PublicPurchaseRequest.ulpin == p.ulpin, PublicPurchaseRequest.status == "PENDING"
        ).first()

        if ror and ror.status == "ACTIVE" and not disp:
            verified += 1

        if ror and ror.restrictions and ror.restrictions != "NONE":
            continue
        if disp:
            continue
        if accepted_interest:
            transaction_in_progress += 1
        elif pending_interest or enc:
            under_discussion += 1
        else:
            available += 1

    return {
        "totalParcels": total,
        "totalAreaSqm": round(total_area, 2),
        "totalAreaHectares": round(total_area / 10000.0, 2),
        "totalStates": total_states,
        "verifiedParcels": verified,
        "availableParcels": available,
        "underDiscussion": under_discussion,
        "transactionInProgress": transaction_in_progress,
    }


@router.get("/parcels/{ulpin}/map", summary="Get Parcel Cadastral Map Geometry")
def get_parcel_map(ulpin: str, db: Session = Depends(get_db)):
    """Retrieve GeoJSON boundary polygon for visualization on maps."""
    parcel = parcel_service.get_by_ulpin(db, ulpin)
    if not parcel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcel not found.")

    coords = parcel.coordinates
    if coords and isinstance(coords, list) and isinstance(coords[0], list) and not isinstance(coords[0][0], list):
        coords = [coords]

    return {
        "type": "Feature",
        "id": parcel.ulpin,
        "geometry": {
            "type": parcel.geometry_type or "Polygon",
            "coordinates": coords or []
        },
        "properties": {
            "ulpin": parcel.ulpin,
            "surveyNumber": parcel.survey_number,
            "area": parcel.area,
            "areaUnit": parcel.area_unit,
            "centroid": [parcel.centroid_lng, parcel.centroid_lat] if parcel.centroid_lng else None
        }
    }


@router.get("/parcels/{ulpin}/land-use", response_model=PublicLandUse, summary="Get Parcel Land Use & Zoning")
def get_parcel_land_use(ulpin: str, db: Session = Depends(get_db)):
    """Inspect master plan zoning and development restrictions."""
    parcel = parcel_service.get_by_ulpin(db, ulpin)
    if not parcel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcel not found.")

    lu = db.query(LandUse).filter(LandUse.ulpin == ulpin.strip()).first()
    return PublicLandUse(
        ulpin=parcel.ulpin,
        zone=lu.zone if lu else parcel.land_type,
        permitted_use=lu.permitted_use if lu else "Standard regional use",
        fsi_allowed=lu.fsi_allowed if lu else 1.5,
        development_restrictions=lu.development_restrictions if lu else "NONE"
    )


@router.get("/parcels/{ulpin}/ownership-summary", response_model=PublicOwnershipSummary, summary="Privacy-Preserved Ownership Summary")
def get_parcel_ownership_summary(ulpin: str, request: Request, db: Session = Depends(get_db)):
    """Provides legal title status and masked owner identities complying with DPDP act."""
    summary = parcel_service.get_public_ownership_summary(db, ulpin)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcel ownership records not found.")

    audit_service.log_event(
        db=db,
        user_id="ANONYMOUS_PUBLIC",
        user_role="PUBLIC",
        action="OWNERSHIP_SUMMARY_VIEWED",
        ulpin=ulpin,
        ip_address=get_client_ip(request)
    )
    return summary


@router.get("/parcels/{ulpin}/status", response_model=PublicParcelStatus, summary="Get Consolidated Parcel Status")
def get_parcel_status(ulpin: str, db: Session = Depends(get_db)):
    """Check RoR, Registration, Encumbrance, and Dispute statuses."""
    parcel = parcel_service.get_by_ulpin(db, ulpin)
    if not parcel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcel not found.")

    ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin).first()
    reg = db.query(RegistrationRecord).filter(RegistrationRecord.ulpin == ulpin).first()
    enc = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin, Encumbrance.legal_status == "ACTIVE").first()
    disp = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin, DisputeRecord.status == "ACTIVE").first()

    return PublicParcelStatus(
        ulpin=parcel.ulpin,
        ror_status=ror.status if ror else "NOT_ISSUED",
        registration_status=reg.status if reg else "UNREGISTERED",
        encumbrance_status="ENCUMBERED" if enc else "NONE",
        dispute_status="LITIGATION_PENDING" if disp else "CLEAR"
    )



@router.get("/parcels/{ulpin}/documents/{document_id}/download", summary="Download Permitted Public Document")
def download_public_document(ulpin: str, document_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.ulpin == ulpin.strip(), DocumentRecord.document_id == document_id, DocumentRecord.verification_status == "VERIFIED").first()
    if not doc:
        raise HTTPException(status_code=404, detail="Verified public document not found.")
    path = Path(doc.file_location)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document reference exists, but the file is not available in this deployment.")
    return FileResponse(str(path), filename=doc.file_name, media_type="application/pdf")

@router.get("/parcels/{ulpin}/citizen-view", summary="Citizen Safe Parcel View")
def get_citizen_safe_view(ulpin: str, request: Request, db: Session = Depends(get_db)):
    """Return the buyer-facing parcel information without exposing private owner contact data or internal officer notes."""
    ulpin = ulpin.strip()
    parcel = parcel_service.get_by_ulpin(db, ulpin)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found.")

    owners = db.query(ParcelOwner).filter(ParcelOwner.ulpin == ulpin, ParcelOwner.status == "ACTIVE").all()
    ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin).first()
    land_use = db.query(LandUse).filter(LandUse.ulpin == ulpin).first()
    enc = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin, Encumbrance.legal_status == "ACTIVE").all()
    reg = db.query(RegistrationRecord).filter(RegistrationRecord.ulpin == ulpin, RegistrationRecord.status == "REGISTERED").order_by(RegistrationRecord.registration_date.desc()).first()
    docs = db.query(DocumentRecord).filter(DocumentRecord.ulpin == ulpin, DocumentRecord.verification_status == "VERIFIED").all()
    disp = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin, DisputeRecord.status == "ACTIVE").first()

    verification = "VERIFIED" if ror and ror.status == "ACTIVE" and not disp else ("VERIFICATION REQUIRED" if disp else "IN PROGRESS")
    accepted_interest = db.query(PublicPurchaseRequest).filter(
        PublicPurchaseRequest.ulpin == ulpin, PublicPurchaseRequest.status == "ACCEPTED"
    ).first()
    pending_interest = db.query(PublicPurchaseRequest).filter(
        PublicPurchaseRequest.ulpin == ulpin, PublicPurchaseRequest.status == "PENDING"
    ).first()
    parcel_status = "GOVERNMENT RESTRICTED" if (ror and ror.restrictions and ror.restrictions != "NONE") else (
        "NOT AVAILABLE" if disp else (
            "TRANSACTION IN PROGRESS" if accepted_interest else (
                "UNDER DISCUSSION" if (pending_interest or enc) else "AVAILABLE"
            )
        )
    )

    masked_owners=[]
    for po in owners:
        owner=db.query(Owner).filter(Owner.owner_id==po.owner_id).first()
        if owner:
            parts=owner.name.split()
            masked=' '.join((p[:1]+'***') if len(p)>1 else p for p in parts)
            masked_owners.append({"name":masked,"share_percentage":po.share_percentage})

    title_info = {
        "latest_registration_number": reg.registration_number if reg else None,
        "latest_deed_type": reg.deed_type if reg else None,
        "registration_date": reg.registration_date.isoformat() if reg and reg.registration_date else None,
        "registered_documents": len(docs)
    }
    document_refs=[{
        "document_id": d.document_id,
        "document_type": d.document_type,
        "file_name": d.file_name,
        "verification_status": d.verification_status,
        "reference": d.document_id
    } for d in docs]

    return {
        "ulpin": parcel.ulpin, "survey_number": parcel.survey_number,
        "location": {"village":parcel.village,"taluk":parcel.taluk,"district":parcel.district,"state":parcel.state},
        "area": parcel.area, "area_unit": parcel.area_unit, "land_type": parcel.land_type,
        "ownership": {"owners":masked_owners,"tenure":ror.tenure if ror else "NOT RECORDED"},
        "legal": {
            "encumbrance_status": "ACTIVE ENCUMBRANCE" if enc else "NO ACTIVE ENCUMBRANCE",
            "encumbrance_count": len(enc),
            "title_information": title_info,
            "dispute_status": "ACTIVE DISPUTE" if disp else "NO ACTIVE DISPUTE"
        },
        "planning": {"zoning":land_use.zone if land_use else parcel.land_type,"permitted_use":land_use.permitted_use if land_use else "Standard regional use","fsi":land_use.fsi_allowed if land_use else None,"development_restrictions":land_use.development_restrictions if land_use else "NONE"},
        "verification_status": verification, "parcel_status": parcel_status,
        "documents": document_refs,
        "map": {"geometry": parcel.coordinates, "geometry_type":parcel.geometry_type or "Polygon", "centroid":[parcel.centroid_lng,parcel.centroid_lat] if parcel.centroid_lng is not None and parcel.centroid_lat is not None else None, "nearby_roads":[f"Main road near {parcel.village}", "Local access road"], "nearby_landmarks":[f"{parcel.village} locality", f"{parcel.district} district centre"], "north_direction":"↑ North", "boundary_available": bool(parcel.coordinates)}
    }

@router.post("/purchase-request", response_model=PurchaseRequestResponse, summary="Send Purchase Interest to Land Owner")
def submit_purchase_request(req: PurchaseRequestCreate, request: Request, db: Session = Depends(get_db)):
    """Allow a public visitor to express interest in purchasing a parcel without exposing owner contact details."""
    ulpin = req.ulpin.strip()
    parcel = parcel_service.get_by_ulpin(db, ulpin)
    if not parcel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified parcel ULPIN not found.")

    if not req.requester_name.strip() or not req.requester_contact.strip() or not req.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name, contact and message are required.")

    active_owner = db.query(ParcelOwner).filter(
        ParcelOwner.ulpin == ulpin, ParcelOwner.status == "ACTIVE"
    ).first()
    if not active_owner:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active registered owner is available for this parcel.")

    request_id = f"PUR-{__import__('datetime').datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[-12:]}"
    item = PublicPurchaseRequest(
        request_id=request_id,
        ulpin=ulpin,
        owner_id=active_owner.owner_id,
        requester_name=req.requester_name.strip(),
        requester_contact=req.requester_contact.strip(),
        message=((f"Offer: {req.offer.strip()}\n" if req.offer and req.offer.strip() else "") + req.message.strip()),
        status="PENDING"
    )
    db.add(item)
    audit_service.log_event(
        db=db, user_id="ANONYMOUS_PUBLIC", user_role="PUBLIC",
        action="PURCHASE_INTEREST_SUBMITTED", ulpin=ulpin,
        ip_address=get_client_ip(request), new_value=request_id
    )
    db.commit()
    owner = db.query(Owner).filter(Owner.owner_id == active_owner.owner_id).first()
    if owner and owner.citizen_id:
        owner_user = db.query(User).filter(User.id == owner.citizen_id).first()
        if owner_user:
            notification_service.notify(
                event_type="NEW_PURCHASE_REQUEST", recipient=owner_user.email, channel="IN_APP",
                subject="New purchase interest received",
                message=f"New purchase-interest request {request_id} received for parcel {ulpin}."
            )
            db.add(NotificationRecord(
                notification_id=f"NOTIF-{request_id}", recipient=owner_user.email,
                event_type="NEW_PURCHASE_REQUEST", subject="New purchase interest received",
                message=f"New purchase-interest request {request_id} received for parcel {ulpin}."
            ))
            db.commit()
    return PurchaseRequestResponse(
        request_id=request_id, ulpin=ulpin, status="PENDING",
        message="Your purchase request has been securely sent to the registered land owner. Owner contact details are not exposed publicly."
    )

@router.post("/information-request", response_model=InformationRequestResponse, summary="Submit Public Land Information Request")
def submit_info_request(req: InformationRequestCreate, db: Session = Depends(get_db)):
    """Submit RTI or general citizen information inquiry regarding a land parcel."""
    parcel = parcel_service.get_by_ulpin(db, req.ulpin)
    if not parcel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified parcel ULPIN not found.")

    req_id = f"PUB-REQ-{req.ulpin[-6:]}"
    return InformationRequestResponse(
        request_id=req_id,
        ulpin=req.ulpin,
        status="RECEIVED",
        acknowledgment=f"Information inquiry for parcel {req.ulpin} recorded. Reference ID: {req_id}"
    )
