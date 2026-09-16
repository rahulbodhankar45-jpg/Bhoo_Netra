"""
Authentication Router: Citizen OTP login and Government Officer RBAC & MFA.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, generate_otp
from app.core.dependencies import get_client_ip
from app.models.users import User, UserRole, OTPVerification
from app.schemas.auth import (
    CitizenLoginRequest,
    CitizenOTPVerifyRequest,
    OfficerLoginRequest,
    OfficerMFAVerifyRequest,
    SendEmailOTPRequest,
    VerifyEmailOTPRequest,
    TokenResponse
)
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service
from app.services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.post("/citizen/login", summary="Request OTP for Citizen Login")
def citizen_login(req: CitizenLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Citizens authenticate passwordlessly using Phone or Email OTP."""
    identifier = req.phone_or_email.strip()
    user = db.query(User).filter(
        (User.phone == identifier) | (User.email == identifier)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citizen record not found with provided phone/email. Please register first."
        )

    # Invalidate prior OTPs
    db.query(OTPVerification).filter(
        OTPVerification.recipient == identifier,
        OTPVerification.is_used == False
    ).update({"is_used": True})

    otp = generate_otp(6)
    expires = datetime.utcnow() + timedelta(minutes=10)

    otp_rec = OTPVerification(
        recipient=identifier,
        otp_code=otp,
        purpose="LOGIN",
        expires_at=expires,
        is_used=False
    )
    db.add(otp_rec)
    db.commit()

    # Dispatch simulated SMS/Email notification
    notification_service.notify(
        event_type="CITIZEN_LOGIN_OTP",
        recipient=identifier,
        subject="Your Land Stack India Login OTP",
        message=f"Your OTP for Land Stack portal is {otp}. Valid for 10 minutes.",
        channel="SMS"
    )

    audit_service.log_event(
        db=db,
        user_id=str(user.id),
        user_role=user.role.value,
        action="CITIZEN_OTP_REQUESTED",
        ip_address=get_client_ip(request)
    )

    return {
        "message": f"OTP successfully dispatched to {identifier}",
        "expires_in_seconds": 600,
        "demo_hint_otp": otp  # Included for rapid hackathon testing/evaluation
    }


@router.post("/citizen/otp", response_model=TokenResponse, summary="Verify Citizen OTP & Issue JWT")
def citizen_verify_otp(req: CitizenOTPVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """Verifies OTP and returns role-scoped JWT."""
    identifier = req.phone_or_email.strip()
    otp_code = req.otp_code.strip()

    otp_rec = db.query(OTPVerification).filter(
        OTPVerification.recipient == identifier,
        OTPVerification.otp_code == otp_code,
        OTPVerification.is_used == False,
        OTPVerification.expires_at > datetime.utcnow()
    ).first()

    if not otp_rec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code."
        )

    otp_rec.is_used = True
    db.commit()

    user = db.query(User).filter(
        (User.phone == identifier) | (User.email == identifier)
    ).first()

    token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        extra_claims={"email": user.email, "full_name": user.full_name}
    )

    audit_service.log_event(
        db=db,
        user_id=str(user.id),
        user_role=user.role.value,
        action="CITIZEN_LOGIN_SUCCESS",
        ip_address=get_client_ip(request)
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email
    )


