"""
Aggregate models package for Land Stack India.
"""
from app.models.users import User, UserRole, CitizenProfile, OTPVerification
from app.models.land import Parcel, ULPINRegistry, ParcelBoundary, ParcelHistory
from app.models.ownership import Owner, ParcelOwner, OwnershipHistory, MutationRecord
from app.models.ror import RoRRecord, RoRHistory
from app.models.registration import SROOffice, RegistrationRecord, Deed, Encumbrance, Mortgage
from app.models.planning import LandUse, MasterPlan, BuildingPermission
from app.models.municipal import PropertyTax, UtilityConnection, DisputeRecord, PoliceRecord, GovernmentLetter
from app.models.workflow import WorkflowStage, Application, ApplicationDocument, StatusHistory, CitizenRequest
from app.models.documents import DocumentRecord
from app.models.audit import AuditLog
from app.models.public_purchase import PublicPurchaseRequest
from app.models.notifications import NotificationRecord

__all__ = [
    "User",
    "UserRole",
    "CitizenProfile",
    "OTPVerification",
    "Parcel",
    "ULPINRegistry",
    "ParcelBoundary",
    "ParcelHistory",
    "Owner",
    "ParcelOwner",
    "OwnershipHistory",
    "MutationRecord",
    "RoRRecord",
    "RoRHistory",
    "SROOffice",
    "RegistrationRecord",
    "Deed",
    "Encumbrance",
    "Mortgage",
    "LandUse",
    "MasterPlan",
    "BuildingPermission",
    "PropertyTax",
    "UtilityConnection",
    "DisputeRecord",
    "PoliceRecord",
    "GovernmentLetter",
    "WorkflowStage",
    "Application",
    "ApplicationDocument",
    "StatusHistory",
    "CitizenRequest",
    "DocumentRecord",
    "AuditLog",
    "PublicPurchaseRequest",
    "NotificationRecord"
]
