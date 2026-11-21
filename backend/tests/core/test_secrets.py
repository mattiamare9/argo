import pytest
from cryptography.fernet import Fernet

from app.core import secrets
from app.core.config import Settings


def settings(key: str | None) -> Settings:
    return Settings(database_url="x", secrets_key=key)


def test_encrypt_decrypt_roundtrip() -> None:
    s = settings(Fernet.generate_key().decode())
    token = secrets.encrypt(s, "tok-123")
    assert "tok-123" not in token
    assert secrets.decrypt(s, token) == "tok-123"


def test_missing_or_invalid_key_is_an_error() -> None:
    with pytest.raises(secrets.SecretsError):
        secrets.encrypt(settings(None), "x")
    with pytest.raises(secrets.SecretsError):
        secrets.encrypt(settings("non-una-chiave"), "x")


def test_wrong_key_cannot_decrypt() -> None:
    token = secrets.encrypt(settings(Fernet.generate_key().decode()), "x")
    with pytest.raises(secrets.SecretsError):
        secrets.decrypt(settings(Fernet.generate_key().decode()), token)
