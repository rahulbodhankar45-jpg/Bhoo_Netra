"""
Registration / SRO Service - Deeds, Encumbrance Certificates, Mortgages, and SRO Office metadata.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.registration import RegistrationRecord, Deed, Encumbrance, Mortgage, SROOffice


class SROService:
    """Connects parcels to SRO registration databases and encumbrance tracking."""

    @staticmethod
    def get_registration_summary(db: Session, ulpin: str) -> Dict[str, Any]:
        """Aggregate registration records, encumbrances, and deeds for a parcel."""
        regs = db.query(RegistrationRecord).filter(RegistrationRecord.ulpin == ulpin.strip()).all()
        deeds = db.query(Deed).filter(Deed.ulpin == ulpin.strip()).all()
        encumbrances = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin.strip()).all()
        mortgages = db.query(Mortgage).filter(Mortgage.ulpin == ulpin.strip()).all()

        active_encumbrances = [e for e in encumbrances if e.legal_status == "ACTIVE"]

        return {
            "ulpin": ulpin,
            "registrationStatus": "REGISTERED" if regs else "NOT_REGISTERED",
            "hasEncumbrance": len(active_encumbrances) > 0,
            "totalRegistrations": len(regs),
            "registrations": [
                {
                    "registrationNumber": r.registration_number,
                    "sroCode": r.sro_code,
                    "deedType": r.deed_type,
                    "marketValue": r.market_value,
                    "considerationAmount": r.consideration_amount,
                    "registrationDate": r.registration_date.isoformat(),
                    "status": r.status
                }
                for r in regs
            ],
            "activeEncumbrances": [
                {
                    "encumbranceId": e.encumbrance_id,
                    "type": e.encumbrance_type,
                    "beneficiary": e.beneficiary,
                    "amount": e.amount,
                    "status": e.legal_status
                }
                for e in active_encumbrances
            ]
        }

    @staticmethod
    def get_deeds_by_ulpin(db: Session, ulpin: str) -> List[Dict[str, Any]]:
        """Fetch all registered sale deeds, gift deeds, and release deeds."""
        deeds = db.query(Deed).filter(Deed.ulpin == ulpin.strip()).all()
        return [
            {
                "deedId": d.deed_id,
                "registrationNumber": d.registration_number,
                "deedType": d.deed_type,
                "executionDate": d.execution_date.isoformat() if d.execution_date else None,
                "documentId": d.document_id,
                "parties": d.parties or []
            }
            for d in deeds
        ]

    @staticmethod
    def get_encumbrances_by_ulpin(db: Session, ulpin: str) -> List[Dict[str, Any]]:
        """Fetch Encumbrance Certificate (EC) items."""
        encs = db.query(Encumbrance).filter(Encumbrance.ulpin == ulpin.strip()).all()
        return [
            {
                "encumbranceId": e.encumbrance_id,
                "type": e.encumbrance_type,
                "beneficiary": e.beneficiary,
                "amount": e.amount,
                "status": e.legal_status,
                "recordedDate": e.recorded_date.isoformat() if e.recorded_date else None,
                "dischargedDate": e.discharged_date.isoformat() if e.discharged_date else None
            }
            for e in encs
        ]

    @staticmethod
    def get_mortgages_by_ulpin(db: Session, ulpin: str) -> List[Dict[str, Any]]:
        """Fetch bank liens and mortgage records."""
        mortgages = db.query(Mortgage).filter(Mortgage.ulpin == ulpin.strip()).all()
        return [
            {
                "mortgageId": m.mortgage_id,
                "bankName": m.bank_name,
                "loanAccountNo": m.loan_account_no,
                "mortgageAmount": m.mortgage_amount,
                "status": m.status,
                "dateRecorded": m.date_recorded.isoformat() if m.date_recorded else None
            }
            for m in mortgages
        ]

    @staticmethod
    def get_sro_office_status(db: Session, sro_code: str) -> Optional[Dict[str, Any]]:
        """Fetch status and jurisdiction of an SRO office."""
        sro = db.query(SROOffice).filter(SROOffice.sro_code == sro_code.strip()).first()
        if not sro:
            return None
        return {
            "sroCode": sro.sro_code,
            "sroName": sro.sro_name,
            "district": sro.district,
            "state": sro.state,
            "address": sro.address,
            "jurisdictionVillages": sro.jurisdiction_villages or [],
            "operationalStatus": "ONLINE"
        }


sro_service = SROService()
