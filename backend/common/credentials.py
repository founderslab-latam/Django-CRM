"""Symmetric encryption for third-party credentials stored in the database
(a customer's IMAP/SMTP password, for instance).

The key is `CREDENTIALS_ENCRYPTION_KEY` when set, otherwise one derived from
`SECRET_KEY`. Either way, changing it makes every stored credential
undecryptable: rotating `SECRET_KEY` without a dedicated key set means every
admin re-enters their mailbox passwords. Set the dedicated key in production
so the two can rotate independently.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CredentialError(Exception):
    pass


def _fernet() -> Fernet:
    key = getattr(settings, "CREDENTIALS_ENCRYPTION_KEY", "") or ""
    if not key:
        digest = hashlib.sha256(
            f"credentials:{settings.SECRET_KEY}".encode("utf-8")
        ).digest()
        key = base64.urlsafe_b64encode(digest).decode("ascii")
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise CredentialError(
            "Stored credential can't be decrypted (was the encryption key changed?)"
        ) from exc
