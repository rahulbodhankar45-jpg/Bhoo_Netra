"""
Ownership, Land Title Holders, Parcel Ownership, and Mutation Records.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from app.core.database import Base, TimestampMixin


class Owner(Base, TimestampMixin):
    __tablename__ = "owners"

    owner_id = Column(String(50), primary_key=True, index=True)  # e.g. 'OWN-001'
    citizen_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    identity_type = Column(String(50), default="AADHAAR")  # AADHAAR, PAN, PASSPORT, CORP_ID
    identity_hash = Column(String(64), nullable=True)


class ParcelOwner(Base, TimestampMixin):
    __tablename__ = "parcel_owners"

    id = Column(Integer, primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    owner_id = Column(String(50), ForeignKey("owners.owner_id"), index=True, nullable=False)
    share_percentage = Column(Float, default=100.0, nullable=False)
    acquisition_mode = Column(String(50), default="PURCHASE")  # PURCHASE, INHERITANCE, GIFT, ALLOTMENT
    status = Column(String(20), default="ACTIVE")  # ACTIVE, TRANSFERRED, DISPUTED


class OwnershipHistory(Base):
    __tablename__ = "ownership_history"

    id = Column(Integer, primary_key=True, index=True)
    ulpin = Column(String(32), index=True, nullable=False)
    previous_owners_json = Column(JSON, nullable=False)
    new_owners_json = Column(JSON, nullable=False)
    mutation_id = Column(String(50), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)


class MutationRecord(Base, TimestampMixin):
    __tablename__ = "mutation_records"

    mutation_id = Column(String(50), primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    application_id = Column(String(50), index=True, nullable=True)
    mutation_number = Column(String(50), unique=True, nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(100), nullable=False)  # Officer username/name
    remarks = Column(String(500), nullable=True)
