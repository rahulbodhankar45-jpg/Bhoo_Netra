"""
Document Management Router - Cryptographic File Upload and SHA-256 Tamper Checking.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_client_ip
from app.models.users import User
from app.schemas.document import DocumentUploadResponse, DocumentIntegrityCheck
from app.services.document_service import document_service
from app.services.audit_service import audit_service

router = APIRouter(prefix="/documents", tags=["Document Service"])


@router.post("/upload", response_model=DocumentUploadResponse, summary="Upload Land Document with SHA-256 Fingerprinting")
async def upload_document(
    request: Request,
    ulpin: str = Form(...),
    document_type: str = Form(..., description="RoR, Sale Deed, Mutation Order, Encumbrance Certificate, etc."),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uploads file to secure storage, calculates SHA-256 hash, and binds to ULPIN."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    doc = document_service.upload_document(
        db=db,
        ulpin=ulpin.strip(),
        document_type=document_type.strip(),
        file_name=file.filename or "document.pdf",
        file_content=content,
        uploaded_by=current_user.full_name
    )

    audit_service.log_event(
        db=db,
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        action="DOCUMENT_UPLOADED",
        ulpin=ulpin,
        ip_address=get_client_ip(request),
        new_value=f"DocID: {doc.document_id}, Type: {doc.document_type}, SHA256: {doc.sha256_hash}"
    )

    return DocumentUploadResponse(
        document_id=doc.document_id,
        ulpin=doc.ulpin,
        document_type=doc.document_type,
        file_name=doc.file_name,
        file_size=doc.file_size,
        sha256_hash=doc.sha256_hash,
        uploaded_at=doc.uploaded_at,
        verification_status=doc.verification_status
    )


@router.get("/{documentId}/verify-integrity", response_model=DocumentIntegrityCheck, summary="Cryptographic SHA-256 Tamper Check")
def verify_integrity(documentId: str, db: Session = Depends(get_db)):
    """Validates physical file contents against original registered cryptographic hash."""
    try:
        check = document_service.verify_integrity(db, documentId)
        return DocumentIntegrityCheck(
            document_id=check["document_id"],
            ulpin=check.get("ulpin", "UNKNOWN"),
            stored_hash=check["stored_hash"],
            calculated_hash=check["calculated_hash"],
            is_tamper_free=check["is_tamper_free"],
            status=check["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
