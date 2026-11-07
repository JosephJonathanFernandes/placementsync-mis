"""Tests for the audit log API (Phase 5)."""

from app.models.audit_log import AuditLog
from app.services.gmail_service.client import GmailMessageSummary  # noqa: F401


def test_audit_log_endpoint_empty(client, clean_db):
    """Audit log list should return empty when no logs exist."""
    r = client.get("/api/audit")
    assert r.status_code == 200
    assert r.json() == []


def test_audit_log_summary_empty(client, clean_db):
    """Audit summary should return empty dict when no logs exist."""
    r = client.get("/api/audit/summary")
    assert r.status_code == 200
    assert r.json() == {}


def test_audit_log_written_on_approval(client, clean_db):
    """An audit log entry should be created when a placement record is approved."""
    from io import BytesIO

    # Upload and extract an email
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

    r = client.post(f"/api/extraction/run/{email_id}")
    assert r.status_code in (200, 201)
    res = r.json()

    r = client.post(
        f"/api/extraction/{res['id']}/approve",
        json={
            "action": "approve",
            "edited_students": res["extracted_students"],
            "edited_company": res["company_name"],
        },
    )
    assert r.status_code == 200

    # Check audit logs
    r = client.get("/api/audit")
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) >= 1
    approve_logs = [l for l in logs if l["action"] == "approve"]
    assert len(approve_logs) >= 1


def test_audit_log_filter_by_table(client, clean_db):
    """Audit log list should support filtering by table_name."""
    r = client.get("/api/audit?table_name=placement_records")
    assert r.status_code == 200


def test_audit_log_filter_by_action(client, clean_db):
    """Audit log list should support filtering by action."""
    r = client.get("/api/audit?action=approve")
    assert r.status_code == 200
