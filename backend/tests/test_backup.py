"""Tests for the backup API (Phase 5)."""

import os


def test_backup_database(client, clean_db):
    """Database backup endpoint should return the SQLite file."""
    r = client.post("/api/backup/database")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/x-sqlite3"
    assert r.headers["content-disposition"]
    assert len(r.content) > 0


def test_backup_excel_when_missing(client, clean_db):
    """Excel backup should return 404 when no register exists."""
    import os
    # Ensure no Excel file exists from a previous test
    if os.path.exists("./.test_placement_register.xlsx"):
        os.remove("./.test_placement_register.xlsx")
    r = client.post("/api/backup/excel")
    assert r.status_code == 404


def test_backup_restore_returns_docs(client, clean_db):
    """Restore endpoint should return documentation."""
    r = client.post("/api/backup/restore")
    assert r.status_code == 200
    body = r.json()
    assert "steps" in body
    assert len(body["steps"]) > 0


def test_backup_database_filename(client, clean_db):
    """Backup database filename should contain a timestamp."""
    r = client.post("/api/backup/database")
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "placement_sync_backup_" in cd
    assert cd.endswith(".db\"")


def test_backup_excel_when_present(client, clean_db):
    """Excel backup should work when a register exists."""
    # First create an Excel register via export
    from io import BytesIO

    eml = b"""From: placement.coordinator@college.edu
Subject: Placement Selections - TechNova Solutions

Name: Arjun Mehta
Reg No: 22CS014
Branch: CSE
Role: Software Engineer
CTC: 12 LPA
"""
    r = client.post(
        "/api/emails/upload",
        files={"file": ("a.eml", BytesIO(eml), "message/rfc822")},
    )
    assert r.status_code == 201
    email_id = r.json()["email_id"]

    client.post(f"/api/extraction/run/{email_id}")
    client.post(
        f"/api/extraction/{1}/approve",
        json={
            "action": "approve",
            "edited_students": [
                {
                    "name": "Arjun Mehta",
                    "registration_number": "22CS014",
                    "branch": "CSE",
                    "job_role": "Software Engineer",
                    "package": "12 LPA",
                }
            ],
            "edited_company": "TechNova Solutions",
        },
    )

    # Export creates the Excel file
    client.get("/api/excel/export")

    # Now backup should work
    r = client.post("/api/backup/excel")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats"
    )
    assert len(r.content) > 0
