"""Tests for the Gmail automatic processing pipeline (Phase 2).

Uses a mocked Gmail API service so no real Google credentials are needed.
"""

import base64
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from app.services.gmail_service.processor import process_new_messages


def _make_eml_bytes(subject: str, body: str) -> bytes:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "placement.coordinator@college.edu"
    msg["To"] = "ps@college.edu"
    msg.set_content(body)
    return msg.as_bytes()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _mock_service(message_id: str, eml_bytes: bytes):
    """Build a mocked Gmail API service returning one raw message."""
    get_mock = MagicMock()
    get_mock.execute.return_value = {"raw": _b64url(eml_bytes)}

    list_mock = MagicMock()
    list_mock.execute.return_value = {
        "messages": [{"id": message_id, "threadId": "thread1"}]
    }

    messages_mock = MagicMock()
    messages_mock.get.return_value = get_mock
    messages_mock.list.return_value = list_mock

    users_mock = MagicMock()
    users_mock.messages.return_value = messages_mock

    service_mock = MagicMock()
    service_mock.users.return_value = users_mock
    return service_mock


@patch("app.services.gmail_service.processor.load_credentials")
@patch("app.services.gmail_service.processor.build_service")
def test_process_new_messages_stores_and_extracts(
    mock_build_service, mock_load_credentials, clean_db
):
    from google.oauth2.credentials import Credentials

    mock_load_credentials.return_value = Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="cid",
        client_secret="csecret",
    )

    eml = _make_eml_bytes(
        "Placement Selections - TechNova Solutions",
        "Name: Arjun Mehta\nReg No: 22CS014\nBranch: CSE\nRole: Software Engineer\nCTC: 12 LPA",
    )
    mock_build_service.return_value = _mock_service("gmail-msg-1", eml)

    summary = process_new_messages(
        user_id=1, query="selected", max_results=5
    )

    assert summary.fetched == 1
    assert summary.stored == 1
    assert summary.skipped_duplicate == 0
    assert summary.classified_selection == 1
    assert summary.created_review_results == 1
    assert summary.errors == 0


@patch("app.services.gmail_service.processor.load_credentials")
@patch("app.services.gmail_service.processor.build_service")
def test_process_skips_duplicate_messages(
    mock_build_service, mock_load_credentials, clean_db
):
    from google.oauth2.credentials import Credentials

    mock_load_credentials.return_value = Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="cid",
        client_secret="csecret",
    )

    eml = _make_eml_bytes(
        "Placement Selections - TechNova Solutions",
        "Name: Arjun Mehta\nReg No: 22CS014\nBranch: CSE\nRole: Software Engineer\nCTC: 12 LPA",
    )
    mock_build_service.return_value = _mock_service("gmail-msg-1", eml)

    # First run stores it
    summary1 = process_new_messages(user_id=1, query="selected", max_results=5)
    assert summary1.stored == 1

    # Second run skips it as duplicate
    summary2 = process_new_messages(user_id=1, query="selected", max_results=5)
    assert summary2.skipped_duplicate == 1
    assert summary2.stored == 0


@patch("app.services.gmail_service.processor.load_credentials")
@patch("app.services.gmail_service.processor.build_service")
def test_shortlist_email_not_extracted(
    mock_build_service, mock_load_credentials, clean_db
):
    from google.oauth2.credentials import Credentials

    mock_load_credentials.return_value = Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="cid",
        client_secret="csecret",
    )

    eml = _make_eml_bytes(
        "Shortlisted Candidates - Alpha Systems",
        "The following students have been shortlisted: Vikram Patel, Neha Agarwal.",
    )
    mock_build_service.return_value = _mock_service("gmail-msg-2", eml)

    summary = process_new_messages(user_id=1, query="shortlisted", max_results=5)

    assert summary.stored == 1
    assert summary.classified_selection == 0
    assert summary.created_review_results == 0


@patch("app.services.gmail_service.processor.load_credentials")
@patch("app.services.gmail_service.processor.build_service")
def test_process_with_user_id(
    mock_build_service, mock_load_credentials, clean_db
):
    """Test that user_id is properly passed to load_credentials."""
    from google.oauth2.credentials import Credentials

    mock_load_credentials.return_value = Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="cid",
        client_secret="csecret",
    )

    eml = _make_eml_bytes(
        "Placement Selections - TechNova Solutions",
        "Name: Arjun Mehta\nReg No: 22CS014\nBranch: CSE\nRole: Software Engineer\nCTC: 12 LPA",
    )
    mock_build_service.return_value = _mock_service("gmail-msg-1", eml)

    summary = process_new_messages(
        user_id=42, query="selected", max_results=5
    )

    # Verify load_credentials was called with user_id=42
    mock_load_credentials.assert_called_with(42)
    assert summary.stored == 1


@patch("app.services.gmail_service.processor.load_credentials")
def test_no_credentials_returns_empty_summary(mock_load_credentials, clean_db):
    mock_load_credentials.return_value = None

    summary = process_new_messages(user_id=1, query="selected", max_results=5)

    assert summary.fetched == 0
    assert summary.stored == 0
    assert summary.created_review_results == 0
