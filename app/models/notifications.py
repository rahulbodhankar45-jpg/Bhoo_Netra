"""Persistent in-app notification records."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import Base

class NotificationRecord(Base):
    __tablename__ = "notification_records"
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(80), unique=True, index=True, nullable=False)
    recipient = Column(String(255), index=True, nullable=False)
    event_type = Column(String(80), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="UNREAD")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
