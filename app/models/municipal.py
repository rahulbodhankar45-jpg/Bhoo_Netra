"""
Municipal, Taxation, Utilities, Disputes, Police Records, and Government Notices.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from app.core.database import Base, TimestampMixin


class PropertyTax(Base, TimestampMixin):
    __tablename__ = "property_tax"

    assessment_no = Column(String(50), primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    annual_tax = Column(Float, nullable=False)
    paid_status = Column(String(20), default="PAID")  # PAID, DUE, OVERDUE
    last_paid_date = Column(DateTime, default=datetime.utcnow)
    due_amount = Column(Float, default=0.0)


class UtilityConnection(Base, TimestampMixin):
    __tablename__ = "utility_connections"

    connection_id = Column(String(50), primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    utility_type = Column(String(50), nullable=False)  # Water, Electricity, Sewerage, Gas, Telecom
    provider = Column(String(100), nullable=False)     # e.g., 'TANGEDCO', 'CMWSSB', 'MSEDCL'
    status = Column(String(20), default="CONNECTED")   # CONNECTED, DISCONNECTED, PENDING


class DisputeRecord(Base, TimestampMixin):
    __tablename__ = "dispute_records"

    dispute_id = Column(String(50), primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    court_name = Column(String(255), nullable=False)
    case_number = Column(String(100), nullable=False)
    dispute_type = Column(String(100), nullable=False)  # Title Dispute, Boundary Demarcation, Inheritance
    status = Column(String(20), default="ACTIVE")       # ACTIVE, RESOLVED, DISMISSED
    injunction_status = Column(Boolean, default=False)
    remarks = Column(Text, nullable=True)


class PoliceRecord(Base, TimestampMixin):
    __tablename__ = "police_records"

    record_id = Column(String(50), primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    incident_reported = Column(Boolean, default=False)
    incident_details = Column(Text, nullable=True)
    clearance_status = Column(String(50), default="CLEARED")  # CLEARED, UNDER_INVESTIGATION, ENCROACHMENT_REPORTED
    verified_by = Column(String(100), nullable=True)
    verification_date = Column(DateTime, default=datetime.utcnow)


class GovernmentLetter(Base, TimestampMixin):
    __tablename__ = "government_letters"

    letter_id = Column(String(50), primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    application_id = Column(String(50), index=True, nullable=True)
    letter_type = Column(String(50), nullable=False)  # NOTICE, MUTATION_ORDER, NOC, REJECTION_NOTICE
    issued_by = Column(String(100), nullable=False)   # Officer username/designation
    issued_date = Column(DateTime, default=datetime.utcnow)
    content = Column(Text, nullable=False)
