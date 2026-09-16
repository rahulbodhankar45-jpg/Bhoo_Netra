"""
Audit Service - Immutable, append-only security audit trail for all sensitive land actions.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


class AuditService:
    """Provides append-only compliance logging for all land stack operations."""

    @staticmethod
    def log_event(
        db: Session,
        user_id: str,
        user_role: str,
        action: str,
        ulpin: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        previous_value: Optional[str] = None,
        new_value: Optional[str] = None
    ) -> AuditLog:
        """Create an append-only audit log entry."""
        log_entry = AuditLog(
            user_id=str(user_id),
            user_role=user_role,
            action=action,
            ulpin=ulpin,
            timestamp=datetime.utcnow(),
            ip_address=ip_address or "127.0.0.1",
            user_agent=user_agent or "LandStack-Client",
            previous_value=previous_value,
            new_value=new_value,
            is_immutable=True
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def get_logs(
        db: Session,
        ulpin: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Query audit trail for authorized Auditors & Super Admins."""
        query = db.query(AuditLog)
        if ulpin:
            query = query.filter(AuditLog.ulpin == ulpin.strip())
        if action:
            query = query.filter(AuditLog.action == action.strip())
        return query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()


audit_service = AuditService()
