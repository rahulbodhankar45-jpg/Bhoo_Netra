"""
Pydantic schemas for Document Management and Integrity Verification.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    ulpin: str
    document_type: str
    file_name: str
    file_size: int
    sha256_hash: str
    uploaded_at: datetime
    verification_status: str


class DocumentDetail(BaseModel):
    document_id: str
    ulpin: str
    document_type: str
    file_name: str
    file_size: int
    sha256_hash: str
    uploaded_by: str
    uploaded_at: datetime
    verification_status: str
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None


class DocumentIntegrityCheck(BaseModel):
    document_id: str
    ulpin: str
    stored_hash: str
    calculated_hash: str
    is_tamper_free: bool
    status: str
