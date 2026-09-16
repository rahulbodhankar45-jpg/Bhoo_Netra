"""
Registration, SRO (Sub-Registrar Office), Deeds, Encumbrances, and Mortgages.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from app.core.database import Base, TimestampMixin


class SROOffice(Base):
    __tablename__ = "sro_offices"

    sro_code = Column(String(50), primary_key=True, index=True)  # e.g., 'SRO-TN-CHN-01'
    sro_name = Column(String(255), nullable=False)
    district = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    address = Column(String(255), nullable=True)
    contact_email = Column(String(100), nullable=True)
    jurisdiction_villages = Column(JSON, default=list)


class RegistrationRecord(Base, TimestampMixin):
    __tablename__ = "registration_records"

    registration_number = Column(String(50), primary_key=True, index=True)  # e.g., 'DOC/2026/0458'
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    sro_code = Column(String(50), ForeignKey("sro_offices.sro_code"), nullable=False)
    registration_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    deed_type = Column(String(50), nullable=False)  # Sale Deed, Gift Deed, Release Deed, Mortgage Deed
    market_value = Column(Float, nullable=False)
    consideration_amount = Column(Float, nullable=False)
    status = Column(String(20), default="REGISTERED")  # REGISTERED, PENDING, CANCELLED


class Deed(Base, TimestampMixin):
    __tablename__ = "deeds"

    deed_id = Column(String(50), primary_key=True, index=True)
    registration_number = Column(String(50), ForeignKey("registration_records.registration_number"), nullable=False)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    deed_type = Column(String(50), nullable=False)
    execution_date = Column(DateTime, default=datetime.utcnow)
    document_id = Column(String(50), nullable=True)  # Links to DocumentRecord
    parties = Column(JSON, default=list)  # [{"role": "SELLER", "name": "..."}, {"role": "BUYER", "name": "..."}]


class Encumbrance(Base, TimestampMixin):
    __tablename__ = "encumbrances"

    encumbrance_id = Column(String(50), primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    encumbrance_type = Column(String(50), nullable=False)  # MORTGAGE, COURT_ATTACHMENT, LEASE, CHARGE
    beneficiary = Column(String(255), nullable=False)  # Bank, Court, Individual
    amount = Column(Float, default=0.0)
    legal_status = Column(String(20), default="ACTIVE")  # NONE, ACTIVE, DISCHARGED
    recorded_date = Column(DateTime, default=datetime.utcnow)
    discharged_date = Column(DateTime, nullable=True)


class Mortgage(Base, TimestampMixin):
    __tablename__ = "mortgages"

    mortgage_id = Column(String(50), primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    bank_name = Column(String(255), nullable=False)
    loan_account_no = Column(String(50), nullable=False)
    mortgage_amount = Column(Float, nullable=False)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, DISCHARGED
    date_recorded = Column(DateTime, default=datetime.utcnow)
