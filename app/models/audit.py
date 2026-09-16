"""
Immutable Audit Trail Models.
Stores tamper-evident append-only logs for all sensitive system events.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)  # User email/id or 'ANONYMOUS_PUBLIC'
    user_role = Column(String(50), nullable=False)            # Role at time of action
    action = Column(String(100), nullable=False, index=True)  # ULPIN_SEARCHED, DOCUMENT_VIEWED, etc.
    ulpin = Column(String(32), nullable=True, index=True)     # Target parcel
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    is_immutable = Column(Boolean, default=True, nullable=False)
