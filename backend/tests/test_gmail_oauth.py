"""Tests for Gmail OAuth helpers (Phase 2)."""

from app.services.gmail_service.client import (
    generate_authorize_url,
    verify_and_consume_state,
)


def test_generate_authorize_url_returns_url_and_state():
    url, state = generate_authorize_url()
    assert url.startswith("https://accounts.google.com/o/oauth2/auth")
    assert "client_id=" in url
    assert "redirect_uri=" in url
    assert "scope=" in url
    assert "state=" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert isinstance(state, str) and len(state) > 0


def test_state_consumed_only_once():
    url, state = generate_authorize_url()
    assert verify_and_consume_state(state) is True
    assert verify_and_consume_state(state) is False  # already consumed


def test_unknown_state_is_invalid():
    assert verify_and_consume_state("never-issued-state") is False
