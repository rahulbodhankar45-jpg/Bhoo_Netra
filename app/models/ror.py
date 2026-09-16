"""
Record of Rights (RoR) Models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from app.core.database import Base, TimestampMixin


class RoRRecord(Base, TimestampMixin):
    __tablename__ = "ror_records"

    ror_number = Column(String(50), primary_key=True, index=True)  # e.g., 'ROR-2026-00123'
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), unique=True, index=True, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, PENDING, DISPUTED, INACTIVE
    rights = Column(JSON, default=list, nullable=False)  # e.g., ["OWNERSHIP", "TRANSFER_RIGHTS", "MORTGAGE_RIGHTS"]
    tenure = Column(String(50), default="Freehold", nullable=False)  # Freehold, Leasehold, Government Grant
    restrictions = Column(String(255), default="NONE", nullable=False)  # NONE, NO_ALIENATION, TRIBAL_LAND, WAKF
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)


class RoRHistory(Base):
    __tablename__ = "ror_history"

    id = Column(Integer, primary_key=True, index=True)
    ror_number = Column(String(50), index=True, nullable=False)
    ulpin = Column(String(32), index=True, nullable=False)
    change_reason = Column(String(255), nullable=False)
    snapshot = Column(JSON, nullable=True)
    updated_by = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
