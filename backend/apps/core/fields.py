import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _fernet_key() -> bytes:
    raw = settings.FIELD_ENCRYPTION_KEY or settings.SECRET_KEY
    try:
        Fernet(raw.encode())
        return raw.encode()
    except (ValueError, TypeError):
        return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    return Fernet(_fernet_key())


class EncryptedTextField(models.TextField):
    """Transparently encrypts values at rest with Fernet (AES-128-CBC + HMAC)."""

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return get_fernet().encrypt(str(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return value

    def to_python(self, value):
        if value is None or value == "":
            return value
        if isinstance(value, str):
            try:
                return get_fernet().decrypt(value.encode()).decode()
            except (InvalidToken, ValueError):
                return value
        return value
