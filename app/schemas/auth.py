"""
Pydantic schemas for Authentication, Roles, and User Profiles.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.users import UserRole


class CitizenLoginRequest(BaseModel):
    phone_or_email: str


class CitizenOTPVerifyRequest(BaseModel):
    phone_or_email: str
    otp_code: str


class OfficerLoginRequest(BaseModel):
    email: EmailStr
    password: str


class OfficerMFAVerifyRequest(BaseModel):
    email: EmailStr
    mfa_code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    full_name: str
    email: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    phone: str
    full_name: str
    role: UserRole
    department: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    is_active: bool


class CitizenProfileOut(BaseModel):
    user_id: int
    full_name: str
    phone: str
    email: str
    aadhar_masked: str
    pan: Optional[str]
    address: str
    city: str
    state: str
    pincode: str
    verified: bool


class SendEmailOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "REGISTRATION"


class VerifyEmailOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str
    purpose: str = "REGISTRATION"
