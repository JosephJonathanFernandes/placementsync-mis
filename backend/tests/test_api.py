"""API-level tests: upload, extraction, approval workflow, stats, export."""

import os
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "sample_emails")


def _upload(client: TestClient, filename: str):
    with open(os.path.join(SAMPLES_DIR, filename), "rb") as f:
        return client.post(
            "/api/emails/upload",
            files={"file": (filename, f, "message/rfc822")},
        )


def _run_extraction(client: TestClient, email_id: int):
    return client.post(f"/api/extraction/run/{email_id}")


def _approve(client: TestClient, result_id: int, students, company: str):
    return client.post(
        f"/api/extraction/{result_id}/approve",
        json={
            "action": "approve",
            "edited_students": students,
            "edited_company": company,
        },
    )


def test_upload_eml(client: TestClient, clean_db):
    r = _upload(client, "selection_simple.eml")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email_id"] is not None
    assert body["subject"] == "Placement Selections - TechNova Solutions"

    # Re-uploading the same .eml is idempotent (content-hash dedupe)
    r2 = _upload(client, "selection_simple.eml")
    assert r2.status_code == 201
    assert r2.json()["email_id"] == body["email_id"]


def test_upload_rejects_non_eml(client: TestClient, clean_db):
    r = client.post(
        "/api/emails/upload",
        files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 400


def test_list_emails(client: TestClient, clean_db):
    _upload(client, "selection_simple.eml")
    r = client.get("/api/emails")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_extraction_run_and_pending(client: TestClient, clean_db):
    r = _upload(client, "shortlist_only.eml")
    email_id = r.json()["email_id"]

    r = _run_extraction(client, email_id)
    assert r.status_code in (200, 201), r.text
    res = r.json()
    assert res["review_status"] == "pending"
    assert res["company_name"] == "Alpha Systems"

    r = client.get("/api/extraction/pending")
    assert r.status_code == 200
    pending = r.json()
    assert len(pending) >= 1


def test_approve_creates_placement_record(client: TestClient, clean_db):
    _upload(client, "selection_simple.eml")
    r = _run_extraction(client, 1)
    res = r.json()
    result_id = res["id"]

    payload = {
        "action": "approve",
        "edited_students": res["extracted_students"],
        "edited_company": res["company_name"],
    }
    r = _approve(client, result_id, res["extracted_students"], res["company_name"])
    assert r.status_code == 200, r.text
    assert r.json()["review_status"] == "approved"

    r = client.get("/api/records")
    assert r.status_code == 200
    records = r.json()
    assert len(records) == 2
    companies = {rec["company_name"] for rec in records}
    assert companies == {"TechNova Solutions"}


def test_same_student_two_companies_supported(client: TestClient, clean_db):
    # Two emails selecting the same student at different companies
    _upload(client, "selection_simple.eml")  # Arjun Mehta at TechNova
    r = _run_extraction(client, 1)
    assert r.status_code in (200, 201)
    res1 = r.json()
    _approve(client, res1["id"], res1["extracted_students"], res1["company_name"])

    eml = b"""From: hr@other.edu
Subject: Selections - Other Corp

Name: Arjun Mehta
Reg No: 22CS014
Branch: CSE
Role: Developer
Package: 9 LPA
"""
    r = client.post(
        "/api/emails/upload",
        files={"file": ("other.eml", BytesIO(eml), "message/rfc822")},
    )
    assert r.status_code == 201
    other_email_id = r.json()["email_id"]

    r = _run_extraction(client, other_email_id)
    assert r.status_code in (200, 201)
    res = r.json()

    r = _approve(
        client,
        res["id"],
        [
            {
                "name": "Arjun Mehta",
                "registration_number": "22CS014",
                "branch": "CSE",
                "job_role": "Developer",
                "package": "9 LPA",
            }
        ],
        "Other Corp",
    )
    assert r.status_code == 200, r.text

    r = client.get("/api/records")
    records = r.json()
    arjun_records = [rec for rec in records if rec["student_name"] == "Arjun Mehta"]
    assert len(arjun_records) == 2  # same student, two companies


def test_shortlisting_cannot_be_approved(client: TestClient, clean_db):
    _upload(client, "shortlist_only.eml")
    r = _run_extraction(client, 1)
    res = r.json()
    assert res["raw_extraction"]["status"] == "Shortlisted"

    r = _approve(
        client,
        res["id"],
        [{"name": "Vikram Patel", "registration_number": "22CSE001"}],
        "Alpha Systems",
    )
    assert r.status_code == 400, r.text
    assert "shortlist" in r.json()["detail"].lower()


def test_reject_result(client: TestClient, clean_db):
    _upload(client, "selection_simple.eml")
    r = _run_extraction(client, 1)
    res = r.json()

    r = client.post(
        f"/api/extraction/{res['id']}/reject",
        json={"action": "reject"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["review_status"] == "rejected"


def test_stats_endpoint(client: TestClient, clean_db):
    _upload(client, "selection_simple.eml")
    r = _run_extraction(client, 1)
    res = r.json()

    _approve(client, res["id"], res["extracted_students"], res["company_name"])

    r = client.get("/api/records/stats")
    assert r.status_code == 200
    stats = r.json()
    assert stats["total_selected_students"] == 2
    assert stats["total_unique_placed_students"] == 2
    assert stats["total_companies"] == 1


def test_excel_export(client: TestClient, clean_db):
    _upload(client, "selection_simple.eml")
    r = _run_extraction(client, 1)
    res = r.json()

    _approve(client, res["id"], res["extracted_students"], res["company_name"])

    r = client.get("/api/excel/export")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats"
    )
    assert len(r.content) > 0
