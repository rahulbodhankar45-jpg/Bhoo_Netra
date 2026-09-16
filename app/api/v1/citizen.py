"""
Citizen Portal Router - Authenticated Land Management, Applications, and Document Access.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_citizen, get_client_ip
from app.models.users import User, CitizenProfile
from app.models.land import Parcel
from app.models.ownership import ParcelOwner, Owner
from app.models.ror import RoRRecord
from app.models.documents import DocumentRecord
from app.models.workflow import Application, WorkflowStage, StatusHistory, CitizenRequest
from app.models.public_purchase import PublicPurchaseRequest
from app.models.notifications import NotificationRecord
from app.schemas.auth import CitizenProfileOut
from app.schemas.citizen import (
    MyLandItem,
    CitizenRoRResponse,
    ApplicationCreateRequest,
    ApplicationResponse,
    CitizenActionRequest,
    CitizenInformationRequest
)
from app.schemas.document import DocumentDetail
from app.services.workflow_service import workflow_service
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/citizen", tags=["Citizen Portal"])


@router.get("/profile", response_model=CitizenProfileOut, summary="Get Citizen Profile")
def get_citizen_profile(current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Fetch profile of currently logged-in citizen."""
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first()
    if not profile:
        # Create default profile if missing
        profile = CitizenProfile(
            user_id=current_user.id,
            aadhar_masked="XXXX-XXXX-9876",
            pan="ABCDE1234F",
            address="Demo Citizen Residence",
            city="Chennai",
            state="Tamil Nadu",
            pincode="600001",
            verified=True
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return CitizenProfileOut(
        user_id=current_user.id,
        full_name=current_user.full_name,
        phone=current_user.phone,
        email=current_user.email,
        aadhar_masked=profile.aadhar_masked,
        pan=profile.pan,
        address=profile.address,
        city=profile.city,
        state=profile.state,
        pincode=profile.pincode,
        verified=profile.verified
    )


@router.get("/my-land", response_model=List[MyLandItem], summary="List Citizen Owned Land Holdings")
def get_my_land(current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Lists all parcels legally linked to this authenticated citizen."""
    owners = db.query(Owner).filter(Owner.citizen_id == current_user.id).all()
    owner_ids = [o.owner_id for o in owners]

    if not owner_ids:
        return []

    parcel_owners = db.query(ParcelOwner).filter(
        ParcelOwner.owner_id.in_(owner_ids),
        ParcelOwner.status == "ACTIVE"
    ).all()

    results = []
    for po in parcel_owners:
        parcel = db.query(Parcel).filter(Parcel.ulpin == po.ulpin).first()
        if parcel:
            results.append(MyLandItem(
                ulpin=parcel.ulpin,
                survey_number=parcel.survey_number,
                state=parcel.state,
                district=parcel.district,
                taluk=parcel.taluk,
                village=parcel.village,
                area=parcel.area,
                area_unit=parcel.area_unit,
                land_type=parcel.land_type,
                share_percentage=po.share_percentage,
                acquisition_mode=po.acquisition_mode,
                status=po.status
            ))
    return results


@router.get("/my-land/{ulpin}", summary="Get Detailed Citizen Land Record")
def get_my_land_by_ulpin(ulpin: str, current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Detailed view for citizen's owned parcel."""
    owners = db.query(Owner).filter(Owner.citizen_id == current_user.id).all()
    owner_ids = [o.owner_id for o in owners]

    link = db.query(ParcelOwner).filter(
        ParcelOwner.ulpin == ulpin.strip(),
        ParcelOwner.owner_id.in_(owner_ids)
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not possess verified ownership rights for this parcel."
        )

    parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin.strip()).first()
    return {
        "ulpin": parcel.ulpin,
        "surveyNumber": parcel.survey_number,
        "state": parcel.state,
        "district": parcel.district,
        "taluk": parcel.taluk,
        "village": parcel.village,
        "area": parcel.area,
        "areaUnit": parcel.area_unit,
        "landType": parcel.land_type,
        "sharePercentage": link.share_percentage,
        "acquisitionMode": link.acquisition_mode,
        "coordinates": parcel.coordinates,
        "centroid": [parcel.centroid_lng, parcel.centroid_lat]
    }


@router.get("/my-land/{ulpin}/ror", response_model=CitizenRoRResponse, summary="Get Full RoR Record")
def get_citizen_ror(ulpin: str, current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Unmasked Record of Rights (RoR) extract for the rightful owner."""
    ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin.strip()).first()
    if not ror:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RoR record not found.")

    parcel_owners = db.query(ParcelOwner).filter(ParcelOwner.ulpin == ulpin.strip()).all()
    owners_list = []
    for po in parcel_owners:
        owner = db.query(Owner).filter(Owner.owner_id == po.owner_id).first()
        if owner:
            owners_list.append({
                "owner_id": owner.owner_id,
                "name": owner.name,
                "share": po.share_percentage,
                "status": po.status
            })

    return CitizenRoRResponse(
        ulpin=ror.ulpin,
        ror_number=ror.ror_number,
        status=ror.status,
        owners=owners_list,
        rights=ror.rights or ["OWNERSHIP"],
        tenure=ror.tenure,
        restrictions=ror.restrictions,
        last_updated=ror.last_updated
    )


@router.get("/my-land/{ulpin}/documents", response_model=List[DocumentDetail], summary="Get Parcel Documents")
def get_citizen_documents(ulpin: str, current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """List legal documents (deeds, EC, orders) tied to this parcel."""
    docs = db.query(DocumentRecord).filter(DocumentRecord.ulpin == ulpin.strip()).all()
    return [
        DocumentDetail(
            document_id=d.document_id,
            ulpin=d.ulpin,
            document_type=d.document_type,
            file_name=d.file_name,
            file_size=d.file_size,
            sha256_hash=d.sha256_hash,
            uploaded_by=d.uploaded_by,
            uploaded_at=d.uploaded_at,
            verification_status=d.verification_status,
            verified_by=d.verified_by,
            verified_at=d.verified_at
        )
        for d in docs
    ]



@router.get("/purchase-requests", summary="List Public Purchase Interest for Owned Parcels")
def list_purchase_requests(current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Show purchase-interest messages received for parcels owned by the logged-in citizen."""
    owners = db.query(Owner).filter(Owner.citizen_id == current_user.id).all()
    owner_ids = [o.owner_id for o in owners]
    if not owner_ids:
        return []
    owner = owners[0]
    rows = db.query(PublicPurchaseRequest).filter(
        PublicPurchaseRequest.owner_id == owner.owner_id
    ).order_by(PublicPurchaseRequest.created_at.desc()).all()
    return [{
        "request_id": r.request_id, "ulpin": r.ulpin,
        "requester_name": r.requester_name, "requester_contact": r.requester_contact,
        "message": r.message, "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None
    } for r in rows]

@router.post("/purchase-requests/{request_id}/decision", summary="Accept or Reject Purchase Interest")
def decide_purchase_request(request_id: str, decision: str, response_message: Optional[str] = None, current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    decision = decision.strip().upper()
    if decision not in {"ACCEPT", "REJECT"}:
        raise HTTPException(status_code=400, detail="Decision must be ACCEPT or REJECT.")
    owners = db.query(Owner).filter(Owner.citizen_id == current_user.id).all()
    owner_ids = [o.owner_id for o in owners]
    item = db.query(PublicPurchaseRequest).filter(PublicPurchaseRequest.request_id == request_id, PublicPurchaseRequest.owner_id.in_(owner_ids)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Purchase request not found for your land holdings.")
    item.status = "ACCEPTED" if decision == "ACCEPT" else "REJECTED"
    item.owner_response = (response_message or "").strip() or ("Owner accepted the purchase interest." if decision == "ACCEPT" else "Owner rejected the purchase interest.")
    db.commit()
    contact_email = item.requester_contact.split("|")[0].strip()
    notification_service.notify(
        event_type="PURCHASE_REQUEST_DECISION", recipient=contact_email, channel="IN_APP",
        subject=f"Purchase request {item.status}",
        message=f"Your purchase-interest request {item.request_id} for parcel {item.ulpin} was {item.status.lower()} by the registered owner. {item.owner_response}"
    )
    return {"request_id": item.request_id, "status": item.status, "message": item.owner_response}

@router.get("/notifications", summary="Get Citizen Notifications")
def get_citizen_notifications(current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    rows = db.query(NotificationRecord).filter(NotificationRecord.recipient == current_user.email).order_by(NotificationRecord.created_at.desc()).limit(50).all()
    volatile = notification_service.get_recipient_notifications(current_user.email)
    return [
        {"notification_id": r.notification_id, "event_type": r.event_type, "subject": r.subject, "message": r.message, "status": r.status, "timestamp": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ] or volatile

@router.get("/applications", response_model=List[ApplicationResponse], summary="List Citizen Applications")
def get_applications(current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Lists applications where the citizen is applicant or transferee."""
    apps = db.query(Application).filter(
        (Application.applicant_citizen_id == current_user.id) |
        (Application.target_citizen_id == current_user.id)
    ).order_by(Application.created_at.desc()).all()
    return apps


@router.post("/applications", response_model=ApplicationResponse, summary="Submit Land Ownership Transfer / Mutation")
def submit_application(
    req: ApplicationCreateRequest,
    request: Request,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db)
):
    """Initiates the 11-step ownership transfer and mutation workflow."""
    # Find buyer / target citizen
    target_user = db.query(User).filter(
        (User.email == req.target_citizen_email.strip().lower()) |
        (User.phone == req.target_citizen_email.strip())
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target citizen '{req.target_citizen_email}' not found in registry."
        )

    # Verify applicant owns the land
    owners = db.query(Owner).filter(Owner.citizen_id == current_user.id).all()
    owner_ids = [o.owner_id for o in owners]
    has_rights = db.query(ParcelOwner).filter(
        ParcelOwner.ulpin == req.ulpin.strip(),
        ParcelOwner.owner_id.in_(owner_ids),
        ParcelOwner.status == "ACTIVE"
    ).first()

    if not has_rights:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Applicant does not hold active title to transfer this parcel."
        )

    application = workflow_service.create_application(
        db=db,
        applicant_id=current_user.id,
        ulpin=req.ulpin.strip(),
        target_citizen_id=target_user.id,
        application_type=req.application_type,
        remarks=req.remarks,
        document_ids=req.document_ids
    )

    # Trigger automated checks pipeline
    workflow_service.run_automated_checks(db, application.application_id)

    notification_service.notify(
        event_type="APPLICATION_SUBMITTED",
        recipient=current_user.email,
        subject=f"Application {application.application_id} Submitted",
        message=f"Your transfer application for parcel {application.ulpin} was submitted and queued for officer review.",
        channel="EMAIL"
    )

    audit_service.log_event(
        db=db,
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        action="OWNERSHIP_TRANSFER_STARTED",
        ulpin=application.ulpin,
        ip_address=get_client_ip(request),
        new_value=f"Target: {target_user.full_name} ({target_user.email})"
    )

    return application


@router.get("/applications/{applicationId}", response_model=ApplicationResponse, summary="Get Application Status")
def get_application_detail(applicationId: str, current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Fetch detailed progress of a specific application."""
    app = db.query(Application).filter(Application.application_id == applicationId).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return app


@router.post("/applications/{applicationId}/accept", summary="Transferee Citizen Accepts Transfer")
def accept_transfer(
    applicationId: str,
    req: CitizenActionRequest,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db)
):
    """Target transferee confirms acceptance of transfer terms."""
    app = db.query(Application).filter(Application.application_id == applicationId).first()
    if not app or app.target_citizen_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

    history = StatusHistory(
        application_id=app.application_id,
        previous_status=app.status.value,
        new_status=app.status.value,
        transitioned_by=f"Transferee:{current_user.full_name}",
        comments=f"Transferee accepted transfer terms. {req.remarks or ''}"
    )
    db.add(history)
    db.commit()
    return {"message": "Transfer terms accepted by transferee."}


@router.post("/applications/{applicationId}/decline", summary="Transferee Citizen Declines Transfer")
def decline_transfer(
    applicationId: str,
    req: CitizenActionRequest,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db)
):
    """Target transferee declines transfer proposal."""
    app = db.query(Application).filter(Application.application_id == applicationId).first()
    if not app or app.target_citizen_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

    old = app.status.value
    app.status = WorkflowStage.REJECTED
    app.rejection_reason = f"Declined by target citizen: {req.remarks or 'Not interested'}"

    history = StatusHistory(
        application_id=app.application_id,
        previous_status=old,
        new_status=WorkflowStage.REJECTED.value,
        transitioned_by=f"Transferee:{current_user.full_name}",
        comments=app.rejection_reason
    )
    db.add(history)
    db.commit()
    return {"message": "Transfer declined."}


@router.post("/request-information", summary="Citizen Official Information Request")
def citizen_request_info(req: CitizenInformationRequest, current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Submit formal citizen request for records or demarcation."""
    req_id = f"CREQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    item = CitizenRequest(
        request_id=req_id,
        citizen_id=current_user.id,
        ulpin=req.ulpin.strip(),
        request_type=req.request_type,
        message=req.message,
        status="PENDING"
    )
    db.add(item)
    db.commit()
    return {"request_id": req_id, "status": "PENDING", "message": "Request submitted to Revenue Department."}
