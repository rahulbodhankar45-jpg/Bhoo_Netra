"""
FastAPI Dependencies for Authentication, RBAC (Role-Based Access Control), and Audit Context.
"""
from typing import List, Optional
from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.users import User, UserRole

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Validate JWT token from Authorization header and return active user."""
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated.")
    return user


class RoleChecker:
    """Enforces Role-Based Access Control (RBAC) across government and citizen portals."""
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if UserRole.SUPER_ADMIN in [user.role]:
            return user  # Super Admin has universal access
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{user.role.value}' is not authorized for this operation. Required: {[r.value for r in self.allowed_roles]}"
            )
        return user


# Common role dependencies
require_citizen = RoleChecker([UserRole.CITIZEN])
require_super_admin = RoleChecker([UserRole.SUPER_ADMIN])
require_revenue_officer = RoleChecker([UserRole.REVENUE_OFFICER, UserRole.DISTRICT_OFFICER, UserRole.STATE_ADMIN])
require_sro_officer = RoleChecker([UserRole.SRO_OFFICER, UserRole.STATE_ADMIN])
require_planning_officer = RoleChecker([UserRole.PLANNING_OFFICER, UserRole.STATE_ADMIN])
require_municipal_officer = RoleChecker([UserRole.MUNICIPAL_OFFICER, UserRole.STATE_ADMIN])
require_police_officer = RoleChecker([UserRole.POLICE_OFFICER, UserRole.STATE_ADMIN])
require_auditor = RoleChecker([UserRole.AUDITOR, UserRole.SUPER_ADMIN])
require_any_officer = RoleChecker([
    UserRole.SUPER_ADMIN,
    UserRole.STATE_ADMIN,
    UserRole.DISTRICT_OFFICER,
    UserRole.REVENUE_OFFICER,
    UserRole.SRO_OFFICER,
    UserRole.PLANNING_OFFICER,
    UserRole.MUNICIPAL_OFFICER,
    UserRole.POLICE_OFFICER,
    UserRole.AUDITOR
])


def get_client_ip(request: Request) -> str:
    """Helper to extract client IP for audit logging."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
