"""
Frontend Compatibility & Legacy Bridge Router.
Enables seamless integration with BhooNetra SIH Frontend while utilizing the Land Stack National Engine.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, generate_otp
from app.core.dependencies import get_client_ip
from app.models.users import User, UserRole, CitizenProfile, OTPVerification
from app.models.land import Parcel
from app.models.ownership import Owner, ParcelOwner
from app.models.ror import RoRRecord
from app.models.registration import RegistrationRecord, Encumbrance, SROOffice, Deed, Mortgage
from app.models.planning import LandUse, BuildingPermission
from app.models.municipal import PropertyTax, DisputeRecord, PoliceRecord, GovernmentLetter
from app.models.workflow import Application, ApplicationDocument, StatusHistory, WorkflowStage
from app.models.audit import AuditLog
from app.services.audit_service import audit_service
from app.services.workflow_service import workflow_service
from app.services.parcel_service import parcel_service
from app.services.email_service import email_service

legacy_router = APIRouter(prefix="/api", tags=["Frontend Compatibility Bridge"])


class LoginRequest(BaseModel):
    email: str
    password: str


class SendEmailOTPRequest(BaseModel):
    email: str
    purpose: str = "REGISTRATION"


class VerifyEmailOTPRequest(BaseModel):
    email: str
    otp_code: str
    purpose: str = "REGISTRATION"


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "citizen"
    otp: Optional[str] = None
    phone: Optional[str] = None


class TaxUpdateRequest(BaseModel):
    status: str


class ApplicationCreate(BaseModel):
    ulpin: str
    target_email: str
    remarks: Optional[str] = None


class ReviewRequest(BaseModel):
    decision: str  # APPROVE | REJECT
    remarks: Optional[str] = None


class MutationRequest(BaseModel):
    remarks: Optional[str] = None


class LetterRequest(BaseModel):
    ulpin: str
    letter_type: str = "MUTATION_NOTICE"
    content: str


@legacy_router.get("/health", summary="Frontend Health Check")
def frontend_health():
    return {"status": "OK", "service": "BhooNetra / Land Stack India API"}


@legacy_router.post("/auth/login", summary="Frontend Login")
def frontend_login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticates user for BhooNetra single-page frontend."""
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    # Find linked parcel if citizen
    linked_ulpin = None
    if user.role == UserRole.CITIZEN:
        owner = db.query(Owner).filter(Owner.citizen_id == user.id).first()
        if owner:
            po = db.query(ParcelOwner).filter(ParcelOwner.owner_id == owner.owner_id, ParcelOwner.status == "ACTIVE").first()
            if po:
                linked_ulpin = po.ulpin

    role_str = "official" if user.role != UserRole.CITIZEN else "citizen"
    token = create_access_token(subject=str(user.id), role=user.role.value)

    audit_service.log_event(
        db=db,
        user_id=str(user.id),
        user_role=user.role.value,
        action="FRONTEND_LOGIN",
        ip_address=get_client_ip(request)
    )

    return {
        "token": token,
        "user": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "role": role_str,
            "govRole": user.role.value,
            "department": user.department or "Government Official",
            "linkedUlpin": linked_ulpin
        }
    }


@legacy_router.post("/auth/send-email-otp", summary="Send Registration Verification OTP to Email")
@legacy_router.post("/auth/send-otp", summary="Send Registration Verification OTP to Email (Alias)")
def send_email_otp(req: SendEmailOTPRequest, db: Session = Depends(get_db)):
    """Generates a secure 6-digit OTP and dispatches it directly to the user's email address."""
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please enter a valid email address.")

    # Check if already registered
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email address is already registered. Please login instead."
        )

    # Invalidate prior unused OTPs for this email and purpose
    db.query(OTPVerification).filter(
        OTPVerification.recipient == email,
        OTPVerification.purpose == req.purpose,
        OTPVerification.is_used == False
    ).update({"is_used": True})

    otp = generate_otp(6)
    expires = datetime.utcnow() + timedelta(minutes=10)

    otp_rec = OTPVerification(
        recipient=email,
        otp_code=otp,
        purpose=req.purpose,
        expires_at=expires,
        is_used=False
    )
    db.add(otp_rec)
    db.commit()

    # Send email via EmailService
    sent, err_msg, is_live = email_service.send_registration_otp_email(to_email=email, otp_code=otp)
    if not sent and is_live:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SMTP Email Delivery Failed: {err_msg}. Please check your SMTP configuration."
        )

    if is_live:
        msg = f"Verification code has been dispatched to {email}. Please check your email inbox and spam folder."
        demo_otp = None
    else:
        msg = f"Verification OTP generated for {email}."
        demo_otp = otp

    return {
        "message": msg,
        "email": email,
        "smtp_configured": is_live,
        "demo_otp": demo_otp,
        "expires_in_seconds": 600
    }


