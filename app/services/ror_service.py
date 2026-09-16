"""
RoR Service - Record of Rights Management, Rights Tenure, and Ownership Share resolution.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.ror import RoRRecord, RoRHistory
from app.models.ownership import ParcelOwner, Owner


class RoRService:
    """Manages legal title rights, restrictions, and history."""

    @staticmethod
    def get_by_ulpin(db: Session, ulpin: str) -> Optional[Dict[str, Any]]:
        """Retrieve full RoR record with owner details for authorized parties."""
        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin.strip()).first()
        if not ror:
            return None

        parcel_owners = db.query(ParcelOwner).filter(ParcelOwner.ulpin == ulpin).all()
        owners_list = []
        for po in parcel_owners:
            owner = db.query(Owner).filter(Owner.owner_id == po.owner_id).first()
            if owner:
                owners_list.append({
                    "ownerId": owner.owner_id,
                    "name": owner.name,
                    "share": po.share_percentage,
                    "status": po.status,
                    "acquisitionMode": po.acquisition_mode
                })

        return {
            "ulpin": ror.ulpin,
            "rorNumber": ror.ror_number,
            "status": ror.status,
            "owners": owners_list,
            "rights": ror.rights or ["OWNERSHIP"],
            "tenure": ror.tenure,
            "restrictions": ror.restrictions,
            "lastUpdated": ror.last_updated.isoformat() if ror.last_updated else None
        }

    @staticmethod
    def update_ror_status(db: Session, ulpin: str, new_status: str, reason: str, officer_name: str) -> bool:
        """Update RoR status (e.g. to DISPUTED or ACTIVE) and record history."""
        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin.strip()).first()
        if not ror:
            return False

        old_status = ror.status
        ror.status = new_status
        ror.last_updated = datetime.utcnow()

        history = RoRHistory(
            ror_number=ror.ror_number,
            ulpin=ulpin,
            change_reason=f"Status changed from {old_status} to {new_status}: {reason}",
            snapshot={"previous_status": old_status, "new_status": new_status},
            updated_by=officer_name,
            timestamp=datetime.utcnow()
        )
        db.add(history)
        db.commit()
        return True


ror_service = RoRService()
