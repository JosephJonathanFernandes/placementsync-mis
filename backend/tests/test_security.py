"""Tests for token encryption/decryption (Phase 2 security)."""

from app.core.security import decrypt, encrypt


def test_encrypt_decrypt_roundtrip():
    original = "ya29.a0AfH6SMC..."  # fake access token
    encrypted = encrypt(original)
    assert encrypted != original
    assert decrypt(encrypted) == original


def test_encrypt_none_is_none():
    assert encrypt(None) is None


def test_decrypt_none_is_none():
    assert decrypt(None) is None


def test_different_values_produce_different_ciphertext():
    assert encrypt("token-aaa") != encrypt("token-bbb")
