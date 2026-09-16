"""
Tests for Document Service: File upload, SHA-256 calculation, and integrity checking.
"""
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_document_upload_and_integrity_check():
    # Citizen login
    req = client.post("/api/v1/auth/citizen/login", json={"phone_or_email": "9876543210"})
    otp = req.json()["demo_hint_otp"]
    token = client.post("/api/v1/auth/citizen/otp", json={"phone_or_email": "9876543210", "otp_code": otp}).json()["access_token"]

    sample_bytes = b"SAMPLE_DEED_DOCUMENT_CONTENT_FOR_HASH_VERIFICATION"
    file_payload = ("test_deed.pdf", io.BytesIO(sample_bytes), "application/pdf")

    res = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "ulpin": "IN-TN-CHN-000001234567",
            "document_type": "Sale Deed"
        },
        files={"file": file_payload}
    )
    assert res.status_code == 200
    doc_data = res.json()
    doc_id = doc_data["document_id"]
    assert len(doc_data["sha256_hash"]) == 64

    # Verify integrity
    verify_res = client.get(f"/api/v1/documents/{doc_id}/verify-integrity")
    assert verify_res.status_code == 200
    int_data = verify_res.json()
    assert int_data["is_tamper_free"] is True
    assert int_data["stored_hash"] == doc_data["sha256_hash"]
