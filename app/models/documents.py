"""
Document Service models: Cryptographic document tracking, SHA-256 checksums, and verification state.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.core.database import Base, TimestampMixin


class DocumentRecord(Base, TimestampMixin):
    __tablename__ = "documents"

    document_id = Column(String(50), primary_key=True, index=True)  # e.g., 'DOC-2026-00456'
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    document_type = Column(String(50), nullable=False)  # RoR, Sale Deed, Encumbrance Certificate, Mutation Order, etc.
    file_name = Column(String(255), nullable=False)
    file_location = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    sha256_hash = Column(String(64), nullable=False, index=True)
    uploaded_by = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verification_status = Column(String(20), default="PENDING")  # PENDING, VERIFIED, REJECTED
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
