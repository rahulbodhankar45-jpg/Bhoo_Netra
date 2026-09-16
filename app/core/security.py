"""
Security utilities: Password hashing, JWT token management, OTP generation, SHA-256 calculation, and PII masking.
"""
import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import bcrypt
from jose import JWTError, jwt
from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str, role: str, extra_claims: Optional[Dict[str, Any]] = None, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token containing subject and RBAC role."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a signed JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP for citizen login and officer MFA verification."""
    return "".join(random.choices(string.digits, k=length))


def calculate_sha256(data: bytes) -> str:
    """Compute SHA-256 hexadecimal hash for document integrity and tamper verification."""
    return hashlib.sha256(data).hexdigest()


def mask_name(name: str) -> str:
    """Mask citizen name for public privacy protection (e.g., 'Rahul Sharma' -> 'R*** S***')."""
    if not name:
        return "Anonymous"
    parts = name.strip().split()
    masked_parts = []
    for p in parts:
        if len(p) <= 2:
            masked_parts.append(p[0] + "*")
        else:
            masked_parts.append(p[0] + "***")
    return " ".join(masked_parts)


def mask_identifier(val: str) -> str:
    """Mask sensitive national ID / Aadhaar / Phone number."""
    if not val or len(val) < 4:
        return "****"
    return f"XXXX-XXXX-{val[-4:]}"