@router.post("/government/login", summary="Officer Credentials Verification")
def officer_login(req: OfficerLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Validates Government Officer email & password; initiates MFA step."""
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid officer credentials."
        )

    if user.role == UserRole.CITIZEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Citizen accounts cannot log into the Government Administration Portal."
        )

    # Generate MFA OTP for Government login
    mfa_code = generate_otp(6)
    expires = datetime.utcnow() + timedelta(minutes=5)
    otp_rec = OTPVerification(
        recipient=user.email,
        otp_code=mfa_code,
        purpose="GOV_MFA",
        expires_at=expires,
        is_used=False
    )
    db.add(otp_rec)
    db.commit()

    notification_service.notify(
        event_type="OFFICER_MFA_REQUEST",
        recipient=user.email,
        subject="Government Portal MFA Passcode",
        message=f"Your Government Land Stack MFA passcode is {mfa_code}",
        channel="EMAIL"
    )

    audit_service.log_event(
        db=db,
        user_id=str(user.id),
        user_role=user.role.value,
        action="GOVERNMENT_LOGIN_INITIATED",
        ip_address=get_client_ip(request)
    )

    return {
        "message": "Credentials verified. MFA verification required.",
        "mfa_required": True,
        "email": user.email,
        "role": user.role.value,
        "demo_hint_mfa": mfa_code
    }


@router.post("/government/mfa", response_model=TokenResponse, summary="Officer MFA Verification & Issue JWT")
def officer_verify_mfa(req: OfficerMFAVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """Verifies MFA passcode and issues role-based Government officer access token."""
    email = req.email.strip().lower()
    otp_rec = db.query(OTPVerification).filter(
        OTPVerification.recipient == email,
        OTPVerification.otp_code == req.mfa_code.strip(),
        OTPVerification.is_used == False,
        OTPVerification.expires_at > datetime.utcnow()
    ).first()

    if not otp_rec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired MFA passcode."
        )

    otp_rec.is_used = True
    db.commit()

    user = db.query(User).filter(User.email == email).first()

    token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        extra_claims={
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "state": user.state,
            "district": user.district
        }
    )

    audit_service.log_event(
        db=db,
        user_id=str(user.id),
        user_role=user.role.value,
        action="GOVERNMENT_LOGIN_SUCCESS",
        ip_address=get_client_ip(request)
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email
    )


@router.post("/send-email-otp", summary="Send Registration Verification OTP to Email")
def v1_send_email_otp(req: SendEmailOTPRequest, db: Session = Depends(get_db)):
    """Generates a secure 6-digit OTP and dispatches it directly to the user's email address."""
    email = req.email.strip().lower()

    # Check if already registered
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email address is already registered. Please login instead."
        )

    # Invalidate prior unused OTPs for this email and purpose
    db.query(OTPVerification).filter(
        OTPVerification.recipient == email,
        OTPVerification.purpose == req.purpose,
        OTPVerification.is_used == False
    ).update({"is_used": True})

    otp = generate_otp(6)
    expires = datetime.utcnow() + timedelta(minutes=10)

    otp_rec = OTPVerification(
        recipient=email,
        otp_code=otp,
        purpose=req.purpose,
        expires_at=expires,
        is_used=False
    )
    db.add(otp_rec)
    db.commit()

    # Send email
    sent, err_msg, is_live = email_service.send_registration_otp_email(to_email=email, otp_code=otp)
    if not sent and is_live:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SMTP Email Delivery Failed: {err_msg}. Please check your SMTP configuration."
        )

    if is_live:
        msg = f"Verification code has been dispatched to {email}. Please check your email inbox and spam folder."
        demo_otp = None
    else:
        msg = f"Verification OTP generated for {email}."
        demo_otp = otp

    return {
        "message": msg,
        "email": email,
        "smtp_configured": is_live,
        "demo_otp": demo_otp,
        "expires_in_seconds": 600
    }


@router.post("/verify-email-otp", summary="Verify Email Registration OTP")
def v1_verify_email_otp(req: VerifyEmailOTPRequest, db: Session = Depends(get_db)):
    """Verifies that the entered 6-digit OTP matches the one dispatched to the user's email."""
    email = req.email.strip().lower()
    otp_code = req.otp_code.strip()

    otp_rec = db.query(OTPVerification).filter(
        OTPVerification.recipient == email,
        OTPVerification.otp_code == otp_code,
        OTPVerification.purpose == req.purpose,
        OTPVerification.is_used == False,
        OTPVerification.expires_at > datetime.utcnow()
    ).first()

    if not otp_rec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code."
        )

    otp_rec.is_used = True
    db.commit()

    return {
        "verified": True,
        "message": "Email verified successfully!"
    }

