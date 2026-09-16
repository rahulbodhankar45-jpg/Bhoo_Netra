"""
User, Authentication, Role, and Citizen Profile models.
"""
from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base, TimestampMixin


class UserRole(str, PyEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    STATE_ADMIN = "STATE_ADMIN"
    DISTRICT_OFFICER = "DISTRICT_OFFICER"
    REVENUE_OFFICER = "REVENUE_OFFICER"
    SRO_OFFICER = "SRO_OFFICER"
    PLANNING_OFFICER = "PLANNING_OFFICER"
    MUNICIPAL_OFFICER = "MUNICIPAL_OFFICER"
    POLICE_OFFICER = "POLICE_OFFICER"
    AUDITOR = "AUDITOR"
    CITIZEN = "CITIZEN"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CITIZEN, nullable=False, index=True)
    department = Column(String(100), nullable=True)  # e.g., 'Revenue', 'Registration/SRO', 'Town Planning', 'Police'
    state = Column(String(100), nullable=True)       # e.g., 'Tamil Nadu', 'Maharashtra'
    district = Column(String(100), nullable=True)    # e.g., 'Chennai', 'Pune'
    is_active = Column(Boolean, default=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(100), nullable=True)

    citizen_profile = relationship("CitizenProfile", back_populates="user", uselist=False)


class CitizenProfile(Base, TimestampMixin):
    __tablename__ = "citizen_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    aadhar_masked = Column(String(20), nullable=False)
    pan = Column(String(20), nullable=True)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    verified = Column(Boolean, default=True)

    user = relationship("User", back_populates="citizen_profile")


class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String(255), nullable=False, index=True)  # phone or email
    otp_code = Column(String(10), nullable=False)
    purpose = Column(String(50), default="LOGIN")  # 'LOGIN', 'MFA', 'TRANSFER_CONFIRMATION'
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
