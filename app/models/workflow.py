"""
Workflow Engine Models: Applications, State Transitions, and Verification Pipelines.
"""
from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum
from app.core.database import Base, TimestampMixin


class WorkflowStage(str, PyEnum):
    SUBMITTED = "SUBMITTED"
    DOCUMENT_CHECK = "DOCUMENT_CHECK"
    ULPIN_CHECK = "ULPIN_CHECK"
    ROR_CHECK = "ROR_CHECK"
    REGISTRATION_CHECK = "REGISTRATION_CHECK"
    ENCUMBRANCE_CHECK = "ENCUMBRANCE_CHECK"
    DISPUTE_CHECK = "DISPUTE_CHECK"
    OFFICER_REVIEW = "OFFICER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MUTATION = "MUTATION"
    ROR_UPDATE = "ROR_UPDATE"
    COMPLETED = "COMPLETED"


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    application_id = Column(String(50), primary_key=True, index=True)  # e.g., 'APP-2026-00891'
    application_type = Column(String(50), default="OWNERSHIP_TRANSFER", nullable=False)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    applicant_citizen_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    target_citizen_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Buyer / Transferee
    status = Column(Enum(WorkflowStage), default=WorkflowStage.SUBMITTED, nullable=False, index=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    remarks = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class ApplicationDocument(Base, TimestampMixin):
    __tablename__ = "application_documents"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(String(50), ForeignKey("applications.application_id"), index=True, nullable=False)
    document_id = Column(String(50), nullable=False)
    document_type = Column(String(50), nullable=False)  # SALE_DEED, ROR_EXTRACT, AADHAAR, NOC
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)


class StatusHistory(Base):
    __tablename__ = "application_status_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(String(50), ForeignKey("applications.application_id"), index=True, nullable=False)
    previous_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)
    transitioned_by = Column(String(100), nullable=False)
    comments = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class CitizenRequest(Base, TimestampMixin):
    __tablename__ = "citizen_requests"

    request_id = Column(String(50), primary_key=True, index=True)  # e.g., 'REQ-2026-0045'
    citizen_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    request_type = Column(String(50), default="INFORMATION_REQUEST")  # INFORMATION_REQUEST, BOUNDARY_SURVEY, CERTIFICATE
    message = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, IN_PROGRESS, RESOLVED, REJECTED
    response = Column(Text, nullable=True)
