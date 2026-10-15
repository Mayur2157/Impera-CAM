"""Carry a PDF password from the API to a worker without storing it.

The password travels only inside the queued task message, encrypted. Redis
runs with persistence off, so the ciphertext lives in memory until a worker
takes the task — never on disk, in MySQL or in a log (rules H10).
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .config import settings

# a fixed label keeps this key distinct from the JWT signing use of the secret
_CONTEXT = b"impera-cam/pdf-password/v1"


def _fernet() -> Fernet:
    key = hashlib.sha256(_CONTEXT + settings.jwt_secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def seal(password: str | None) -> str | None:
    if not password:
        return None
    return _fernet().encrypt(password.encode()).decode()


def unseal(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        # the JWT secret changed between enqueue and run
        raise RuntimeError("PDF password could not be decrypted; resubmit the file") from exc
