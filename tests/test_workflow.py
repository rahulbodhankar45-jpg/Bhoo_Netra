"""
End-to-end integration test: 11-step Ownership Transfer & Mutation State Machine.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(role="citizen"):
    if role == "citizen":
        req = client.post("/api/v1/auth/citizen/login", json={"phone_or_email": "9876543210"})
        otp = req.json()["demo_hint_otp"]
        return client.post("/api/v1/auth/citizen/otp", json={"phone_or_email": "9876543210", "otp_code": otp}).json()["access_token"]
    elif role == "revenue_officer":
        log = client.post("/api/v1/auth/government/login", json={"email": "revenue.officer@landstack.gov.in", "password": "Password@123"})
        mfa = log.json()["demo_hint_mfa"]
        return client.post("/api/v1/auth/government/mfa", json={"email": "revenue.officer@landstack.gov.in", "mfa_code": mfa}).json()["access_token"]


def test_end_to_end_ownership_transfer_workflow():
    citizen_token = get_token("citizen")
    officer_token = get_token("revenue_officer")
    ulpin = "IN-TN-CHN-000001234567"

    # 1. Citizen submits transfer to Priya Sundaram
    app_res = client.post(
        "/api/v1/citizen/applications",
        headers={"Authorization": f"Bearer {citizen_token}"},
        json={
            "ulpin": ulpin,
            "application_type": "OWNERSHIP_TRANSFER",
            "target_citizen_email": "citizen.priya@gmail.com",
            "remarks": "Sale deed executed. Requesting mutation.",
            "document_ids": ["DOC-2024-001"]
        }
    )
    assert app_res.status_code == 200
    app_data = app_res.json()
    app_id = app_data["application_id"]
    # Due to automated validation pipeline, status progresses to OFFICER_REVIEW
    assert app_data["status"] == "OFFICER_REVIEW"

    # 2. Revenue Officer reviews and approves
    review_res = client.post(
        f"/api/v1/government/applications/{app_id}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "decision": "APPROVE",
            "remarks": "All documents verified against SRO and RoR. Approved for mutation."
        }
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

    # 3. Revenue Officer executes mutation
    mutation_res = client.post(
        f"/api/v1/government/applications/{app_id}/mutate",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "remarks": "Formal mutation order passed."
        }
    )
    assert mutation_res.status_code == 200
    mut_data = mutation_res.json()
    assert mut_data["status"] == "COMPLETED"
    assert "MUT-" in mut_data["mutation_number"]
    assert mut_data["new_owner"] == "Priya Sundaram"
