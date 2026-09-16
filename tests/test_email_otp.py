"""
Unit and Integration tests for Email Verification OTP system.
Ensures OTP is generated on backend, emailed to the user, not leaked to website,
and correctly verifies user before registration.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import get_db
from app.models.users import OTPVerification, User

client = TestClient(app)


def test_send_email_otp_new_user():
    test_email = "newcitizen.test@example.com"
    res = client.post("/api/auth/send-email-otp", json={"email": test_email, "purpose": "REGISTRATION"})
    assert res.status_code == 200
    data = res.json()
    assert "verification" in data["message"].lower() or "otp" in data["message"].lower()
    assert data["email"] == test_email
    assert "smtp_configured" in data
    assert "otp_code" not in data

    # Verify that OTP was saved in DB
    db: Session = next(get_db())
    try:
        otp_rec = db.query(OTPVerification).filter(
            OTPVerification.recipient == test_email,
            OTPVerification.purpose == "REGISTRATION",
            OTPVerification.is_used == False
        ).order_by(OTPVerification.id.desc()).first()
        assert otp_rec is not None
        assert len(otp_rec.otp_code) == 6
        assert otp_rec.otp_code.isdigit()
    finally:
        db.close()


def test_send_email_otp_already_registered():
    res = client.post("/api/auth/send-email-otp", json={
        "email": "citizen.ramesh@gmail.com",
        "purpose": "REGISTRATION"
    })
    assert res.status_code == 400
    assert "already registered" in res.json()["detail"].lower()


def test_verify_email_otp_lifecycle():
    test_email = "verify.lifecycle@example.com"
    # 1. Send OTP
    send_res = client.post("/api/auth/send-email-otp", json={"email": test_email, "purpose": "REGISTRATION"})
    assert send_res.status_code == 200

    # Retrieve generated OTP from DB
    db: Session = next(get_db())
    try:
        otp_rec = db.query(OTPVerification).filter(
            OTPVerification.recipient == test_email,
            OTPVerification.purpose == "REGISTRATION",
            OTPVerification.is_used == False
        ).order_by(OTPVerification.id.desc()).first()
        valid_otp = otp_rec.otp_code
    finally:
        db.close()

    # 2. Verify with wrong OTP
    wrong_res = client.post("/api/auth/verify-email-otp", json={
        "email": test_email,
        "otp_code": "000000",
        "purpose": "REGISTRATION"
    })
    assert wrong_res.status_code == 400
    assert "invalid" in wrong_res.json()["detail"].lower()

    # 3. Verify with correct OTP
    correct_res = client.post("/api/auth/verify-email-otp", json={
        "email": test_email,
        "otp_code": valid_otp,
        "purpose": "REGISTRATION"
    })
    assert correct_res.status_code == 200
    assert correct_res.json()["verified"] is True

    # 4. Complete Registration with verified OTP
    reg_res = client.post("/api/auth/register", json={
        "name": "Verified Citizen",
        "email": test_email,
        "password": "Password@123",
        "role": "citizen",
        "otp": valid_otp
    })
    assert reg_res.status_code == 200
    assert "registered successfully" in reg_res.json()["message"]

    # 5. User can now sign in
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "Password@123"
    })
    assert login_res.status_code == 200
    assert "token" in login_res.json()
