"""
Ownership Service - Handles title records, owner relationships, and mutation updates.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.ownership import Owner, ParcelOwner, OwnershipHistory, MutationRecord
from app.models.ror import RoRRecord, RoRHistory
from app.models.users import User


class OwnershipService:
    """Manages ownership shares, title holders, and executes mutations."""

    @staticmethod
    def get_parcel_owners(db: Session, ulpin: str) -> List[Dict[str, Any]]:
        """Retrieve all active owners and share splits for a parcel."""
        links = db.query(ParcelOwner).filter(ParcelOwner.ulpin == ulpin, ParcelOwner.status == "ACTIVE").all()
        result = []
        for l in links:
            owner = db.query(Owner).filter(Owner.owner_id == l.owner_id).first()
            if owner:
                result.append({
                    "ownerId": owner.owner_id,
                    "citizenId": owner.citizen_id,
                    "name": owner.name,
                    "sharePercentage": l.share_percentage,
                    "acquisitionMode": l.acquisition_mode,
                    "status": l.status
                })
        return result

    @staticmethod
    def execute_mutation_and_transfer(
        db: Session,
        ulpin: str,
        new_owner_user: User,
        approved_by_officer: str,
        application_id: Optional[str] = None,
        remarks: Optional[str] = None
    ) -> MutationRecord:
        """
        Executes formal land mutation:
        1. Archives existing owner records in OwnershipHistory
        2. Links target citizen as new owner
        3. Generates unique Mutation Record
        4. Updates RoR timestamp and history
        """
        # 1. Fetch current owners
        current_links = db.query(ParcelOwner).filter(ParcelOwner.ulpin == ulpin, ParcelOwner.status == "ACTIVE").all()
        prev_owners_snapshot = []
        for l in current_links:
            o = db.query(Owner).filter(Owner.owner_id == l.owner_id).first()
            prev_owners_snapshot.append({
                "owner_id": l.owner_id,
                "name": o.name if o else "Unknown",
                "share": l.share_percentage
            })
            # Mark previous ownership as TRANSFERRED
            l.status = "TRANSFERRED"

        # 2. Check if new owner exists in Owner table or create
        existing_owner = db.query(Owner).filter(Owner.citizen_id == new_owner_user.id).first()
        if not existing_owner:
            owner_id = f"OWN-{new_owner_user.id:04d}"
            existing_owner = Owner(
                owner_id=owner_id,
                citizen_id=new_owner_user.id,
                name=new_owner_user.full_name,
                identity_type="AADHAAR",
                identity_hash=f"SHA256_{new_owner_user.email}"
            )
            db.add(existing_owner)
            db.flush()

        # 3. Add new parcel ownership link
        new_link = ParcelOwner(
            ulpin=ulpin,
            owner_id=existing_owner.owner_id,
            share_percentage=100.0,
            acquisition_mode="SALE_MUTATION",
            status="ACTIVE"
        )
        db.add(new_link)

        # 4. Generate unique mutation record
        mutation_id = f"MUT-{datetime.utcnow().year}-{datetime.utcnow().strftime('%m%d%H%M%S')}"
        mutation_number = f"MUT-REV-{datetime.utcnow().year}-{ulpin[-6:]}"
        mutation_record = MutationRecord(
            mutation_id=mutation_id,
            ulpin=ulpin,
            application_id=application_id,
            mutation_number=mutation_number,
            order_date=datetime.utcnow(),
            approved_by=approved_by_officer,
            remarks=remarks or f"Ownership transferred to {new_owner_user.full_name}"
        )
        db.add(mutation_record)

        # 5. Record Ownership History
        history = OwnershipHistory(
            ulpin=ulpin,
            previous_owners_json=prev_owners_snapshot,
            new_owners_json=[{"owner_id": existing_owner.owner_id, "name": new_owner_user.full_name, "share": 100.0}],
            mutation_id=mutation_id,
            changed_at=datetime.utcnow()
        )
        db.add(history)

        # 6. Update RoR record
        ror = db.query(RoRRecord).filter(RoRRecord.ulpin == ulpin).first()
        if ror:
            ror.last_updated = datetime.utcnow()
            ror_history = RoRHistory(
                ror_number=ror.ror_number,
                ulpin=ulpin,
                change_reason=f"Mutation {mutation_number} executed by {approved_by_officer}",
                snapshot={"mutation_id": mutation_id, "new_owner": new_owner_user.full_name},
                updated_by=approved_by_officer,
                timestamp=datetime.utcnow()
            )
            db.add(ror_history)

        db.commit()
        db.refresh(mutation_record)
        return mutation_record


ownership_service = OwnershipService()
