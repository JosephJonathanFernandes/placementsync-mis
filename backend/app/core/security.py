"""Encryption utilities for securely storing sensitive tokens at rest.

Derives a Fernet key from the application SECRET_KEY so that OAuth access/
refresh tokens are never stored in plaintext in the database.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key_material = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(key_material)
        _fernet = Fernet(key)
    return _fernet


def encrypt(value: str | None) -> str | None:
    """Encrypt a string value. Returns None for None input."""
    if value is None:
        return None
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str | None) -> str | None:
    """Decrypt a string value. Returns None for None input."""
    if value is None:
        return None
    return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