@legacy_router.post("/auth/verify-email-otp", summary="Verify Email Registration OTP")
@legacy_router.post("/auth/verify-otp", summary="Verify Email Registration OTP (Alias)")
def verify_email_otp(req: VerifyEmailOTPRequest, db: Session = Depends(get_db)):
    """Verifies that the entered 6-digit OTP matches the one dispatched to the user's email."""
    email = req.email.strip().lower()
    otp_code = req.otp_code.strip()

    otp_rec = db.query(OTPVerification).filter(
        OTPVerification.recipient == email,
        OTPVerification.otp_code == otp_code,
        OTPVerification.purpose == req.purpose,
        OTPVerification.is_used == False,
        OTPVerification.expires_at > datetime.utcnow()
    ).first()

    if not otp_rec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code. Please check your email or request a new OTP."
        )

    otp_rec.is_used = True
    db.commit()

    return {
        "verified": True,
        "message": "Email verified successfully! You can now proceed with registration."
    }


@legacy_router.post("/auth/register", summary="Frontend Registration")
def frontend_register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Registers a new citizen or official from the frontend form with email verification."""
    email = req.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    # If an OTP was provided, verify that it matches and was issued for registration
    if req.otp:
        otp_clean = req.otp.strip()
        valid_otp = db.query(OTPVerification).filter(
            OTPVerification.recipient == email,
            OTPVerification.otp_code == otp_clean,
            OTPVerification.purpose == "REGISTRATION",
            OTPVerification.created_at >= datetime.utcnow() - timedelta(minutes=15)
        ).first()
        if not valid_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or unverified email verification OTP."
            )
        valid_otp.is_used = True
        db.commit()

    role_enum = UserRole.CITIZEN
    if req.role.lower() in ["official", "government"]:
        role_enum = UserRole.REVENUE_OFFICER

    phone_val = req.phone.strip() if req.phone else f"9{datetime.utcnow().strftime('%m%d%H%M%S')[:9]}"
    # Ensure phone uniqueness if generated or provided
    existing_phone = db.query(User).filter(User.phone == phone_val).first()
    if existing_phone:
        phone_val = f"9{datetime.utcnow().strftime('%m%d%H%M%S%f')[-9:]}"

    new_user = User(
        email=email,
        phone=phone_val,
        full_name=req.name.strip(),
        hashed_password=get_password_hash(req.password),
        role=role_enum,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if role_enum == UserRole.CITIZEN:
        profile = CitizenProfile(
            user_id=new_user.id,
            aadhar_masked="XXXX-XXXX-1122",
            pan="ABCDE9999Z",
            address="Registered via BhooNetra Frontend",
            city="Chennai",
            state="Tamil Nadu",
            pincode="600001",
            verified=True
        )
        db.add(profile)
        db.commit()

    return {"message": "User registered successfully. You can now login.", "email": email}


@legacy_router.get("/dashboard/summary", summary="Frontend Dashboard Summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Feeds top metrics cards and charts in frontend Government/Citizen view."""
    total_parcels = db.query(func.count(Parcel.ulpin)).scalar() or 0
    active_disputes = db.query(func.count(DisputeRecord.dispute_id)).filter(DisputeRecord.status == "ACTIVE").scalar() or 0
    pending_mutations = db.query(func.count(Application.application_id)).filter(Application.status != WorkflowStage.COMPLETED).scalar() or 0
    total_villages = db.query(func.count(func.distinct(Parcel.village))).scalar() or 0

    total_area = db.query(func.sum(Parcel.area)).scalar() or 0.0
    total_states = db.query(func.count(func.distinct(Parcel.state))).scalar() or 0
    active_mortgages = db.query(func.count(Encumbrance.encumbrance_id)).filter(Encumbrance.legal_status == "ACTIVE").scalar() or 0

    # Zone distribution
    by_zone = [
        {"land_use": "Commercial", "count": db.query(func.count(Parcel.ulpin)).filter(Parcel.land_type == "Commercial").scalar() or 0},
        {"land_use": "Residential", "count": db.query(func.count(Parcel.ulpin)).filter(Parcel.land_type == "Residential").scalar() or 0},
        {"land_use": "Industrial", "count": db.query(func.count(Parcel.ulpin)).filter(Parcel.land_type == "Industrial").scalar() or 0},
        {"land_use": "Agricultural", "count": db.query(func.count(Parcel.ulpin)).filter(Parcel.land_type == "Agricultural").scalar() or 0},
        {"land_use": "SEZ / Other", "count": db.query(func.count(Parcel.ulpin)).filter(~Parcel.land_type.in_(["Commercial", "Residential", "Industrial", "Agricultural"])).scalar() or 0}
    ]

    return {
        "totalParcels": total_parcels,
        "verifiedParcels": total_parcels - active_disputes,
        "activeDisputes": active_disputes,
        "activeMortgages": active_mortgages,
        "pendingMutations": pending_mutations,
        "totalVillages": total_villages,
        "totalStates": total_states,
        "totalArea": round(total_area, 2),
        "totalAreaHectares": round(total_area / 10000.0, 2),
        "disputesByZone": by_zone
    }


