"""Public requests to contact a parcel owner about a potential purchase."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.core.database import Base, TimestampMixin


class PublicPurchaseRequest(Base, TimestampMixin):
    __tablename__ = "public_purchase_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), unique=True, index=True, nullable=False)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    owner_id = Column(String(50), ForeignKey("owners.owner_id"), index=True, nullable=True)
    requester_name = Column(String(255), nullable=False)
    requester_contact = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(30), default="PENDING")  # PENDING, VIEWED, RESPONDED, CLOSED
    owner_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
