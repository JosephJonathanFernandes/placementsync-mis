"""Tests for error handling (Phase 5 + Phase 7 auth)."""


def test_404_on_nonexistent_email(client):
    """Requesting a nonexistent email should return 404."""
    r = client.get("/api/emails/99999")
    assert r.status_code == 404


def test_404_on_nonexistent_extraction(client):
    """Requesting a nonexistent extraction result should return 404."""
    r = client.get("/api/extraction/99999")
    assert r.status_code == 404


def test_404_on_nonexistent_record(client):
    """Requesting a nonexistent placement record should return 404."""
    r = client.get("/api/records/99999")
    assert r.status_code == 404


def test_approve_nonexistent_extraction(client):
    """Approving a nonexistent extraction result should return 404."""
    r = client.post(
        "/api/extraction/99999/approve",
        json={"action": "approve"},
    )
    assert r.status_code == 404


def test_reject_nonexistent_extraction(client):
    """Rejecting a nonexistent extraction result should return 404."""
    r = client.post(
        "/api/extraction/99999/reject",
        json={"action": "reject"},
    )
    assert r.status_code == 404


def test_extraction_run_nonexistent_email(client):
    """Running extraction on a nonexistent email should return 404."""
    r = client.post("/api/extraction/run/99999")
    assert r.status_code == 404


def test_gmail_without_credentials(client_no_auth):
    """Gmail endpoints should return 401 when no account is connected."""
    r = client_no_auth.get("/api/gmail/messages")
    assert r.status_code == 401

    r = client_no_auth.get("/api/gmail/labels")
    assert r.status_code == 401

    r = client_no_auth.post("/api/gmail/process")
    assert r.status_code == 401


def test_health_endpoint(client):
    """Health endpoint should return ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ("ok", "degraded")


def test_unauthenticated_requests_rejected(client_no_auth):
    """Unauthenticated requests to protected endpoints should return 401."""
    r = client_no_auth.get("/api/emails")
    assert r.status_code == 401

    r = client_no_auth.get("/api/records")
    assert r.status_code == 401

    r = client_no_auth.get("/api/records/stats")
    assert r.status_code == 401

    r = client_no_auth.get("/api/excel/export")
    assert r.status_code == 401

    r = client_no_auth.get("/api/audit")
    assert r.status_code == 401

    r = client_no_auth.post("/api/backup/database")
    assert r.status_code == 401
