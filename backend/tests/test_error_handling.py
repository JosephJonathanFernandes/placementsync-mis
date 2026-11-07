"""Tests for error handling (Phase 5)."""


def test_404_on_nonexistent_email(client, clean_db):
    """Requesting a nonexistent email should return 404."""
    r = client.get("/api/emails/99999")
    assert r.status_code == 404


def test_404_on_nonexistent_extraction(client, clean_db):
    """Requesting a nonexistent extraction result should return 404."""
    r = client.get("/api/extraction/99999")
    assert r.status_code == 404


def test_404_on_nonexistent_record(client, clean_db):
    """Requesting a nonexistent placement record should return 404."""
    r = client.get("/api/records/99999")
    assert r.status_code == 404


def test_approve_nonexistent_extraction(client, clean_db):
    """Approving a nonexistent extraction result should return 404."""
    r = client.post(
        "/api/extraction/99999/approve",
        json={"action": "approve"},
    )
    assert r.status_code == 404


def test_reject_nonexistent_extraction(client, clean_db):
    """Rejecting a nonexistent extraction result should return 404."""
    r = client.post(
        "/api/extraction/99999/reject",
        json={"action": "reject"},
    )
    assert r.status_code == 404


def test_extraction_run_nonexistent_email(client, clean_db):
    """Running extraction on a nonexistent email should return 404."""
    r = client.post("/api/extraction/run/99999")
    assert r.status_code == 404


def test_gmail_without_credentials(client, clean_db):
    """Gmail endpoints should return 401 when no account is connected."""
    r = client.get("/api/gmail/messages")
    assert r.status_code == 401

    r = client.get("/api/gmail/labels")
    assert r.status_code == 401

    r = client.post("/api/gmail/process")
    assert r.status_code == 401


def test_health_endpoint(client, clean_db):
    """Health endpoint should return ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
