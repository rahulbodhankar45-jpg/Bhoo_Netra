"""
Government Portal Router - Role-Based Access Control (RBAC) for Officers & Administrators.
Supports ULPIN Verification, Document Hash Auditing, SRO Registry, Mutation Approval, and Compliance Audit Trail.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.dependencies import (
    require_any_officer,
    require_revenue_officer,
    require_sro_officer,
    require_police_officer,
    require_auditor,
    get_client_ip
)
from app.models.users import User, UserRole
from app.models.land import Parcel
from app.models.ror import RoRRecord
from app.models.registration import RegistrationRecord, Encumbrance, Deed, Mortgage
from app.models.municipal import DisputeRecord, PoliceRecord, GovernmentLetter
from app.models.workflow import Application, WorkflowStage
from app.schemas.government import (
    ULPINVerificationResponse,
    DocumentVerificationRequest,
    SROStatusResponse,
    OfficerReviewRequest,
    MutationExecuteRequest,
    PoliceCheckResponse,
    DisputeResponse,
    LetterGenerateRequest,
    AuditLogResponse,
    AnalyticsDashboardResponse
)
from app.schemas.workflow import ApplicationResponse
from app.services.ulpin_service import ulpin_service
from app.services.parcel_service import parcel_service
from app.services.sro_service import sro_service
from app.services.workflow_service import workflow_service
from app.services.document_service import document_service
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service
from app.services.ai_service import ai_service

router = APIRouter(prefix="/government", tags=["Government Portal (RBAC)"])


@router.get("/verify/ulpin/{ulpin}", response_model=ULPINVerificationResponse, summary="Government 360° ULPIN Verification")
def verify_ulpin(
    ulpin: str,
    request: Request,
    officer: User = Depends(require_any_officer),
    db: Session = Depends(get_db)
):
    """Deep verification checking ULPIN format, RoR, SRO registry, active liens, court disputes, and police reports."""
    check = ulpin_service.verify_ulpin_in_db(db, ulpin)
    if not check["exists_in_database"]:
        return ULPINVerificationResponse(
            ulpin=ulpin,
            is_valid=check["format_valid"],
            exists=False,
            risk_level="CRITICAL"
        )

    parcel = parcel_service.get_by_ulpin(db, ulpin)
    ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin).first()
    reg = db.query(RegistrationRecord).filter(RegistrationRecord.ulpin == ulpin).first()
    encs = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin, Encumbrance.legal_status == "ACTIVE").all()
    disputes = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin, DisputeRecord.status == "ACTIVE").all()
    police = db.query(PoliceRecord).filter(PoliceRecord.ulpin == ulpin).first()

    risk_info = ai_service.calculate_risk_score(db, ulpin)

    audit_service.log_event(
        db=db,
        user_id=str(officer.id),
        user_role=officer.role.value,
        action="ULPIN_VERIFIED",
        ulpin=ulpin,
        ip_address=get_client_ip(request)
    )

    return ULPINVerificationResponse(
        ulpin=ulpin,
        is_valid=True,
        exists=True,
        parcel={
            "surveyNumber": parcel.survey_number,
            "state": parcel.state,
            "district": parcel.district,
            "taluk": parcel.taluk,
            "village": parcel.village,
            "area": parcel.area,
            "landType": parcel.land_type
        },
        ror={
            "rorNumber": ror.ror_number if ror else None,
            "status": ror.status if ror else "NOT_FOUND",
            "tenure": ror.tenure if ror else "Unknown"
        },
        sro_status=reg.status if reg else "UNREGISTERED",
        encumbrances_count=len(encs),
        disputes_count=len(disputes),
        police_status=police.clearance_status if police else "NOT_FILED",
        risk_level=risk_info["risk_tier"]
    )


@router.post("/verify/document/{documentId}", summary="Officer Document Verification")
def verify_document(
    documentId: str,
    req: DocumentVerificationRequest,
    request: Request,
    officer: User = Depends(require_any_officer),
    db: Session = Depends(get_db)
):
    """Officer marks document as cryptographically and legally verified."""
    doc = document_service.set_verification_status(
        db=db,
        document_id=documentId,
        status=req.decision,
        verified_by=officer.full_name
    )

    audit_service.log_event(
        db=db,
        user_id=str(officer.id),
        user_role=officer.role.value,
        action="DOCUMENT_VERIFIED",
        ulpin=doc.ulpin,
        ip_address=get_client_ip(request),
        new_value=f"Status: {doc.verification_status}, Remarks: {req.remarks or ''}"
    )

    return {
        "document_id": doc.document_id,
        "verification_status": doc.verification_status,
        "verified_by": doc.verified_by,
        "verified_at": doc.verified_at.isoformat()
    }


@router.get("/sro/status/{ulpin}", response_model=SROStatusResponse, summary="SRO Registration & Encumbrance Ledger")
def get_sro_status(
    ulpin: str,
    officer: User = Depends(require_sro_officer),
    db: Session = Depends(get_db)
):
    """SRO Officer inspects registration deeds, encumbrance certificates, and mortgages."""
    summary = sro_service.get_registration_summary(db, ulpin)
    deeds = sro_service.get_deeds_by_ulpin(db, ulpin)
    encs = sro_service.get_encumbrances_by_ulpin(db, ulpin)
    mortgages = sro_service.get_mortgages_by_ulpin(db, ulpin)

    return SROStatusResponse(
        ulpin=ulpin,
        registration_records=summary["registrations"],
        deeds=deeds,
        encumbrances=encs,
        mortgages=mortgages
    )


@router.post("/applications/{applicationId}/review", summary="Revenue Officer Application Review (Approve/Reject)")
def review_application(
    applicationId: str,
    req: OfficerReviewRequest,
    request: Request,
    officer: User = Depends(require_revenue_officer),
    db: Session = Depends(get_db)
):
    """Revenue Officer approves or rejects the ownership transfer application."""
    app = workflow_service.process_officer_review(
        db=db,
        application_id=applicationId,
        officer=officer,
        decision=req.decision,
        remarks=req.remarks,
        rejection_reason=req.rejection_reason
    )

    action_label = "OWNERSHIP_TRANSFER_APPROVED" if req.decision.upper() == "APPROVE" else "OWNERSHIP_TRANSFER_REJECTED"
    audit_service.log_event(
        db=db,
        user_id=str(officer.id),
        user_role=officer.role.value,
        action=action_label,
        ulpin=app.ulpin,
        ip_address=get_client_ip(request),
        new_value=f"Decision: {req.decision}, Remarks: {req.remarks or req.rejection_reason or ''}"
    )

    return {
        "application_id": app.application_id,
        "status": app.status.value,
        "reviewed_by": officer.full_name,
        "remarks": app.remarks or app.rejection_reason
    }


@router.post("/applications/{applicationId}/mutate", summary="Revenue Officer Execute Mutation")
def execute_mutation(
    applicationId: str,
    req: MutationExecuteRequest,
    request: Request,
    officer: User = Depends(require_revenue_officer),
    db: Session = Depends(get_db)
):
    """Executes official land record mutation on approved transfer application."""
    result = workflow_service.execute_approved_mutation(
        db=db,
        application_id=applicationId,
        officer=officer,
        remarks=req.remarks
    )

    audit_service.log_event(
        db=db,
        user_id=str(officer.id),
        user_role=officer.role.value,
        action="ROR_UPDATED",
        ulpin=result.get("ulpin"),
        ip_address=get_client_ip(request),
        new_value=f"Mutation No: {result['mutation_number']} to new owner {result['new_owner']}"
    )

    return result


@router.get("/police/check/{ulpin}", response_model=PoliceCheckResponse, summary="Police Record Verification")
def get_police_check(
    ulpin: str,
    officer: User = Depends(require_police_officer),
    db: Session = Depends(get_db)
):
    """Police Department verification check for criminal complaints, encroachment, or land mafia cases."""
    record = db.query(PoliceRecord).filter(PoliceRecord.ulpin == ulpin.strip()).first()
    if not record:
        return PoliceCheckResponse(
            ulpin=ulpin,
            incident_reported=False,
            incident_details=None,
            clearance_status="CLEARED",
            verified_by=officer.full_name,
            verification_date=datetime.utcnow()
        )

    return PoliceCheckResponse(
        ulpin=record.ulpin,
        incident_reported=record.incident_reported,
        incident_details=record.incident_details,
        clearance_status=record.clearance_status,
        verified_by=record.verified_by or officer.full_name,
        verification_date=record.verification_date
    )


@router.post("/letters/generate", summary="Issue Official Government Letter / Notice")
def generate_letter(
    req: LetterGenerateRequest,
    request: Request,
    officer: User = Depends(require_any_officer),
    db: Session = Depends(get_db)
):
    """Drafts and issues a formal government order, notice, or NOC."""
    letter_id = f"GOV-LTR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    letter = GovernmentLetter(
        letter_id=letter_id,
        ulpin=req.ulpin.strip(),
        application_id=req.application_id,
        letter_type=req.letter_type,
        issued_by=f"{officer.full_name} ({officer.department or officer.role.value})",
        issued_date=datetime.utcnow(),
        content=req.content
    )
    db.add(letter)
    db.commit()

    audit_service.log_event(
        db=db,
        user_id=str(officer.id),
        user_role=officer.role.value,
        action="LETTER_GENERATED",
        ulpin=req.ulpin,
        ip_address=get_client_ip(request),
        new_value=f"Type: {req.letter_type}, Letter ID: {letter_id}"
    )

    return {
        "letter_id": letter_id,
        "ulpin": letter.ulpin,
        "letter_type": letter.letter_type,
        "issued_by": letter.issued_by,
        "issued_date": letter.issued_date.isoformat()
    }


@router.get("/disputes/{ulpin}", response_model=DisputeResponse, summary="Court Disputes & Injunction Ledger")
def get_disputes(
    ulpin: str,
    officer: User = Depends(require_any_officer),
    db: Session = Depends(get_db)
):
    """Retrieve active and historical judicial disputes on land parcel."""
    disputes = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin.strip()).all()
    active_disputes = [d for d in disputes if d.status == "ACTIVE"]
    return DisputeResponse(
        ulpin=ulpin,
        has_active_disputes=len(active_disputes) > 0,
        disputes=[
            {
                "dispute_id": d.dispute_id,
                "court_name": d.court_name,
                "case_number": d.case_number,
                "dispute_type": d.dispute_type,
                "status": d.status,
                "injunction_granted": d.injunction_status,
                "remarks": d.remarks
            }
            for d in disputes
        ]
    )


@router.get("/audit-trail", response_model=List[AuditLogResponse], summary="Immutable Audit Trail (Auditor Role)")
def get_audit_trail(
    ulpin: Optional[str] = Query(None, description="Filter by ULPIN"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    limit: int = Query(100, le=500),
    offset: int = 0,
    officer: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    """Auditors inspect tamper-evident audit logs."""
    logs = audit_service.get_logs(db=db, ulpin=ulpin, action=action, limit=limit, offset=offset)
    return [
        AuditLogResponse(
            log_id=l.log_id,
            user_id=l.user_id,
            user_role=l.user_role,
            action=l.action,
            ulpin=l.ulpin,
            timestamp=l.timestamp,
            ip_address=l.ip_address,
            previous_value=l.previous_value,
            new_value=l.new_value
        )
        for l in logs
    ]


@router.get("/analytics/dashboard", response_model=AnalyticsDashboardResponse, summary="Government Executive Analytics")
def get_analytics(
    officer: User = Depends(require_any_officer),
    db: Session = Depends(get_db)
):
    """Executive KPI metrics across parcels, mutations, disputes, and geography."""
    total_parcels = db.query(func.count(Parcel.ulpin)).scalar() or 0
    total_area_sqm = db.query(func.sum(Parcel.area)).scalar() or 0.0
    active_apps = db.query(func.count(Application.application_id)).filter(
        Application.status.notin_([WorkflowStage.COMPLETED, WorkflowStage.REJECTED])
    ).scalar() or 0
    completed_mut = db.query(func.count(Application.application_id)).filter(
        Application.status == WorkflowStage.COMPLETED
    ).scalar() or 0
    active_disputes = db.query(func.count(DisputeRecord.dispute_id)).filter(
        DisputeRecord.status == "ACTIVE"
    ).scalar() or 0
    total_deeds = db.query(func.count(Deed.deed_id)).scalar() or 0

    # Group by state
    state_rows = db.query(Parcel.state, func.count(Parcel.ulpin)).group_by(Parcel.state).all()
    state_breakdown = {s: count for s, count in state_rows if s}

    # Group by land type
    type_rows = db.query(Parcel.land_type, func.count(Parcel.ulpin)).group_by(Parcel.land_type).all()
    type_breakdown = {t: count for t, count in type_rows if t}

    return AnalyticsDashboardResponse(
        total_parcels=total_parcels,
        total_area_hectares=round(total_area_sqm / 10000.0, 2),
        total_active_applications=active_apps,
        completed_mutations=completed_mut,
        active_disputes=active_disputes,
        total_registered_deeds=total_deeds,
        state_breakdown=state_breakdown,
        land_type_breakdown=type_breakdown
    )
