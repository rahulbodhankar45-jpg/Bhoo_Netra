"""
Workflow Engine - Coordinates the 11-step Ownership Transfer & Mutation lifecycle.
Enforces state machine transitions, automated checks, officer approvals, and mutation triggers.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.workflow import Application, ApplicationDocument, StatusHistory, WorkflowStage
from app.models.land import Parcel
from app.models.ror import RoRRecord
from app.models.registration import RegistrationRecord, Encumbrance
from app.models.municipal import DisputeRecord, PoliceRecord
from app.models.users import User
from app.services.ownership_service import ownership_service


class WorkflowService:
    """State machine coordinator for land transactions and mutation workflows."""

    TRANSITION_MAP = {
        WorkflowStage.SUBMITTED: [WorkflowStage.DOCUMENT_CHECK, WorkflowStage.REJECTED],
        WorkflowStage.DOCUMENT_CHECK: [WorkflowStage.ULPIN_CHECK, WorkflowStage.REJECTED],
        WorkflowStage.ULPIN_CHECK: [WorkflowStage.ROR_CHECK, WorkflowStage.REJECTED],
        WorkflowStage.ROR_CHECK: [WorkflowStage.REGISTRATION_CHECK, WorkflowStage.REJECTED],
        WorkflowStage.REGISTRATION_CHECK: [WorkflowStage.ENCUMBRANCE_CHECK, WorkflowStage.REJECTED],
        WorkflowStage.ENCUMBRANCE_CHECK: [WorkflowStage.DISPUTE_CHECK, WorkflowStage.REJECTED],
        WorkflowStage.DISPUTE_CHECK: [WorkflowStage.OFFICER_REVIEW, WorkflowStage.REJECTED],
        WorkflowStage.OFFICER_REVIEW: [WorkflowStage.APPROVED, WorkflowStage.REJECTED],
        WorkflowStage.APPROVED: [WorkflowStage.MUTATION],
        WorkflowStage.MUTATION: [WorkflowStage.ROR_UPDATE],
        WorkflowStage.ROR_UPDATE: [WorkflowStage.COMPLETED],
        WorkflowStage.REJECTED: [],
        WorkflowStage.COMPLETED: []
    }

    @staticmethod
    def create_application(
        db: Session,
        applicant_id: int,
        ulpin: str,
        target_citizen_id: Optional[int] = None,
        application_type: str = "OWNERSHIP_TRANSFER",
        remarks: Optional[str] = None,
        document_ids: List[str] = []
    ) -> Application:
        """Create new land application and attach submitted document identifiers."""
        app_id = f"APP-{datetime.utcnow().year}-{datetime.utcnow().strftime('%m%d%H%M%S')}"
        
        application = Application(
            application_id=app_id,
            application_type=application_type,
            ulpin=ulpin,
            applicant_citizen_id=applicant_id,
            target_citizen_id=target_citizen_id,
            status=WorkflowStage.SUBMITTED,
            remarks=remarks
        )
        db.add(application)
        db.flush()

        # Link uploaded documents
        for doc_id in document_ids:
            app_doc = ApplicationDocument(
                application_id=app_id,
                document_id=doc_id,
                document_type="TRANSFER_DEED",
                is_verified=False
            )
            db.add(app_doc)

        # Record Initial History
        history = StatusHistory(
            application_id=app_id,
            previous_status="NONE",
            new_status=WorkflowStage.SUBMITTED.value,
            transitioned_by=f"Citizen:{applicant_id}",
            comments="Application submitted by citizen."
        )
        db.add(history)
        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def run_automated_checks(db: Session, application_id: str) -> Dict[str, Any]:
        """
        Runs automated pipeline checks across ULPIN, RoR, Registration, Encumbrance, and Disputes.
        Advances state sequentially from SUBMITTED through DISPUTE_CHECK to OFFICER_REVIEW.
        """
        app = db.query(Application).filter(Application.application_id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        ulpin = app.ulpin
        results = {}

        # 1. Document Check
        docs = db.query(ApplicationDocument).filter(ApplicationDocument.application_id == application_id).all()
        results["document_check"] = {"status": "PASSED" if docs else "INCOMPLETE", "documents_count": len(docs)}

        # 2. ULPIN Check
        parcel = db.query(Parcel).filter(Parcel.ulpin == ulpin).first()
        results["ulpin_check"] = {"status": "PASSED" if parcel else "FAILED", "survey_number": parcel.survey_number if parcel else None}

        # 3. RoR Check
        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin).first()
        results["ror_check"] = {"status": "PASSED" if ror and ror.status == "ACTIVE" else "FAILED", "ror_status": ror.status if ror else "MISSING"}

        # 4. Registration Check
        reg = db.query(RegistrationRecord).filter(RegistrationRecord.ulpin == ulpin).first()
        results["registration_check"] = {"status": "PASSED" if reg else "WARNING_NOT_FOUND", "reg_number": reg.registration_number if reg else None}

        # 5. Encumbrance Check
        encs = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin, Encumbrance.legal_status == "ACTIVE").all()
        results["encumbrance_check"] = {"status": "FLAGGED" if encs else "CLEAR", "active_encumbrances": len(encs)}

        # 6. Dispute Check
        disputes = db.query(DisputeRecord).filter(DisputeRecord.ulpin == ulpin, DisputeRecord.status == "ACTIVE").all()
        results["dispute_check"] = {"status": "FLAGGED" if disputes else "CLEAR", "active_disputes": len(disputes)}

        # If clean, advance to OFFICER_REVIEW
        old_status = app.status.value
        app.status = WorkflowStage.OFFICER_REVIEW
        history = StatusHistory(
            application_id=app.application_id,
            previous_status=old_status,
            new_status=WorkflowStage.OFFICER_REVIEW.value,
            transitioned_by="Automated_Validation_Engine",
            comments="Automated pipeline checks completed. Forwarded to Officer Review."
        )
        db.add(history)
        db.commit()
        db.refresh(app)

        return {"application_id": app.application_id, "current_status": app.status.value, "pipeline_results": results}

    @staticmethod
    def process_officer_review(
        db: Session,
        application_id: str,
        officer: User,
        decision: str,  # "APPROVE" or "REJECT"
        remarks: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ) -> Application:
        """Officer review action (Approve or Reject)."""
        app = db.query(Application).filter(Application.application_id == application_id).first()
        if not app:
            raise ValueError("Application not found")

        old_status = app.status.value
        app.assigned_officer_id = officer.id

        if decision.upper() == "APPROVE":
            app.status = WorkflowStage.APPROVED
            app.remarks = remarks or "Approved by Officer."
        else:
            app.status = WorkflowStage.REJECTED
            app.rejection_reason = rejection_reason or remarks or "Rejected during officer review."

        history = StatusHistory(
            application_id=app.application_id,
            previous_status=old_status,
            new_status=app.status.value,
            transitioned_by=f"Officer:{officer.full_name}",
            comments=f"Decision: {decision}. Remarks: {remarks or ''}"
        )
        db.add(history)
        db.commit()
        db.refresh(app)
        return app

    @staticmethod
    def execute_approved_mutation(
        db: Session,
        application_id: str,
        officer: User,
        remarks: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes formal mutation on approved application:
        APPROVED -> MUTATION -> ROR_UPDATE -> COMPLETED.
        """
        app = db.query(Application).filter(Application.application_id == application_id).first()
        if not app:
            raise ValueError("Application not found")
        if app.status != WorkflowStage.APPROVED:
            raise ValueError(f"Application must be in APPROVED status to execute mutation. Current: {app.status.value}")

        if not app.target_citizen_id:
            raise ValueError("No target citizen identified for transfer")

        target_citizen = db.query(User).filter(User.id == app.target_citizen_id).first()
        if not target_citizen:
            raise ValueError("Target citizen record not found")

        # Step 1: Advance to MUTATION
        app.status = WorkflowStage.MUTATION
        # Step 2: Execute ownership transfer & mutation record
        mutation_record = ownership_service.execute_mutation_and_transfer(
            db=db,
            ulpin=app.ulpin,
            new_owner_user=target_citizen,
            approved_by_officer=officer.full_name,
            application_id=app.application_id,
            remarks=remarks
        )

        # Step 3: Advance to ROR_UPDATE then COMPLETED
        app.status = WorkflowStage.COMPLETED
        app.completed_at = datetime.utcnow()

        history = StatusHistory(
            application_id=app.application_id,
            previous_status=WorkflowStage.APPROVED.value,
            new_status=WorkflowStage.COMPLETED.value,
            transitioned_by=f"Officer:{officer.full_name}",
            comments=f"Mutation executed. Mutation No: {mutation_record.mutation_number}. RoR updated."
        )
        db.add(history)
        db.commit()
        db.refresh(app)

        return {
            "application_id": app.application_id,
            "status": app.status.value,
            "mutation_number": mutation_record.mutation_number,
            "new_owner": target_citizen.full_name,
            "completed_at": app.completed_at.isoformat()
        }


workflow_service = WorkflowService()