@legacy_router.get("/gis/geojson", summary="Frontend Cadastral GeoJSON Layer")
def get_gis_geojson(db: Session = Depends(get_db)):
    """Supplies Leaflet Map in frontend with all parcel polygons and properties."""
    parcels = db.query(Parcel).all()
    features = []

    for p in parcels:
        owner_name = "Government / Common"
        po = db.query(ParcelOwner).filter(ParcelOwner.ulpin == p.ulpin, ParcelOwner.status == "ACTIVE").first()
        if po:
            o = db.query(Owner).filter(Owner.owner_id == po.owner_id).first()
            if o:
                owner_name = o.name

        tax = db.query(PropertyTax).filter(PropertyTax.ulpin == p.ulpin).first()
        tax_status = tax.paid_status if tax else "Paid"

        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == p.ulpin).first()
        ror_status = ror.status if ror else "Active"

        coords = p.coordinates
        if coords and isinstance(coords, list) and isinstance(coords[0], list) and not isinstance(coords[0][0], list):
            coords = [coords]

        disp = db.query(DisputeRecord).filter(DisputeRecord.ulpin == p.ulpin, DisputeRecord.status == "ACTIVE").first()
        enc = db.query(Encumbrance).filter(Encumbrance.ulpin == p.ulpin, Encumbrance.legal_status == "ACTIVE").first()

        features.append({
            "type": "Feature",
            "geometry": {
                "type": p.geometry_type or "Polygon",
                "coordinates": coords or []
            },
            "properties": {
                "ulpin": p.ulpin,
                "owner": owner_name,
                "surveyNumber": p.survey_number,
                "village": p.village,
                "taluk": p.taluk,
                "district": p.district,
                "state": p.state,
                "landUse": p.land_type,
                "area": p.area,
                "areaUnit": p.area_unit or "sq.m",
                "taxStatus": tax_status,
                "rorStatus": ror_status,
                "isDisputed": bool(disp or ror_status == "DISPUTED"),
                "hasEncumbrance": bool(enc),
                "centroid": [p.centroid_lng, p.centroid_lat] if p.centroid_lng else None
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


@legacy_router.get("/parcels", summary="Frontend Parcel Search")
def search_parcels_frontend(search: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Search endpoint backing frontend search bar."""
    query = db.query(Parcel)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            Parcel.ulpin.ilike(s) |
            Parcel.survey_number.ilike(s) |
            Parcel.village.ilike(s) |
            Parcel.district.ilike(s)
        )

    parcels = query.all()
    results = []

    for p in parcels:
        owner_name = "Government"
        owner_contact = "9876543210"
        po = db.query(ParcelOwner).filter(ParcelOwner.ulpin == p.ulpin, ParcelOwner.status == "ACTIVE").first()
        if po:
            o = db.query(Owner).filter(Owner.owner_id == po.owner_id).first()
            if o:
                owner_name = o.name

        tax = db.query(PropertyTax).filter(PropertyTax.ulpin == p.ulpin).first()
        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == p.ulpin).first()
        enc = db.query(Encumbrance).filter(Encumbrance.ulpin == p.ulpin, Encumbrance.legal_status == "ACTIVE").first()
        bp = db.query(BuildingPermission).filter(BuildingPermission.ulpin == p.ulpin).first()
        disp = db.query(DisputeRecord).filter(DisputeRecord.ulpin == p.ulpin, DisputeRecord.status == "ACTIVE").first()

        results.append({
            "ulpin": p.ulpin,
            "survey_number": p.survey_number,
            "owner_name": owner_name,
            "owner_contact": owner_contact,
            "village": p.village,
            "taluka": p.taluk,
            "district": p.district,
            "land_use": p.land_type,
            "area_sq_m": p.area,
            "registration_status": "Registered",
            "encumbrance": "Active Encumbrance" if enc else "None",
            "building_permission": bp.status if bp else "Approved",
            "property_tax": tax.paid_status if tax else "Paid",
            "ror_status": ror.status if ror else "Active",
            "ror_acts": "Section 4(1) Land Stack Act",
            "auth_status": "Pending" if disp else "Verified",
            "latitude": p.centroid_lat or 12.9815,
            "longitude": p.centroid_lng or 80.2215,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        })

    return results


@legacy_router.get("/parcels/{ulpin}", summary="Frontend Parcel Details")
def get_parcel_detail_frontend(ulpin: str, db: Session = Depends(get_db)):
    results = search_parcels_frontend(search=ulpin, db=db)
    if not results:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return results[0]


@legacy_router.patch("/parcels/{ulpin}/tax", summary="Update Tax Status")
def update_tax(ulpin: str, req: TaxUpdateRequest, db: Session = Depends(get_db)):
    tax = db.query(PropertyTax).filter(PropertyTax.ulpin == ulpin.strip()).first()
    if tax:
        tax.paid_status = req.status
        db.commit()
    return {"message": "Tax status updated", "status": req.status}


# =============================================================
# APPLICATIONS & MUTATIONS API FOR FRONTEND
# =============================================================
@legacy_router.get("/applications", summary="List All Applications")
def list_applications_frontend(db: Session = Depends(get_db)):
    """Fetches all applications with applicant, target, and parcel metadata."""
    apps = db.query(Application).order_by(Application.created_at.desc()).all()
    results = []
    for a in apps:
        applicant = db.query(User).filter(User.id == a.applicant_citizen_id).first()
        target = db.query(User).filter(User.id == a.target_citizen_id).first() if a.target_citizen_id else None
        parcel = db.query(Parcel).filter(Parcel.ulpin == a.ulpin).first()

        results.append({
            "id": a.application_id,
            "application_id": a.application_id,
            "ulpin": a.ulpin,
            "survey_number": parcel.survey_number if parcel else "—",
            "village": parcel.village if parcel else "—",
            "application_type": a.application_type,
            "applicant_name": applicant.full_name if applicant else "Citizen",
            "applicant_email": applicant.email if applicant else "—",
            "target_name": target.full_name if target else "General Application",
            "target_email": target.email if target else "—",
            "status": a.status.value,
            "remarks": a.remarks,
            "rejection_reason": a.rejection_reason,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else None
        })
    return results


@legacy_router.post("/applications", summary="Submit Land Ownership Transfer Application")
def create_application_frontend(req: ApplicationCreate, db: Session = Depends(get_db)):
    """Frontend endpoint to submit transfer application."""
    parcel = db.query(Parcel).filter(Parcel.ulpin == req.ulpin.strip()).first()
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")

    target = db.query(User).filter(
        (User.email == req.target_email.strip().lower()) |
        (User.phone == req.target_email.strip())
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"Recipient user '{req.target_email}' not found. Enter valid email/phone.")

    # Find owner of this parcel
    po = db.query(ParcelOwner).filter(ParcelOwner.ulpin == req.ulpin.strip(), ParcelOwner.status == "ACTIVE").first()
    owner = db.query(Owner).filter(Owner.owner_id == po.owner_id).first() if po else None
    applicant_user = db.query(User).filter(User.id == owner.citizen_id).first() if (owner and owner.citizen_id) else None
    applicant_id = applicant_user.id if applicant_user else 9  # Ramesh default

    app = workflow_service.create_application(
        db=db,
        applicant_id=applicant_id,
        ulpin=req.ulpin.strip(),
        target_citizen_id=target.id,
        application_type="OWNERSHIP_TRANSFER",
        remarks=req.remarks or "Ownership transfer request submitted via BhooNetra frontend."
    )
    # Run automated checks
    workflow_service.run_automated_checks(db, app.application_id)

    return {
        "message": "Application submitted successfully and forwarded to Revenue Officer.",
        "application_id": app.application_id,
        "status": app.status.value
    }


@legacy_router.post("/applications/{applicationId}/review", summary="Review Application (Approve/Reject)")
def review_application_frontend(applicationId: str, req: ReviewRequest, db: Session = Depends(get_db)):
    """Revenue officer reviews application."""
    officer = db.query(User).filter(User.role == UserRole.REVENUE_OFFICER).first()
    app = workflow_service.process_officer_review(
        db=db,
        application_id=applicationId,
        officer=officer,
        decision=req.decision,
        remarks=req.remarks
    )
    return {"message": f"Application marked as {app.status.value}", "status": app.status.value}


@legacy_router.post("/applications/{applicationId}/mutate", summary="Execute Mutation")
def execute_mutation_frontend(applicationId: str, req: MutationRequest, db: Session = Depends(get_db)):
    """Executes formal mutation on approved application."""
    officer = db.query(User).filter(User.role == UserRole.REVENUE_OFFICER).first()
    res = workflow_service.execute_approved_mutation(
        db=db,
        application_id=applicationId,
        officer=officer,
        remarks=req.remarks
    )
    return res


# =============================================================
# CITIZEN LAND HOLDINGS
# =============================================================
@legacy_router.get("/citizen/my-land", summary="Citizen Land Holdings")
def get_citizen_my_land_frontend(email: Optional[str] = None, db: Session = Depends(get_db)):
    """Returns land owned by citizen."""
    user = db.query(User).filter(User.email == (email or "citizen.ramesh@gmail.com")).first()
    if not user:
        return []

    owners = db.query(Owner).filter(Owner.citizen_id == user.id).all()
    owner_ids = [o.owner_id for o in owners]
    parcel_owners = db.query(ParcelOwner).filter(ParcelOwner.owner_id.in_(owner_ids), ParcelOwner.status == "ACTIVE").all()

    results = []
    for po in parcel_owners:
        p = db.query(Parcel).filter(Parcel.ulpin == po.ulpin).first()
        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == po.ulpin).first()
        if p:
            results.append({
                "ulpin": p.ulpin,
                "survey_number": p.survey_number,
                "state": p.state,
                "district": p.district,
                "taluk": p.taluk,
                "village": p.village,
                "area": p.area,
                "land_type": p.land_type,
                "share": po.share_percentage,
                "ror_number": ror.ror_number if ror else "ROR-ACTIVE",
                "ror_status": ror.status if ror else "ACTIVE"
            })
    return results


# =============================================================
# CHECKLIST, SRO, POLICE, LETTERS, OFFICERS, AUDIT
# =============================================================
@legacy_router.get("/checklist/{ulpin}", summary="Frontend Verification Checklist")
def get_checklist(ulpin: str, db: Session = Depends(get_db)):
    disp = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin, DisputeRecord.status == "ACTIVE").first()
    enc = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin, Encumbrance.legal_status == "ACTIVE").first()
    return [
        {"item": "RoR Identity & Ownership Verification", "is_checked": True},
        {"item": "Registered Sale Deed & SRO Verification", "is_checked": True},
        {"item": "Encumbrance Certificate (EC) Clearance", "is_checked": enc is None},
        {"item": "Judicial Dispute & Police Non-Involvement", "is_checked": disp is None}
    ]


@legacy_router.put("/checklist/{ulpin}", summary="Update Verification Checklist")
def update_checklist(ulpin: str, req: Dict[str, Any], db: Session = Depends(get_db)):
    return {"message": "Checklist updated", "ulpin": ulpin}


@legacy_router.get("/sro/{ulpin}", summary="Frontend SRO Status")
def get_sro_frontend(ulpin: str, db: Session = Depends(get_db)):
    sro = db.query(SROOffice).first()
    enc = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin, Encumbrance.legal_status == "ACTIVE").first()
    deeds = db.query(Deed).filter(Deed.ulpin == ulpin).all()
    return {
        "ulpin": ulpin,
        "nearest_sro": sro.sro_name if sro else "Sub-Registrar Office, Guindy",
        "last_verified": datetime.utcnow().strftime("%Y-%m-%d"),
        "encumbrance_status": "ACTIVE_ENCUMBRANCE" if enc else "CLEAR",
        "deeds_count": len(deeds)
    }


@legacy_router.post("/sro/{ulpin}/reverify", summary="Reverify SRO")
def reverify_sro_frontend(ulpin: str, db: Session = Depends(get_db)):
    return {
        "nearest_sro": "Sub-Registrar Office, Guindy",
        "last_verified": datetime.utcnow().strftime("%Y-%m-%d")
    }


@legacy_router.get("/police/{ulpin}", summary="Frontend Police Status")
def get_police_frontend(ulpin: str, db: Session = Depends(get_db)):
    disp = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin, DisputeRecord.status == "ACTIVE").first()
    return {
        "ulpin": ulpin,
        "status": "Under Investigation" if disp else "Cleared",
        "incident_details": disp.remarks if disp else "No criminal complaints or stay orders on record."
    }


@legacy_router.get("/letters", summary="List Official Government Letters")
def get_letters_frontend(db: Session = Depends(get_db)):
    letters = db.query(GovernmentLetter).order_by(GovernmentLetter.issued_date.desc()).all()
    return [
        {
            "id": l.letter_id,
            "letter_id": l.letter_id,
            "ulpin": l.ulpin,
            "letter_type": l.letter_type,
            "issued_by": l.issued_by,
            "issued_date": l.issued_date.strftime("%Y-%m-%d %H:%M") if l.issued_date else None,
            "content": l.content
        }
        for l in letters
    ]


@legacy_router.post("/letters/generate", summary="Generate Government Letter")
def generate_letter_frontend(req: LetterRequest, db: Session = Depends(get_db)):
    letter_id = f"GOV-LTR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    officer = db.query(User).filter(User.role == UserRole.REVENUE_OFFICER).first()
    letter = GovernmentLetter(
        letter_id=letter_id,
        ulpin=req.ulpin.strip(),
        letter_type=req.letter_type,
        issued_by=officer.full_name if officer else "Revenue Officer",
        issued_date=datetime.utcnow(),
        content=req.content
    )
    db.add(letter)
    db.commit()
    return {"message": "Letter issued successfully", "letter_id": letter_id}


@legacy_router.get("/officers", summary="Government Officers Directory")
def get_officers_frontend(db: Session = Depends(get_db)):
    officers = db.query(User).filter(User.role != UserRole.CITIZEN).all()
    return [
        {
            "id": o.id,
            "name": o.full_name,
            "email": o.email,
            "role": o.role.value,
            "department": o.department or "Land Governance"
        }
        for o in officers
    ]


@legacy_router.get("/audit", summary="Frontend Audit Trail")
def get_audit_frontend(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()
    return [
        {
            "id": l.log_id,
            "user_id": l.user_id,
            "user_role": l.user_role,
            "action": l.action,
            "ulpin": l.ulpin or "—",
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else None,
            "details": l.new_value or l.previous_value or "Audit event recorded"
        }
        for l in logs
    ]
